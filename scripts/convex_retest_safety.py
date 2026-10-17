"""Narrow owner amendment for the NEW namespace; never revive an old campaign.

This evaluates a predeclared transition's actual native observations; it performs
no lifecycle action. The controller must durably reserve the ordinal BEFORE the
stop, retain matching logs/kernel evidence, and verify acknowledged data AFTER
every permitted start. A139 remains FAILED, not a clean-lifecycle certificate.
"""
import re
import json

PROJECT='baas-convex4g-retest-v1'


def validate_attempt(vus,tier,smoke):
    if type(vus) is not int or tier!='standard' or type(smoke) is not bool or not 1<=vus<=2000 or (smoke and vus not in (25,100)):
        raise ValueError('Outside approved fresh standard-tier retest traffic scope')
    return True


def known_teardown_matches(backend_log,kernel_jsonl,*,owned_tids):
    """Match the known isolate-thread fault, NOT just container PID1.

    The caller must capture these task IDs from /proc/ownedPID/task BEFORE its
    predeclared SIGINT and bound/filter the kernel journal to that interval.
    This returns a boolean only; malformed/private raw bodies are never echoed.
    """
    if not isinstance(backend_log,bytes) or not isinstance(kernel_jsonl,bytes) or len(backend_log)>8*1024**2 or len(kernel_jsonl)>1024**2:
        return False
    if not isinstance(owned_tids,(set,frozenset)) or not owned_tids or len(owned_tids)>4096 or any(type(tid) is not int or tid<=0 for tid in owned_tids):
        return False
    if b'A Tokio 1.x context was found, but it is being shutdown.' not in backend_log:return False
    try:
        matched=False
        for line in kernel_jsonl.splitlines():
            value=json.loads(line);message=value['MESSAGE']
            if not isinstance(message,str):return False
            found=re.search(r'(?:^|\b)traps: isolate\[([0-9]+)\] general protection fault\b',message)
            if found and int(found.group(1)) in owned_tids:matched=True
        return matched
    except (ValueError,KeyError,TypeError,UnicodeError):return False


def project_container_ids(capture):
    """Docker ps truncates IDs by default; identity gates require full IDs."""
    ids=set(capture(['docker','ps','-aq','--no-trunc','--filter','label=com.docker.compose.project='+PROJECT]).split())
    if any(not re.fullmatch(r'[a-f0-9]{64}',item) for item in ids):raise RuntimeError('Full owned namespace container IDs unavailable')
    return ids


def setup_recovery_targets(before,after):
    """Explicit setup recovery ONLY: exact retained clean exits, never revival.

    before is the actual private pre-stop Docker snapshot. Authorization and
    the unstarted/prior-NULL ledger proof are separate mandatory caller gates.
    No raw configuration/credentials/paths appear in returned errors or data.
    """
    try:
        if set(before)!= {'backend','postgres'} or set(after)!=set(before):raise ValueError()
        result={}
        for role in before:
            prior,current=before[role],after[role]
            if any(current[key]!=prior[key] for key in ('Id','Image','RestartCount','Config','HostConfig','Mounts')):raise ValueError()
            if not re.fullmatch(r'[a-f0-9]{64}',current['Id']) or not re.fullmatch(r'sha256:[a-f0-9]{64}',current['Image']):raise ValueError()
            labels=current['Config']['Labels'];host=current['HostConfig'];state=current['State']
            memory=3221225472 if role=='backend' else 1073741824
            if labels.get('com.docker.compose.project')!=PROJECT or labels.get('com.docker.compose.service')!=role:raise ValueError()
            if host['CgroupParent']!='tdsbaasconvex4gretestv1.slice' or host['NanoCpus']!=1000000000 or host['Memory']!=memory or host['MemorySwap']!=memory:raise ValueError()
            if any(state[key] is not False for key in ('Running','OOMKilled','Paused','Restarting','Dead')) or state['Pid']!=0 or state['ExitCode']!=0:raise ValueError()
            volume=PROJECT+('_data' if role=='backend' else '_pgdata')
            if not any(item.get('Type')=='volume' and item.get('Name')==volume and item.get('RW') is True for item in current['Mounts']):raise ValueError()
            result[role]=current['Id']
        return result
    except (ValueError,KeyError,TypeError):
        raise RuntimeError('Retained setup identity/state/configuration differs; no recovery start') from None


def planned_shutdown(intent,observed,*,approved_transition_limit=8):
    try:
        if type(approved_transition_limit) is not int or approved_transition_limit not in (8,11):raise ValueError()
        if intent['project']!=PROJECT or observed['project']!=PROJECT:raise ValueError()
        if type(intent['ordinal']) is not int or not 1<=intent['ordinal']<=approved_transition_limit:raise ValueError()
        if intent['signal']!='SIGINT':raise ValueError()
        for key in ('predeclared','was_running','known_shutdown_exception_approved'):
            if intent[key] is not True:raise ValueError()
        for key,pattern in [('container_id',r'[0-9a-f]{64}'),('image_id',r'sha256:[0-9a-f]{64}')]:
            if not isinstance(intent[key],str) or not re.fullmatch(pattern,intent[key]) or observed[key]!=intent[key]:raise ValueError()
        for key,expected in [('stop_request_issued',True),('running',False),('oom_killed',False),('unexpected_serving_failure',False)]:
            if observed[key] is not expected:raise ValueError()
        before=observed['parent_oom_before'];after=observed['parent_oom_after']
        for key in ('oom','oom_kill','oom_group_kill'):
            if type(before[key]) is not int or type(after[key]) is not int or before[key]!=0 or after[key]!=0:raise ValueError()
        exit_code=observed['exit_code'];matched=observed['known_teardown_evidence_matches']
        if type(exit_code) is not int or type(matched) is not bool:raise ValueError()
        if exit_code!=0 and not (exit_code==139 and matched):raise ValueError()
    except (KeyError,TypeError,ValueError):
        raise RuntimeError('Unmatched/unapproved shutdown or serving/OOM failure; no start permitted') from None
    return {'clean_shutdown':'PASS' if exit_code==0 else 'FAILED',
            'scope':'serving-path-only','planned_start_permitted':True,
            'acknowledged_data_reverification_required':True,
            'power_loss_durability_certified':False}
