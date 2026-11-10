"""Small authenticated deployment receiver; reachable only through the TLS gateway.

Each token controls one fixed Compose project, never arbitrary shell commands.
Images become digest-pinned before replacement. Failed health checks restore the
previous configuration. This is a classroom controller, not a tenant security boundary.
"""
import fcntl
import hmac
import json
import os
import re
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path('/opt/classroom-cd')
TEAMS = ['team'] + ['team'+str(i) for i in range(1, 9)]
SERIAL = threading.Lock()


def validate_image(team, image):
    if team not in TEAMS or not isinstance(image, str):
        raise ValueError('Unknown team or image')
    base = 'docker.minq.live/'+team+'/idea-support-server'
    if not re.fullmatch(re.escape(base)+r'(?:@sha256:[0-9a-f]{64}|:dev-[0-9a-f]{40})', image):
        raise ValueError('Use your own team image with a commit tag or digest')
    return image


def command(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=240)


def compose(team, *args):
    return command(['docker', 'compose', '-p', team, '-f', str(ROOT/team/'compose.json'), *args])


def health(team, attempts=70):
    prefix = 'example' if team == 'team' else team
    for _ in range(attempts):
        try:
            with urllib.request.urlopen('https://daelim.minq.live/'+prefix+'/common/health', timeout=4) as response:
                result = json.load(response)
                if response.status == 200 and result.get('status') == 'ok' and result.get('database') == 'up':
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False


def atomic_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2)+'\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def deploy(team, image, revision):
    validate_image(team, image)
    # Both thread and process locks cover manual invocations and concurrent teams.
    with SERIAL, (ROOT/'deploy.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        command(['docker', 'pull', image])
        digests = json.loads(command(['docker', 'image', 'inspect', image, '--format', '{{json .RepoDigests}}']))
        repository = image.split('@')[0].split(':')[0]
        pinned = next(d for d in digests if d.startswith(repository+'@sha256:'))
        path = ROOT/team/'compose.json'
        config = json.loads(path.read_text())
        previous = config['services']['app']['image']
        result = {'team': team, 'image': pinned, 'previous': previous, 'revision': revision, 'time': int(time.time())}
        if previous == pinned and health(team, attempts=1):
            result['status'] = 'unchanged'
        else:
            config['services']['app']['image'] = pinned
            atomic_json(path, config)
            try:
                compose(team, 'up', '-d', '--no-deps', 'app')
                if not health(team):
                    raise RuntimeError('New application health check failed')
                result['status'] = 'deployed'
            except Exception:
                config['services']['app']['image'] = previous
                atomic_json(path, config)
                try:
                    compose(team, 'up', '-d', '--no-deps', 'app')
                    result['rollback_healthy'] = health(team)
                except Exception:
                    result['rollback_healthy'] = False
                result['status'] = 'rolled_back'
        atomic_json(ROOT/team/'deployment-result.json', result)
        return result


class Handler(BaseHTTPRequestHandler):
    server_version = 'ClassroomCD'

    def log_message(self, format, *args):
        # Never log headers, tokens, request bodies or registry credentials.
        pass

    def reply(self, status, result):
        body = json.dumps(result).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def authenticate(self):
        match = re.fullmatch(r'/_cd/(team[1-8]?)', self.path)
        if not match:
            self.reply(404, {'error': 'Not found'})
            return None
        team = match.group(1)
        tokens = json.loads((ROOT/'deploy-tokens.json').read_text())
        supplied = self.headers.get('Authorization', '')
        if not hmac.compare_digest(supplied, 'Bearer '+tokens[team]):
            self.reply(401, {'error': 'Unauthorized'})
            return None
        return team

    def do_GET(self):
        team = self.authenticate()
        if team:
            path = ROOT/team/'deployment-result.json'
            self.reply(200, json.loads(path.read_text()) if path.exists() else {'team': team, 'status': 'initial-example'})

    def do_POST(self):
        self.connection.settimeout(15)
        team = self.authenticate()
        if not team:
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2048:
                raise ValueError('Invalid body length')
            payload = json.loads(self.rfile.read(length))
            image = validate_image(team, payload['image'])
            revision = payload.get('revision', '')
            if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision):
                raise ValueError('A full Git revision is required')
        except (ValueError, KeyError, TypeError):
            self.reply(400, {'error': 'Invalid image or revision'})
            return
        # Wait in a bounded queue; avoid simultaneous pulls and JVM starts on 8GB.
        if not self.server.slots.acquire(blocking=False):
            self.reply(429, {'error': 'Deployment queue full; retry later'})
            return
        try:
            result = deploy(team, image, revision)
            self.reply(200 if result['status'] in ('deployed', 'unchanged') else 502, result)
        except Exception:
            self.reply(502, {'team': team, 'error': 'Deployment failed; consult administrator logs'})
        finally:
            self.server.slots.release()


if __name__ == '__main__':
    os.umask(0o077)
    server = ThreadingHTTPServer(('127.0.0.1', 9001), Handler)
    server.slots = threading.BoundedSemaphore(10)
    server.serve_forever()
