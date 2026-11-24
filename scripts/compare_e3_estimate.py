#!/usr/bin/env python3
"""Retrospective, group-defined linear ingestion baseline; not a DBMS cost model."""
import argparse
import csv
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path


def read_cases(path, expected_n, expected_per_batch):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    groups = {batch: [] for batch in (10000, 100000, 1000000)}
    for row in rows:
        batch = int(row['batch_rows'])
        elapsed = float(row['ingest_ack_s'])
        if int(row['rows']) != expected_n or not math.isfinite(elapsed) or elapsed <= 0:
            raise ValueError('Invalid row count or elapsed time')
        groups[batch].append(row)
    if any(len(group) != expected_per_batch for group in groups.values()):
        raise ValueError('Incomplete experiment matrix')
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', required=True, type=Path)
    parser.add_argument('--formal', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    pilot = read_cases(args.pilot, 1000000, 3)
    formal = read_cases(args.formal, 30000000, 9)
    result = []
    for batch in pilot:
        pilot_mean = statistics.mean(float(row['ingest_ack_s']) for row in pilot[batch])
        actual = statistics.mean(float(row['ingest_ack_s']) for row in formal[batch])
        estimated = 30 * pilot_mean
        result.append(dict(batch_rows=batch, pilot_n=1000000, pilot_observations=3,
                           pilot_ack_mean_s=pilot_mean, target_n=30000000,
                           actual_observations=9, estimated_ack_s=estimated,
                           actual_ack_mean_s=actual, signed_error_s=estimated-actual,
                           absolute_error_s=abs(estimated-actual),
                           ape_percent=100*abs(estimated-actual)/actual))
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out/'estimated_vs_actual_e3.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    manifest = dict(created_at=datetime.now(timezone.utc).isoformat(),
                    analysis_type='retrospective; no preregistered forecast or validation holdout',
                    authorship='Group-defined empirical baseline, not an author-provided formula or official ClickHouse cost model',
                    formula='T_est(N,B) = (N/N0) * mean(T_ACK(N0,B)); N0=1000000',
                    assumptions=['same batch, row format, settings, machine and row order policy',
                                 'constant average per-request/per-row cost across scales',
                                 'negligible fixed run overhead and scale-dependent merge/cache effects'],
                    caveats=['single pilot scale; no alpha/beta fit or validated extrapolation',
                             'pilot source commit differs and git_dirty was true at initialization',
                             'formal protocol adds provenance notes; numeric schema/settings match pilot',
                             'all original observations retained, including the slow first 10k pilot'],
                    inputs={name: dict(name=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                            for name,path in [('pilot',args.pilot),('formal',args.formal)]},
                    mae_s=statistics.mean(row['absolute_error_s'] for row in result),
                    mape_percent=statistics.mean(row['ape_percent'] for row in result),
                    results=result)
    (args.out/'model_and_provenance.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
