"""Prospective continuity only. Never rewrites an older failed identity comparison."""
from collections import Counter

LIFECYCLE = ('Starting ', 'Started ', 'Stopping ', 'Stopped ',
             'Main process exited', 'Failed with result', 'Scheduled restart job')


def event_counts(entries, watched):
    counts = Counter()
    for entry in entries:
        unit, message = entry.get('UNIT'), entry.get('MESSAGE')
        if unit in watched and unit != 'user@0.service' and isinstance(message, str):
            if any(pattern in message for pattern in LIFECYCLE):
                counts[unit] += 1
    return dict(counts)


def require_dmarie_off(value):
    if (value.get('ActiveState') != 'inactive' or value.get('SubState') != 'dead'
            or value.get('UnitFileState') != 'disabled' or value.get('MainPID') != '0'
            or value.get('Job', '') not in ('', '0')):
        raise RuntimeError('Owner-paused dmarie is not disabled/inactive/dead without a pending job')


def require_host_context(expected, actual):
    if expected != actual:
        raise RuntimeError('Prospective host boot/kernel/Docker/CPU/memory identity changed')


def require_continuity(baseline, before, after, counts, complete):
    if complete is not True:
        raise RuntimeError('Continuous service journal window unavailable/incomplete')
    if not isinstance(counts, dict) or any(type(v) is not int or v < 0 for v in counts.values()):
        raise RuntimeError('Malformed service lifecycle counts')
    if any(counts.values()):
        raise RuntimeError('Persistent-service lifecycle events observed; keep continuity failed')
    expected = {k:v for k,v in baseline['services'].items() if k != 'user@0.service'}
    for current in (before, after):
        actual = {k:v for k,v in current['services'].items() if k != 'user@0.service'}
        if expected != actual:
            raise RuntimeError('Persistent-service identity differs from prospective frozen baseline')
        if current['port4000_processes'] != baseline['port4000_processes']:
            raise RuntimeError('Prospective unrelated port4000 listener identity changed')
