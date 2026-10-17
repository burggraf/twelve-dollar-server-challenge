"""Numeric diagnostic primitives for the pinned native strict-uncached retest.

Raw Prometheus text stays PRIVATE: it can contain client/function labels. Values
below preserve distinct series but remove ALL labels. Histogram sums/counts are
not instantaneous heaps, pool maxima are not active-worker counts, and V8 heap,
process RSS and cgroup memory are overlapping views, never additive categories.
"""
import math
from pathlib import Path
import re
import time
import threading

PREFIX='convex_local_backend_'
GAUGES={
    'cache_size_bytes','cache_plan_go_total','cache_plan_ready_total','cache_plan_wait_total',
    'isolate_pool_max_info','isolate_pool_running_count_info',
    'isolate_total_used_heap_size_bytes','isolate_total_heap_size_bytes',
    'isolate_total_heap_size_executable_bytes','isolate_total_external_memory_bytes',
    'isolate_total_physical_size_bytes','isolate_total_malloced_memory_bytes',
    'isolate_total_array_buffer_memory_bytes','postgres_pool_max_connections',
    'udf_execute_full_total',
}
HISTOGRAMS={
    'isolate_used_heap_size_bytes','isolate_heap_size_bytes','isolate_physical_size_bytes',
    'isolate_external_memory_bytes','postgres_get_connection_seconds',
    'postgres_pool_active_connections','udf_queue_seconds',
    'application_function_runner_wait_seconds','application_function_runner_run_seconds',
}
ALLOWED={PREFIX+name for name in GAUGES}|{PREFIX+name+suffix for name in HISTOGRAMS for suffix in ('_count','_sum')}
REQUIRED={PREFIX+name for name in ('cache_size_bytes','isolate_pool_max_info','isolate_total_used_heap_size_bytes','postgres_get_connection_seconds_count')}
SAMPLE=re.compile(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{[^\n]*\})?\s+([^\s]+)(?:\s+[0-9]+)?\s*$')


class MissingMetrics(RuntimeError):
    def __init__(self,missing):
        super().__init__('Required native diagnostic metric family missing')
        self.missing=frozenset(missing)


def parse_metrics(text):
    if not isinstance(text,str) or len(text.encode())>8*1024**2:
        raise RuntimeError('Native metric observation missing or exceeds bound')
    values={}
    for line in text.splitlines():
        if not line or line.startswith('#'):continue
        name=re.split(r'[\s{]',line,maxsplit=1)[0]
        if name not in ALLOWED:continue
        match=SAMPLE.fullmatch(line)
        try:value=float(match.group(2)) if match else float('nan')
        except ValueError:value=float('nan')
        if not math.isfinite(value) or value<0:
            raise RuntimeError('Malformed/nonfinite selected native metric observation')
        values.setdefault(name,[]).append(value)
    if not REQUIRED.issubset(values):
        raise MissingMetrics(REQUIRED-values.keys())
    return values


def startup_metrics(fetch,verify_runtime,record_raw,*,clock=time.monotonic,wait=None,limit=120):
    """Startup ONLY: observe the pinned scheduler's lazy30s aggregate gauge.

    No function/load retry, knob change or synthetic sample. All raw responses
    must be retained natively/private by record_raw. Other missing/malformed
    metrics and ANY ownership/runtime/kernel failure stop immediately. Scored
    Observer.sample remains strict and never calls this readiness function.
    """
    if type(limit) is not int or not 1<=limit<=120:raise ValueError('Startup observation ceiling must be1..120seconds')
    if wait is None:wait=threading.Event().wait
    start=clock();last=start
    if type(start) not in (int,float) or not math.isfinite(start):raise RuntimeError('Invalid startup observation clock')
    def now():
        nonlocal last
        value=clock()
        if type(value) not in (int,float) or not math.isfinite(value) or value<last:raise RuntimeError('Invalid startup observation clock')
        last=value
        return value
    while True:
        if now()-start>=limit:raise RuntimeError('Required startup gauge did not arrive within observation ceiling')
        verify_runtime()
        text=fetch()
        if not isinstance(text,bytes) or len(text)>8*1024**2:raise RuntimeError('Invalid startup metrics body')
        record_raw(text)
        try:value=parse_metrics(text.decode())
        except MissingMetrics as error:
            if error.missing!={PREFIX+'isolate_total_used_heap_size_bytes'}:raise
        else:
            if now()-start>=limit:raise RuntimeError('Startup metrics returned after observation ceiling')
            return value
        remaining=limit-(now()-start)
        if remaining<=0:raise RuntimeError('Required startup gauge did not arrive within observation ceiling')
        wait(min(3,remaining))


def connection_headroom(settings,*,pool_count,pool_limit,other_clients,maintenance_reserve):
    """Authorize no change: only test the approved32-connection sizing hypothesis."""
    for value,minimum in [(pool_count,1),(pool_limit,1),(other_clients,0),(maintenance_reserve,1)]:
        if type(value) is not int or value<minimum:
            raise ValueError('Complete nonnegative native pool/client counts required')
    if pool_limit!=32:
        raise ValueError('Only the approved32-connection trial is in scope')
    try:
        for name in ('fsync','synchronous_commit','full_page_writes'):
            if settings[name]!='on':raise ValueError()
        counts=[]
        for name in ('max_connections','reserved_connections','superuser_reserved_connections'):
            value=settings[name]
            if not isinstance(value,str) or not value.isascii() or not value.isdigit():raise ValueError()
            counts.append(int(value))
        maximum,reserved,super_reserved=counts
        ordinary=maximum-reserved-super_reserved
        if maximum<=0 or ordinary<=0:raise ValueError()
    except (ValueError,KeyError,TypeError):
        raise RuntimeError('Incomplete connection budget or weakened native durability') from None
    proposed=pool_count*pool_limit
    spare=ordinary-proposed-other_clients-maintenance_reserve
    if spare<0:
        raise RuntimeError('Proposed native pools leave insufficient maintenance/client headroom')
    return {'ordinary_usable_connections':ordinary,'proposed_pool_connection_ceiling':proposed,
            'other_clients':other_clients,'maintenance_reserve':maintenance_reserve,
            'spare_after_pools_other_clients_and_maintenance':spare}


def process_memory(pid,proc=Path('/proc')):
    """Read status numeric memory/thread fields only, never cmdline/environ/maps."""
    fields={'VmRSS':'rss_bytes','RssAnon':'rss_anon_bytes','RssFile':'rss_file_bytes',
            'RssShmem':'rss_shmem_bytes','VmSwap':'swap_bytes','Threads':'threads'}
    try:
        if type(pid) is not int or pid<=0:raise ValueError()
        result={'pid':pid}
        for line in (proc/str(pid)/'status').read_text().splitlines():
            key,sep,value=line.partition(':')
            if not sep or key not in fields:continue
            target=fields[key]
            if target in result:raise ValueError()
            match=re.fullmatch(r'\s*([0-9]+)\s*' if key=='Threads' else r'\s*([0-9]+)\s+kB\s*',value)
            if not match:raise ValueError()
            result[target]=int(match.group(1))*(1 if key=='Threads' else 1024)
        if set(result)!={'pid',*fields.values()}:raise ValueError()
        return result
    except (OSError,ValueError,TypeError):
        raise RuntimeError('Incomplete or malformed owned-process memory observation') from None
