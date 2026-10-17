"""Bounded read-only NEW-namespace observation; raw inputs stay private.

No serving SQL, restart, load launch or implicit adoption. Missing evidence raises;
the serving adapter must promptly stop only its exact-owned runner on failure.
V8 gauges, process RSS and charged cgroup memory are overlapping views, NOT sums.
Unlabelled native aggregate heap gauges may reflect the last reporting pool;
pool maxima/active counts do not prove allocated-worker counts or a leak cause.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request
from convex_retest_metrics import parse_metrics,process_memory
from convex_retest_safety import PROJECT

SLICE='tdsbaasconvex4gretestv1.slice'
MEMORY={'parent':4294967296,'backend':3221225472,'postgres':1073741824}
KERNEL=('cpu.max','cpu.stat','cpu.pressure','memory.max','memory.current','memory.peak','memory.swap.max','memory.events','memory.stat','memory.pressure','io.stat','io.pressure')
SQL="""SELECT json_build_object(
 'settings',json_build_object(
  'max_connections',current_setting('max_connections'),
  'reserved_connections',current_setting('reserved_connections'),
  'superuser_reserved_connections',current_setting('superuser_reserved_connections'),
  'fsync',current_setting('fsync'),'synchronous_commit',current_setting('synchronous_commit'),
  'full_page_writes',current_setting('full_page_writes'),'work_mem',current_setting('work_mem')),
 'connections',(SELECT json_build_object(
  'total',count(*),'client_backends',count(*) FILTER (WHERE backend_type='client backend'),
  'active',count(*) FILTER (WHERE backend_type='client backend' AND state='active'),
  'idle',count(*) FILTER (WHERE backend_type='client backend' AND state='idle'),
  'idle_in_transaction',count(*) FILTER (WHERE backend_type='client backend' AND state LIKE 'idle in transaction%'),
  'waiting',count(*) FILTER (WHERE backend_type='client backend' AND state='active' AND wait_event IS NOT NULL))
  FROM pg_stat_activity));
"""


class ObservationError(RuntimeError):
    """Sanitized failure reason; never attach raw bodies/commands/credentials."""


def _fetch():
    from convex import _NoRedirect
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
    with opener.open('http://127.0.0.1:13211/metrics',timeout=2) as response:
        return response.read(8*1024**2+1)


class Observer:
    def __init__(self,directory,baseline,*,capture=subprocess.check_output,fetch=_fetch,proc=Path('/proc'),cgroups=Path('/sys/fs/cgroup'),clock=time.time):
        if baseline.get('project')!=PROJECT or baseline.get('slice')!=SLICE or set(baseline.get('targets',{}))!={'backend','postgres'}:
            raise ObservationError('Only exact new serving namespace may be observed')
        self.baseline=copy.deepcopy(baseline);self.capture=capture;self.fetch=fetch
        self.proc=Path(proc);self.cgroups=Path(cgroups);self.clock=clock;self.index=0
        self.directory=Path(directory);self.directory.mkdir(mode=0o700,parents=True,exist_ok=False)

    def _read(self,argv,**kwargs):
        return self.capture(argv,text=True,stderr=subprocess.PIPE,timeout=5,**kwargs)

    def _private(self,name,data):
        if isinstance(data,str):data=data.encode()
        fd=os.open(self.directory/(f'{self.index:06d}-'+name),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as output:output.write(data);output.flush()
        return hashlib.sha256(data).hexdigest()

    def _runtime(self,records):
        if not isinstance(records,list) or len(records)!=2:raise ObservationError('Required runtime observation missing')
        by_id={item['Id']:item for item in records}
        for role,expected in self.baseline['targets'].items():
            current=by_id.get(expected['Id'])
            if current is None:raise ObservationError('Owned runtime replaced or missing')
            state=current['State'];before=expected['State'];labels=current['Config']['Labels']
            if labels.get('com.docker.compose.project')!=PROJECT or labels.get('com.docker.compose.service')!=role:
                raise ObservationError('Runtime ownership differs')
            if current['Image']!=expected['Image'] or current['RestartCount']!=expected['RestartCount'] or state['StartedAt']!=before['StartedAt'] or type(state['Pid']) is not int or state['Pid']<=0 or state['Pid']!=before['Pid']:
                raise ObservationError('Runtime image/process identity changed')
            if state.get('Running') is not True or any(state.get(key) is not False for key in ('OOMKilled','Paused','Restarting')) or state.get('Health',{}).get('Status')!='healthy':
                raise ObservationError('Serving runtime OOM/exit/restart/pause/unhealthy; stop')
        return by_id

    def _kernel(self):
        groups={'parent':self.cgroups/SLICE}
        for role,item in self.baseline['targets'].items():
            cid=item['Id']
            if not isinstance(cid,str) or not re.fullmatch(r'[0-9a-f]{64}',cid):raise ObservationError('Malformed owned runtime identity')
            expected='/'+SLICE+'/docker-'+cid+'.scope'
            membership=(self.proc/str(item['State']['Pid'])/'cgroup').read_text().strip()
            if membership!='0::'+expected:raise ObservationError('Serving cgroup membership changed/escaped')
            groups[role]=self.cgroups/expected.lstrip('/')
        return {role:{key:(path/key).read_text() for key in KERNEL} for role,path in groups.items()}

    def _validate_kernel(self,groups):
        for role,fields in groups.items():
            if fields['cpu.max'].split()!=['100000','100000'] or fields['memory.max'].strip()!=str(MEMORY[role]) or fields['memory.swap.max'].strip()!='0':
                raise ObservationError('Actual parent/child CPU/memory/swap limits changed')
            events=dict(line.split() for line in fields['memory.events'].splitlines())
            if any(int(events[key])!=0 for key in ('oom','oom_kill','oom_group_kill')):
                raise ObservationError('Serving parent/child OOM event; no continuation')
            if any(not fields[key].strip() for key in KERNEL if key!='io.stat'):
                raise ObservationError('Incomplete actual kernel observation')

    def _postgres(self,value):
        if not isinstance(value,dict):raise ObservationError('PG metadata observation missing')
        settings=value['settings'];connections=value['connections']
        for name in ('fsync','synchronous_commit','full_page_writes'):
            if settings[name]!='on':raise ObservationError('Native PG durability differs')
        for name in ('max_connections','reserved_connections','superuser_reserved_connections'):
            if not isinstance(settings[name],str) or not re.fullmatch(r'[0-9]+',settings[name]):raise ObservationError('Malformed PG connection setting')
        if int(settings['max_connections'])<=int(settings['reserved_connections'])+int(settings['superuser_reserved_connections']):
            raise ObservationError('No ordinary PG connection budget')
        if not isinstance(settings['work_mem'],str) or not re.fullmatch(r'[0-9]+(?:kB|MB|GB|B)?',settings['work_mem']):raise ObservationError('Native work_mem metadata missing')
        counts={}
        for name in ('total','client_backends','active','idle','idle_in_transaction','waiting'):
            if type(connections[name]) is not int or connections[name]<0:raise ObservationError('Missing/invalid PG connection counts')
            counts[name]=connections[name]
        if counts['client_backends']>counts['total'] or any(counts[key]>counts['client_backends'] for key in ('active','idle','idle_in_transaction','waiting')):
            raise ObservationError('Inconsistent PG connection counts')
        return {'settings':{name:settings[name] for name in ('max_connections','reserved_connections','superuser_reserved_connections','fsync','synchronous_commit','full_page_writes','work_mem')},'connections':counts}

    def sample(self):
        self.index+=1;started=self.clock();raw={}
        try:
            ids=[item['Id'] for item in self.baseline['targets'].values()]
            runtime=self._read(['docker','inspect',*ids]);raw['runtime']=self._private('runtime-private.json',runtime)
            self._runtime(json.loads(runtime))
            groups=self._kernel();raw['cgroups']=self._private('cgroups-original.json',json.dumps(groups))
            self._validate_kernel(groups)
            processes={role:process_memory(item['State']['Pid'],proc=self.proc) for role,item in self.baseline['targets'].items()}
            text=self.fetch()
            if not isinstance(text,bytes) or len(text)>8*1024**2:raise ObservationError('Native metrics exceed observation bound')
            raw['metrics']=self._private('metrics-private.txt',text);metrics=parse_metrics(text.decode())
            for suffix in ('cache_size_bytes','cache_plan_ready_total','cache_plan_wait_total'):
                if any(value!=0 for value in metrics.get('convex_local_backend_'+suffix,[])):
                    raise ObservationError('Strict uncached native serving invariant failed')
            pg_id=self.baseline['targets']['postgres']['Id']
            argv=['docker','exec','-i','--env','PGCONNECT_TIMEOUT=2','--env','PGOPTIONS=-c statement_timeout=1000 -c lock_timeout=500',pg_id,
                  'sh','-euc','export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -XqAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres']
            pg=self._read(argv,input=SQL)
            if len(pg)>2*1024**2:raise ObservationError('PG metadata exceeds bound')
            raw['postgres']=self._private('postgres-original.json',pg);postgres=self._postgres(json.loads(pg))
            finished=self.clock()
            if finished<started:raise ObservationError('Native observation clock regressed')
            return {'sample_index':self.index,'started_unix':started,'finished_unix':finished,'processes':processes,
                    'metrics':metrics,'postgres':postgres,'cgroups':groups,'raw_sha256':raw}
        except ObservationError:raise
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError):
            raise ObservationError('Required native observation unavailable/malformed; retain raw private inputs and stop') from None
