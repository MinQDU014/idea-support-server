"""Create a private logical-data/config backup without stopping the source VM.

Run again with writes paused immediately before cutover. This preparatory backup
does not make the destination authoritative, and never changes DNS or deletes a VM.
"""
import gzip
import hashlib
import json
import os
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path('/opt/classroom-cd')
TEAMS=['team']+['team'+str(i) for i in range(1,9)]
if os.geteuid()!=0:
    raise RuntimeError('Run using sudo')
os.umask(0o077)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
folder=ROOT/'migration'/stamp
folder.mkdir(parents=True,mode=0o700)
subprocess.run(['/usr/local/sbin/classroom-db-backup'],check=True,stdout=subprocess.DEVNULL)
backup=max((ROOT/'backups').glob('*.sql.gz'),key=lambda p:p.stat().st_mtime_ns)
with gzip.open(backup,'rt') as stream:
    sql=stream.read()
assert sql.count('CREATE DATABASE')==18,'Expected all 18 databases'
credentials=json.loads((ROOT/'credentials.json').read_text())
tokens=json.loads((ROOT/'deploy-tokens.json').read_text())
assert set(credentials['teams'])==set(TEAMS)==set(tokens)
files=['credentials.json','deploy-tokens.json','mysql-root','mysql-image.txt','gateway-image.txt',
       'infra.json','Caddyfile','deploy-server.py','registry-access.json','docker-client','caddy-data','caddy-config']
images={}
for team in TEAMS:
    for name in ['compose.json','.env.dev','deployment-result.json']:
        if (ROOT/team/name).exists(): files.append(team+'/'+name)
    images[team]=json.loads((ROOT/team/'compose.json').read_text())['services']['app']['image']
hashes={relative:hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
        for relative in files if (ROOT/relative).is_file()}
manifest={'created_utc':stamp,'source_region':'ap-southeast-2','destination_region':'ap-northeast-2',
          'team_count':8,'example_count':1,'database_count':18,'images':images,'file_sha256':hashes,
          'cutover_backup':False,'note':'Source is still live; refresh with writes paused before final cutover.'}
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=folder/'classroom-state.tar.gz'
with tarfile.open(archive,'w:gz') as output:
    for relative in files: output.add(ROOT/relative,arcname=relative)
    output.add(backup,arcname='migration-data.sql.gz')
    output.add(folder/'manifest.json',arcname='migration-manifest.json')
archive.chmod(0o600)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
result={'archive':str(archive),'sha256':digest,'compressed_bytes':archive.stat().st_size,
        'team_count':8,'example_count':1,'database_count':18,'source_still_live':True,
        'cutover_backup':False}
(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
