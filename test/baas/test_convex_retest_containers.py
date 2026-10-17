"""Exact-owned untimed tools/runner lifecycle using fake Docker IO only."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
if importlib.util.find_spec('convex_retest_containers'):
    import convex_retest_containers as containers
else:containers=None
PROJECT='baas-convex4g-retest-v1';CID='a'*64


class ExactOwnedContainers(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'src';self.root.mkdir()
        (self.root.parent/'.benchmark-owned').write_text(json.dumps({'project':PROJECT}))
        self.commands=[];self.item=None;self.occupied=False

    def create(self):
        factory=getattr(containers,'OwnedContainers',None)
        self.assertTrue(callable(factory),'Missing precreated exact-owned tool/load lifecycle')
        def capture(argv,**kwargs):
            self.commands.append(argv)
            if argv[:3]==['docker','ps','-aq']:return CID if self.occupied else ''
            if argv[:2]==['docker','create']:
                role='k6' if 'benchmark.role=k6' in argv else 'tools'
                self.item={'Id':CID,'Image':'image-'+role,'Config':{'Labels':{'com.docker.compose.project':PROJECT,'com.docker.compose.service':role,'benchmark.role':role,'benchmark.operation':'op-1'}},'State':{'Running':False,'Pid':0},'HostConfig':{'NanoCpus':2000000000,'Memory':8589934592 if role=='k6' else 4294967296,'MemorySwap':8589934592 if role=='k6' else 4294967296}}
                return CID+'\n'
            if argv[:3]==['docker','image','inspect']:
                return json.dumps([{'Id':'image-k6' if 'grafana/k6' in argv[3] else 'image-tools','Architecture':'amd64','Os':'linux'}])
            if argv[:2]==['docker','inspect']:return json.dumps([self.item])
            if argv[:2] in (['docker','stop'],['docker','rm']):return CID
            raise AssertionError('Unexpected command')
        return factory(self.root,self.root.parent/'operations',capture=capture)

    def test_create_load_records_identity_before_any_start_and_uses_exact_runner_budget(self):
        value=self.create();cid=value.create_load(25,False,'op-1')
        self.assertEqual(cid,CID);self.assertFalse(any(argv[:2]==['docker','start'] for argv in self.commands))
        self.assertTrue(list((self.root.parent/'operations').glob('*')))
        argv=next(argv for argv in self.commands if argv[:2]==['docker','create'])
        self.assertIn('8589934592',argv);self.assertIn('2',argv)
        self.assertNotIn('compat-jwt.env',' '.join(argv));self.assertNotIn('cli.env',' '.join(argv))

    def test_tools_use_bounded_known_image_and_private_env_files_not_secret_arguments(self):
        value=self.create();value.create_tools('python3 /work/test/baas/test_api.py','op-1')
        argv=next(argv for argv in self.commands if argv[:2]==['docker','create'])
        self.assertIn('4294967296',argv);self.assertIn('--env-file',argv)
        self.assertNotIn('JWT_SECRET=', ' '.join(argv))
        self.assertFalse(any(argv[:2]==['docker','start'] for argv in self.commands))

    def test_out_of_scope_load_is_refused_before_any_docker_probe(self):
        value=self.create()
        for vus,smoke in [(2001,False),(1000,True),(True,False)]:
            with self.assertRaises(ValueError):value.create_load(vus,smoke,'op-1')
        self.assertEqual(self.commands,[])

    def test_occupied_names_are_not_adopted_removed_or_started(self):
        value=self.create();self.occupied=True
        with self.assertRaises(RuntimeError):value.create_load(25,False,'op-1')
        self.assertFalse(any(argv[1] in ('create','start','rm','stop') for argv in self.commands))

    def test_cleanup_requires_original_id_image_role_project_and_operation_identity(self):
        value=self.create();value.create_load(25,False,'op-1')
        good=copy.deepcopy(self.item)
        for field in ('Id','Image'):
            self.item=copy.deepcopy(good);self.item[field]='different'
            with self.assertRaises(RuntimeError):value.stop_exact(CID)
        self.item=copy.deepcopy(good);self.item['Config']['Labels']['com.docker.compose.project']='unrelated'
        with self.assertRaises(RuntimeError):value.stop_exact(CID)
        self.assertFalse(any(argv[:2]==['docker','stop'] for argv in self.commands))

    def test_unregistered_ids_cannot_be_stopped_even_if_they_share_a_project_label(self):
        value=self.create()
        with self.assertRaises(RuntimeError):value.stop_exact(CID)
        self.assertEqual(self.commands,[])

    def test_stop_only_affects_registered_identity_and_preserves_container_evidence(self):
        value=self.create();value.create_load(25,False,'op-1');self.item['State']['Running']=True
        value.stop_exact(CID)
        stops=[argv for argv in self.commands if argv[:2]==['docker','stop']]
        self.assertEqual(len(stops),1);self.assertEqual(stops[0][-1],CID)
        self.assertFalse(any(argv[:2]==['docker','rm'] for argv in self.commands))

    def test_drifted_kernel_intent_or_native_platform_is_not_a_launchable_container(self):
        value=self.create();value.create_load(25,False,'op-1');self.item['HostConfig']['Memory']=4294967296
        with self.assertRaises(RuntimeError):value.verify(CID)


if __name__=='__main__':unittest.main(verbosity=2)
