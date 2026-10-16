"""Owner f81b2fc4 clarification; no named unit exceptions, no event deletion."""


def partition(units, no_resident_processes):
    result = {'persistent': [], 'transient': []}
    for name, value in units.items():
        for key in ('Type', 'ActiveState', 'SubState'):
            if not isinstance(value.get(key), str) or not value[key]:
                raise RuntimeError('Incomplete unit classification properties')
        for key in ('MainPID', 'ControlPID'):
            if not isinstance(value.get(key), str) or not value[key].isdigit():
                raise RuntimeError('Invalid unit main/control process evidence')
        completed = (value['Type'] == 'oneshot'
                     and (value['ActiveState'], value['SubState']) in
                         {('active', 'exited'), ('inactive', 'dead')}
                     and int(value['MainPID']) == int(value['ControlPID']) == 0
                     and value.get('Job', None) in ('', '0'))
        transient = False
        if completed:
            proof = no_resident_processes.get(name)
            if type(proof) is not bool:
                raise RuntimeError('No complete resident-process evidence for completed oneshot')
            transient = proof
        result['transient' if transient else 'persistent'].append(name)
    return {key: sorted(value) for key, value in result.items()}
