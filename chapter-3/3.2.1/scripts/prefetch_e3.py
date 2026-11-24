#!/usr/bin/env python3
"""Preparation only: resumable bounded concurrent downloads, no database writes."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'src'))
from mtstudy.common import ROOT,read
from mtstudy.dataset import BASE_URL,download

p=argparse.ArgumentParser()
p.add_argument('--workers',type=int,default=8)
a=p.parse_args()
data=ROOT/'data'
data.mkdir(exist_ok=True)
jobs=[data/f'hits_{i}.parquet' for i in read(ROOT/'configs/protocol.json')['shards'] if not (data/f'hits_{i}.parquet').exists()]
def fetch(path):
    print('DOWNLOAD '+path.name,flush=True)
    download(BASE_URL+'/'+path.name,path)
    print(f'READY {path.name}: {path.stat().st_size} bytes',flush=True)
with ThreadPoolExecutor(max_workers=a.workers) as pool:
    for f in as_completed([pool.submit(fetch,x) for x in jobs]):
        f.result()
print('All source files available; run dataset to verify hashes and normalize.',flush=True)
