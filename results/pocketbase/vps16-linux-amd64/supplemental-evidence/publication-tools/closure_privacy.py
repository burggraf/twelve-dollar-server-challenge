"""Pure byte/path checks for the finite PocketBase closure-publication candidate."""
import json,re
from pathlib import PurePosixPath

BASE='results/pocketbase/vps16-linux-amd64/supplemental-evidence/retained/'
ALLOWED_JSONL={BASE+'supplemental-phase-journal.jsonl',BASE+'rebracket-01/supplemental-phase-journal.jsonl',BASE+'repeatability-post-update-01/study-phase-journal.jsonl'}
JWT=re.compile(rb'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')
# Construct the slash token separately: these are regex syntax, not captured URLs.
SLASH=bytes([47]);ATOM=rb'[^\s?<>\"\x27\x1b]+'
QUERY=re.compile(rb'((?:https?:'+SLASH+SLASH+ATOM+rb'|(?:GET|POST|PUT|PATCH|DELETE|HEAD) '+SLASH+rb'[^ ?\"\r\n]*|'+SLASH+ATOM+rb')\?)([^\s<>\"\x27\x1b]+)')

def issues(name,data,values,signatures):
 result=[];p=PurePosixPath(name)
 if (p.is_absolute() or '..' in p.parts or '.state' in p.parts or 'credentials' in p.parts or '\\' in name or '\0' in name or 'PRIVATE' in name or p.suffix in {'.env','.tsv','.db','.sqlite','.sqlite3','.gz','.tar'} or (p.suffix=='.jsonl' and name not in ALLOWED_JSONL)):
  result.append('private_path')
 if any(value and value in data for value in values):result.append('private_value')
 if any(sig in signatures for sig in re.findall(rb'[A-Za-z0-9_-]{43}',data)):result.append('issued_signature')
 if JWT.search(data):result.append('jwt_shape')
 if any(not match.group(2).startswith(b'<redacted') for match in QUERY.finditer(data)):result.append('http_query')
 if name in ALLOWED_JSONL:
  try:
   rows=[json.loads(line) for line in data.splitlines()]
   assert rows and all(isinstance(row,dict) and isinstance(row.get('time'),(int,float)) and isinstance(row.get('attempts'),list) and isinstance(row.get('status'),str) and isinstance(row.get('total_physical_full_attempts_accounted'),int) for row in rows)
  except (ValueError,TypeError,AssertionError):result.append('invalid_phase_journal')
 return result
