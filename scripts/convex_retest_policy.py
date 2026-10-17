#!/usr/bin/env python3
"""Versioned strict-uncached ascending policy; never starts or revives a server.

The supplied adapter must distinguish valid SLO failures from runtime/measurement
failures. Reserve and fsync a slot BEFORE entering that adapter. An exception
keeps the outcome null and stops; no resume, replacement, retry or pooled holds.
The original benchmark.campaign and its historical evidence are unchanged.
"""
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import tempfile
import time

PROTOCOL='convex4g-strict-uncached-ascending-v1'
FULL_ATTEMPT_ALLOWANCE_SECONDS=600  # Existing 540s phases plus graceful allowances.


class _TimeBudgetReached(Exception):
    pass


def resolution(vus):
    return 1 if vus<25 else 25 if vus<250 else 250


def campaign(args,tier='standard',attempt_runner=None,results=None,campaign_file=None,clock=time.monotonic):
    """Execute one exclusive, finite campaign; result still requires raw audit.

    Slot accounting is conservative if the adapter raises before its physical
    load-start marker. That marker/raw artifacts, not a null ledger result,
    determine whether traffic actually started. No additional slot is available.
    """
    for name,low,high in [('max_vus',25,2000),('max_attempts',1,16),('time_budget_seconds',1,14400)]:
        value=getattr(args,name,None)
        if type(value) is not int or not low<=value<=high:
            raise ValueError('Outside the approved versioned retest budget: '+name)
    if tier!='standard' or not callable(attempt_runner) or campaign_file is None:
        raise ValueError('Explicit standard-tier adapter and exclusive campaign path required')
    campaign_file=Path(campaign_file)
    journal_file=campaign_file.with_suffix('.journal.jsonl')
    results=Path(results) if results is not None else campaign_file.parent/'campaign-evidence'
    campaign_file.parent.mkdir(parents=True,exist_ok=True)
    lock_fd=os.open(campaign_file.with_suffix('.lock'),os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(lock_fd,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if campaign_file.exists() or campaign_file.is_symlink() or journal_file.exists() or journal_file.is_symlink():
            raise RuntimeError('Retained campaign evidence exists; no implicit resume or overwrite')
        started=clock()
        if type(started) not in (int,float) or not math.isfinite(started):
            raise ValueError('Valid monotonic clock required')
        state={'protocol':PROTOCOL,'tier':tier,'status':'in_progress','maximum_established':False,
               'candidate_vus':None,'upper_failure_vus':None,'resolution_vus':None,
               'confirmation_attempt_indices':[],'attempts':[],'slots_consumed':0,
               'limits':{'max_vus':args.max_vus,'max_attempts':args.max_attempts,'time_budget_seconds':args.time_budget_seconds},
               'started_utc':datetime.now(timezone.utc).isoformat()}
        def elapsed():
            now=clock()
            if type(now) not in (int,float) or not math.isfinite(now) or now<started:
                raise RuntimeError('Monotonic campaign clock invalid; stop')
            return now-started
        def sync_directory():
            fd=os.open(campaign_file.parent,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
        def save(status=None):
            if status is not None:state['status']=status
            state['slots_consumed']=len(state['attempts'])
            with tempfile.NamedTemporaryFile(mode='w',dir=campaign_file.parent,prefix='.campaign-',delete=False) as output:
                temporary=Path(output.name)
                try:
                    json.dump(state,output,indent=2,allow_nan=False);output.write('\n');output.flush();os.fsync(output.fileno())
                except BaseException:
                    temporary.unlink(missing_ok=True);raise
            os.replace(temporary,campaign_file);sync_directory()
        def available():return args.max_attempts-len(state['attempts'])
        def time_available():return args.time_budget_seconds-elapsed()>=FULL_ATTEMPT_ALLOWANCE_SECONDS
        def exhausted():
            return 'unconfirmed_budget_exhausted' if not available() else 'unconfirmed_time_budget'
        with journal_file.open('x') as journal:
            def event(kind,attempt):
                journal.write(json.dumps({'event':kind,'elapsed_seconds':elapsed(),'attempt':attempt},allow_nan=False)+'\n')
                journal.flush();os.fsync(journal.fileno())
            # Exclusive initial creation plus directory fsync, before any adapter.
            with campaign_file.open('x') as output:
                json.dump(state,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())
            sync_directory()
            def run(vus,purpose):
                if not available() or not time_available():raise RuntimeError('Attempt called outside remaining budget; stop')
                row={'index':len(state['attempts'])+1,'vus':vus,'purpose':purpose,'outcome':None,'path':None}
                state['attempts'].append(row);event('reserved',row);save()
                result=attempt_runner(vus,tier)
                if not isinstance(result,(tuple,list)) or len(result)!=2:
                    raise RuntimeError('Malformed adapter verdict; no continuation')
                outcome,path=result
                if outcome not in ('pass','fail','invalid') or not isinstance(path,str) or not path or Path(path).is_absolute() or '..' in Path(path).parts:
                    raise RuntimeError('Unrecognized adapter verdict or artifact identity; no continuation')
                row.update(outcome=outcome,path=path);event('completed',row);save()
                if outcome=='invalid':raise RuntimeError('Invalid measurement; not a target-failure bracket')
                if elapsed()>args.time_budget_seconds:raise _TimeBudgetReached()
                return outcome=='pass'
            low=0;high=None;probes=set()
            try:
                target=25
                while True:
                    if not available() or not time_available():save(exhausted());return
                    if low and available()<=3:break
                    if run(target,'discovery'):
                        low=target;probes.add(target)
                        if target==args.max_vus:break
                        target=min(target*2,args.max_vus)
                    else:
                        high=target;state['upper_failure_vus']=high
                        break
                if low==0:
                    for target in (10,5,1):
                        if not available() or not time_available():save(exhausted());return
                        if run(target,'sub25_probe'):
                            low=target;probes.add(target);break
                        high=target;state['upper_failure_vus']=high
                    if low==0:save('no_passing_probe');return
                while high is not None and high-low>resolution(low):
                    if available()<=3 or not time_available():break
                    step=resolution(low)
                    mid=((low+high)//(2*step))*step
                    mid=max(low+step,min(high-step,mid))
                    if run(mid,'narrowing'):
                        low=mid;probes.add(mid)
                    else:
                        high=mid;state['upper_failure_vus']=high
                while low>0:
                    if low not in probes:
                        if available()<4 or not time_available():save(exhausted());return
                        if run(low,'stepdown_probe'):probes.add(low)
                        else:
                            high=low;state['upper_failure_vus']=high
                            low-=250 if low>250 else 25 if low>25 else 1
                            continue
                    confirmations=[]
                    if available()<3 or not time_available():save(exhausted());return
                    for _ in range(3):
                        if not time_available():save('unconfirmed_time_budget');return
                        if not run(low,'confirmation'):
                            high=low;state['upper_failure_vus']=high
                            break
                        confirmations.append(len(state['attempts']))
                    if len(confirmations)==3:
                        state.update(candidate_vus=low,resolution_vus=resolution(low),confirmation_attempt_indices=confirmations,
                                     boundary_resolution_met=high is not None and high-low<=resolution(low))
                        save('confirmed_lower_bound_pending_human_review');return
                    # Every lower candidate needs its own probe and three fresh
                    # confirmations; earlier favorable holds are never selected.
                    low-=250 if low>250 else 25 if low>25 else 1
                save('no_passing_confirmation')
            except _TimeBudgetReached:
                save('unconfirmed_time_budget')
                return
            except BaseException:
                # Raw exception/details stay in the private native driver log.
                # In particular do not serialize bodies, URLs or secret messages.
                state['reason']='Attempt/controller raised; preserve evidence, no resume or revival'
                save('paused_unconfirmed')
                raise
            finally:
                results.mkdir(parents=True,exist_ok=True)
                with (results/'campaign-final.json').open('x') as output:
                    json.dump(state,output,indent=2,allow_nan=False);output.write('\n');output.flush();os.fsync(output.fileno())
