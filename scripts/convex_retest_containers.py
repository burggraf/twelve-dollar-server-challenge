"""Precreate exact-owned untimed tools/runner; register BEFORE starting work.

No target lifecycle effects. No name adoption or broad project cleanup. Keep
stopped containers until the caller has retained evidence and explicitly removes
them. The runner mounts only bench, compatibility tokens, and run outputs.
"""
import json
import os
from pathlib import Path
import re
import subprocess
from convex_retest_safety import PROJECT,validate_attempt

TOOLS='sha256:7b35188938d0b5a3b50178d6a85e776b09db24314a2643c64b95b3da49f4f9f2'
K6='grafana/k6:1.3.0@sha256:a90b459a3768c46ad1013da53af24189f735d7112273c6ac3212ca8ed0e18656'


class OwnedContainers:
    def __init__(self,root,evidence,*,capture=subprocess.check_output):
        self.root=Path(root);self.evidence=Path(evidence);self.capture=capture;self.registered={}
        if json.loads((self.root.parent/'.benchmark-owned').read_text()).get('project')!=PROJECT:
            raise RuntimeError('Exact-owned fresh workspace required')
        self.evidence.mkdir(mode=0o700,parents=True,exist_ok=False)

    def _read(self,argv):return self.capture(argv,text=True,stderr=subprocess.PIPE,timeout=30)

    def _write(self,name,value):
        with (self.evidence/name).open('x') as output:
            json.dump(value,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())

    def _create(self,role,operation,options,command):
        if not isinstance(operation,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,100}',operation):raise ValueError('Bounded operation identity required')
        name=PROJECT+'-load' if role=='k6' else PROJECT+'-tools-'+operation
        if self._read(['docker','ps','-aq','--filter','name=^'+name+'$']).strip():raise RuntimeError('Occupied owned name; no adoption/replacement')
        reference=K6 if role=='k6' else TOOLS
        image=json.loads(self._read(['docker','image','inspect',reference]))[0]
        if image['Os']!='linux' or image['Architecture']!='amd64':raise RuntimeError('Actual native pinned tool/runner image required')
        memory=8589934592 if role=='k6' else 4294967296
        labels={'com.docker.compose.project':PROJECT,'com.docker.compose.service':role,'benchmark.role':role,'benchmark.operation':operation}
        intent={'role':role,'operation':operation,'name':name,'image':image['Id'],'memory':memory,'labels':labels}
        self._write(operation+'-'+role+'-intent.json',intent)
        argv=['docker','create','--name',name,'--platform','linux/amd64','--network',PROJECT+'_default',
              '--cpus','2','--memory',str(memory),'--memory-swap',str(memory),'--ulimit','nofile=65535:65535','--user','0:0']
        for key,value in labels.items():argv+=['--label',key+'='+value]
        cid=self._read(argv+options+[reference]+command).strip()
        if not re.fullmatch(r'[0-9a-f]{64}',cid):raise RuntimeError('Ambiguous created container identity; do not start')
        self.registered[cid]=intent
        item=self.verify(cid)
        if item['State']['Running'] or item['State']['Pid']!=0:raise RuntimeError('Created work unexpectedly running before registration')
        self._write(operation+'-'+role+'-created.json',{'Id':cid,**intent})
        return cid

    def create_load(self,vus,smoke,operation):
        validate_attempt(vus,'standard',smoke)
        root=self.root;options=['--workdir','/work/bench','--env','BASE_URL=http://backend:3211','--env','VUS='+str(vus),
            '--env','SMOKE='+str(int(smoke)),'--env','TOKENS=/tokens.json','--env','SUMMARY=/runs/'+operation+'/k6-summary.json']
        for source,destination,readonly in [(root/'bench','/work/bench',True),(root/'.state/convex/benchmark-tokens.json','/tokens.json',True),(root/'.state/convex/runs','/runs',False)]:
            options+=['--mount','type=bind,src='+str(source)+',dst='+destination+(',readonly' if readonly else '')]
        return self._create('k6',operation,options,['run','--quiet','--out','json=/runs/'+operation+'/samples.json.gz','/work/bench/baas.mjs'])

    def create_tools(self,script,operation):
        if not isinstance(script,str) or not script:raise ValueError('Explicit untimed tool command required')
        root=self.root;options=['--workdir','/work/services/convex/app','--env','BASE_URL=http://backend:3211','--env','PYTHONDONTWRITEBYTECODE=1',
            '--env-file',str(root/'.state/convex/cli.env'),'--env-file',str(root/'.state/convex/compat-jwt.env'),
            '--tmpfs','/tmp:mode=1777,size=536870912']
        for source,destination,readonly in [(root,'/work',True),(root/'services/convex/app','/work/services/convex/app',False),(root/'.state/convex','/state/convex',False)]:
            options+=['--mount','type=bind,src='+str(source)+',dst='+destination+(',readonly' if readonly else '')]
        return self._create('tools',operation,options,['bash','-euc',script])

    def verify(self,cid):
        if cid not in self.registered:raise RuntimeError('Unregistered container; refusing lifecycle effects')
        expected=self.registered[cid];item=json.loads(self._read(['docker','inspect',cid]))[0]
        labels=item['Config']['Labels'];host=item['HostConfig']
        if item['Id']!=cid or item['Image']!=expected['image'] or any(labels.get(key)!=value for key,value in expected['labels'].items()):
            raise RuntimeError('Exact recorded container ownership/identity changed')
        if host['NanoCpus']!=2000000000 or host['Memory']!=expected['memory'] or host['MemorySwap']!=expected['memory']:
            raise RuntimeError('Owned tool/runner resource intent differs')
        return item

    def stop_exact(self,cid):
        item=self.verify(cid)
        if item['State']['Running']:self._read(['docker','stop','--time','10',cid])

    def start_and_wait(self,cid,log,*,timeout=1800):
        item=self.verify(cid)
        if item['State']['Running'] or item['State']['Pid']!=0:raise RuntimeError('Only newly created recorded work may start')
        try:
            return subprocess.run(['docker','start','-a',cid],stdout=log,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except BaseException:
            self.stop_exact(cid);raise

    def remove_exact(self,cid):
        item=self.verify(cid)
        if item['State']['Running']:raise RuntimeError('Retain/stop running work before explicit removal')
        self._read(['docker','rm',cid]);del self.registered[cid]
