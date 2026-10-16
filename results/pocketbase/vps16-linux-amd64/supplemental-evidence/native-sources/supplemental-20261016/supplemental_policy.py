"""Owner-approved bounded follow-up policy; no product/scoring implementation."""
from copy import deepcopy


def finish(attempt, record=lambda phase: None, max_attempts=10):
    if type(max_attempts) is not int or not 1 <= max_attempts <= 10:
        raise ValueError('Owner approved at most ten supplemental attempts')
    phase = {'status': 'in_progress', 'historical_full_attempts': 11,
             'supplemental_limit': 10, 'execution_budget': max_attempts,
             'total_physical_full_attempts_accounted': 11, 'attempts': []}

    class Pause(Exception):
        pass

    def save():
        phase['total_physical_full_attempts_accounted'] = 11 + len(phase['attempts'])
        record(deepcopy(phase))

    def run(vus, purpose, expected=None):
        if len(phase['attempts']) >= max_attempts:
            raise Pause('Supplemental attempt budget exhausted; no implicit extension')
        row = {'vus': vus, 'purpose': purpose, 'outcome': None}
        phase['attempts'].append(row)
        save()  # Persist intent BEFORE a physical side effect, including partial failures.
        value = attempt(vus, purpose)
        row['outcome'] = value['outcome']
        for name in ['run', 'reason']:
            if name in value:
                row[name] = value[name]
        save()
        if row['outcome'] not in ('pass', 'fail'):
            raise Pause('Invalid/unknown measurement; never use it as a target-failure bracket')
        if expected is not None and row['outcome'] != expected:
            raise Pause(purpose + ' contradicted required ' + expected + '; stop and investigate')
        return row['outcome']

    save()
    try:
        run(10000, 'lower_anchor', 'pass')
        run(11250, 'upper_anchor', 'fail')
        lower, upper = 10000, 11250
        while upper - lower > 250:
            middle = ((lower + upper) // 500) * 250
            if run(middle, 'boundary_probe') == 'pass':
                lower = middle
            else:
                upper = middle
        phase.update(candidate_vus=lower, upper_vus=upper)
        save()
        for _ in range(3):
            run(lower, 'candidate_confirmation', 'pass')
        # Exactly one fresh failure already established this upper bound.
        for _ in range(2):
            run(upper, 'upper_confirmation', 'fail')
        phase['status'] = 'confirmed_pending_evidence_review'
    except Exception as error:
        phase['status'] = 'paused_unconfirmed'
        phase['reason'] = str(error)
    save()
    return phase
