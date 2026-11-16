#!/usr/bin/env python3
"""Read-only consistency check for normalized shard 0 against the actual Parquet."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mtstudy.common import ROOT,read,quote,save

parser=argparse.ArgumentParser()
parser.add_argument('--data',default=str(ROOT/'data'))
args=parser.parse_args()
p=read(ROOT/'configs/protocol.json')
data=Path(args.data).resolve()
structure=', '.join(f'{name} {typ}' for name,typ,_ in p['schema'])
columns=','.join(f'`{c[0]}`' for c in p['schema'])
rowbinary=f"file({quote(data/'hits_0.rowbinary')}, RowBinary, {quote(structure)})"
receipt=read(data/'hits_0.conversion.json')
parquet='('+receipt['sql'].removesuffix(' FORMAT RowBinary')+')'
records={}
for name,source in [('parquet',parquet),('rowbinary',rowbinary)]:
    sql=(f'SELECT count() AS n,sum(cityHash64(tuple({columns}))) AS hash_sum,'
         f'groupBitXor(cityHash64(tuple({columns}))) AS hash_xor,min(EventDate) AS first_day,'
         "max(EventDate) AS last_day,countIf(CounterID=3258) AS counter_rows,"
         "countIf(RegionID=225) AS region_rows,countIf(CounterID=3258 AND "
         "EventDate>=toDate('2013-07-15') AND EventDate<toDate('2013-07-22')) AS combined_rows "
         f'FROM {source} FORMAT JSONEachRow')
    r=subprocess.run(['clickhouse-local','--max_threads=1','--max_memory_usage=1000000000',
        '--input_format_parquet_memory_high_watermark=134217728','--query',sql],capture_output=True,text=True,check=True)
    records[name]=json.loads(r.stdout)
if records['parquet']!=records['rowbinary']:
    raise RuntimeError('Converted content differs')
save(data/'sample_consistency.json',records)
print(json.dumps(records,indent=2))
print('Workload literals are validated on the all-shard systematic samples by the query runner.')
