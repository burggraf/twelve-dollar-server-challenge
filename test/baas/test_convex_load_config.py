"""The optional runner is isolated from the unchanged two-server allocation."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[2]


class ConvexLoadConfig(unittest.TestCase):
    def test_optional_native_runner_and_tools_do_not_expand_serving_budget(self):
        overlay=ROOT/'services/convex/compose.benchmark.yaml'
        self.assertTrue(overlay.is_file(), 'Optional isolated Convex runner profile missing')
        value=json.loads(subprocess.check_output(['docker','compose','-p','baas-convexpg-vps16','-f',str(ROOT/'services/convex/compose.yaml'),'-f',str(ROOT/'services/convex/compose.postgres.yaml'),'-f',str(overlay),'--profile','*','config','--no-env-resolution','--format','json'],text=True))
        self.assertEqual(set(value['services']),{'backend','postgres','tools','k6'})
        for role,memory in [('backend',3221225472),('postgres',1073741824)]:
            item=value['services'][role];self.assertEqual(str(item['mem_limit']),str(memory));self.assertEqual(item['cgroup_parent'],'tdsbaasconvexpgvps16.slice');self.assertEqual(float(item['cpus']),1)
        item=value['services']['k6']
        self.assertEqual(item['profiles'],['load']);self.assertEqual(item['platform'],'linux/amd64')
        self.assertEqual(item['image'],'grafana/k6:1.3.0@sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656')
        self.assertEqual(float(item['cpus']),2);self.assertEqual(str(item['mem_limit']),'8589934592');self.assertEqual(str(item['memswap_limit']),'8589934592')
        self.assertNotIn('cgroup_parent',item);self.assertNotIn('env_file',item)
        self.assertEqual(item['environment']['BASE_URL'],'http://backend:3211')
        mounts={v['target']:v for v in item['volumes']};self.assertEqual(set(mounts),{'/work/bench','/tokens.json','/runs'})
        self.assertTrue(mounts['/tokens.json']['read_only']);self.assertTrue(mounts['/work/bench']['read_only'])
        tools=value['services']['tools'];self.assertEqual(tools['profiles'],['tools']);self.assertEqual(float(tools['cpus']),2);self.assertEqual(str(tools['mem_limit']),'4294967296');self.assertNotIn('cgroup_parent',tools)


if __name__=='__main__':unittest.main(verbosity=2)
