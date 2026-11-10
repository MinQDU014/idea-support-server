"""One shared Registry and a read-only UI on a NEW Ubuntu EC2 host.

The first run binds HTTP to loopback only. Add --hostname later to enable
automatic HTTPS. Team names are namespaces, not access rules.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess

ROOT = Path('/opt/classroom-registry')


def write(path, text, mode=0o600):
    path.write_text(text)
    path.chmod(mode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hostname')
    parser.add_argument('--certificate', type=Path)
    parser.add_argument('--private-key', type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run as root on the new registry host')
    tls = bool(args.hostname)
    if tls and not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.-]*', args.hostname):
        parser.error('HTTPS requires a valid DNS name')
    if bool(args.certificate) != bool(args.private_key):
        parser.error('Supply both certificate and private key, or neither for automatic HTTPS')
    if args.certificate and (not args.certificate.is_file() or not args.private_key.is_file()):
        parser.error('Certificate files do not exist')
    subprocess.run(['docker', 'compose', 'version'], check=True)
    ROOT.mkdir(mode=0o700, exist_ok=True)
    (ROOT / 'auth').mkdir(mode=0o755, exist_ok=True)
    (ROOT / 'html').mkdir(mode=0o755, exist_ok=True)
    access_file = ROOT / 'team-access.json'
    access = json.loads(access_file.read_text()) if access_file.exists() else {}
    hashes = []
    for n in range(1, 9):
        team = f'team{n}'
        if team not in access:
            access[team] = {'username': team, 'password': secrets.token_urlsafe(32)}
            write(access_file, json.dumps(access, indent=2))
        auth_file = ROOT / 'auth' / f'{team}.htpasswd'
        if not auth_file.exists():
            result = subprocess.run(['htpasswd', '-niB', team], input=access[team]['password'] + '\n',
                                    text=True, capture_output=True, check=True)
            write(auth_file, result.stdout, 0o644)
        hashes.append(auth_file.read_text().strip())
    write(ROOT / 'auth' / 'all.htpasswd', '\n'.join(hashes) + '\n', 0o644)
    secret_file = ROOT / 'registry-secret'
    if not secret_file.exists():
        write(secret_file, secrets.token_hex(32))
    address = args.hostname if tls else 'http://:8080'
    config = '{\n  auto_https disable_redirects\n}\n' + address + ' {\n'
    if tls and args.certificate:
        config += '  tls /etc/registry-tls/fullchain.pem /etc/registry-tls/privkey.pem\n'
    elif tls:
        # TLS-ALPN-01 uses the already authorized HTTPS port; no public HTTP port.
        config += '  tls {\n    issuer acme {\n      disable_http_challenge\n    }\n  }\n'
    config += '  header Docker-Distribution-Api-Version "registry/2.0"\n'
    config += '  basic_auth bcrypt "Classroom dev registry" {\n'
    for line in hashes:
        username, password_hash = line.split(':', 1)
        config += f'    {username} {password_hash}\n'
    config += '''  }
  handle /v2/* {
    @blocked not method GET HEAD POST PATCH PUT
    respond @blocked 403
    reverse_proxy registry:5000 {
      header_up -Authorization
    }
  }
  handle {
    root * /srv
    try_files {path} /index.html
    file_server
  }
}
'''
    write(ROOT / 'Caddyfile', config)
    compose_file = ROOT / 'compose.json'
    previous = json.loads(compose_file.read_text()) if compose_file.exists() else {}
    images = {}
    for service, tag in [('registry', 'registry:3'), ('gateway', 'caddy:2-alpine')]:
        if previous and previous['services'][service]['image'].split('@')[0].split('/')[-1] == tag.split(':')[0]:
            images[service] = previous['services'][service]['image']
        else:
            subprocess.run(['docker', 'pull', tag], check=True)
            images[service] = subprocess.check_output(
                ['docker', 'image', 'inspect', '--format', '{{index .RepoDigests 0}}', tag], text=True).strip()
    logs = {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '2'}}
    volumes = ['./Caddyfile:/etc/caddy/Caddyfile:ro', './html:/srv:ro',
               '/data/caddy:/data', '/data/caddy-config:/config']
    if tls and args.certificate:
        volumes += [f'{args.certificate.resolve()}:/etc/registry-tls/fullchain.pem:ro',
                    f'{args.private_key.resolve()}:/etc/registry-tls/privkey.pem:ro']
    compose = {'services': {
        'registry': {'image': images['registry'], 'restart': 'unless-stopped', 'mem_limit': '256m',
                     'environment': {'REGISTRY_HTTP_SECRET': secret_file.read_text(),
                                     'REGISTRY_HTTP_RELATIVEURLS': 'true',
                                     'REGISTRY_STORAGE_DELETE_ENABLED': 'false',
                                     'OTEL_TRACES_EXPORTER': 'none'},
                     'volumes': ['/data/registry:/var/lib/registry'], 'logging': logs},
        'gateway': {'image': images['gateway'], 'restart': 'unless-stopped', 'mem_limit': '96m',
                    'environment': {'GOMEMLIMIT': '64MiB'},
                    'depends_on': ['registry'], 'volumes': volumes,
                    'ports': ['443:443'] if tls else ['127.0.0.1:8080:8080'], 'logging': logs},
    }}
    write(compose_file, json.dumps(compose, indent=2))
    shutil.copyfile(Path(__file__).parent / 'index.html', ROOT / 'html' / 'index.html')
    (ROOT / 'html' / 'index.html').chmod(0o644)
    subprocess.run(['docker', 'compose', '-f', str(compose_file), 'config', '-q'], check=True)
    subprocess.run(['docker', 'compose', '-f', str(compose_file), 'run', '--rm', '--no-deps',
                    'gateway', 'caddy', 'validate', '--config', '/etc/caddy/Caddyfile', '--adapter', 'caddyfile'], check=True)
    subprocess.run(['docker', 'compose', '-f', str(compose_file), 'up', '-d'], check=True)
    subprocess.run(['docker', 'compose', '-f', str(compose_file), 'exec', '-T', 'gateway',
                    'caddy', 'reload', '--config', '/etc/caddy/Caddyfile', '--adapter', 'caddyfile'], check=True)
    print('One Registry and UI installed. Namespaces team1..team8 share authenticated access.')
    print('Credentials saved in root-only team-access.json; no passwords printed.')
    print('Public HTTPS enabled.' if tls else 'Loopback only. Ready for DNS and a trusted TLS certificate.')


if __name__ == '__main__':
    main()
