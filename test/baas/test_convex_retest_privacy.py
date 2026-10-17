"""Collect actual fresh credentials privately BEFORE retrieving new stack logs."""
import base64
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
if importlib.util.find_spec('convex_retest_privacy'):
    import convex_retest_privacy as privacy
else:privacy=None


class FreshActualValues(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)/'workspace';self.state=self.root/'src/.state/convex';self.state.mkdir(parents=True)
        (self.root/'.benchmark-owned').write_text(json.dumps({'project':'baas-convex4g-retest-v1'}))

    def collect(self,**kwargs):
        function=getattr(privacy,'fresh_inputs',None)
        self.assertTrue(callable(function),'Missing fresh actual-value/signature privacy collection')
        return function(self.root,**kwargs)

    def test_empty_pre_serving_workspace_is_distinct_from_missing_required_native_secret(self):
        values,signatures,metadata=self.collect()
        self.assertEqual(values,set());self.assertEqual(signatures,set())
        self.assertEqual(metadata['credential_files_present'],0)
        with self.assertRaises(RuntimeError):self.collect(require_native_secret=True)

    def test_only_exact_owned_fresh_workspace_may_be_read(self):
        (self.root/'.benchmark-owned').write_text(json.dumps({'project':'baas-convexpg-vps16'}))
        with self.assertRaises(RuntimeError):self.collect()

    def test_new_env_secrets_password_dsn_and_decoded_password_are_all_collected(self):
        (self.state/'backend.env').write_text('INSTANCE_SECRET=sample-instance-secret-value\nPOSTGRES_URL=postgresql://owner:encoded%2Fpassword@postgres/database\n')
        (self.state/'postgres.env').write_text('POSTGRES_PASSWORD=sample-postgres-password\n')
        (self.state/'cli.env').write_text('CONVEX_SELF_HOSTED_ADMIN_KEY="sample-admin-key-value"\n')
        (self.state/'compat-jwt.env').write_text('JWT_SECRET=sample-hs256-key-value\n')
        values,signatures,metadata=self.collect()
        for value in [b'sample-instance-secret-value',b'sample-postgres-password',b'sample-admin-key-value',b'sample-hs256-key-value',b'encoded%2Fpassword',b'encoded/password',b'postgresql://owner:encoded%2Fpassword@postgres/database']:
            self.assertIn(value,values)
        self.assertEqual(metadata['credential_files_present'],4)
        self.assertFalse(signatures)

    def test_actual_native_volume_secret_is_collected_not_replaced_by_an_env_fingerprint(self):
        secret=self.root/'native-secret';secret.write_bytes(b'sample-native-generated-secret\n')
        values,_,metadata=self.collect(native_secret_file=secret,require_native_secret=True)
        self.assertIn(b'sample-native-generated-secret',values)
        self.assertTrue(metadata['native_secret_present'])

    def test_every_issued_signature_is_collected_without_returning_tokens_in_metadata(self):
        def encoded(value):return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b'=').decode()
        header=encoded({'alg':'HS256','typ':'JWT'});payload=encoded({'sub':'1','exp':2000000000})
        signatures=['A'*43,'B'*43]
        tokens=[{'token':'.'.join([header,payload,signature])} for signature in signatures]
        (self.state/'benchmark-tokens.json').write_text(json.dumps(tokens))
        _,actual,metadata=self.collect()
        self.assertEqual(actual,{signature.encode() for signature in signatures})
        self.assertEqual(metadata['issued_signatures'],2)
        self.assertNotIn(tokens[0]['token'],json.dumps(metadata))

    def test_malformed_private_token_file_fails_closed_without_echoing_contents(self):
        (self.state/'benchmark-tokens.json').write_text('[{"token":"private-malformed-token-value"}]')
        with self.assertRaises(RuntimeError) as caught:self.collect()
        self.assertNotIn('private-malformed-token-value',str(caught.exception))

    def test_malformed_env_or_missing_requested_secret_is_not_silently_skipped(self):
        (self.state/'backend.env').write_text('private-malformed-env-line\n')
        with self.assertRaises(RuntimeError) as caught:self.collect()
        self.assertNotIn('private-malformed-env-line',str(caught.exception))

    def generated_tokens(self,signature='C'):
        path=self.state/'benchmark-seed';path.mkdir(exist_ok=True)
        token='header.payload.'+signature*43
        (path/'tokens.json').write_text(json.dumps([{'token':token}]))
        return path/'tokens.json'

    def test_issued_original_generator_signatures_are_collected_before_the_fixture_copy(self):
        self.generated_tokens();_,signatures,_=self.collect()
        self.assertIn(b'C'*43,signatures)

    def test_all_generator_and_final_fixture_signatures_are_unioned(self):
        self.generated_tokens();(self.state/'benchmark-tokens.json').write_text(json.dumps([{'token':'header.payload.'+'D'*43}]))
        _,signatures,metadata=self.collect()
        self.assertEqual(signatures,{b'C'*43,b'D'*43});self.assertEqual(metadata['issued_signatures'],2)

    def test_partial_generator_token_output_blocks_retrieval_even_before_fixture_copy(self):
        path=self.generated_tokens();path.write_text('malformed-private-generator-output')
        with self.assertRaises(RuntimeError):self.collect()

    def test_generator_directory_symlink_is_not_followed_or_silently_ignored(self):
        outside=self.root/'outside';outside.mkdir()
        (self.state/'benchmark-seed').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(RuntimeError):self.collect()

    def test_generator_token_symlink_is_not_followed_or_silently_ignored(self):
        path=self.generated_tokens();path.unlink();other=self.root/'other-private';other.write_text('private')
        path.symlink_to(other)
        with self.assertRaises(RuntimeError):self.collect()

    def native_collect(self,volumes,containers,volume=None,fail=False):
        function=getattr(privacy,'native_fresh_inputs',None)
        self.assertTrue(callable(function),'Missing actual owned Docker/private-source integration')
        def capture(argv,**kwargs):
            if fail:raise RuntimeError('private-docker-error-detail')
            if argv==['docker','volume','ls','-q']:return '\n'.join(volumes)
            if argv[:3]==['docker','ps','-aq']:return '\n'.join(containers)
            if argv[:3]==['docker','volume','inspect']:return json.dumps([volume])
            raise AssertionError('Unexpected/mutating Docker command')
        return function(self.root,capture=capture)

    def test_native_integration_distinguishes_pre_serving_absence_without_creating_resources(self):
        values,signatures,metadata=self.native_collect([],[])
        self.assertFalse(values);self.assertFalse(signatures)
        self.assertFalse(metadata['native_secret_present'])

    def test_backend_presence_requires_actual_native_secret_before_retrieval(self):
        with self.assertRaises(RuntimeError):self.native_collect([],['owned-backend'])

    def test_native_volume_ownership_is_checked_before_credential_read(self):
        volume={'Name':'baas-convex4g-retest-v1_data','Labels':{'com.docker.compose.project':'unrelated'},'Mountpoint':str(self.root/'unrelated-volume')}
        with self.assertRaises(RuntimeError):self.native_collect([volume['Name']],[],volume)

    def test_owned_native_volume_secret_is_included_in_actual_retrieval_candidates(self):
        mount=self.root/'owned-volume';(mount/'credentials').mkdir(parents=True)
        (mount/'credentials/instance_secret').write_text('sample-native-volume-secret')
        volume={'Name':'baas-convex4g-retest-v1_data','Labels':{'com.docker.compose.project':'baas-convex4g-retest-v1','com.docker.compose.volume':'data'},'Mountpoint':str(mount)}
        values,_,metadata=self.native_collect([volume['Name']],['owned-backend'],volume)
        self.assertIn(b'sample-native-volume-secret',values)
        self.assertTrue(metadata['native_secret_present'])

    def test_failed_docker_inventory_blocks_retrieval_without_echoing_private_error(self):
        with self.assertRaises(RuntimeError) as caught:self.native_collect([],[],fail=True)
        self.assertNotIn('private-docker-error-detail',str(caught.exception))

    def test_symlinked_private_input_is_not_followed_to_unrelated_state(self):
        outside=Path(self.directory.name)/'outside-private';outside.write_text('JWT_SECRET=unrelated-private-value\n')
        (self.state/'compat-jwt.env').symlink_to(outside)
        with self.assertRaises(RuntimeError):self.collect()


if __name__=='__main__':unittest.main(verbosity=2)
