"""Explicitly authorized continuation; preserve two old slots, at most eight new."""
from copy import deepcopy


def finish(attempt, prior, record=lambda phase: None, max_attempts=8):
    if type(max_attempts) is not int or not 1 <= max_attempts <= 8:
        raise ValueError('Owner approved only eight remaining supplemental attempts')
    rows = prior.get('attempts', [])
    if (prior.get('status') != 'paused_unconfirmed'
            or prior.get('reason') != 'upper_anchor contradicted required fail; stop and investigate'
            or len(rows) != 2):
        raise ValueError('Exactly the two preserved paused anchor attempts are required')
    for row, vus, purpose in zip(rows, [10000, 11250], ['lower_anchor', 'upper_anchor']):
        if (row.get('vus') != vus or row.get('purpose') != purpose
                or row.get('outcome') != 'pass' or not row.get('run')):
            raise ValueError('Prior anchors cannot be missing, invalid or relabelled')
    if rows[0]['run'] == rows[1]['run']:
        raise ValueError('Prior anchors must be independent physical attempts')
    phase = {'status': 'in_progress', 'historical_full_attempts': 11,
             'supplemental_limit': 10, 'execution_budget': max_attempts,
             'prior_supplemental_attempts': 2,
             'total_physical_full_attempts_accounted': 13,
             'attempts': deepcopy(rows)}

    class Pause(Exception):
        pass

    def save():
        phase['total_physical_full_attempts_accounted'] = 11 + len(phase['attempts'])
        record(deepcopy(phase))

    def run(vus, purpose, expected=None):
        if len(phase['attempts']) - 2 >= max_attempts or len(phase['attempts']) >= 10:
            raise Pause('Remaining supplemental attempt budget exhausted; no reset/extension')
        row = {'vus': vus, 'purpose': purpose, 'outcome': None}
        phase['attempts'].append(row)
        save()  # Keep conservative pending intent BEFORE every physical side effect.
        value = attempt(vus, purpose)
        row['outcome'] = value['outcome']
        for name in ['run', 'reason']:
            if name in value:
                row[name] = value[name]
        save()
        if row['outcome'] not in ('pass', 'fail'):
            raise Pause('Invalid/unknown measurement; never a target-failure bracket')
        if expected is not None and row['outcome'] != expected:
            raise Pause(purpose + ' contradicted required ' + expected + '; stop and investigate')
        return row['outcome']

    save()
    try:
        run(12250, 'upper_anchor', 'fail')
        lower, upper = 11250, 12250
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
        for _ in range(2):
            run(upper, 'upper_confirmation', 'fail')
        phase['status'] = 'confirmed_pending_evidence_review'
    except Exception as error:
        phase['status'] = 'paused_unconfirmed'
        phase['reason'] = str(error)
    save()
    return phase
