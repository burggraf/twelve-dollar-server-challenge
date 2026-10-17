"""Blocking control protocol for the new finite serving-path study.

Only explicit structured actions; never execute a supplied shell command. Raw
callbacks and exception text never enter control stdout. EOF/error terminates
owned work via the outer cleanup, rather than adopting retained study state.
"""
import json
from convex_retest_safety import validate_attempt
from convex_retest_session import STAGES


ACTIONS={'prepare':{'action'},'smoke':{'action','vus'},'stage':{'action','stage'},'freeze':{'action'},'capacity':{'action'},'stop':{'action'}}
STATUSES={'confirmed_lower_bound_pending_human_review','confirmed_candidate_pending_human_review','unconfirmed_time_budget','unconfirmed_attempt_budget','no_passing_probe','unconfirmed','stopped_invalid','stopped_runtime_failure'}


def serve(session,stream,emit):
    try:
        emit({'event':'ready','phase':session.phase,'stage':session.stage})
        for line in stream:
            if len(line)>4096:raise RuntimeError('Control command exceeds scope')
            try:
                command=json.loads(line)
                if not isinstance(command,dict) or command.get('action') not in ACTIONS or set(command)!=ACTIONS[command['action']]:raise ValueError()
                action=command['action'];result=None
                if action=='prepare':session.prepare()
                elif action=='smoke':
                    validate_attempt(command['vus'],'standard',True);result=session.smoke(command['vus'])
                elif action=='stage':
                    if command['stage'] not in STAGES:raise ValueError()
                    session.apply_stage(command['stage'])
                elif action=='freeze':session.freeze()
                elif action=='capacity':result=session.capacity()
                elif action=='stop':session.stop()
            except Exception:
                raise RuntimeError('Native control action failed; preserve private evidence, no retry/resume') from None
            report={'event':'complete','action':action,'phase':session.phase,'stage':session.stage}
            if action=='smoke' and isinstance(result,(tuple,list)) and result[0] in ('pass','fail','invalid'):report['outcome']=result[0]
            if action=='capacity' and isinstance(result,dict):
                if result.get('status') in STATUSES:report['status']=result['status']
                candidate=result.get('candidate_vus')
                if type(candidate) is int and 1<=candidate<=2000:report['candidate_vus']=candidate
            emit(report)
            if action=='stop':break
    finally:
        try:
            if session.phase!='stopped':session.stop()
        finally:session.close()
