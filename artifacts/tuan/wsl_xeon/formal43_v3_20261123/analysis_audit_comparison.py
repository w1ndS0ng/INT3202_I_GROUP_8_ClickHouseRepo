#!/usr/bin/env python3
"""Recompute report values from saved observations; never query a live DB."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def number(value, digits=0):
    return f'{value:,.{digits}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def audit(root):
    validation=load(root/'validation.json')
    rows=list(csv.DictReader((root/'queries.csv').open(encoding='utf-8-sig')))
    summary=list(csv.DictReader((root/'summary.csv').open(encoding='utf-8-sig')))
    assert len(rows)==300 and len({r['query_id'] for r in rows})==300
    assert all(r['ok']=='True' for r in rows)
    assert sum(r['warmup']=='False' for r in rows)==250
    assert all(hashlib.sha256((root/'source'/k).read_bytes()).hexdigest()==v
               for k,v in load(root/'source_hashes.json').items())
    reference=load(root/'source_check.json')['fingerprint']
    assert reference['rows']==validation['rows']
    assert all(x==reference for x in load(root/'fingerprints.json').values())
    answers=load(root/'answers.json')
    assert all(x==answers['ch0'] for x in answers.values())
    values={}
    for variant in ['ch0','ch1','pg0','pg1','pg2']:
        for case in ['w0','w1','w2','w3','w4']:
            vals=[float(r['client_ms']) for r in rows if r['variant']==variant and r['case']==case and r['warmup']=='False']
            assert len(vals)==10
            q1,_,q3=statistics.quantiles(vals,n=4,method='inclusive')
            result=dict(median=statistics.median(vals),q1=q1,q3=q3,iqr=q3-q1)
            recorded=next(r for r in summary if r['variant']==variant and r['case']==case)
            assert all(abs(result[k]-float(recorded[k]))<1e-8 for k in result)
            values[(variant,case)]=result
    log=load(root/'ch_query_log.json');lookup={r['query_id']:r for r in log}
    assert len(log)==120
    assert set(lookup)=={r['query_id'] for r in rows if r['variant'].startswith('ch')}
    pruning=list(csv.DictReader((root/'ch_pruning.csv').open(encoding='utf-8-sig')))
    for p in pruning:
        assert abs(float(p['pruning'])-(1-int(p['selected_marks'])/int(p['total_marks'])))<1e-12
        ids=[r['query_id'] for r in rows if r['variant']==p['variant'] and r['case']==p['case'] and r['warmup']=='False']
        assert statistics.median(int(lookup[i]['read_rows']) for i in ids)==float(p['read_rows_median'])
    latency=[['Workload','CH0','CH1','PG0','PG1','PG2']]
    for case in ['w0','w1','w2','w3','w4']:
        latency.append([case.upper()]+[number(values[(v,case)]['median'],2)+'\n('+number(values[(v,case)]['iqr'],2)+')'
                       for v in ['ch0','ch1','pg0','pg1','pg2']])
    marks=[['Workload','Marks chọn/tổng','Pruning (%)','Dòng đọc']]
    for case in ['w0','w1','w2','w3','w4']:
        p=next(r for r in pruning if r['variant']=='ch1' and r['case']==case)
        marks.append([case.upper(),number(int(p['selected_marks']))+'/'+number(int(p['total_marks'])),
                      number(float(p['pruning'])*100,3),number(float(p['read_rows_median']))])
    scans=list(csv.DictReader((root/'pg_scans.csv').open(encoding='utf-8-sig')))
    selected=[['Case / cấu hình','Kiểu quét','Heap blocks\nexact/lossy','Dòng loại\nfilter/recheck']]
    for case in ['w0','w3']:
        for v in ['pg0','pg1','pg2']:
            s=next(r for r in scans if r['variant']==v and r['case']==case)
            heap='—' if not s.get('Exact Heap Blocks') and not s.get('Lossy Heap Blocks') else '/'.join(number(float(s.get(k) or 0)) for k in ['Exact Heap Blocks','Lossy Heap Blocks'])
            removed=[]
            for key in ['Rows Removed by Filter','Rows Removed by Index Recheck']:
                if not s.get(key):
                    removed.append('—')
                    continue
                x=float(s.get(key) or 0)*float(s['Actual Loops'])
                removed.append(('≈' if float(s['Actual Loops'])>1 else '')+number(x))
            selected.append([case.upper()+' / '+v.upper(),('Parallel ' if float(s['Actual Loops'])>1 else '')+s['Node Type'],heap,'/'.join(removed)])
    result={'rows':validation['rows'],'latency':latency,'ch_marks':marks,'pg_selected':selected,
            'answers':answers['ch0'],'latency_values':{v:{c:values[(v,c)] for c in ['w0','w1','w2','w3','w4']} for v in ['ch0','ch1','pg0','pg1','pg2']}}
    (root/'report_tables.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (root/'audit.json').write_text(json.dumps(dict(status='PASS',rows=validation['rows'],measured=250,warmups=50,
        unique_query_ids=300,ch_queryfinish=120,cells_recomputed=25,source_archive_hashes_match=True,
        data_fingerprints_match=True,answers_match=True),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    audit(parser.parse_args().run)
