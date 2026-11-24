"""Isolated cross-DB pilot/formal runs; chapter-3 data and protocol stay intact."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import re
import struct
import subprocess
import time
import urllib.parse
import uuid

from .common import (ROOT, Client, csv_write, distribution, fixed_batches,
                     identifier, object_sha, quote, read, save, sha, utc)
from .runner import ddl, workloads

ROW = struct.Struct('<qqiHIihhhhhi')
PG_FIELDS = ('q', 'q', 'i', 'i', 'q', 'i', 'h', 'h', 'h', 'h', 'h', 'i')
PG_HEADER = b'PGCOPY\n\xff\r\n\0' + struct.pack('!ii', 0, 0)
MODULUS = 1 << 256
VARIANTS = ('ch0', 'ch1', 'pg0', 'pg1', 'pg2')


class Digest:
    """Practical order-independent check of every field, including duplicates."""
    def __init__(self):
        self.n = self.total = self.xor = 0

    def add(self, line):
        value = int.from_bytes(hashlib.sha256(line).digest(), 'big')
        self.n += 1
        self.total = (self.total + value) % MODULUS
        self.xor ^= value
        if self.n % 5000000 == 0:print('Fingerprint rows:',self.n,flush=True)

    def result(self):
        return dict(rows=self.n, sha256_sum=f'{self.total:064x}', sha256_xor=f'{self.xor:064x}')


def canonical_line(values):
    return ('\t'.join(str(x) for x in values) + '\n').encode('ascii')


def pg_binary_row(values):
    converted = list(values)
    converted[3] -= 10957  # PostgreSQL Date epoch: 2000-01-01.
    converted[4] = (converted[4] - 946684800) * 1000000
    fields = [struct.pack('!h', len(values))]
    for fmt, value in zip(PG_FIELDS, converted):
        payload = struct.pack('!' + fmt, value)
        fields.extend((struct.pack('!i', len(payload)), payload))
    return b''.join(fields)


def convert_input(source, target):
    return convert_inputs([source], target)


def convert_inputs(sources, target):
    digest = Digest()
    with Path(target).open('xb') as out:
        out.write(PG_HEADER)
        for source in sources:
            with Path(source).open('rb') as src:
                while chunk := src.read(ROW.size * 10000):
                    if len(chunk) % ROW.size:
                        raise RuntimeError('Truncated RowBinary input')
                    buffer = bytearray()
                    for values in ROW.iter_unpack(chunk):
                        digest.add(canonical_line(values))
                        buffer.extend(pg_binary_row(values))
                    out.write(buffer)
            if len(sources)>1:print('Converted source',Path(source).name,'rows',digest.n,flush=True)
        out.write(struct.pack('!h', -1))
    return digest.result()


def locked_inputs(manifest, base, data, scale):
    if scale=='1m':
        sample=manifest['samples']['1m']
        entries=[(Path(data)/sample['filename'],sample['sha256'])]
        count=sample['rows']
    else:
        if [f['shard'] for f in manifest['files']]!=base['shards'] or len(manifest['files'])!=30:
            raise RuntimeError('30M requires all 30 shards in locked order')
        entries=[(Path(data)/f'hits_{f["shard"]}.rowbinary',f['rowbinary_sha256']) for f in manifest['files']]
        count=sum(f['rows'] for f in manifest['files'])
        if count!=30000000:raise RuntimeError('Expected exactly 30M source rows')
    hashes={}
    for path,wanted in entries:
        actual=sha(path)
        if actual!=wanted:raise RuntimeError('Locked input changed: '+str(path))
        hashes[path.name]=actual
    return [p for p,_ in entries],count,hashes


def selected_marks(plan):
    ratios=re.findall(r'Granules:\s*(\d+)\s*/\s*(\d+)',plan)
    if ratios:return int(ratios[-1][0])
    single=re.findall(r'Granules:\s*(\d+)',plan)
    if single:return int(single[0])
    raise RuntimeError('Cannot extract selected granules from saved EXPLAIN')


def scan_nodes(plan):
    result=[]
    if 'Relation Name' in plan and 'Scan' in plan.get('Node Type',''):
        # Rows/removed rows are per-loop means. Buffers already include children;
        # do not add index-child buffers again or multiply buffers by loops.
        fields=['Node Type','Relation Name','Index Name','Actual Rows','Actual Loops',
                'Rows Removed by Filter','Rows Removed by Index Recheck',
                'Exact Heap Blocks','Lossy Heap Blocks','Shared Hit Blocks','Shared Read Blocks']
        result.append({key:plan[key] for key in fields if key in plan})
    for child in plan.get('Plans',[]):result.extend(scan_nodes(child))
    return result


def pg_ddl(table, schema):
    mapping = {'Int64': 'bigint', 'Int32': 'integer', 'Int16': 'smallint',
               'Date': 'date', "DateTime('UTC')": 'timestamp with time zone'}
    fields = ', '.join(f'{name} {mapping[typ]} NOT NULL' for name, typ, _ in schema)
    return f'CREATE TABLE {table} ({fields})'


def pg_workloads(table, parameters):
    queries = workloads(table, parameters)
    return {key: query.replace('count()', 'count(*)').replace('toDate(', 'DATE(')
            for key, query in queries.items()}


def schedule(config):
    randomizer = random.Random(config['seed'])
    cells = [(variant, case) for variant in VARIANTS for case in ('w0', 'w1', 'w2', 'w3', 'w4')]
    result = []
    for warmup, rounds in ((True, config['warmups']), (False, config['query_rounds'])):
        for round_no in range(rounds):
            shuffled = list(cells)
            randomizer.shuffle(shuffled)
            result.extend(dict(variant=v, case=c, warmup=warmup, round=round_no)
                          for v, c in shuffled)
    return result


def numeric_select(table, schema, engine):
    fields = []
    for name, typ, _ in schema:
        if typ == 'Date':
            expr = f'toUInt16({name})' if engine == 'ch' else f"({name}-DATE '1970-01-01')"
        elif typ.startswith('DateTime'):
            expr = f'toUInt32({name})' if engine == 'ch' else f'extract(epoch FROM {name})::bigint'
        else:
            expr = name
        fields.append(expr)
    return 'SELECT ' + ','.join(fields) + ' FROM ' + table


def ch_lines(client, sql):
    params = dict(client.settings, query=sql + ' FORMAT TabSeparated', wait_end_of_query=1)
    client.conn.close()
    client.conn.request('POST', '/?' + urllib.parse.urlencode(params),
                        body=b'', headers=dict(client.headers, **{'Content-Length': '0'}))
    response = client.conn.getresponse()
    if response.status != 200:
        raise RuntimeError(response.read().decode(errors='replace')[:1000])
    for line in response:
        yield line
    client.last_end = time.perf_counter()


def digest_lines(lines):
    digest = Digest()
    pending = b''
    for block in lines:
        pending += bytes(block)
        chunks = pending.split(b'\n')
        pending = chunks.pop()
        for line in chunks:
            digest.add(line + b'\n')
    if pending:
        raise RuntimeError('Incomplete canonical row')
    return digest.result()


def snapshot(client, database, table):
    return client.rows('SELECT name,rows,marks,part_type,bytes_on_disk,data_compressed_bytes,'
                       'data_uncompressed_bytes,marks_bytes,primary_key_bytes_in_memory '
                       f'FROM system.parts WHERE active AND database={quote(database)} '
                       f'AND table={quote(table)} ORDER BY name')


def stable(client, database, tables, out):
    trace, previous, consecutive = [], None, 0
    started = time.perf_counter()
    while time.perf_counter() - started < 1200:
        parts = {t: snapshot(client, database, t) for t in tables}
        busy = client.rows('SELECT '
            f'(SELECT count() FROM system.merges WHERE database={quote(database)}) AS merges, '
            f'(SELECT count() FROM system.mutations WHERE database={quote(database)} AND NOT is_done) AS mutations')[0]
        quiet = not busy['merges'] and not busy['mutations']
        consecutive = consecutive + 1 if quiet and parts == previous else 1 if quiet else 0
        trace.append(dict(elapsed_s=time.perf_counter()-started, parts=parts, **busy))
        previous = parts
        if consecutive == 3:
            save(out, trace)
            return parts
        time.sleep(10)
    save(out, trace)
    raise RuntimeError('Stability timeout')


def pilot(args):
    # Import only for this optional workflow; chapter-3 commands need no psycopg.
    import psycopg
    config = read(ROOT/'configs/comparison.json')
    base_path = ROOT/config['base_protocol']
    if sha(base_path) != config['base_protocol_sha256']:
        raise RuntimeError('Base protocol changed; review and version the comparison first')
    base = read(base_path)
    out = ROOT/'results/tuan'/identifier(args.machine)/identifier(args.run)
    if out.exists():
        raise RuntimeError('Run already exists; use a new run ID')
    namespace = identifier('cmp_' + args.run)
    manifest = read(ROOT/'manifests/hits30m.lock.json')
    paths,n,source_hashes=locked_inputs(manifest,base,args.data,args.scale)
    if manifest['schema_hash'] != object_sha(base['schema']) or ROW.size != manifest['row_bytes']:
        raise RuntimeError('Schema or RowBinary width mismatch')
    if sorted(os.sched_getaffinity(0)) != config['cpu_affinity']:
        raise RuntimeError('Client CPU affinity differs from protocol')
    client = Client(base['settings'])
    if client.scalar('SELECT version()') != base['expected_clickhouse_version']:
        raise RuntimeError('ClickHouse version mismatch')
    keep_alive=int(client.scalar("SELECT value FROM system.server_settings WHERE name='keep_alive_timeout'"))
    if keep_alive < config['http_keep_alive_timeout_s']:
        raise RuntimeError('Dedicated HTTP keep-alive shorter than comparison protocol')
    # Unix peer authentication; no password or private connection string in outputs.
    pg = psycopg.connect(host=args.pg_socket, port=args.pg_port, dbname='postgres',
                        autocommit=True, prepare_threshold=config['psycopg_prepare_threshold'])
    if int(pg.execute('SHOW server_version_num').fetchone()[0]) != config['expected_postgresql_version_num']:
        raise RuntimeError('PostgreSQL version mismatch')
    for key, value in config['postgresql_settings'].items():
        pg.execute('SELECT set_config(%s,%s,false)', (key, value))
    if int(client.scalar(f'EXISTS DATABASE {namespace}')) or pg.execute(
            'SELECT EXISTS(SELECT FROM pg_namespace WHERE nspname=%s)', (namespace,)).fetchone()[0]:
        raise RuntimeError('Database/schema exists; no overwrite')
    out.mkdir(parents=True)
    source_files = ['src/mtstudy/comparison.py', 'src/mtstudy/common.py',
                    'src/mtstudy/runner.py', 'scripts/compare_databases.py',
                    'configs/comparison.json', 'requirements-comparison.txt']
    save(out/'source_hashes.json', {name: sha(ROOT/name) for name in source_files})
    for name in source_files:
        copy_path = out/'source'/name
        copy_path.parent.mkdir(parents=True, exist_ok=True)
        copy_path.write_bytes((ROOT/name).read_bytes())
    started = utc()
    save(out/'config.json', dict(protocol=config, protocol_hash=object_sha(config),
         base_protocol_hash=sha(base_path), source_sha256=source_hashes, rows=n,scale=args.scale,
         namespace=namespace, started_at=started, status='FORMAL' if args.scale=='30m' else 'PILOT_ONLY',
         git_commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip(),
         git_dirty=bool(subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True).stdout)))
    save(out/'input_manifest.json', manifest)
    save(out/'environment.json', dict(platform=platform.platform(), python=platform.python_version(),
         affinity=sorted(os.sched_getaffinity(0)), cpu=Path('/proc/cpuinfo').read_text(),
         memory=Path('/proc/meminfo').read_text(), psycopg=psycopg.__version__,
         clickhouse=client.scalar('SELECT version()'),
         postgresql=pg.execute('SELECT version()').fetchone()[0],
         pg_prepare_threshold=pg.prepare_threshold,
         pg_timezone=pg.execute('SHOW timezone').fetchone()[0],
         pg_backend_pid=pg.info.backend_pid))
    names = list(config['postgresql_settings']) + ['shared_buffers','fsync','synchronous_commit',
              'full_page_writes','max_parallel_workers','max_worker_processes','block_size','autovacuum']
    save(out/'pg_settings.json',dict(pg.execute('SELECT name,setting FROM pg_settings WHERE name=ANY(%s)',(names,)).fetchall()))
    save(out/'ch_settings.json',client.rows('SELECT name,value FROM system.settings WHERE name IN (' +
         ','.join(quote(key) for key in base['settings']) + ') ORDER BY name'))
    derived = Path(args.derived)/args.run
    derived.mkdir(parents=True, exist_ok=False)
    binary = derived/(args.scale+'.pgcopy')
    source_digest = convert_inputs(paths, binary)
    if source_digest['rows']!=n:raise RuntimeError('Conversion row count differs from lock')
    save(out/'source_check.json',dict(fingerprint=source_digest, pgcopy_sha256=sha(binary),
         conversion_excluded_from_timing=True))
    client.execute(f'CREATE DATABASE {namespace}')
    pg.execute(f'CREATE SCHEMA {namespace}')
    queries, setup = {}, []
    for variant in VARIANTS:
        table = f'{namespace}.{variant}'
        engine = variant[:2]
        sql = ddl(table,base,'tuple()' if variant=='ch0' else '(CounterID, EventDate)') if engine=='ch' else pg_ddl(table,base['schema'])
        (out/'ddl').mkdir(exist_ok=True)
        (out/'ddl'/f'{variant}.sql').write_text(sql+';\n')
        print('Build',variant,flush=True)
        if engine=='ch':
            client.execute(sql)
            t0=time.perf_counter()
            for payload in fixed_batches(paths,ROW.size,1000000):
                client.execute(f'INSERT INTO {table} FORMAT RowBinary',payload=payload)
            loaded=time.perf_counter()-t0
            _,optimized=client.execute(f'OPTIMIZE TABLE {table} FINAL')
            queries[variant]=workloads(table,base['parameters'])
            (out/'ddl'/f'{variant}.actual.sql').write_text(client.execute(f'SHOW CREATE TABLE {table} FORMAT TSVRaw')[0])
            setup.append(dict(variant=variant,load_s=loaded,optimize_ms=optimized))
        else:
            pg.execute(sql)
            t0=time.perf_counter()
            with pg.cursor().copy(f'COPY {table} FROM STDIN WITH (FORMAT BINARY)') as copy:
                with binary.open('rb') as stream:
                    while chunk:=stream.read(2**20):copy.write(chunk)
            loaded=time.perf_counter()-t0
            index_sql = (f'CREATE INDEX {variant}_idx ON {table} USING brin (CounterID,EventDate) WITH (pages_per_range={config["brin_pages_per_range"]})' if variant=='pg1' else
                         f'CREATE INDEX {variant}_idx ON {table} USING btree (CounterID,EventDate)' if variant=='pg2' else None)
            t0=time.perf_counter()
            if index_sql:
                pg.execute(index_sql)
                (out/'ddl'/f'{variant}_index.sql').write_text(index_sql+';\n')
            indexed=time.perf_counter()-t0 if index_sql else 0
            t0=time.perf_counter();pg.execute(f'VACUUM (ANALYZE) {table}');vacuumed=time.perf_counter()-t0
            queries[variant]=pg_workloads(table,base['parameters'])
            setup.append(dict(variant=variant,load_s=loaded,index_s=indexed,vacuum_analyze_s=vacuumed))
        save(out/'setup.json',setup)
    save(out/'setup.json',setup)
    parts=stable(client,namespace,['ch0','ch1'],out/'stability_before.json')
    if any(len(x)!=1 or x[0]['part_type']!='Wide' or int(x[0]['rows'])!=n for x in parts.values()):
        raise RuntimeError('Controlled SELECT requires one Wide part with all source rows')
    fingerprints,answers,plans={}, {}, {}
    for variant in VARIANTS:
        table=f'{namespace}.{variant}'
        sql=numeric_select(table,base['schema'],variant[:2])
        print('Validate all fields:',variant,flush=True)
        if variant.startswith('ch'):
            fingerprints[variant]=digest_lines(ch_lines(client,sql))
        else:
            with pg.cursor().copy(f'COPY ({sql}) TO STDOUT WITH (FORMAT TEXT)') as copy:
                fingerprints[variant]=digest_lines(copy)
        if fingerprints[variant]!=source_digest:
            save(out/'fingerprints_failed.json',fingerprints)
            raise RuntimeError('Whole-row fingerprint differs from input: '+variant)
        answers[variant],plans[variant]={},{}
        for case,query in queries[variant].items():
            if variant.startswith('ch'):
                answers[variant][case]=[int(x) for x in client.execute(query+' FORMAT TabSeparated')[0].strip().split('\t')]
                plans[variant][case]=client.execute('EXPLAIN indexes=1 '+query)[0]
            else:
                answers[variant][case]=[int(x) for x in pg.execute(query).fetchone()]
                plans[variant][case]=pg.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+query).fetchone()[0]
        if answers[variant]!=answers['ch0']:
            save(out/'answers_failed.json',answers)
            raise RuntimeError('COUNT/SUM mismatch: '+variant)
    save(out/'fingerprints.json',fingerprints);save(out/'answers.json',answers);save(out/'plans.json',plans)
    save(out/'sql.json',queries)
    pg.execute('CHECKPOINT')
    measurements=[]
    order=schedule(config);save(out/'schedule.json',order)
    journal=out/'journal.jsonl'
    for item in order:
        variant,case=item['variant'],item['case'];query=queries[variant][case]
        entry=dict(item,started_at=utc(),query_id='cmp_'+uuid.uuid4().hex)
        try:
            busy=int(client.scalar('SELECT count() FROM system.processes WHERE query_id!=currentQueryID()'))
            others=pg.execute("SELECT count(*) FROM pg_stat_activity WHERE pid<>pg_backend_pid() "
                              "AND backend_type='client backend' AND state='active'").fetchone()[0]
            if busy or others:raise RuntimeError('Other active query on comparison instance')
            if variant.startswith('ch'):
                # The dedicated server keeps HTTP sockets for 3600 s. Suppress
                # common.Client's chapter-3 idle reconnect in this workflow only.
                client.last_end=time.perf_counter()
            t0=time.perf_counter()
            if variant.startswith('ch'):
                text,_=client.execute(query+' FORMAT TabSeparated',query_id=entry['query_id'])
                result=[int(x) for x in text.strip().split('\t')]
            else:result=[int(x) for x in pg.execute(query).fetchone()]
            entry['client_ms']=(time.perf_counter()-t0)*1000
            if result!=answers['ch0'][case]:raise RuntimeError('Result changed during measurement')
            if variant.startswith('ch'):entry['http_local_port']=client.conn.sock.getsockname()[1]
            entry['result']=result;entry['ok']=True
        except Exception as exc:
            entry['ok']=False;entry['error']=str(exc)
            with journal.open('a') as f:f.write(json.dumps(entry)+'\n')
            raise
        with journal.open('a') as f:f.write(json.dumps(entry)+'\n')
        measurements.append(entry)
    csv_write(out/'queries.csv',measurements)
    client.execute('SYSTEM FLUSH LOGS')
    query_ids=[r['query_id'] for r in measurements if r['variant'].startswith('ch')]
    query_log=client.rows('SELECT query_id,query_duration_ms,read_rows,read_bytes,memory_usage '
                         "FROM system.query_log WHERE type='QueryFinish' AND query_id IN (" +
                         ','.join(quote(query_id) for query_id in query_ids) + ')')
    save(out/'ch_query_log.json',query_log)
    if len(query_log)!=len(query_ids) or {r['query_id'] for r in query_log}!=set(query_ids):
        raise RuntimeError('ClickHouse QueryFinish coverage mismatch')
    after=stable(client,namespace,['ch0','ch1'],out/'stability_after.json')
    if after!=parts:raise RuntimeError('Parts changed during measurement')
    pg_indexes=pg.execute('SELECT tablename,indexdef FROM pg_indexes WHERE schemaname=%s ORDER BY tablename',(namespace,)).fetchall()
    save(out/'pg_indexes.json',pg_indexes)
    save(out/'pg_correlations.json',pg.execute('SELECT tablename,attname,correlation FROM pg_stats '
         "WHERE schemaname=%s AND attname IN ('counterid','eventdate') ORDER BY tablename,attname",
         (namespace,)).fetchall())
    pg_sizes=pg.execute('SELECT relname,pg_table_size(oid),pg_indexes_size(oid) FROM pg_class '
                       'WHERE relnamespace=%s::regnamespace AND relkind=\'r\' ORDER BY relname',(namespace,)).fetchall()
    save(out/'pg_storage.json',pg_sizes);save(out/'ch_storage.json',parts)
    summaries=[]
    for variant in VARIANTS:
        for case in queries[variant]:
            vals=[r['client_ms'] for r in measurements if r['variant']==variant and r['case']==case and not r['warmup']]
            summaries.append(dict(variant=variant,case=case,**distribution(vals)))
    csv_write(out/'summary.csv',summaries)
    pruning=[]
    for variant in ['ch0','ch1']:
        total=sum(int(p['marks']) for p in parts[variant])
        for case in queries[variant]:
            chosen=selected_marks(plans[variant][case])
            ids={r['query_id'] for r in measurements if r['variant']==variant and r['case']==case and not r['warmup']}
            logs=[r for r in query_log if r['query_id'] in ids]
            pruning.append(dict(variant=variant,case=case,selected_marks=chosen,total_marks=total,
                 pruning=1-chosen/total,read_rows_median=distribution([int(r['read_rows']) for r in logs])['median'],
                 read_bytes_median=distribution([int(r['read_bytes']) for r in logs])['median']))
    csv_write(out/'ch_pruning.csv',pruning)
    scans=[]
    for variant in ['pg0','pg1','pg2']:
        for case in queries[variant]:
            scans.extend(dict(variant=variant,case=case,**node) for node in scan_nodes(plans[variant][case][0]['Plan']))
    csv_write(out/'pg_scans.csv',scans)
    save(out/'validation.json',dict(status='PASS_FORMAL' if args.scale=='30m' else 'PASS_PILOT_ONLY',completed_at=utc(),rows=n,
         configurations=list(VARIANTS),whole_row_fingerprints_match=True,answers_match=True,
         normal_select_measured=sum(not r['warmup'] for r in measurements),
         warmups=sum(r['warmup'] for r in measurements),parts_unchanged=True,
         ch_queryfinish_covered=len(query_log),pg_prepare_threshold=pg.prepare_threshold,
         formal_30m_executed=args.scale=='30m',independent_review=False,
         timed_http_connections=len({r['http_local_port'] for r in measurements if r['variant'].startswith('ch')})))
    client.conn.close();pg.close()
    print('PASS_FORMAL:' if args.scale=='30m' else 'PASS_PILOT_ONLY:',out,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',required=True)
    parser.add_argument('--derived',required=True)
    parser.add_argument('--pg-socket',required=True)
    parser.add_argument('--pg-port',type=int,default=55432)
    parser.add_argument('--machine',default='wsl_xeon')
    parser.add_argument('--run',required=True)
    parser.add_argument('--scale',choices=['1m','30m'],default='1m')
    pilot(parser.parse_args())
