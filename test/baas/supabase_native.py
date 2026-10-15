"""Native PostgREST permission, bridge isolation and binary-text contract checks."""
import base64,hmac,json,os,time,unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import test_api as app
REST=os.environ.get('REST_URL','http://rest:3000')
def rpc(name,body,token=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 req=Request(REST+'/'+name,data=json.dumps(body).encode(),headers=headers,method='POST')
 try:r=urlopen(req,timeout=15)
 except HTTPError as e:r=e
 with r:
  raw=r.read()
  try:value=json.loads(raw)
  except ValueError:value={'non_json':True}
  return r.status,value
class NativeSupabase(unittest.TestCase):
 def test_native_gateway_api_key_layer_is_enforced(self):
  for key,expected in [(None,401),('wrong-key',401),(os.environ['ANON_KEY'],200)]:
   headers={'Content-Type':'application/json'}
   if key:headers['apikey']=key
   req=Request(app.BASE+'/rest/v1/rpc/feed',data=b'{}',headers=headers,method='POST')
   try:response=urlopen(req,timeout=15)
   except HTTPError as error:response=error
   with response:self.assertEqual(response.status,expected)
 def test_native_feed_is_real_supported_rpc(self):
  status,value=rpc('rpc/feed',{})
  self.assertEqual(status,200,value);self.assertEqual(len(value),20)
  self.assertTrue(all('body_b64' in row and 'like_count' in row for row in value))
 def test_anon_cannot_write_rpc_or_exposed_tables(self):
  for endpoint,body in [('rpc/create_post',{'p_body_b64':'eA=='}),('rpc/like_post',{'p_post_id':1}),('users',{'id':999999,'username':'forged'}),('posts',{'body':'forged'}),('likes',{'user_id':1,'post_id':1})]:
   status,_=rpc(endpoint,body)
   self.assertIn(status,[401,403,404],endpoint)
 def test_compat_signer_cannot_forge_native_writer_identity(self):
  encode=lambda v:base64.urlsafe_b64encode(json.dumps(v).encode()).decode().rstrip('=')
  text=encode({'alg':'HS256','typ':'JWT'})+'.'+encode({'role':'feed_writer','app_user_id':'2','exp':int(time.time())+60})
  sig=base64.urlsafe_b64encode(hmac.digest(app.SECRET,text.encode(),'sha256')).decode().rstrip('=')
  self.assertEqual(rpc('rpc/create_post',{'p_body_b64':'eA=='},text+'.'+sig)[0],401)
 def test_nul_and_unicode_roundtrip_without_database_text_loss(self):
  text='binary-safe \x00 café 😀'
  status,value=app.request('POST','/posts',{'body':text},app.token())
  self.assertEqual(status,201,value);post=value['post'];self.assertEqual(post['body'],text)
  self.assertEqual(app.request('GET',f'/posts/{post["id"]}'),(200,{'post':post}))
if __name__=='__main__':unittest.main(verbosity=2)
