"""Audit the exact finite Git-index candidate; no target mutation or raw-value output."""
import hashlib,json,os,pathlib,sqlite3,subprocess,sys,tarfile
from closure_privacy import issues,ALLOWED_JSONL
P=pathlib.Path('/opt/twelve-dollar-baas-pocketbase-16g');R=P/'src';O=P/'supplemental-20261016';C=O/'repeatability-post-update-01';D=O/'publication-close-20261016';B='results/pocketbase/vps16-linux-amd64/';E=B+'supplemental-evidence/'
os.environ['DOCKER_CONFIG']='/opt/twelve-dollar-baas-benchmark-16g/.docker'
manifest=json.loads((D/'exact-index2-manifest.json').read_text());expected={r['path']:r for r in manifest['files']};assert len(expected)==len(manifest['files'])
values={line.partition(b'=')[2] for line in (R/'.state/pocketbase/runtime.env').read_bytes().splitlines() if line.partition(b'=')[1] and line.partition(b'=')[2]}
v=json.loads(subprocess.check_output(['docker','volume','inspect','baas-pocketbase-vps16_data']))[0];assert v['Labels']['com.docker.compose.project']=='baas-pocketbase-vps16'
with sqlite3.connect(pathlib.Path(v['Mountpoint'],'data.db').as_uri()+'?mode=ro',uri=True) as db:
 for row in db.execute('SELECT password,tokenKey FROM _superusers'):values.update(x.encode() for x in row if isinstance(x,str) and x)
signatures={v['token'].split('.')[2].encode() for v in json.loads((R/'.state/seed/tokens.json').read_text())};assert len(values)==3 and len(signatures)==20000
seen={};findings=[];code_equal=[]
with tarfile.open(D/'exact-index2.tar') as archive:
 for item in archive:
  assert item.isfile() and item.name in expected and item.name not in seen
  assert item.name in ['README.md','MASTER_PLAN.md','POCKETBASE_REPEATABILITY_RETEST_PLAN.md'] or item.name.startswith('results/pocketbase/')
  data=archive.extractfile(item).read();row=expected[item.name]
  assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'] and item.mode==int(row['mode'],8)&0o777
  flags=issues(item.name,data,values,signatures)
  if flags:findings.append({'path':item.name,'kinds':flags})
  seen[item.name]=data
assert set(seen)==set(expected)
cat=json.loads((C/'complete-post-update-input-catalog-v2-PRIVATE.json').read_text())
for name,data in seen.items():
 if name.startswith(E+'native-sources/'):
  original=name.removeprefix(E+'native-sources/');assert hashlib.sha256(data).hexdigest()==cat['external_sources_and_preserved_evidence'][original] and data==(P/original).read_bytes();code_equal.append(name)
 if name.startswith(E+'publication-tools/'):
  original=name.removeprefix(E+'publication-tools/');assert data==(D/original).read_bytes();code_equal.append(name)
assert len([x for x in code_equal if x.startswith(E+'native-sources/')])==24
assert seen['POCKETBASE_REPEATABILITY_RETEST_PLAN.md']==(C/'approved-study-clarified-plan.md').read_bytes()
assert seen[E+'owner-acceptance.json']==(D/'closure-owner-acceptance.json').read_bytes()
provenance=json.loads(seen[E+'provenance.json']);links=provenance['retention_links'];assert len(links)==271
for row in links:
 for key,sizekey,hashkey in [('original','original_bytes','original_sha256'),('public_derivative','derivative_bytes','derivative_sha256')]:
  raw=(O/row[key]).read_bytes();assert len(raw)==row[sizekey] and hashlib.sha256(raw).hexdigest()==row[hashkey]
 data=seen[row['published_derivative']];assert len(data)==row['derivative_bytes'] and hashlib.sha256(data).hexdigest()==row['derivative_sha256']
 assert row in [{**x,'retention_record':row['retention_record'],'published_derivative':row['published_derivative']} for x in json.loads(seen[row['retention_record']])['artifacts']]
closure=json.loads(seen[B+'supplemental-studies-closed.json']);phase=json.loads((C/'study-phase.json').read_text());assert len(closure['rows'])==14 and phase['attempts'][-1]['outcome'] is None
assert closure['accounting']['all_full_physical_attempts']==25 and closure['final_confirmed_lower_bound_vus']==10000 and not closure['maximum_established'] and not closure['exact_250_vu_boundary_established']
for row in closure['rows']:
 replay=json.loads(seen[B+row['raw_review_path']])['attempts'][0]
 assert row['run']==replay['run'] and row['raw_quantiles_reproduced']==replay['raw_quantiles_reproduced'] and row['requests_by_endpoint']==replay['requests_by_endpoint'] and row['errors_by_endpoint']==replay['errors_by_endpoint'] and row['schema_errors']==replay['schema_errors']
for checksum_name in ['SUPPLEMENTAL_SHA256SUMS','REPORT_SHA256SUMS']:
 for line in seen[B+checksum_name].decode().splitlines():
  digest,name=line.split('  ',1);data=seen.get(B+name)
  if data is None:data=(R/B/name).read_bytes()
  assert hashlib.sha256(data).hexdigest()==digest
assert ALLOWED_JSONL.issubset(seen)
report={'scope':'Exact proposed changed Git-index files plus two unchanged public checksum references, authenticated by local index-tree/object manifest and native SHA/byte/source/private checks; all other untouched historical Git blobs are not newly certified. No loads/builds/resets/service changes.','git_index_tree':manifest['git_index_tree'],'parent_commit':manifest['parent_commit'],'manifest_sha256':hashlib.sha256((D/'exact-index2-manifest.json').read_bytes()).hexdigest(),'archive_sha256':hashlib.sha256((D/'exact-index2.tar').read_bytes()).hexdigest(),'files':len(seen),'changed_index_files':manifest['changed_files'],'unchanged_checksum_reference_files':manifest['reference_files'],'bytes':sum(len(x) for x in seen.values()),'actual_private_candidates_checked':3,'actual_issued_signatures_checked':20000,'all_jwt_shapes_http_queries_private_paths_checked':True,'exact_phase_journal_jsonl_allowlist':sorted(ALLOWED_JSONL),'native_original_derivative_public_provenance_links_verified':len(links),'native_historical_and_publication_source_files_equal':code_equal,'all14_structured_rows_match_native_replay_derivatives':True,'seventh_null_ledger_and_failed_continuity_remain':True,'public_derivative_and_mutable_report_checksums_verified':True,'findings':findings}
with (D/'exact-index2-privacy-audit-public.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
assert not findings,'Publication blocked; inspect path-only findings, no private values'
print(json.dumps({'exact_index_native_audit_passed':True,'files':len(seen),'bytes':report['bytes'],'git_index_tree':manifest['git_index_tree'],'report_sha256':hashlib.sha256((D/'exact-index2-privacy-audit-public.json').read_bytes()).hexdigest(),'report_bytes':(D/'exact-index2-privacy-audit-public.json').stat().st_size}))
