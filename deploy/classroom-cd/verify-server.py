"""Print only non-secret health and database isolation evidence; run using sudo."""
import concurrent.futures
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path('/opt/classroom-cd')
credentials = json.loads((ROOT/'credentials.json').read_text())
def check(team):
    prefix = 'example' if team == 'team' else team
    base = 'https://daelim.minq.live/'+prefix
    with urllib.request.urlopen(base+'/common/health', timeout=20) as response:
        result = json.load(response)
    with urllib.request.urlopen(base+'/v3/api-docs', timeout=30) as response:
        swagger = json.load(response)
    isolation = []
    for env in ['dev','main']:
        cfg = credentials['teams'][team]['environments'][env]
        def sql(database):
            return subprocess.run(['docker','compose','-p','classroom-infra','-f',str(ROOT/'infra.json'),
                'exec','-T','-e','MYSQL_PWD='+cfg['password'],'mysql','mysql','-h127.0.0.1',
                '-u'+cfg['username'],'--database='+database,'--batch','--skip-column-names','-e','SELECT 1;'],
                capture_output=True,text=True)
        own = sql(cfg['database'])
        other_team = 'team1' if team != 'team1' else 'team2'
        other = sql(credentials['teams'][other_team]['environments'][env]['database'])
        other_env = sql(credentials['teams'][team]['environments']['main' if env=='dev' else 'dev']['database'])
        item = {'environment':env,'own_database':own.returncode==0,
                'other_team_denied':other.returncode!=0 and 'Access denied' in other.stderr,
                'other_environment_denied':other_env.returncode!=0 and 'Access denied' in other_env.stderr}
        assert all(item[k] for k in ['own_database','other_team_denied','other_environment_denied']), item
        isolation.append(item)
    assert result['status']=='ok' and result['database']=='up'
    return {'team':team,'health_url':base+'/common/health','health':result,
            'swagger_status':200,'swagger_server_urls':[x['url'] for x in swagger.get('servers',[])],
            'database_isolation':isolation}

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    result = list(pool.map(check,credentials['teams']))
print(json.dumps({'teams':result,'database_count':18},indent=2))
