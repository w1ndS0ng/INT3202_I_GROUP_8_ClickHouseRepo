#!/usr/bin/env python3
"""Independent source/normalized audits, outside experiment timings."""
from pathlib import Path
import json
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'src'))
from mtstudy.common import ROOT, read,save,quote,sha,object_sha,utc

p=read(ROOT/'configs/protocol.e3.v2.json')
data=ROOT/'data'
manifest=read(data/'manifest.json')
assert len(manifest['files'])==30
assert sum(f['rows'] for f in manifest['files'])==30000000
structure=', '.join(f'`{n}` {t}' for n,t,_ in p['schema'])
cols=','.join(f'`{x[0]}`' for x in p['schema'])
agg=f'count() AS n,sum(cityHash64(tuple({cols}))) AS hash_sum,groupBitXor(cityHash64(tuple({cols}))) AS hash_xor'
def local(sql):
    r=subprocess.run(['clickhouse-local','--max_threads=1','--max_memory_usage=1000000000',
        '--input_format_parquet_memory_high_watermark=134217728','--query',sql+' FORMAT JSONEachRow'],
        text=True,capture_output=True,check=True)
    return [json.loads(x) for x in r.stdout.splitlines() if x]
def equal(a,b):
    return all(int(a[k])==int(b[k]) for k in ['n','hash_sum','hash_xor'])
audits=[]
for f in manifest['files']:
    i=f['shard']
    source=data/f'hits_{i}.parquet'
    binary=data/f'hits_{i}.rowbinary'
    assert sha(source)==f['parquet_sha256'] and sha(binary)==f['rowbinary_sha256']
    conversion=read(data/f'hits_{i}.conversion.json')['sql'].removesuffix(' FORMAT RowBinary')
    a=local(f'SELECT {agg} FROM ({conversion})')[0]
    b=local(f'SELECT {agg} FROM file({quote(binary)}, RowBinary, {quote(structure)})')[0]
    if not equal(a,b) or int(a['n'])!=1000000:
        raise RuntimeError(f'Source normalization mismatch: shard {i}')
    conditions=[]
    for name,typ,_ in p['schema']:
        lo,hi={'Int16':(-2**15,2**15-1),'Int32':(-2**31,2**31-1),
               'Int64':(-2**63,2**63-1),'Date':(0,65535),"DateTime('UTC')":(0,2**32-1)}[typ]
        conditions.append(f'countIf(isNull(`{name}`) OR toInt128(assumeNotNull(`{name}`))<{lo} '
                          f'OR toInt128(assumeNotNull(`{name}`))>{hi}) AS `{name}`')
    invalid=local('SELECT '+','.join(conditions)+f' FROM file({quote(source)}, Parquet)')[0]
    if any(int(v) for v in invalid.values()):
        raise RuntimeError(f'NULL or out-of-domain values: {i}: {invalid}')
    audits.append(dict(shard=i,source_fingerprint=a,normalized_fingerprint=b,invalid=invalid))
    save(ROOT/'manifests/hits30m.e3.schema-audit.json',dict(complete=False,files=audits))
    print(f'AUDIT shard {i}: 1M rows, no invalid casts, source/binary fingerprints match',flush=True)
fingerprints={}
profiles={}
for scale in ['1m','3m','10m','30m']:
    if scale=='30m':
        names=','.join(f'hits_{x}.rowbinary' for x in p['shards'])
        file=str(data/('{'+names+'}'))
    else:
        file=str(data/manifest['samples'][scale]['filename'])
    source=f'file({quote(file)}, RowBinary, {quote(structure)})'
    fp=local(f'SELECT {agg} FROM {source}')[0]
    fingerprints[scale]=fp
    profile=local("SELECT count() AS n,min(EventDate) AS first_day,max(EventDate) AS last_day,"
        "uniqExact(EventDate) AS days,uniqExact(CounterID) AS counters,uniqExact(RegionID) AS regions,"
        "countIf(CounterID=3258) AS w1,countIf(EventDate>=toDate('2013-07-15') AND EventDate<toDate('2013-07-23')) AS w2,"
        "countIf(CounterID=3258 AND EventDate>=toDate('2013-07-15') AND EventDate<toDate('2013-07-23')) AS w3,"
        f"countIf(RegionID=229) AS w4 FROM {source}")[0]
    profiles[scale]=profile
    for case in ['w1','w2','w3','w4']:
        if int(profile[case])==0:
            raise RuntimeError('Empty v2 workload')
    print(f'PROFILE {scale}: {profile}',flush=True)
reported_counts={}
for scale,expected in [('1m',[1294,382135,134,205725]),('30m',[38841,11464429,4012,6185519])]:
    actual=[int(profiles[scale][k]) for k in ['w1','w2','w3','w4']]
    reported_counts[scale]=dict(actual=actual,reported=expected,match=actual==expected)
    if scale=='30m':
        assert actual==expected,(scale,actual,expected)
assert sum(f['parquet_bytes'] for f in manifest['files'])==4711867682
manifest['fingerprints']=fingerprints
manifest['source_audit']='independent full 30-shard audit; 30M aggregate workload counts match shared report; 1M own systematic sample differs from reported pilot; curator hash-lock comparison pending'
save(data/'manifest.json',manifest)
save(ROOT/'manifests/hits30m.e3.lock.json',manifest)
save(ROOT/'manifests/hits30m.e3.schema-audit.json',dict(complete=True,files=audits))
save(ROOT/'manifests/hits30m.e3.profile.json',dict(profiles=profiles,fingerprints=fingerprints,
     source_parquet_bytes=sum(f['parquet_bytes'] for f in manifest['files']),
     reported_counts_comparison=reported_counts,completed_at=utc()))
print('PASS: source audits, samples, counts and fingerprints frozen before benchmark.',flush=True)
