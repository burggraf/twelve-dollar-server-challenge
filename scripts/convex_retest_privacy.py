"""Native-only actual fresh input collection; NEVER print/serialize returned sets.

The caller must establish Docker volume/container ownership before supplying a
native secret file. This augments, never replaces, historical actual-value and
JWT/query/private-path screening. Empty pre-serving state is not post-start proof.
"""
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote,urlsplit
from convex_retest_safety import PROJECT


def _read(path,limit,*,within=None):
    if within is not None:
        relative=path.relative_to(within)
        current=within
        if current.is_symlink():raise ValueError()
        for part in relative.parts:
            current=current/part
            if current.is_symlink():raise ValueError()
    elif path.is_symlink():raise ValueError()
    with path.open('rb') as source:data=source.read(limit+1)
    if len(data)>limit:raise ValueError()
    return data


def fresh_inputs(root,*,native_secret_file=None,require_native_secret=False):
    """Return private candidate/signature sets and value-free inventory metadata."""
    values=set();signatures=set();count=0;native_present=False
    try:
        root=Path(root)
        if type(require_native_secret) is not bool:raise ValueError()
        marker=json.loads(_read(root/'.benchmark-owned',16384,within=root))
        if marker['project']!=PROJECT:raise ValueError()
        state=root/'src/.state/convex'
        for name in ('cli.env','backend.env','postgres.env','compat-jwt.env'):
            path=state/name
            if path.is_symlink():raise ValueError()
            if not path.exists():continue
            text=_read(path,65536,within=root).decode();count+=1
            for line in text.splitlines():
                if not line.strip() or line.lstrip().startswith('#'):continue
                key,separator,raw=line.partition('=')
                if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',key):raise ValueError()
                value=raw
                if value[:1] in ('"',"'"):
                    if len(value)<2 or value[-1]!=value[0]:raise ValueError()
                    value=value[1:-1]
                if re.search(r'SECRET|PASSWORD|ADMIN_KEY',key):
                    if not value:raise ValueError()
                    values.update((raw.encode(),value.encode()))
                if key=='POSTGRES_URL':
                    parsed=urlsplit(value)
                    if parsed.scheme not in ('postgres','postgresql') or not parsed.password:raise ValueError()
                    values.update((raw.encode(),value.encode(),parsed.password.encode(),unquote(parsed.password).encode()))
        if native_secret_file is not None:
            secret=Path(native_secret_file)
            if secret.is_symlink():raise ValueError()
            if secret.exists():
                data=_read(secret,4096).strip()
                if not data:raise ValueError()
                values.add(data);native_present=True
        if require_native_secret and not native_present:raise ValueError()
        # The original generator issues signatures BEFORE its final fixture
        # copy. Partial/malformed temporary output must also refuse retrieval.
        if (state/'benchmark-seed').is_symlink():raise ValueError()
        for tokens in (state/'benchmark-tokens.json',state/'benchmark-seed/tokens.json'):
            if tokens.is_symlink():raise ValueError()
            if tokens.exists():
                items=json.loads(_read(tokens,16*1024**2,within=root))
                if not isinstance(items,list) or not items:raise ValueError()
                for item in items:
                    token=item['token']
                    if not isinstance(token,str):raise ValueError()
                    parts=token.split('.')
                    if len(parts)!=3 or any(not re.fullmatch(r'[A-Za-z0-9_-]+',part) for part in parts) or len(parts[2])!=43:raise ValueError()
                    signatures.add(parts[2].encode())
        return values,signatures,{'credential_files_present':count,'native_secret_present':native_present,'issued_signatures':len(signatures)}
    except (OSError,ValueError,KeyError,TypeError,UnicodeError):
        raise RuntimeError('Fresh private input inventory incomplete or malformed; retrieval refused') from None


def native_fresh_inputs(root,*,capture=subprocess.check_output):
    """Read-only Docker discovery; no secret read from an unowned volume."""
    try:
        # Establish workspace ownership before even querying its Docker names.
        fresh_inputs(root)
        def read(argv):return capture(argv,text=True,stderr=subprocess.PIPE,timeout=15)
        names=read(['docker','volume','ls','-q']).splitlines()
        backends=read(['docker','ps','-aq','--filter','label=com.docker.compose.project='+PROJECT,
                       '--filter','label=com.docker.compose.service=backend']).splitlines()
        volume_name=PROJECT+'_data';secret=None
        if volume_name in names:
            records=json.loads(read(['docker','volume','inspect',volume_name]))
            if not isinstance(records,list) or len(records)!=1:raise ValueError()
            volume=records[0];labels=volume['Labels']
            if volume['Name']!=volume_name or labels['com.docker.compose.project']!=PROJECT or labels['com.docker.compose.volume']!='data':raise ValueError()
            mount=Path(volume['Mountpoint'])
            if not mount.is_absolute() or not mount.is_dir() or mount.resolve()!=mount:raise ValueError()
            if (mount/'credentials').is_symlink():raise ValueError()
            secret=mount/'credentials/instance_secret'
        values,signatures,metadata=fresh_inputs(root,native_secret_file=secret,require_native_secret=bool(backends))
        metadata.update(backend_container_present=bool(backends),owned_data_volume_present=volume_name in names)
        return values,signatures,metadata
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError):
        raise RuntimeError('Actual owned fresh private-source inventory unavailable; retrieval refused') from None
