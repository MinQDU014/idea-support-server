"""Run with AWS CLI in the classroom account. Never handles private keys."""
import argparse
import base64
import json
import subprocess
import shlex
import time
from pathlib import Path

ACCOUNT = '950177940921'
REGION = 'ap-southeast-2'
NAME = 'classroom-dev-compose'


def aws(service, operation, **kwargs):
    command = ['aws', service, operation, '--region', REGION, '--output', 'json', '--no-cli-pager']
    if kwargs:
        command += ['--cli-input-json', json.dumps(kwargs)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout or '{}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ssh-public-key', required=True)
    parser.add_argument('--management-cidr', required=True)
    args = parser.parse_args()
    if not args.ssh_public_key.startswith('ssh-rsa ') or not args.management_cidr.endswith('/32'):
        raise ValueError('An administrator public key and single-IP /32 are required')
    identity = aws('sts', 'get-caller-identity')
    if identity['Account'] != ACCOUNT:
        raise RuntimeError('Wrong AWS account; refusing to create resources')
    bundles = aws('lightsail', 'get-bundles')['bundles']
    choices = [b for b in bundles if b['isActive'] and b['ramSizeInGb'] == 8
               and 'LINUX_UNIX' in b['supportedPlatforms'] and 'ipv6' not in b['bundleId']
               and b['price'] <= 44]
    if not choices:
        raise RuntimeError('No expected public-IPv4 8GB Linux bundle at USD44 or less')
    bundle = min(choices, key=lambda b: b['price'])
    blueprints = aws('lightsail', 'get-blueprints')['blueprints']
    blueprint = next(b for b in blueprints if b['isActive'] and b['blueprintId'] == 'ubuntu_24_04')
    instances = aws('lightsail', 'get-instances')['instances']
    user_data = '''#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl python3
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
printf 'Types: deb\\nURIs: https://download.docker.com/linux/ubuntu\\nSuites: %s\\nComponents: stable\\nArchitectures: amd64\\nSigned-By: /etc/apt/keyrings/docker.asc\\n' "$VERSION_CODENAME" > /etc/apt/sources.list.d/docker.sources
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
install -d -m 0700 /opt/classroom-cd
touch /opt/classroom-cd/docker-ready
'''
    # Register the administrator's public key on the OS through first-boot setup.
    # No private key is sent to AWS, and no local AWS API credentials are required.
    key_setup = 'install -d -m 0700 -o ubuntu -g ubuntu /home/ubuntu/.ssh\n'
    key_setup += "printf '%s\\n' " + shlex.quote(args.ssh_public_key.strip()) + ' > /home/ubuntu/.ssh/authorized_keys\n'
    key_setup += 'chown ubuntu:ubuntu /home/ubuntu/.ssh/authorized_keys\nchmod 0600 /home/ubuntu/.ssh/authorized_keys\n'
    user_data = user_data.replace('export DEBIAN_FRONTEND=noninteractive\n', 'export DEBIAN_FRONTEND=noninteractive\n' + key_setup)
    if not any(i['name'] == NAME for i in instances):
        aws('lightsail', 'create-instances', instanceNames=[NAME], availabilityZone=REGION+'a',
            blueprintId=blueprint['blueprintId'], bundleId=bundle['bundleId'],
            userData=user_data, ipAddressType='ipv4',
            tags=[{'key': 'Environment', 'value': 'dev'}, {'key': 'Purpose', 'value': 'week11-team1-team8'}])
    static_name = NAME + '-ip'
    statics = aws('lightsail', 'get-static-ips')['staticIps']
    static = next((s for s in statics if s['name'] == static_name), None)
    if static is None:
        aws('lightsail', 'allocate-static-ip', staticIpName=static_name)
    # AWS provisioning is asynchronous. Emit progress without ever printing credentials.
    for _ in range(90):
        instance = aws('lightsail', 'get-instance', instanceName=NAME)['instance']
        if instance['state']['name'] == 'running':
            break
        print('Waiting for Lightsail VM:', instance['state']['name'], flush=True)
        time.sleep(10)
    else:
        raise RuntimeError('Lightsail VM did not become running in time')
    # Lightsail rejects firewall changes while an instance is pending.
    # Only the administrator gets SSH. Never expose MySQL or Docker API publicly.
    aws('lightsail', 'put-instance-public-ports', instanceName=NAME, portInfos=[
        {'fromPort': 22, 'toPort': 22, 'protocol': 'tcp', 'cidrs': [args.management_cidr]},
        {'fromPort': 80, 'toPort': 80, 'protocol': 'tcp', 'cidrs': ['0.0.0.0/0']},
        {'fromPort': 443, 'toPort': 443, 'protocol': 'tcp', 'cidrs': ['0.0.0.0/0']},
    ])
    static = aws('lightsail', 'get-static-ip', staticIpName=static_name)['staticIp']
    if static.get('attachedTo') not in (None, NAME):
        raise RuntimeError('Static IP belongs to another instance')
    if static.get('attachedTo') != NAME:
        aws('lightsail', 'attach-static-ip', staticIpName=static_name, instanceName=NAME)
    state = {'account': ACCOUNT, 'region': REGION, 'instance': NAME,
             'bundle': bundle['bundleId'], 'monthly_bundle_usd': bundle['price'],
             'ram_gb': 8, 'static_ip': static['ipAddress'], 'private_ip': instance['privateIpAddress']}
    Path('classroom-lightsail-state.json').write_text(json.dumps(state, indent=2)+'\n')
    print(json.dumps(state, indent=2), flush=True)


if __name__ == '__main__':
    main()
