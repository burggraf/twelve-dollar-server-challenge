"""Storage-failure and actual process-restart proof, coordinated by owned lifecycle."""
import argparse,json,os,time
from pathlib import Path
import test_api as app
FILE=Path(os.environ.get('RESTART_PROOF','/state/restart-proof.json'))
def run(phase):
 if phase=='prepare':
  status,value=app.request('POST','/posts',{'body':'Supabase acknowledged restart persistence proof'},app.token())
  assert status==201,(status,value)
  post=value['post'];status,value=app.request('POST',f'/posts/{post["id"]}/like',auth=app.token())
  assert (status,value)==(201,{'liked':True,'already_liked':False,'post_id':post['id']})
  post['like_count']=1;FILE.write_text(json.dumps(post)+'\n');print('Acknowledged committed post and like recorded; no tokens retained.')
 elif phase=='unavailable':
  assert app.request('GET','/health')==(503,{'status':'degraded','db':'unreachable','error':'storage probe failed'})
  assert app.request('POST','/posts',{'body':'must not acknowledge unavailable storage'},app.token())==(500,{'error':'internal server error'})
  print('Stopped native storage produces degraded health and sanitized failed writes, not fake success.')
 elif phase=='verify':
  expected=json.loads(FILE.read_text())
  assert app.request('GET',f'/posts/{expected["id"]}')==(200,{'post':expected})
  assert app.request('POST',f'/posts/{expected["id"]}/like',auth=app.token())==(200,{'liked':True,'already_liked':True,'post_id':expected['id']})
  print('Acknowledged post and exactly-once like survived actual database/application process restart.')
 else:raise ValueError('unknown phase')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','unavailable','verify']);run(parser.parse_args().phase)
