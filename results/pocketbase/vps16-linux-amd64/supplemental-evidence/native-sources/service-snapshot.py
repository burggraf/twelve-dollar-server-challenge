#!/usr/bin/env python3
"""Read-only service identity snapshot. Never collect argv, environments or config."""
import json
from pathlib import Path
import re
import subprocess
import sys

units=json.loads(subprocess.check_output(['systemctl','list-units','--type=service','--state=running','--no-pager','--output=json'],text=True))
properties=['Id','ActiveState','SubState','MainPID','ActiveEnterTimestampMonotonic','NRestarts']
services={}
for item in units:
    name=item['unit']
    if name.startswith('tds-'): continue
    output=subprocess.check_output(['systemctl','show',name]+['--property='+p for p in properties],text=True)
    services[name]=dict(line.split('=',1) for line in output.splitlines() if '=' in line)
listener=subprocess.check_output(['ss','-H','-lntp','sport = :4000'],text=True)
pids=sorted(set(re.findall(r'pid=(\d+)',listener)))
processes={}
for pid in pids:
    stat=Path('/proc')/pid/'stat'
    processes[pid]={'start_ticks':stat.read_text().rsplit(')',1)[1].split()[19],
                    'executable':str((Path('/proc')/pid/'exe').resolve())}
Path(sys.argv[1]).write_text(json.dumps({'services':services,'port4000_listener':listener,'port4000_processes':processes},indent=2)+'\n')
print('Read-only service snapshot saved; service count:',len(services),'; existing listener PID count:',len(pids))
