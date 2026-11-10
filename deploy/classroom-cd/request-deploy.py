"""Request your team's pinned-image deployment/rollback without SSH (Python 3)."""
import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--team',required=True,choices=['team']+['team'+str(i) for i in range(1,9)])
parser.add_argument('--image',required=True,help='Own repository with dev-FULL_SHA or @sha256:DIGEST')
parser.add_argument('--access-file',default='cd-access.json',help='Ignored file containing only your team credentials')
args=parser.parse_args()
base='docker.minq.live/'+args.team+'/idea-support-server'
match=re.fullmatch(re.escape(base)+r'(?::dev-([0-9a-f]{40})|@sha256:([0-9a-f]{64}))',args.image)
if not match:
    parser.error('Use your own team repository and a full dev commit tag or digest')
access=json.loads(Path(args.access_file).read_text(encoding='utf-8-sig'))[args.team]
url='https://daelim.minq.live/_cd/'+args.team
if access['deploy_url']!=url:
    parser.error('Unexpected deployment destination')
payload={'image':args.image,'revision':match.group(1) or '0'*40}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise RuntimeError('Deployment endpoint redirected; refusing to forward credentials')
opener=urllib.request.build_opener(NoRedirect)
req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={
    'Authorization':'Bearer '+access['deploy_token'],'Content-Type':'application/json'})
try:
    with opener.open(req,timeout=1800) as response:
        result=json.load(response)
except urllib.error.HTTPError as error:
    print('Deployment failed: HTTP',error.code)
    raise SystemExit(1)
print(json.dumps(result,indent=2))
if result['status'] not in ['deployed','unchanged']:
    raise SystemExit(1)
