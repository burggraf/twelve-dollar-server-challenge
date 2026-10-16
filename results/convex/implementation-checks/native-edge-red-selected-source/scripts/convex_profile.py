#!/usr/bin/env python3
"""Fail-closed aggregate attestation for the native PostgreSQL-backed candidate."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'baas-convexpg-vps16'
SLICE = 'tdsbaasconvexpgvps16.slice'
MEMORY = {'backend': 3221225472, 'postgres': 1073741824}


def validate_stack(value):
    """Require both native servers and their actual shared parent/child limits."""
    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    try:
        backend = json.loads((ROOT / 'services/convex/versions.json').read_text())
        postgres = json.loads((ROOT / 'services/convex/postgres-versions.json').read_text())
        expected = {'backend': backend['backend']['amd64_manifest'], 'postgres': postgres['amd64_manifest']}
        targets = value['targets']
        require(set(targets) == set(expected), 'Both native serving processes must be accounted for')
        parent = value['parent']
        require(parent['cpu.max'].split() == ['100000', '100000'], 'Entire serving CPU quota must be one core')
        require(parent['memory.max'].strip() == '4294967296', 'Entire serving memory must be exactly 4 GiB')
        require(parent['memory.swap.max'].strip() == '0', 'Serving swap must be zero')
        children = []
        for role, manifest in expected.items():
            target = targets[role]
            identity = target['Id']
            require(bool(re.fullmatch(r'[0-9a-f]{64}', identity)), 'Missing full native container identity')
            require(target['platform'] == 'linux/amd64', 'Serving images must be native Linux AMD64')
            require(target['image_manifest_digest'] == manifest, 'Pinned serving image differs: ' + role)
            require(target['compose_project'] == PROJECT, 'Serving project ownership differs: ' + role)
            require(target['cgroup_parent'] == SLICE, 'Serving parent differs: ' + role)
            scope = 'docker-' + identity + '.scope'
            require(target['process_cgroup'].strip() == f'0::/{SLICE}/{scope}', 'Actual process is outside serving parent: ' + role)
            children.append(scope)
            state = target['State']
            require(state['Running'] is True and state['OOMKilled'] is False, 'Native serving process is not healthy/running: ' + role)
            require(state['Health']['Status'] == 'healthy', 'Native serving health failed: ' + role)
            limits = target['limits']
            require(limits['NanoCpus'] == 1000000000, 'Child CPU quota differs: ' + role)
            require(limits['Memory'] == MEMORY[role] and limits['MemorySwap'] == MEMORY[role], 'Child memory/swap allocation differs: ' + role)
            kernel = target['kernel']
            require(kernel['cpu.max'].split() == ['100000', '100000'], 'Actual child CPU quota differs: ' + role)
            require(kernel['memory.max'].strip() == str(MEMORY[role]), 'Actual child memory differs: ' + role)
            require(kernel['memory.swap.max'].strip() == '0', 'Actual child swap differs: ' + role)
        require(sorted(parent['children']) == sorted(children), 'Unaccounted serving cgroup children')
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise RuntimeError('Malformed or incomplete native serving attestation') from error
    return True
