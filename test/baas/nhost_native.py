"""Actual packaged GraphQL permissions and HTTP byte/exact-ID checks; admin SQL is untimed fixture setup only."""
import base64,hmac,json,os,time,unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import test_api as app
GRAPHQL='http://graphql:8080'
def call(path,payload,token=None,admin=False):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 if admin:headers['x-hasura-admin-secret']=os.environ['GRAPHQL_ADMIN_SECRET']
 request=Request(GRAPHQL+path,data=json.dumps(payload).encode(),headers=headers)
 try:response=urlopen(request,timeout=15)
 except HTTPError as error:response=error
 with response:return response.status,json.load(response)
def token(compat=False):
 encode=lambda value:base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).decode().rstrip('=')
 claims={'exp':int(time.time())+60,'https://hasura.io/jwt/claims':{'x-hasura-default-role':'feed_writer','x-hasura-allowed-roles':['feed_writer'],'x-hasura-user-id':'1'}}
 text=encode({'alg':'HS256','typ':'JWT'})+'.'+encode(claims);key=os.environ['COMPAT_JWT_SECRET' if compat else 'NATIVE_JWT_SECRET'];value=text+'.'+base64.urlsafe_b64encode(hmac.digest(key.encode(),text.encode(),'sha256')).decode().rstrip('=')
 path=Path('/state/issued-tokens.json');rows=json.loads(path.read_text()) if path.exists() else [];rows.append({'token':value});path.write_text(json.dumps(rows)+'\n');return value
class NativeNhost(unittest.TestCase):
 def test_explicit_metadata_template_matches_real_native_permissions(self):
  status,value=call('/v1/metadata',{'type':'export_metadata','args':{}},admin=True);self.assertEqual(status,200)
  metadata=value.get('metadata',value);source=next(item for item in metadata['sources'] if item['name']=='default');tables=source['tables'];functions=source['functions']
  operations=json.loads(Path('/work/services/nhost/metadata-operations.json').read_text())
  for operation in operations:
   args=operation['args'];kind=operation['type']
   if 'table' in args:
    current=next(item for item in tables if item['table']==args['table'])
    if kind=='pg_create_select_permission':
     permission=next(item['permission'] for item in current['select_permissions'] if item['role']==args['role']);self.assertEqual(permission['columns'],['payload']);self.assertEqual(permission['filter'],{})
   else:
    current=next(item for item in functions if item['function']==args['function'])
    if kind=='pg_track_function':
     for key,expected in args['configuration'].items():self.assertEqual(current['configuration'][key],expected)
    else:self.assertIn(args['role'],[item['role'] for item in current['permissions']])
  declared={operation['args']['function']['name'] for operation in operations if 'function' in operation['args']}
  for item in functions:
   if item['function']['schema']=='public' and item['function']['name'] in declared:
    expected={'feed_writer'} if item['function']['name'] in {'nhost_create_post','nhost_like_post'} else {'feed_reader','feed_writer'};self.assertEqual({permission['role'] for permission in item.get('permissions',[])},expected)
  self.assertFalse(any(item['table']['schema']=='feed_data' for item in tables))
 def test_native_feed_uses_real_supported_function(self):
  status,value=call('/v1/graphql',{'query':'query { nhost_feed { payload } }'})
  self.assertEqual(status,200,value);self.assertNotIn('errors',value);rows=value['data']['nhost_feed'][0]['payload'];self.assertEqual(len(rows),20);self.assertTrue(all('body_b64' in row and type(row['id']) is str and type(row['like_count']) is str for row in rows))
 def test_anonymous_cannot_write_or_access_application_tables(self):
  for query in ['mutation { nhost_create_post(args:{p_body_b64:"eA=="}) { payload } }','mutation { nhost_like_post(args:{p_post_id:1}) { payload } }','mutation { insert_feed_data_users_one(object:{id:999999,username:"forged"}) { id } }']:
   status,value=call('/v1/graphql',{'query':query});self.assertIn(status,[200,400]);self.assertIn('errors',value)
 def test_compatibility_signer_cannot_forge_native_writer(self):
  self.assertNotEqual(os.environ['COMPAT_JWT_SECRET'],os.environ['NATIVE_JWT_SECRET'])
  count={'type':'run_sql','args':{'source':'default','sql':'SELECT count(*) FROM feed_data.posts;'}}
  status,before=call('/v2/query',count,admin=True);self.assertEqual(status,200,before)
  status,value=call('/v1/graphql',{'query':'mutation { nhost_create_post(args:{p_body_b64:"eA=="}) { payload } }'},token(compat=True));self.assertEqual(status,200,value);self.assertNotIn('data',value);self.assertTrue(value.get('errors'),value)
  self.assertTrue(all(error.get('extensions',{}).get('code')=='invalid-jwt' for error in value['errors']),value)
  status,after=call('/v2/query',count,admin=True);self.assertEqual(status,200,after);self.assertEqual(after,before,'Rejected native JWT must not commit a post')
 def test_session_argument_is_hidden_even_from_signed_writer(self):
  status,value=call('/v1/graphql',{'query':'mutation { nhost_create_post(args:{p_body_b64:"eA==",hasura_session:"{}"}) { payload } }'},token());self.assertIn(status,[200,400]);self.assertIn('errors',value)
 def test_stored_wide_id_bom_nul_and_binary_roundtrip(self):
  body='\ufeffstored \0 café 😀';wide=9007199254740993
  status,value=call('/v2/query',{'type':'run_sql','args':{'source':'default','sql':f"INSERT INTO feed_data.posts(id,user_id,body,created_at) VALUES({wide},1,decode('{body.encode().hex()}','hex'),'9999-01-01T00:00:00.000Z');"}},admin=True);self.assertEqual(status,200,value)
  status,value=app.request('GET',f'/posts/{wide}');self.assertEqual(status,200,value);self.assertEqual(value['post']['id'],wide);self.assertEqual(value['post']['body'],body)
  status,value=app.request('GET','/feed');self.assertEqual(status,200,value);self.assertEqual(value['posts'][0]['id'],wide);self.assertEqual(value['posts'][0]['body'],body)
 def test_unicode_nul_and_bom_http_write_read_roundtrip(self):
  body='native binary-safe \0 café 😀';status,value=app.request('POST','/posts',{'body':'\ufeff'+body+'\ufeff'},app.token());self.assertEqual(status,201,value);post=value['post'];self.assertEqual(post['body'],body);self.assertEqual(app.request('GET',f'/posts/{post["id"]}'),(200,{'post':post}))
if __name__=='__main__':unittest.main(verbosity=2)
