#!/usr/bin/env python3
"""Audit exact proposed git-index bytes in memory; never expose matching values."""
import hashlib,json,re,subprocess,tarfile
from pathlib import Path
from urllib.parse import urlsplit,unquote

parent=Path('/opt/twelve-dollar-baas-convexpg-16g');out=parent/'setup-evidence';candidates=set()
for project,directory in [('baas-convex-vps16','/opt/twelve-dollar-baas-convex-16g'),('baas-convexpg-vps16',str(parent))]:
 root=Path(directory)
 assert json.loads((root/'.benchmark-owned').read_text())['project']==project
 for name in ['cli.env','backend.env','postgres.env','compat-jwt.env']:
  p=root/'src/.state/convex'/name
  if not p.exists():continue
  for line in p.read_text().splitlines():
   key,sep,value=line.partition('=')
   if not sep or not value:continue
   if re.search(r'SECRET|PASSWORD|ADMIN_KEY',key):
    candidates.add(value.encode());candidates.add(value.strip('\"\x27').encode())
   if key=='POSTGRES_URL':
    candidates.add(value.encode());password=urlsplit(value).password
    if password:candidates.add(password.encode());candidates.add(unquote(password).encode())
 volume=Path(subprocess.check_output(['docker','volume','inspect',project+'_data','--format','{{.Mountpoint}}'],text=True).strip())
 candidates.add((volume/'credentials/instance_secret').read_bytes().strip())
candidates.discard(b'')
assert len(candidates)==7, 'All seven actual private values including compatibility key required'
manifest_path=parent/'blocked-publication-candidates-manifest.json'
manifest=json.loads(manifest_path.read_text());expected={x['path']:x for x in manifest['files']};seen=set();matches=[];forbidden=[];queries=[];jwts=[]
jwt=re.compile(rb'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')
url=re.compile(rb'(?:https?://[^\s?<>\"\x27\x1b]+|(?:GET|POST|PUT|PATCH|DELETE|HEAD) /[^ ?\"\r\n]*|/[^\s?<>\"\x27\x1b]+)\?([^\s<>\"\x27\x1b]+)')
with tarfile.open(parent/'blocked-publication-candidates.tar','r') as tar:
 for item in tar:
  assert item.isfile() and item.name in expected and item.name not in seen
  data=tar.extractfile(item).read();entry=expected[item.name]
  assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
  seen.add(item.name)
  if any(value in data for value in candidates):matches.append(item.name)
  if jwt.search(data):jwts.append(item.name)
  if Path(item.name).suffix in ['.env','.tsv','.jsonl','.sqlite','.sqlite3','.db'] or '/credentials/' in item.name or '/.state/' in item.name:forbidden.append(item.name)
  if item.name.endswith('.log'):
   for match in url.finditer(data):
    if not match.group(1).startswith((b'<redacted',b'<REDACTED')):queries.append(item.name);break
assert seen==set(expected)
report={'scope':'Exact proposed git index publication bytes checked against actual private values from BOTH preserved SQLite and current PostgreSQL attempts; not a public download/CI claim','files':len(seen),'bytes':sum(x['bytes'] for x in expected.values()),'actual_private_candidates_checked':len(candidates),'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'private_match_paths':matches,'forbidden_private_file_paths':forbidden,'unredacted_http_log_query_paths':queries,'jwt_shaped_value_paths':jwts}
with (out/'blocked-publication-privacy-first-public.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
assert not matches and not forbidden and not queries and not jwts, 'Publication audit failed; inspect path-only report, never print matches'
print('BLOCKED_EXACT_INDEX7PRIVATE_VALUES_JWT_SHAPES_HTTP_QUERY_AUDIT_PASSED files='+str(len(seen)),flush=True)
