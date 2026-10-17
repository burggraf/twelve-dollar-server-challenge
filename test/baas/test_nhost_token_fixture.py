"""Native-private fixture validation rejects short user exports, even with all20,000 JWT entries."""
import base64,hashlib,hmac,json,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import nhost_benchmark as n
class TokenFixture(unittest.TestCase):
 def test_complete_fixture_hash_and_each_trust_boundary(self):
  key='NONSECRET_NHOST_UNIT_FIXTURE_SIGNER';encode=lambda value:base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=');header=encode({'alg':'HS256','typ':'JWT'});entries=[];users=[]
  for index in range(1,20001):
   username='user'+str(index);payload=encode({'sub':str(index),'username':username,'exp':int(time.time())+7200});text=header+'.'+payload;signature=base64.urlsafe_b64encode(hmac.digest(key.encode(),text.encode(),'sha256')).decode().rstrip('=')
   entries.append({'id':index,'username':username,'token':text+'.'+signature});users.append(f'{index}\t{username}\t2026\n')
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);seed=root/'.state/seed';seed.mkdir(parents=True);tokens=seed/'tokens.json';file=seed/'users.tsv';raw=json.dumps(entries).encode();tokens.write_bytes(raw);file.write_text(''.join(users))
   with patch.object(n,'ROOT',root),patch.object(n.s,'runtime_values',return_value={'COMPAT_JWT_SECRET':key}):
    with self.subTest(variant='valid'):self.assertEqual(n.token_hash(),hashlib.sha256(raw).hexdigest())
    for variant in ['short-users','wrong-signature','expired','wrong-subject','missing-identity']:
     bad=json.loads(raw);file.write_text(''.join(users[:-1] if variant=='short-users' else users))
     if variant=='wrong-signature':bad[-1]['token']=bad[-1]['token'][:-1]+'!'
     if variant in ['expired','wrong-subject']:
      claims={'sub':'20000' if variant=='expired' else '1','username':'user20000','exp':0 if variant=='expired' else int(time.time())+7200};text=header+'.'+encode(claims);bad[-1]['token']=text+'.'+base64.urlsafe_b64encode(hmac.digest(key.encode(),text.encode(),'sha256')).decode().rstrip('=')
     if variant=='missing-identity':bad.pop()
     tokens.write_text(json.dumps(bad))
     with self.subTest(variant=variant),self.assertRaises(RuntimeError):n.token_hash()
if __name__=='__main__':unittest.main(verbosity=2)
