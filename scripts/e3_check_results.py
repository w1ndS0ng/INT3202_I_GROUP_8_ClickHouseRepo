#!/usr/bin/env python3
"""Verify the completed 9-case matrix and create a concise factual report."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mtstudy.common import ROOT,read,csv_read,save,sha,utc

p=argparse.ArgumentParser()
p.add_argument('--run',required=True)
p.add_argument('--scale',choices=['1m','30m'],required=True)
a=p.parse_args()
out=ROOT/'results/tai/wsl_i5'/a.run
c=read(out/'config.json')
assert c['protocol']['protocol_version']=='mergetree-v2-e3-r1'
assert not c['git_dirty'],'Benchmark source was not clean at init'
assert not (out/'SMOKE_ONLY.json').exists()
n=1000000 if a.scale=='1m' else 30000000
rows=csv_read(out/'ingest'/f'{a.scale}.csv')
assert len(rows)==9
assert read(out/'ingest'/f'{a.scale}_complete.json')['cases']==9
assert {(int(r['repeat']),int(r['batch_rows'])) for r in rows}=={(i,b) for i in range(3) for b in [10000,100000,1000000]}
input_manifest=read(out/'input_manifest.json')
expected=input_manifest['fingerprints'][a.scale]
acks=[]
total_batches=0
for r in rows:
    assert int(r['rows'])==n
    assert abs(float(r['throughput_rows_s'])-n/float(r['ingest_ack_s']))<.001
    short=r['table'].split('.')[1]
    fp=read(out/'checks'/f'{short}_fingerprint.json')
    assert all(int(fp[k])==int(expected[k]) for k in ['n','hash_sum','hash_xor'])
    events=read(out/'ingest'/f'{short}_part_log.json')
    assert all(int(e['error'])==0 for e in events)
    assert sum(int(e['rows']) for e in events if e['event_type']=='NewPart')==n
    batches=read(out/'ingest'/f'{short}_batches.json')
    assert len(batches)==n//int(r['batch_rows']) and sum(int(b['rows']) for b in batches)==n
    assert all(int(b['rows'])==int(r['batch_rows']) for b in batches)
    total_batches+=len(batches)
    timeline=read(out/'ingest'/f'{short}_timeline.json')
    assert timeline and not any('error' in v for v in timeline)
    stability=read(out/'checks'/f'{short}_stability.json')
    assert len(stability)>=3
    assert all(v['merges']==0 and v['mutations']==0 for v in stability[-3:])
    assert stability[-1]['parts']==stability[-2]['parts']==stability[-3]['parts']
    assert all(int(part['part_type']=='Wide') for part in stability[-1]['parts'])
    acks.append(float(r['snapshot_after_ack_delay_s']))
assert total_batches==(333 if a.scale=='1m' else 9990)
summary=csv_read(out/'summary'/f'ingest_{a.scale}.csv')
assert len(summary)==3
lines=['# Kết quả E3 — batch INSERT và background merge','',
f"Run: {a.run}; máy wsl_i5; ClickHouse26.10.3.7; protocol mergetree-v2-e3-r1; commit {c['git_commit']}.",
f'Dataset {n:,} dòng/lượt, 12cột; 3batch×3vòng. Tổng {total_batches:,}request; mọi fingerprint khớp nguồn độc lập.',
'Thiết lập: K1(CounterID,EventDate), g8192, Wide, LZ4, fsync1, async0, insert1thread; merge tự nhiên.',
'','| Batch | ACK trung vị (s) | ACK IQR(s) | Throughput trung vị (dòng/s) | Active storage trung vị(MiB) | Merge row amplification trung vị |',
'|---:|---:|---:|---:|---:|---:|']
for r in sorted(summary,key=lambda x:int(x['batch_rows'])):
    lines.append(f"|{int(r['batch_rows']):,}|{float(r['ingest_ack_s_median']):.3f}|{float(r['ingest_ack_s_iqr']):.3f}|"
        f"{float(r['throughput_rows_s_median']):,.0f}|{float(r['active_bytes_stable_median'])/2**20:.3f}|{float(r['merge_row_amplification_median']):.3f}|")
lines+=['','## Chi tiết9lượt','',
'|Vòng|Vị trí|Batch|ACK(s)|Throughput(dòng/s)|Parts sauACK|Parts ổn định|Merge events|',
'|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in rows:
    lines.append(f"|{int(r['repeat'])+1}|{int(r['position'])+1}|{int(r['batch_rows']):,}|{float(r['ingest_ack_s']):.3f}|"
        f"{float(r['throughput_rows_s']):,.0f}|{r['parts_at_ack']}|{r['parts_stable']}|{r['merge_events']}|")
lines+=['','## Giới hạn và truy vết','',
'Median/Q1/Q3/IQR chỉ mô tả3lượt; không phải khoảng tin cậy hay kết luận nhân quả cho mọi hệ thống.',
'ACK elapsed gồm HTTP và xử lý input/journal giữa batch; không gồm tải mạng/chuyển Parquet hoặc thời gian producer gom batch.',
f'Snapshot gần sauACK: độ trễ hoàn thành từ {min(acks):.4f}s đến {max(acks):.4f}s; không phải snapshot nguyên tử tạiACK.',
'Merge events được tính theo UUID bảng đến mốc server observation_end sau snapshot ổn định; tổngduration có thể chồng thời gian.',
'Ổn định được quan sát3lần cách10s, không có merge/mutation; không bảo đảm không phát sinh merge tương lai.',
'Active storage không gồm mọi inactive/tạm; merge row amplification là proxy đọc lại, không phải physical SSD write amplification.',
'Nguồn đã kiểm độc lập đủ30file; các workload counts30M khớp báo cáo Tuấn. Mẫu1M tự tạo có một số thống kê khác pilot trong Docs; chỉ dùng để kiểm tra pipeline E3. Chưa có curator hash-lock/code2e65b9d để khẳng định cùng chính xác bản khóa của máy E2.',
'Phầncứng/memory/kernel/Python thực tế trong environment.json; không dùng thời gian tuyệt đối đối chiếu máy Xeon.',
'','Dữ liệu gốc trong ingest/, checks/, ddl/; summary/ chứa tóm tắt và figures/ chứa hình. Pilot không thay kết quả30M.']
(out/'summary/E3_REPORT_VI.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
save(out/'summary/verification.json',dict(status='PASS',cases=9,rows_per_case=n,total_batches=total_batches,
     all_fingerprints_match_source=True,all_newpart_rows_accounted=True,completed_at=utc(),
     max_post_ack_snapshot_delay_s=max(acks),summary_csv_sha256=sha(out/'summary'/f'ingest_{a.scale}.csv')))
print('PASS: complete E3 matrix, counts, fingerprints, batches, part logs and stability.',flush=True)
