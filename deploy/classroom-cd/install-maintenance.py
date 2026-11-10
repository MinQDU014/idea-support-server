"""Persistent private DB firewall and local daily backup; run as root."""
import os
import subprocess
from pathlib import Path

if os.geteuid()!=0:
    raise RuntimeError('Run using sudo')
firewall = '''#!/bin/sh
set -eu
iface=$(ip route show default | awk '{print $5; exit}')
iptables -C DOCKER-USER -i "$iface" -p tcp --dport 3306 ! -s 172.31.0.0/16 -j DROP 2>/dev/null || iptables -I DOCKER-USER 1 -i "$iface" -p tcp --dport 3306 ! -s 172.31.0.0/16 -j DROP
'''
path=Path('/usr/local/sbin/classroom-db-firewall')
path.write_text(firewall)
path.chmod(0o700)
Path('/etc/systemd/system/classroom-db-firewall.service').write_text('''[Unit]
Description=Restrict the shared MySQL private port
After=docker.service network-online.target
Requires=docker.service
PartOf=docker.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/classroom-db-firewall
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
''')
backup = '''#!/usr/bin/python3
import gzip,json,os,shutil,subprocess,tempfile,time
from pathlib import Path
os.umask(0o077)
root=Path('/opt/classroom-cd')
folder=root/'backups'
folder.mkdir(mode=0o700,exist_ok=True)
cfg=json.loads((root/'credentials.json').read_text())
databases=[env['database'] for team in cfg['teams'].values() for env in team['environments'].values()]
stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
temporary=folder/(stamp+'.sql.gz.tmp')
with tempfile.TemporaryFile() as errors:
    process=subprocess.Popen(['docker','compose','-p','classroom-infra','-f',str(root/'infra.json'),'exec','-T',
        'mysql','sh','-c','MYSQL_PWD=$(cat /run/secrets/mysql-root) exec mysqldump -uroot --single-transaction --no-tablespaces --routines --events --databases "$@"',
        'dump',*databases],stdout=subprocess.PIPE,stderr=errors)
    # A subprocess writing to a GzipFile's descriptor bypasses compression.
    # Read its pipe in Python so all bytes pass through the gzip writer.
    with gzip.open(temporary,'wb') as output:
        shutil.copyfileobj(process.stdout,output)
    process.stdout.close()
    returncode=process.wait()
if returncode:
    temporary.unlink(missing_ok=True)
    raise RuntimeError('MySQL backup failed')
with gzip.open(temporary,'rb') as compressed:
    while compressed.read(1024*1024):
        pass
destination=temporary.with_suffix('')
temporary.replace(destination)
for previous in folder.glob('*.sql.gz'):
    if previous.stat().st_mtime < time.time()-7*86400:
        previous.unlink()
print('Local backup created:',destination.name,'compressed bytes:',destination.stat().st_size)
'''
path=Path('/usr/local/sbin/classroom-db-backup')
path.write_text(backup)
path.chmod(0o700)
Path('/etc/systemd/system/classroom-db-backup.service').write_text('''[Unit]
Description=Local classroom MySQL backup
After=docker.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/classroom-db-backup
UMask=0077
''')
Path('/etc/systemd/system/classroom-db-backup.timer').write_text('''[Unit]
Description=Daily classroom MySQL backup at 18:00 UTC
[Timer]
OnCalendar=*-*-* 18:00:00 UTC
Persistent=true
[Install]
WantedBy=timers.target
''')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','classroom-db-firewall.service','classroom-db-backup.timer'],check=True)
subprocess.run(['/usr/local/sbin/classroom-db-backup'],check=True)
print('Private DB firewall and local 7-day backup installed. Off-server disaster recovery is separate.')
