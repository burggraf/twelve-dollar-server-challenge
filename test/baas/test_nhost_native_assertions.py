"""Native verifier regression: pinned GraphQL errors are not successful writes; ECMAScript write trim differs from stored reads."""
import os,unittest
from unittest.mock import patch
import nhost_native as live
class NativeAssertions(unittest.TestCase):
 def check_signer(self,response,after='500000'):
  count=lambda value:{'result_type':'TuplesOk','result':[['count'],[value]]}
  observations=0
  def call(path,payload,*args,**kwargs):
   nonlocal observations
   if path=='/v2/query':
    value='500000' if observations==0 else after;observations+=1;return 200,count(value)
   return 200,response
  with patch.dict(os.environ,{'COMPAT_JWT_SECRET':'unit-compat','NATIVE_JWT_SECRET':'unit-native'}),patch.object(live,'token',return_value='unit-token'),patch.object(live,'call',side_effect=call) as calls:
   live.NativeNhost('test_compatibility_signer_cannot_forge_native_writer').test_compatibility_signer_cannot_forge_native_writer()
   self.assertEqual(observations,2);self.assertEqual(calls.call_count,3)
 def test_actual_pinned_invalid_jwt_response_with_no_data_and_no_write_is_rejection(self):
  self.check_signer({'errors':[{'message':'Could not verify JWT: JWSError JWSInvalidSignature','extensions':{'path':'$','code':'invalid-jwt'}}]})
 def test_graphql_data_can_never_be_misclassified_as_rejected_signer(self):
  with self.assertRaises(AssertionError):self.check_signer({'data':{'nhost_create_post':[{'payload':{'id':'500001'}}]}})
 def test_other_graphql_error_cannot_stand_in_for_signature_verification(self):
  with self.assertRaises(AssertionError):self.check_signer({'errors':[{'extensions':{'code':'validation-failed'}}]})
 def test_invalid_jwt_error_cannot_hide_an_actual_committed_write(self):
  with self.assertRaises(AssertionError):self.check_signer({'errors':[{'extensions':{'code':'invalid-jwt'}}]},after='500001')
 def check_trim(self,returned):
  body='native binary-safe \0 café 😀';post={'id':500001,'body':returned,'created_at':'2026-01-01T00:00:00.000Z','author':'golden_ember_1','like_count':0}
  with patch.object(live.app,'token',return_value='unit-token'),patch.object(live.app,'request',side_effect=[(201,{'post':post}),(200,{'post':post})]) as request:
   live.NativeNhost('test_unicode_nul_and_bom_http_write_read_roundtrip').test_unicode_nul_and_bom_http_write_read_roundtrip()
   self.assertEqual(request.call_args_list[0].args[2]['body'],'\ufeff'+body+'\ufeff');self.assertEqual(request.call_count,2)
 def test_boundary_bom_is_trimmed_on_write_while_nul_and_unicode_survive(self):self.check_trim('native binary-safe \0 café 😀')
 def test_untrimmed_bom_cannot_be_accepted_as_correct_write(self):
  with self.assertRaises(AssertionError):self.check_trim('\ufeffnative binary-safe \0 café 😀')
if __name__=='__main__':unittest.main(verbosity=2)
