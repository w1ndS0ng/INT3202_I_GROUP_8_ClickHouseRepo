#!/usr/bin/env python3
"""Capture separate SELECT diagnostics; never append them to formal benchmark data."""
import argparse
import json
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-config', required=True)
    parser.add_argument('--formal-config', required=True, type=Path)
    parser.add_argument('--table', required=True)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*\.[A-Za-z_][A-Za-z_0-9]*', args.table):
        raise ValueError('Expected database.table')
    args.out.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.formal_config.read_text(encoding='utf-8-sig'))
    settings = config['protocol']['settings']
    suffix = ' SETTINGS ' + ', '.join(f'{k}={v}' for k,v in settings.items())
    records = []

    def run(label, sql):
        query_id = 'e3_diagnostic_'+uuid.uuid4().hex
        process = subprocess.run(['clickhouse-client', '--config-file', args.client_config,
                                  '--query_id', query_id, '--query', sql],
                                 text=True, capture_output=True, timeout=180)
        (args.out/(label+'.sql')).write_text(sql+'\n', encoding='utf-8')
        (args.out/(label+'.txt')).write_text(process.stdout+process.stderr, encoding='utf-8')
        records.append(dict(label=label, query_id=query_id, exit_code=process.returncode))
        if process.returncode:
            raise RuntimeError(f'{label} failed; see diagnostic log (no credentials recorded)')
        return process.stdout

    run('version', 'SELECT version() FORMAT TSVRaw')
    database, table = args.table.split('.')
    snapshot = (f"SELECT name, uuid, rows, marks, bytes_on_disk FROM system.parts "
                f"WHERE database='{database}' AND table='{table}' AND active ORDER BY name FORMAT JSONEachRow")
    before = run('parts_before', snapshot)
    ids = []
    for name, where in [('full_scan',''), ('counter_filter',' WHERE CounterID=3258')]:
        query = f'SELECT sum(ResolutionWidth) FROM {args.table}{where}{suffix}'
        run(name+'_estimate', 'EXPLAIN ESTIMATE '+query+' FORMAT TSVRaw')
        run(name+'_plan', 'EXPLAIN indexes=1 '+query+' FORMAT TSVRaw')
        run(name+'_analyze', 'EXPLAIN ANALYZE indexes=1 '+query+' FORMAT TSVRaw')
        ids.append(records[-1]['query_id'])
        run(name+'_actual', query+' FORMAT Null')
        ids.append(records[-1]['query_id'])
    after = run('parts_after', snapshot)
    run('flush_logs', 'SYSTEM FLUSH LOGS')
    literals = ','.join("'"+i+"'" for i in ids)
    run('query_finish', 'SELECT query_id, query_duration_ms, read_rows, read_bytes, result_rows, memory_usage '
        f"FROM system.query_log WHERE query_id IN ({literals}) AND type='QueryFinish' AND is_initial_query "
        'ORDER BY query_id FORMAT JSONEachRow')
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(),
                    purpose='Two one-off SELECT diagnostics, not E1/E2/E3 repeated benchmark results',
                    table=args.table, same_parts_before_after=before==after,
                    settings=settings, records=records)
    (args.out/'diagnostic_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(output=str(args.out),same_parts_before_after=before==after)))


if __name__ == '__main__':
    main()
