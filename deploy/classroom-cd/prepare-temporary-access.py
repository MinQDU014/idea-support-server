"""In the classroom CloudShell, prepare short-lived SSH access without printing keys."""
import json
import subprocess
import zipfile
from pathlib import Path

identity = json.loads(subprocess.check_output(['aws', 'sts', 'get-caller-identity', '--output', 'json']))
assert identity['Account'] == '950177940921', 'Wrong AWS account'
details = json.loads(subprocess.check_output([
    'aws', 'lightsail', 'get-instance-access-details', '--instance-name', 'classroom-dev-compose',
    '--region', 'ap-southeast-2', '--output', 'json', '--no-cli-pager',
]))['accessDetails']
output = Path('/tmp/classroom-cd-temporary-access.zip')
with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('tempkey', details['privateKey'])
    archive.writestr('tempkey-cert.pub', details['certKey'])
    archive.writestr('connection.json', json.dumps({k: details.get(k) for k in ['username', 'ipAddress', 'expiresAt', 'hostKeys']}))
output.chmod(0o600)
print('Prepared short-lived access file:', str(output))
print('Keys are not printed. Use both private key and certificate from the allowed administrator IP.')
