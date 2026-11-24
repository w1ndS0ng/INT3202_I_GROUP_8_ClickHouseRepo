#!/usr/bin/env python3
"""Small synthetic integration test, explicitly excluded from study results.

Creates a new mtr_ database and leaves its outputs for audit. Does not touch
existing ch3/exp35 data or execute the 30-million-row study.
"""
from pathlib import Path
import argparse
import datetime
import struct
import sys
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'src'))
from mtstudy.common import ROOT,object_sha,save,read,sha,utc
from mtstudy.runner import initialize,Run
from mtstudy import analysis
from mtstudy.dataset import make_samples

parser=argparse.ArgumentParser()
parser.add_argument('--client-config')
parser.add_argument('--run',default='smoke'+datetime.datetime.now().strftime('%m%d%H%M%S'))
args=parser.parse_args()
protocol=read(ROOT/'configs/protocol.json')
protocol.update(smoke_test=True,query_rounds=3,warmups=1,ingest_rounds=3,
                stable_samples=2,stable_interval_seconds=.05,batch_rows=[100,1000,10000])
data=ROOT/'data'/args.run
data.mkdir(parents=True,exist_ok=False)
files=[]
epoch=datetime.date(1970,1,1)
day0=(datetime.date(2013,7,15)-epoch).days
pack=struct.Struct('<qqiHIihhhhhi')
assert pack.size==44
for shard in protocol['shards']:
    path=data/f'hits_{shard}.rowbinary'
    with path.open('wb') as out:
        for i in range(1000):
            day=day0+i%14
            out.write(pack.pack(shard*1000+i,i%100,3258 if i%3 else 7,day,day*86400,
                                225 if i%7 else 1,1,0,640+i%600,480,0,i%2000))
    files.append(dict(shard=shard,rowbinary_sha256=sha(path),rowbinary_bytes=path.stat().st_size,rows=1000))
manifest=dict(schema_hash=object_sha(protocol['schema']),files=files,created_at=utc(),row_bytes=44)
manifest['samples']=make_samples(data,manifest)
save(data/'manifest.json',manifest)
a=SimpleNamespace(member='tai',machine='smoketest',run=args.run,data=str(data),client_config=args.client_config)
initialize(a,protocol)
run=Run(a)
for scale in ['1m','3m','10m']:
    run.build('keys',scale)
    run.queries('keys',scale)
analysis.calibrate(run)
run.build('keys','30m')
analysis.forecast(run)
run.queries('keys','30m')
analysis.compare(run)
run.build('granularity','30m')
run.queries('granularity','30m')
run.ingest('1m')
analysis.summarize(run)
save(run.out/'SMOKE_ONLY.json',dict(status='PASS',real_rows_max=30000,at=utc(),
     note='Scale names are test labels, not real million-row results. Exclude from report.'))
print('PASS: synthetic integration pipeline; not official benchmark results.')
