"""Approved fixed study only; preserves history and never changes native scoring."""
from copy import deepcopy
from pathlib import Path

PRIOR = ((10000,'lower_anchor','pass'), (11250,'upper_anchor','pass'),
         (12250,'upper_anchor','fail'), (11750,'boundary_probe','fail'),
         (11500,'boundary_probe','fail'), (11250,'candidate_confirmation','pass'),
         (11250,'candidate_confirmation','fail'))
ROUNDS = ((10000,11000,11250), (10000,11250,11000),
          (10000,11000,11250), (10000,11250,11000))


def finish(attempt, prior, record=lambda phase: None, max_attempts=12):
    if type(max_attempts) is not int or not 1 <= max_attempts <= 12:
        raise ValueError('Only twelve further fixed-study attempts are approved')
    rows = prior.get('attempts', [])
    if (prior.get('status') != 'paused_unconfirmed'
            or prior.get('reason') != 'candidate_confirmation contradicted required pass; stop and investigate'
            or prior.get('historical_full_attempts') != 11
            or prior.get('supplemental_limit') != 10
            or prior.get('total_physical_full_attempts_accounted') != 18
            or len(rows) != 7):
        raise ValueError('Exactly the seven preserved paused supplemental attempts are required')
    for row, expected in zip(rows, PRIOR):
        if ((row.get('vus'), row.get('purpose'), row.get('outcome')) != expected
                or not isinstance(row.get('run'), str) or not row['run']):
            raise ValueError('Prior attempts cannot be invalid, missing or relabelled')
    seen = {Path(row['run']).name for row in rows}
    if len(seen) != 7:
        raise ValueError('Prior physical attempts must have distinct run IDs')
    phase = {'status':'in_progress', 'historical_full_attempts':11,
             'prior_supplemental_attempts':7, 'supplemental_limit':19,
             'execution_budget':max_attempts, 'total_physical_full_attempts_accounted':18,
             'attempts':deepcopy(rows), 'boundary_confirmed_by_hold_gates':False,
             'classifications':{'control':'incomplete','candidate':'incomplete','adjacent':'incomplete'},
             'study_result':'incomplete'}

    class Pause(Exception):
        pass

    def save():
        phase['total_physical_full_attempts_accounted'] = 11 + len(phase['attempts'])
        record(deepcopy(phase))

    def classify(vus):
        outcomes = [row['outcome'] for row in phase['attempts'][7:] if row['vus'] == vus]
        if len(outcomes) != 4 or any(value not in ('pass','fail') for value in outcomes):
            return 'incomplete'
        if all(value == 'pass' for value in outcomes):
            return 'all_pass'
        if all(value == 'fail' for value in outcomes):
            return 'all_fail'
        return 'mixed'

    save()  # Failure to persist the initial state prevents all side effects.
    try:
        for round_number, targets in enumerate(ROUNDS, 1):
            for vus in targets:
                if len(phase['attempts']) - 7 >= max_attempts or len(phase['attempts']) >= 19:
                    raise Pause('Fixed-study attempt budget exhausted; no replacement or implicit resume')
                role = {10000:'control',11000:'candidate',11250:'adjacent'}[vus]
                purpose = role + ('_characterization' if round_number == 1 else ('_confirmation' if role == 'candidate' else '_repeat'))
                row = {'vus':vus, 'purpose':purpose, 'round':round_number, 'outcome':None}
                phase['attempts'].append(row)
                save()  # Conservative pending intent BEFORE every callback/physical side effect.
                result = attempt(vus, purpose)
                if not isinstance(result, dict):
                    raise Pause('Malformed native measurement result; never a failing capacity bound')
                row['outcome'] = result.get('outcome')
                for key in ('run','reason'):
                    if key in result:
                        row[key] = result[key]
                save()
                if row['outcome'] not in ('pass','fail'):
                    raise Pause('Invalid/unknown measurement; never a failing capacity bound')
                if not isinstance(row.get('run'), str) or not row['run']:
                    raise Pause('Physical run ID missing; preserve pending/partial evidence without replacement')
                run_id = Path(row['run']).name
                if run_id in seen:
                    raise Pause('Physical run ID reused; no historical or duplicate confirmation')
                seen.add(run_id)
                if vus == 10000 and row['outcome'] != 'pass':
                    raise Pause('Control hold failed; retain outcome, no host-causality assumption or step-down')
        phase['classifications'] = {role:classify(vus) for role,vus in
                                    [('control',10000),('candidate',11000),('adjacent',11250)]}
        c = phase['classifications']
        phase['boundary_confirmed_by_hold_gates'] = c == {'control':'all_pass','candidate':'all_pass','adjacent':'all_fail'}
        if phase['boundary_confirmed_by_hold_gates']:
            phase['study_result'] = 'observed_250vu_boundary'
        elif c['candidate'] != 'all_pass':
            phase['study_result'] = 'candidate_not_confirmed'
        elif c['adjacent'] == 'all_pass':
            phase['study_result'] = 'no_failing_adjacent_boundary'
        else:
            phase['study_result'] = 'mixed_adjacent_boundary'
        phase['status'] = 'complete_pending_human_review'
    except Exception as error:
        phase['status'] = 'paused_unconfirmed'
        phase['reason'] = str(error)
        phase['boundary_confirmed_by_hold_gates'] = False
        phase['classifications'] = {role:classify(vus) for role,vus in
                                    [('control',10000),('candidate',11000),('adjacent',11250)]}
    save()
    return phase
