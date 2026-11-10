"""Run as root after install-compose.py; preserves credentials and application data."""
import json
import os
import secrets
import shutil
import subprocess
from pathlib import Path

ROOT = Path('/opt/classroom-cd')
if os.geteuid() != 0:
    raise RuntimeError('Run using sudo')
HERE = Path(__file__).parent
tokens = ROOT/'deploy-tokens.json'
if not tokens.exists():
    tokens.write_text(json.dumps({t: secrets.token_urlsafe(48) for t in ['team']+['team'+str(i) for i in range(1,9)]}))
    tokens.chmod(0o600)
shutil.copyfile(HERE/'deploy-server.py', ROOT/'deploy-server.py')
(ROOT/'deploy-server.py').chmod(0o600)
unit = '''[Unit]
Description=Classroom team-scoped Compose deployment receiver
After=docker.service network-online.target
Requires=docker.service
[Service]
ExecStart=/usr/bin/python3 /opt/classroom-cd/deploy-server.py
Restart=on-failure
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/opt/classroom-cd /run/docker.sock
[Install]
WantedBy=multi-user.target
'''
# Docker login and CLI configuration remain available inside the hardened unit.
config = ROOT/'docker-client'
config.mkdir(mode=0o700, exist_ok=True)
shutil.copyfile('/root/.docker/config.json', config/'config.json')
(config/'config.json').chmod(0o600)
unit = unit.replace('UMask=0077', 'UMask=0077\nEnvironment=DOCKER_CONFIG=/opt/classroom-cd/docker-client')
Path('/etc/systemd/system/classroom-deploy.service').write_text(unit)
infra = json.loads((ROOT/'infra.json').read_text())
infra['services']['gateway']['extra_hosts'] = ['host.docker.internal:host-gateway']
# Receiver is loopback-only; a small host port-forward is restricted to the gateway bridge.
# Instead, gateway uses host networking so 127.0.0.1 stays on the host.
gateway = infra['services']['gateway']
gateway.pop('extra_hosts', None)
gateway.pop('ports', None)
gateway.pop('networks', None)
gateway['network_mode'] = 'host'
# Host-network gateway cannot use Docker DNS; apps receive loopback-only mapped ports.
for index, team in enumerate(['team']+['team'+str(i) for i in range(1,9)]):
    path = ROOT/team/'compose.json'
    app = json.loads(path.read_text())
    previous = json.dumps(app, sort_keys=True)
    app['services']['app']['ports'] = ['127.0.0.1:'+str(18080+index)+':8080']
    app['services']['app']['mem_limit'] = '768m'
    path.write_text(json.dumps(app, indent=2)+'\n')
    path.chmod(0o600)
    if previous != json.dumps(app, sort_keys=True):
        subprocess.run(['docker','compose','-p',team,'-f',str(path),'up','-d','--no-deps','app'],check=True)
    # Keep JVM starts sequential and leave a healthy service before moving on.
    import importlib.util
    spec = importlib.util.spec_from_file_location('receiver', ROOT/'deploy-server.py')
    receiver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(receiver)
    if not receiver.health(team):
        raise RuntimeError('Application did not recover: '+team)
    print(team+' updated and healthy', flush=True)
(ROOT/'infra.json').write_text(json.dumps(infra, indent=2)+'\n')
(ROOT/'infra.json').chmod(0o600)
caddy = (ROOT/'Caddyfile').read_text()
for index, team in enumerate(['team']+['team'+str(i) for i in range(1,9)]):
    caddy = caddy.replace('reverse_proxy '+team+'-app:8080', 'reverse_proxy 127.0.0.1:'+str(18080+index))
if 'handle /_cd/*' not in caddy:
    caddy = caddy.replace('    encode zstd gzip', '''    encode zstd gzip
    handle /_cd/* {
        request_body {
            max_size 2KB
        }
        reverse_proxy 127.0.0.1:9001 {
            transport http {
                response_header_timeout 40m
            }
        }
    }''')
(ROOT/'Caddyfile').write_text(caddy)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','classroom-deploy'],check=True)
subprocess.run(['docker','compose','-p','classroom-infra','-f',str(ROOT/'infra.json'),'up','-d','gateway'],check=True)
print('Authenticated team-scoped HTTPS deployment receiver ready; no tokens printed.')
