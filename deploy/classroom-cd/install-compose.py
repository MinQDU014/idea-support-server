"""Install shared MySQL and team applications on the classroom Lightsail VM."""
import argparse
import base64
import json
import os
import secrets
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path('/opt/classroom-cd')
TEAMS = ['team'] + ['team' + str(i) for i in range(1, 9)]
INITIAL_IMAGE = 'docker.minq.live/team/idea-support-server@sha256:a56a12ab1f4af0035f3bbe8646a2b9d6f5e0284a4526068a49199e8974bb0562'


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(content)
    path.chmod(0o600)


def compose(project, file, *args, **kwargs):
    return run(['docker', 'compose', '-p', project, '-f', str(file), *args], **kwargs)


def gateway_config(origin):
    host = origin.removeprefix('http://').removeprefix('https://').rstrip('/')
    site = host if origin.startswith('https://') else 'http://' + host
    lines = [site + ' {', '    encode zstd gzip']
    for index, team in enumerate(TEAMS):
        prefix = 'example' if team == 'team' else team
        lines += [f'    redir /{prefix} /{prefix}/ 308', f'    handle_path /{prefix}/* {{',
                  f'        reverse_proxy 127.0.0.1:{18080+index} {{',
                  f'            header_up X-Forwarded-Prefix /{prefix}', '        }', '    }']
    lines += ['    handle {', '        respond "CD classroom: /example/ and /team1/ through /team8/" 200', '    }', '}']
    return '\n'.join(lines) + '\n'


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run using sudo')
    parser = argparse.ArgumentParser()
    parser.add_argument('--registry-access-file', required=True)
    parser.add_argument('--origin', default='http://13.55.177.148')
    parser.add_argument('--private-ip', default='172.26.7.237')
    parser.add_argument('--configure-only', action='store_true')
    args = parser.parse_args()
    if not args.origin.startswith(('http://', 'https://')) or any(c.isspace() for c in args.origin):
        raise ValueError('A single HTTP(S) origin is required')
    ROOT.mkdir(exist_ok=True, parents=True, mode=0o700)
    ROOT.chmod(0o700)
    credential_path = ROOT / 'credentials.json'
    if credential_path.exists():
        credentials = json.loads(credential_path.read_text())
    else:
        credentials = {'mysql_root': secrets.token_hex(32), 'teams': {}}
        for team in TEAMS:
            credentials['teams'][team] = {'environments': {}}
            for env in ['dev', 'main']:
                credentials['teams'][team]['environments'][env] = {
                    'database': f'idea_{team}_{env}', 'username': f'{team}_{env}',
                    'password': secrets.token_hex(24),
                    'JWT_SECRET': base64.b64encode(secrets.token_bytes(48)).decode(),
                    'SHA_KEY': secrets.token_hex(32), 'AES_KEY': secrets.token_hex(16),
                }
        private_write(credential_path, json.dumps(credentials, indent=2)+'\n')
    private_write(ROOT / 'mysql-root', credentials['mysql_root']+'\n')
    access = json.loads(Path(args.registry_access_file).read_text())['team1']
    run(['docker', 'login', 'docker.minq.live', '--username', access['username'], '--password-stdin'],
        input=access['password']+'\n', capture_output=True)
    pinned = {}
    for name, image in [('mysql', 'mysql:8.4'), ('gateway', 'caddy:2-alpine')]:
        saved = ROOT / (name+'-image.txt')
        if saved.exists():
            pinned[name] = saved.read_text().strip()
        else:
            run(['docker', 'pull', image], stdout=subprocess.DEVNULL)
            digest = subprocess.check_output(['docker', 'image', 'inspect', image, '--format', '{{index .RepoDigests 0}}'], text=True).strip()
            private_write(saved, digest+'\n')
            pinned[name] = digest
    private_write(ROOT / 'Caddyfile', gateway_config(args.origin))
    infra = {'services': {
        'mysql': {'image': pinned['mysql'], 'restart': 'unless-stopped', 'mem_limit': '1g',
            'environment': {'MYSQL_ROOT_PASSWORD_FILE': '/run/secrets/mysql-root'},
            'command': ['--innodb-buffer-pool-size=268435456', '--max-connections=120', '--performance-schema=OFF'],
            'volumes': [str(ROOT/'mysql-data')+':/var/lib/mysql', str(ROOT/'mysql-root')+':/run/secrets/mysql-root:ro'],
            'ports': [args.private_ip+':3306:3306'], 'networks': ['data'],
            'healthcheck': {'test': ['CMD-SHELL', 'MYSQL_PWD=$$(cat /run/secrets/mysql-root) mysqladmin ping -h 127.0.0.1 -uroot --silent'],
                            'interval': '10s', 'timeout': '5s', 'retries': 30}},
        'gateway': {'image': pinned['gateway'], 'restart': 'unless-stopped', 'mem_limit': '128m',
            'network_mode': 'host',
            'volumes': [str(ROOT/'Caddyfile')+':/etc/caddy/Caddyfile:ro', str(ROOT/'caddy-data')+':/data', str(ROOT/'caddy-config')+':/config']},
    }, 'networks': {'data': {'name': 'classroom-data', 'internal': True}, 'web': {'name': 'classroom-web'}},
       'x-classroom': {'origin': args.origin, 'private_ip': args.private_ip}}
    infra_file = ROOT / 'infra.json'
    private_write(infra_file, json.dumps(infra, indent=2)+'\n')
    for index, team in enumerate(TEAMS):
        prefix = 'example' if team == 'team' else team
        cfg = credentials['teams'][team]['environments']['dev']
        env = {'DB_HOST': f"jdbc:mysql://mysql:3306/{cfg['database']}?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true",
               'DB_USERNAME': cfg['username'], 'DB_PASSWORD': cfg['password'],
               'JWT_SECRET': cfg['JWT_SECRET'], 'SHA_KEY': cfg['SHA_KEY'], 'AES_KEY': cfg['AES_KEY'],
               'SERVER_PUBLIC_URL': args.origin.rstrip('/')+'/'+prefix, 'SERVER_FORWARD_HEADERS_STRATEGY': 'framework',
               'CORS_ORIGINS': args.origin.rstrip('/')+',http://localhost:5173,http://localhost:3000,http://localhost:8081',
               'AI_MODE': 'mock', 'SPRING_DATASOURCE_HIKARI_MAXIMUM_POOL_SIZE': '3',
               'SPRING_DATASOURCE_HIKARI_MINIMUM_IDLE': '1', 'SERVER_TOMCAT_THREADS_MAX': '32',
               'JAVA_TOOL_OPTIONS': '-Xms64m -Xmx256m -XX:MaxMetaspaceSize=192m -XX:ReservedCodeCacheSize=64m -Xss512k'}
        config_path = ROOT / team / 'compose.json'
        previous = json.loads(config_path.read_text()) if config_path.exists() else None
        image = previous['services']['app']['image'] if previous else INITIAL_IMAGE
        app = {'services': {'app': {'image': image, 'restart': 'unless-stopped', 'mem_limit': '768m',
                 'ports': [f'127.0.0.1:{18080+index}:8080'],
                 'env_file': ['.env.dev'], 'networks': {'web': {'aliases': [team+'-app']}, 'data': {}},
                 'logging': {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}}}},
               'networks': {'web': {'external': True, 'name': 'classroom-web'}, 'data': {'external': True, 'name': 'classroom-data'}}}
        private_write(ROOT/team/'.env.dev', '\n'.join(key+'='+value for key, value in env.items())+'\n')
        private_write(config_path, json.dumps(app, indent=2)+'\n')
        compose(team, config_path, 'config', '--quiet')
    compose('classroom-infra', infra_file, 'config', '--quiet')
    if args.configure_only:
        return
    compose('classroom-infra', infra_file, 'up', '-d')
    for _ in range(60):
        ping = subprocess.run(['docker', 'compose', '-p', 'classroom-infra', '-f', str(infra_file), 'exec', '-T', 'mysql',
                              'sh', '-c', 'MYSQL_PWD=$(cat /run/secrets/mysql-root) mysqladmin ping -h127.0.0.1 -uroot --silent'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ping.returncode == 0:
            break
        time.sleep(5)
    else:
        raise RuntimeError('MySQL did not become ready')
    sql = []
    for team in TEAMS:
        for cfg in credentials['teams'][team]['environments'].values():
            sql += [f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
                    f"CREATE USER IF NOT EXISTS '{cfg['username']}'@'%' IDENTIFIED BY '{cfg['password']}';",
                    f"GRANT ALL PRIVILEGES ON `{cfg['database']}`.* TO '{cfg['username']}'@'%';"]
    compose('classroom-infra', infra_file, 'exec', '-T', 'mysql', 'sh', '-c',
            'MYSQL_PWD=$(cat /run/secrets/mysql-root) mysql -uroot', input='\n'.join(sql)+'\n', capture_output=True)
    # The public Lightsail firewall never exposes 3306. Limit the private host port too.
    rule = ['-i', 'ens5', '-p', 'tcp', '--dport', '3306', '!', '-s', '172.31.0.0/16', '-j', 'DROP']
    interface = subprocess.check_output(['sh', '-c', "ip route show default | awk '{print $5; exit}'"], text=True).strip()
    rule[1] = interface
    if subprocess.run(['iptables', '-C', 'DOCKER-USER', *rule], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        run(['iptables', '-I', 'DOCKER-USER', '1', *rule])
    results = []
    for team in TEAMS:
        compose(team, ROOT/team/'compose.json', 'up', '-d')
        prefix = 'example' if team == 'team' else team
        url = args.origin.rstrip('/')+'/'+prefix+'/common/health'
        for _ in range(90):
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(3)
        else:
            raise RuntimeError('Application health did not become ready: '+team)
        results.append({'team': team, 'health_url': url, 'status': 200})
        print(team+' health ready', flush=True)
    private_write(ROOT/'installation-result.json', json.dumps({'origin': args.origin, 'teams': results, 'database_count': len(TEAMS)*2}, indent=2)+'\n')
    print('Shared MySQL and classroom applications ready; no passwords printed.')


if __name__ == '__main__':
    main()
