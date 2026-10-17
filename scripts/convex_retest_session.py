"""Versioned ordering around explicit native operations, not a serving adapter.

No constructor deployment, implicit resume, retry or background work. Operations
must themselves verify actual ownership/host/source/correctness/continuity,
known-shutdown matching/data recovery and complete monitoring. Hash fields here
link that evidence; a fake operation in a unit test proves NO native gate.
"""
import json
from pathlib import Path
import re
import time
from types import SimpleNamespace
from convex_retest_budget import StudyBudget
from convex_retest_policy import campaign
from convex_retest_safety import validate_attempt

STAGES=('baseline','official','pg32','workers64','http8','mutation1','http1')


def _gate(value,lifecycle=True):
    names=('correctness_sha256','lifecycle_sha256') if lifecycle else ('correctness_sha256',)
    if not isinstance(value,dict) or any(not isinstance(value.get(name),str) or not re.fullmatch(r'[0-9a-f]{64}',value[name]) for name in names):
        raise RuntimeError('Complete actual gate evidence fingerprints required')
    return {name:value[name] for name in names}


class Session:
    def __init__(self,directory,*,boot_sha256,operations,clock=time.monotonic,setup_recovery=None):
        self.directory=Path(directory);self.ops=operations;self.clock=clock
        self.budget=StudyBudget(self.directory/'study-budget.json',boot_sha256=boot_sha256,clock=clock,setup_recovery=setup_recovery)
        self.phase='new';self.stage='baseline';self.gate={};self.smoked={}

    def _require(self,phase):
        if self.phase!=phase:raise RuntimeError('Session phase does not permit this operation')

    def _restart(self,stage):
        index=self.budget.reserve('shutdown',stage=stage)
        # Native operations retain exact intent/target/kernel/log/data evidence;
        # completion means an authorized transition, NOT a clean shutdown.
        proof=_gate(self.ops.restart(stage,index))
        self.budget.complete(index,'pass');self.gate=proof;self.stage=stage

    def prepare(self):
        self._require('new')
        try:
            _gate(self.ops.prepare(),lifecycle=False)
            self._restart('baseline');self.phase='diagnostics'
        except BaseException:
            self.phase='paused';raise

    def _recheck(self):
        try:self.ops.recheck(self.stage,self.gate)
        except BaseException:
            self.phase='paused';raise

    def _measured(self):
        return self.smoked.get(('baseline',25))=='pass' and self.smoked.get(('baseline',100))=='pass' and self.smoked.get((self.stage,100))=='pass'

    def _attempt(self,vus,smoke):
        validate_attempt(vus,'standard',smoke);self._recheck()
        if self.budget.state['sequence_started_monotonic'] is None:
            self.budget.begin_sequence(**self.gate)
        index=self.budget.reserve('smoke' if smoke else 'full',vus=vus,stage=self.stage)
        try:
            result=self.ops.attempt(vus,smoke,self.stage)
            if not isinstance(result,(tuple,list)) or len(result)!=2:raise RuntimeError('Malformed native attempt verdict')
            outcome,path=result
            if outcome not in ('pass','fail','invalid') or not isinstance(path,str) or not re.fullmatch(r'[A-Za-z0-9_./-]+',path) or Path(path).is_absolute() or '..' in Path(path).parts:
                raise RuntimeError('Unrecognized native attempt verdict/artifact identity')
            self.budget.complete(index,outcome)
            if outcome=='invalid':raise RuntimeError('Invalid measurement; no continuation')
            return outcome,path
        except BaseException:
            # Unknown callbacks remain pending/null; no private exception text
            # enters this session's ledger. Raw details belong in native logs.
            self.phase='paused';raise

    def smoke(self,vus):
        validate_attempt(vus,'standard',True);self._require('diagnostics')
        key=(self.stage,vus)
        if key in self.smoked or (self.stage!='baseline' and vus!=100) or (self.stage=='baseline' and vus==100 and ('baseline',25) not in self.smoked):
            raise RuntimeError('Smoke is not the next predeclared diagnostic; no replacement')
        result=self._attempt(vus,True);self.smoked[key]=result[0]
        return result

    def apply_stage(self,stage):
        self._require('diagnostics')
        if stage not in STAGES:raise ValueError('Unknown sizing stage')
        current=STAGES.index(self.stage)
        if not self._measured() or current+1>=len(STAGES) or stage!=STAGES[current+1]:
            raise RuntimeError('Only the next predeclared trial after measured passing control is permitted')
        self._recheck()
        # This read-only eligibility check is BEFORE a shutdown reservation.
        # Missing/invalid measurement must already fail recheck; an ineligible
        # OPTIONAL candidate need not mutate the currently measured profile.
        self.ops.check_stage(stage)
        try:self._restart(stage)
        except BaseException:
            self.phase='paused';raise

    def freeze(self):
        self._require('diagnostics')
        if not self._measured():raise RuntimeError('Measured passing current profile required before freeze')
        self._recheck()
        try:
            self.gate=_gate(self.ops.freeze(self.stage));self.phase='capacity_ready'
        except BaseException:
            self.phase='paused';raise
        return dict(self.gate)

    def capacity(self):
        self._require('capacity_ready');self._recheck()
        remaining=int(self.budget._remaining())
        if remaining<1:
            self.phase='finished'
            return {'status':'unconfirmed_time_budget','candidate_vus':None,'maximum_established':False}
        used=sum(row['kind']=='full' for row in self.budget.state['operations'])
        args=SimpleNamespace(max_vus=2000,max_attempts=16-used,time_budget_seconds=min(14400,remaining))
        try:
            campaign(args,'standard',attempt_runner=lambda vus,tier:self._attempt(vus,False),
                     campaign_file=self.directory/'capacity-campaign.json',results=self.directory/'capacity-evidence',clock=self.clock)
            result=json.loads((self.directory/'capacity-campaign.json').read_text())
            self.phase='finished';return result
        except BaseException:
            self.phase='paused';raise

    def stop(self):
        if self.phase=='stopped':raise RuntimeError('Terminal cleanup already requested; no retry')
        index=self.budget.reserve('shutdown',stage=self.stage,final_cleanup=True)
        try:
            self.ops.stop(self.stage,index);self.budget.complete(index,'pass');self.phase='stopped'
        except BaseException:
            self.phase='paused';raise

    def close(self):self.budget.close()
