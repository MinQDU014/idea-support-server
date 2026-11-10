"""Verify local backup integrity and maintenance services without printing SQL."""
import gzip
import json
import subprocess
from pathlib import Path

root=Path('/opt/classroom-cd')
backups=sorted((root/'backups').glob('*.sql.gz'))
assert backups,'No valid backup found'
latest=backups[-1]
with gzip.open(latest,'rt') as stream:
    sql=stream.read()
database_count=sql.count('CREATE DATABASE')
assert database_count==18, 'Expected all 18 classroom databases'
services={name:subprocess.check_output(['systemctl','is-active',name],text=True).strip()
          for name in ['classroom-deploy','classroom-db-firewall','classroom-db-backup.timer']}
assert all(value=='active' for value in services.values())
print(json.dumps({'backup':{'filename':latest.name,'compressed_bytes':latest.stat().st_size,
    'gzip_integrity':True,'database_count':database_count,'restoration_tested':False,
    'location':'same VM; off-server recovery is separate'},'services':services},indent=2))
