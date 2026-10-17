"""One exclusive NEW study: shared clock and fsynced reservations before effects.

No implicit resume. Pending/invalid/runtime-failed operations cannot be replaced.
Up to7 planned stop/start cycles leave ordinal8 for terminal stop-only cleanup;
cleanup never unblocks load or grants a start. This is accounting, not evidence
that correctness/lifecycle/continuity or a capacity hold actually passed.
"""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from convex_retest_safety import PROJECT,validate_attempt

STAGES={'baseline','official','pg32','workers64','http8','mutation1','http1'}
LIMITS={'smoke':6,'full':16,'shutdown':8}


def _fingerprint(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{64}',value):
        raise ValueError('Complete gate/host fingerprint required')
    return value


class StudyBudget:
    limits=LIMITS

    def __init__(self,path,*,boot_sha256,clock=time.monotonic,setup_recovery=None):
        self.path=Path(path);self.clock=clock;self.lock=None;self.journal=None;self.prior_setup=None
        _fingerprint(boot_sha256)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        try:
            fd=os.open(self.path.with_suffix('.lock'),os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)
            self.lock=os.fdopen(fd,'w');fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.last_clock=self._now()
            self.state={'protocol':'convex4g-shared-study-budget-v1','project':PROJECT,'boot_sha256':boot_sha256,
                        'sequence_started_monotonic':None,'time_budget_seconds':14400,'limits':dict(self.limits),
                        'correctness_sha256':None,'lifecycle_sha256':None,'blocked':False,'operations':[]}
            if setup_recovery is not None:self.state['setup_recovery']=self._claim_setup_recovery(setup_recovery,boot_sha256)
            fd=os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'w') as output:self._write(output)
            self.journal=self.path.with_suffix('.journal.jsonl').open('x')
            self._sync_directory()
        except (OSError,RuntimeError,ValueError,KeyError,TypeError):
            self.close()
            raise RuntimeError('Retained/occupied study state or invalid clock; no implicit resume/overwrite') from None

    def _claim_setup_recovery(self,proof,boot):
        # A corrected PRE-START preflight may have only another completed
        # terminal reservation. Verify its entire ancestry and carry ALL slots;
        # any actual start/load/clock or failed nonterminal operation forbids it.
        def read(link,approval,depth=0):
            if depth>=6 or not isinstance(link,dict) or set(link) not in ({'prior_path','prior_sha256','approval_sha256'},{'prior_path','prior_sha256','approval_sha256','previous'}):raise ValueError('Explicit bounded setup recovery proof required')
            expected=_fingerprint(link['prior_sha256']);path=Path(link['prior_path'])
            if _fingerprint(link['approval_sha256'])!=approval:raise ValueError('Setup recovery approvals differ')
            with os.fdopen(os.open(path.with_suffix('.lock'),os.O_RDWR|os.O_NOFOLLOW),'r+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as source:raw=source.read(2*1024**2+1)
                if len(raw)>2*1024**2 or hashlib.sha256(raw).hexdigest()!=expected:raise RuntimeError('Prior setup budget bytes differ')
                old=json.loads(raw);rows=old['operations']
                if old['protocol']!='convex4g-shared-study-budget-v1' or old['project']!=PROJECT or old['boot_sha256']!=boot or old['limits']!=LIMITS or old['time_budget_seconds']!=14400 or old['sequence_started_monotonic'] is not None or old['blocked'] is not True or len(rows)!=1:raise RuntimeError('Not the approved unstarted setup ledger')
                ancestors=[]
                if old.get('setup_recovery') is not None:
                    ancestors=read(link['previous'],approval,depth+1)
                    carry=old['setup_recovery']
                    if carry['approval_sha256']!=approval or carry['prior_budget_sha256']!=ancestors[-1][1] or carry['carried_shutdown_reservations']!=len(ancestors):raise RuntimeError('Prior setup ancestry/counters differ')
                elif 'previous' in link:raise ValueError('Unexpected setup ancestry')
                row=rows[0];outcome='pass' if ancestors else None
                if any(row.get(key)!=value for key,value in {'index':1,'kind':'shutdown','kind_index':len(ancestors)+1,'stage':'baseline','vus':None,'final_cleanup':True,'outcome':outcome}.items()):raise RuntimeError('Prior setup is not a closed pre-start terminal reservation')
                return ancestors+[(path,expected)]
        approval=_fingerprint(proof['approval_sha256']);links=read(proof,approval)
        path,expected=links[-1]
        value={'prior_budget_sha256':expected,'approval_sha256':approval,'carried_shutdown_reservations':len(links),'prior_terminal_outcome':None if len(links)==1 else 'pass','ancestor_budget_sha256s':[digest for _,digest in links[:-1]]}
        with os.fdopen(os.open(path.with_suffix('.setup-recovery-claimed.json'),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'w') as output:
            json.dump(value,output);output.flush();os.fsync(output.fileno())
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
        self.prior_setup=links
        return value

    def _verify_recovery(self):
        for path,expected in self.prior_setup or []:
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError('Prior setup evidence drift; no new effects')

    def _now(self):
        value=self.clock()
        if type(value) not in (int,float) or not math.isfinite(value) or value<getattr(self,'last_clock',value):
            raise RuntimeError('Native study monotonic clock invalid')
        self.last_clock=value
        return value

    def _write(self,output):
        json.dump(self.state,output,indent=2,allow_nan=False);output.write('\n');output.flush();os.fsync(output.fileno())

    def _sync_directory(self):
        fd=os.open(self.path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def _save(self):
        with tempfile.NamedTemporaryFile(mode='w',dir=self.path.parent,prefix='.study-budget-',delete=False) as output:
            temporary=Path(output.name)
            try:self._write(output)
            except BaseException:temporary.unlink(missing_ok=True);raise
        os.replace(temporary,self.path);self._sync_directory()

    def _event(self,kind,row):
        self.journal.write(json.dumps({'event':kind,'operation':row},allow_nan=False)+'\n')
        self.journal.flush();os.fsync(self.journal.fileno())

    def _remaining(self):
        now=self._now();start=self.state['sequence_started_monotonic']
        if start is None:raise RuntimeError('Diagnostic/load sequence clock has not started')
        return 14400-(now-start)

    def begin_sequence(self,*,correctness_sha256,lifecycle_sha256):
        _fingerprint(correctness_sha256);_fingerprint(lifecycle_sha256);self._verify_recovery()
        if self.state['sequence_started_monotonic'] is not None or self.state['blocked'] or any(row['outcome'] is None for row in self.state['operations']):
            raise RuntimeError('Sequence already started, blocked or pending; no clock reset')
        self.state.update(sequence_started_monotonic=self._now(),correctness_sha256=correctness_sha256,lifecycle_sha256=lifecycle_sha256)
        self._save()

    def reserve(self,kind,*,stage,vus=None,final_cleanup=False):
        if kind not in LIMITS or stage not in STAGES or type(final_cleanup) is not bool or (final_cleanup and kind!='shutdown'):
            raise ValueError('Unknown/out-of-scope study operation')
        if kind in ('smoke','full'):validate_attempt(vus,'standard',kind=='smoke')
        elif vus is not None:raise ValueError('Shutdown is not a load attempt')
        if not final_cleanup:self._verify_recovery()
        rows=self.state['operations'];count=sum(row['kind']==kind for row in rows)+self.state.get('setup_recovery',{}).get('carried_'+kind+'_reservations',0)
        if count>=self.limits[kind] or (kind=='shutdown' and not final_cleanup and count>=self.limits['shutdown']-1):
            raise RuntimeError('Physical operation budget exhausted; preserve final cleanup slot')
        if not final_cleanup:
            if self.state['blocked'] or any(row['outcome'] is None for row in rows):
                raise RuntimeError('Blocked/pending operation; no implicit replacement')
            if kind!='shutdown' or self.state['sequence_started_monotonic'] is not None:
                required=150 if kind=='smoke' else 600 if kind=='full' else 0
                if self._remaining()<required:raise RuntimeError('Shared diagnostic/full time budget exhausted')
        else:
            # Terminal stop-only cleanup is still counted, even after expiry or
            # a pending failed operation. It never enables another load/start.
            self.state['blocked']=True
        row={'index':len(rows)+1,'kind':kind,'kind_index':count+1,'stage':stage,'vus':vus,
             'final_cleanup':final_cleanup,'outcome':None,'reserved_monotonic':self._now()}
        rows.append(row);self._event('reserved',row);self._save()
        return row['index']

    def complete(self,index,outcome):
        if outcome not in ('pass','fail','invalid','runtime_failure'):raise ValueError('Unrecognized operation verdict')
        rows=self.state['operations']
        if type(index) is not int or not rows or index!=rows[-1]['index'] or rows[-1]['outcome'] is not None:
            raise RuntimeError('Only the latest pending operation may complete once')
        row=rows[-1];row['outcome']=outcome;row['completed_monotonic']=self._now()
        expired=self.state['sequence_started_monotonic'] is not None and self._remaining()<0
        if outcome in ('invalid','runtime_failure') or expired:self.state['blocked']=True
        self._event('completed',row);self._save()
        if expired and not row['final_cleanup']:
            raise RuntimeError('Operation returned after shared diagnostic/full deadline; unconfirmed')

    def close(self):
        if self.journal is not None:self.journal.close();self.journal=None
        if self.lock is not None:self.lock.close();self.lock=None
