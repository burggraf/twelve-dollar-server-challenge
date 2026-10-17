"""Strict native continuity; the Convex-only fwupd waiver is NOT applicable here.

Pure event/oneshot predicates preserve the previously approved uniform algorithm.
Raw journal and service evidence remains native-private, including failed windows.
"""
from collections import Counter
import hashlib,json,math,os,platform,subprocess,time
from pathlib import Path
import nhost as control
LIFECYCLE=('Starting ','Started ','Stopping ','Stopped ','Main process exited','Failed with result','Scheduled restart job','Deactivated successfully.','Reloading ','Reloaded ')
def event_counts(entries,watched):
 counts=Counter()
 for entry in entries:
  unit,message=entry.get('UNIT'),entry.get('MESSAGE')
  if unit in watched and unit!='user@0.service' and isinstance(message,str) and any(pattern in message for pattern in LIFECYCLE):counts[unit]+=1
 return dict(counts)
def partition(units,resident):
 result={'persistent':[],'transient':[]}
 for name,value in units.items():
  if any(not isinstance(value.get(key),str) or not value[key] for key in ['Type','ActiveState','SubState']):raise RuntimeError('Incomplete unit classification')
  if any(not isinstance(value.get(key),str) or not value[key].isdigit() for key in ['MainPID','ControlPID']):raise RuntimeError('Incomplete unit process evidence')
  completed=value['Type']=='oneshot' and (value['ActiveState'],value['SubState']) in {('active','exited'),('inactive','dead')} and int(value['MainPID'])==int(value['ControlPID'])==0 and value.get('Job',None) in ('','0')
  if completed and type(resident.get(name)) is not bool:raise RuntimeError('Completed oneshot lacks positive resident proof')
  result['transient' if completed and resident[name] else 'persistent'].append(name)
 return {key:sorted(value) for key,value in result.items()}
def sha(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def host():
 return {'boot':sha('/proc/sys/kernel/random/boot_id'),'machine':sha('/etc/machine-id'),'kernel':platform.release(),'docker':sha('/usr/bin/docker'),'packages':sha('/var/lib/dpkg/status'),'cpus':os.cpu_count(),'memory_total':next(line for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:'))}
def begin():
 control.protected();return {'time':time.time(),'monotonic':time.monotonic(),'host':host(),'services':control.snapshot()}
def classify(names):
 if not names:return {'persistent':[],'transient':[]},{}
 argv=['systemctl','show',*['--property='+key for key in ['Id','Type','ActiveState','SubState','MainPID','ControlPID','Job','ControlGroup']],'--',*sorted(names)]
 text=control.s.capture(argv,30);units={}
 for block in text.strip().split('\n\n'):
  item=dict(line.split('=',1) for line in block.splitlines() if '=' in line)
  if 'Id' in item:units[item['Id']]=item
 if set(units)!=set(names):raise RuntimeError('Incomplete new-service discovery')
 resident={}
 for name,item in units.items():
  group=item.get('ControlGroup')
  if group=='':resident[name]=True
  elif isinstance(group,str) and group.startswith('/'):
   root=Path('/sys/fs/cgroup');path=(root/group.lstrip('/')).resolve()
   if not path.is_relative_to(root):raise RuntimeError('Invalid resident-proof path')
   value=dict(line.split() for line in (path/'cgroup.events').read_text().splitlines())
   if value.get('populated') not in {'0','1'}:raise RuntimeError('Missing resident-process proof')
   resident[name]=value['populated']=='0'
  else:raise RuntimeError('Missing service cgroup proof')
 if control.s.capture(argv,30)!=text:raise RuntimeError('Unit changed during resident proof')
 return partition(units,resident),{name:{'type':item['Type'],'active_state':item['ActiveState'],'sub_state':item['SubState'],'no_resident_processes':resident[name]} for name,item in units.items()}
def finish(context,directory):
 directory=Path(directory);directory.mkdir(mode=0o700);end=time.time();mono=time.monotonic();after=control.snapshot();after_host=host();raw=directory/'manager-events-PRIVATE.jsonl';anchor=directory/'coverage-anchor-PRIVATE.jsonl'
 (directory/'services-before-PRIVATE.json').write_text(json.dumps(context['services'],indent=2)+'\n');(directory/'services-after-PRIVATE.json').write_text(json.dumps(after,indent=2)+'\n')
 result={'valid':False,'window_complete':False,'window_start':context['time'],'window_end':end,'policy':'strict; no Nhost-specific fwupd exception','possible_performance_interference_not_ruled_out':True}
 try:
  control.protected()
  for path,filters in [(raw,['_PID=1','--since','@'+str(math.floor(context['time'])),'--until','@'+str(math.ceil(end))]),(anchor,['--until','@'+str(math.floor(context['time'])),'--lines=1'])]:
   with path.open('xb') as output,path.with_suffix('.stderr-PRIVATE.log').open('xb') as errors:subprocess.run(['journalctl','-b',*filters,'--output=json','--no-pager'],stdout=output,stderr=errors,check=True,timeout=60)
  anchors=[json.loads(line) for line in anchor.read_text().splitlines()]
  if not anchors or min(int(item['__REALTIME_TIMESTAMP'])/1e6 for item in anchors)>context['time']:raise RuntimeError('Journal window coverage unavailable')
  if end<=context['time'] or abs((end-context['time'])-(mono-context['monotonic']))>2:raise RuntimeError('Wall/monotonic clock discontinuity')
  entries=[]
  with raw.open() as stream:
   for line in stream:
    item=json.loads(line)
    if context['time']<=int(item['__REALTIME_TIMESTAMP'])/1e6<end:entries.append(item)
  baseline=set(context['services']);names={item['UNIT'] for item in entries if isinstance(item.get('UNIT'),str) and item['UNIT'].endswith('.service') and not item['UNIT'].startswith('tds-') and item['UNIT']!='user@0.service'}
  classified,proof=classify(names-baseline);watched=baseline|set(classified['persistent']);counts=event_counts(entries,watched)
  result.update(window_complete=True,persistent_service_event_counts=counts,nonpersistent_oneshot_event_counts_disclosed=event_counts(entries,set(classified['transient'])),unit_classification=proof)
  if context['host']!=after_host:raise RuntimeError('Host/kernel/Docker/package identity changed')
  if {key:value for key,value in context['services'].items() if key!='user@0.service'}!={key:value for key,value in after.items() if key!='user@0.service'}:raise RuntimeError('Persistent-service identity changed')
  if any(counts.values()):raise RuntimeError('Persistent-service lifecycle events observed; no Nhost waiver')
  result['valid']=True
 except (OSError,ValueError,KeyError,subprocess.SubprocessError,RuntimeError) as error:result['reason']=str(error) if isinstance(error,RuntimeError) else 'Continuous native journal evidence unavailable: '+type(error).__name__
 for name,path in [('manager_events',raw),('coverage_anchor',anchor)]:
  if path.exists():result[name]={'bytes':path.stat().st_size,'sha256':sha(path),'distribution':'PRIVATE NATIVE HOST ONLY'}
 (directory/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 if not result['valid']:raise RuntimeError(result['reason'])
 return result
def quiet(directory):
 value=begin();value['time']-=600;value['monotonic']-=600
 result=finish(value,directory);result['method']='Current protected identities plus preceding600s complete manager journal; not proof of no interference';return result
