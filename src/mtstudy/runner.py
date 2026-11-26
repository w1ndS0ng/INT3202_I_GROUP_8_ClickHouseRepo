import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import threading
import time
import uuid

from .common import (ROOT, Client, csv_write, fixed_batches, identifier,
                     object_sha, quote, read, save, sha, utc)


def workloads(table, p):
    select = f'SELECT count() AS matched, sum(ResolutionWidth) AS checksum FROM {table}'
    dates = f"EventDate >= toDate('{p['date_start']}') AND EventDate < toDate('{p['date_end']}')"
    return {
        'w0': select,
        'w1': select + f" WHERE CounterID={int(p['counter_id'])}",
        'w2': select + ' WHERE ' + dates,
        'w3': select + f" WHERE CounterID={int(p['counter_id'])} AND " + dates,
        'w4': select + f" WHERE RegionID={int(p['region_id'])}",
    }


def ddl(table, protocol, key, granularity=8192):
    fields = ',\n  '.join(f'`{name}` {typ} CODEC(LZ4)' for name,typ,_ in protocol['schema'])
    return (f'CREATE TABLE {table} (\n  {fields}\n) ENGINE=MergeTree\n'
            f'ORDER BY {key}\nSETTINGS index_granularity={int(granularity)}, '
            'index_granularity_bytes=0, min_bytes_for_wide_part=0, min_rows_for_wide_part=0, '
            'write_final_mark=0, fsync_after_insert=1, auto_statistics_types=\'\'')


def environment(client):
    server = client.rows('SELECT version() AS version, timezone() AS timezone')[0]
    cpu = subprocess.run(['lscpu'], text=True, capture_output=True, check=False).stdout if shutil.which('lscpu') else ''
    mem = Path('/proc/meminfo').read_text() if Path('/proc/meminfo').exists() else ''
    return dict(recorded_at=utc(), platform=platform.platform(), cpu_count=os.cpu_count(),
                cpu=cpu, memory=mem, python=platform.python_version(), server=server,
                disks=client.rows('SELECT name, type, path, total_space, free_space FROM system.disks'))


def initialize(args, protocol):
    for value in (args.member,args.machine,args.run):
        identifier(value)
    out = ROOT/'results'/args.member/args.machine/args.run
    if out.exists():
        raise RuntimeError(f'Run already exists: {out}; use a new run ID')
    data = Path(args.data).expanduser().resolve()
    manifest = read(data/'manifest.json')
    if manifest['schema_hash'] != object_sha(protocol['schema']):
        raise RuntimeError('Prepared schema differs from protocol')
    client = Client(protocol['settings'], args.client_config)
    env = environment(client)
    if env['server']['version'] != protocol['expected_clickhouse_version']:
        raise RuntimeError('Server version differs: update the shared protocol before initializing all three members')
    database = 'mtr_' + '_'.join((args.member,args.machine,args.run))
    if int(client.scalar(f'EXISTS DATABASE {database}')):
        raise RuntimeError('Database already exists; use a new run ID')
    revision = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
    dirty = subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
    out.mkdir(parents=True)
    config = dict(member=args.member,machine=args.machine,run=args.run,database=database,
                  protocol=protocol,protocol_hash=object_sha(protocol),data_dir=str(data),
                  manifest_hash=object_sha(manifest),git_commit=revision,git_dirty=bool(dirty),created_at=utc())
    save(out/'config.json', config)
    save(out/'input_manifest.json', manifest)
    save(out/'environment.json',env)
    names = ','.join(quote(k) for k in protocol['settings'])
    save(out/'effective_settings.json',client.rows(f'SELECT name,value FROM system.settings WHERE name IN ({names}) ORDER BY name'))
    client.execute(f'CREATE DATABASE {database}')
    print(f'Initialized {out}\nDatabase: {database}',flush=True)


class Run:
    def __init__(self,args):
        self.args=args
        candidate=ROOT/'results'/identifier(args.member)/identifier(args.machine)/identifier(args.run)
        if not candidate.exists():
            art=ROOT/'artifacts'/identifier(args.member)/identifier(args.machine)/identifier(args.run)
            if art.exists():
                candidate=art
        self.out=candidate
        self.c=read(self.out/'config.json')
        self.p=self.c['protocol']
        self.db=self.c['database']
        if not self.db.startswith('mtr_'):
            raise RuntimeError('Unexpected database namespace')
        self.manifest=read(self.out/'input_manifest.json')
        if object_sha(self.manifest)!=self.c['manifest_hash']:
            raise RuntimeError('Run input manifest changed')
        if getattr(args,'command',None) in ('build','queries','ingest'):
            self.client=Client(self.p['settings'],args.client_config)
            if self.client.scalar('SELECT version()')!=self.p['expected_clickhouse_version']:
                raise RuntimeError('ClickHouse version changed during this run')
        else:
            self.client=None
        self.row_bytes=sum(x[2] for x in self.p['schema'])

    def path(self,*parts):
        path=self.out.joinpath(*parts)
        path.parent.mkdir(parents=True,exist_ok=True)
        return path

    def inputs(self,scale):
        if scale!='30m':
            sample=self.manifest.get('samples',{}).get(scale)
            if not sample:
                raise RuntimeError('Prepare all 30 shards and their nested samples before pilot/calibration')
            path=Path(self.c['data_dir'])/sample['filename']
            if sha(path)!=sample['sha256']:
                raise RuntimeError('Sample input changed')
            return [path],sample['rows']
        count=self.p['scales'][scale]
        entries=self.manifest['files'][:count]
        if len(entries)!=count or [f['shard'] for f in entries]!=self.p['shards'][:count]:
            raise RuntimeError(f'Prepare all {count} shards for {scale} before initializing this run')
        paths=[]
        for entry in entries:
            path=Path(self.c['data_dir'])/f'hits_{entry["shard"]}.rowbinary'
            if sha(path)!=entry['rowbinary_sha256']:
                raise RuntimeError(f'Input changed: {path}')
            paths.append(path)
        return paths,sum(e['rows'] for e in entries)

    def variants(self,experiment):
        if experiment=='keys':
            return [(key,value,8192) for key,value in self.p['keys'].items()]
        if experiment=='granularity':
            return [(f'g{g}',self.p['keys']['k1'],g) for g in self.p['granularities']]
        raise ValueError(experiment)

    def name(self,experiment,scale,variant):
        return f'{self.db}.{experiment}_{scale}_{variant}'

    def snapshot(self,table):
        db,name=table.split('.')
        return self.client.rows("SELECT name,rows,marks,bytes_on_disk,data_compressed_bytes,"
            "data_uncompressed_bytes,marks_bytes,primary_key_bytes_in_memory,part_type "
            f"FROM system.parts WHERE active AND database={quote(db)} AND table={quote(name)} ORDER BY name")

    def quiet(self):
        busy=int(self.client.scalar("SELECT count() FROM system.merges WHERE database != 'system'"))
        mutations=int(self.client.scalar("SELECT count() FROM system.mutations WHERE NOT is_done AND database != 'system'"))
        processes=int(self.client.scalar("SELECT count() FROM system.processes WHERE query_id != currentQueryID() AND NOT startsWith(query, 'SYSTEM FLUSH')"))
        if busy or mutations or processes:
            raise RuntimeError(f'Machine busy: merges={busy}, mutations={mutations}, other queries={processes}; rerun in a new measurement run after checking logs')

    def stable(self,table,label):
        start=time.perf_counter()
        previous=None
        consecutive=0
        trace=[]
        while True:
            snap=self.snapshot(table)
            busy=int(self.client.scalar("SELECT count() FROM system.merges WHERE database != 'system'"))
            mutations=int(self.client.scalar("SELECT count() FROM system.mutations WHERE NOT is_done AND database != 'system'"))
            trace.append(dict(elapsed_s=time.perf_counter()-start,parts=snap,merges=busy,mutations=mutations))
            consecutive=consecutive+1 if snap==previous and busy==0 and mutations==0 else 1 if not busy and not mutations else 0
            previous=snap
            if consecutive>=self.p['stable_samples']:
                save(self.path('checks',label+'_stability.json'),trace)
                return time.perf_counter()-start
            if time.perf_counter()-start>self.p['stable_timeout_seconds']:
                save(self.path('checks',label+'_stability_timeout.json'),trace)
                raise RuntimeError('Stability timeout: retain partial results; do not label them stable')
            time.sleep(self.p['stable_interval_seconds'])

    def fingerprint(self,table):
        names=','.join(f'`{x[0]}`' for x in self.p['schema'])
        return self.client.rows(f'SELECT count() AS n, sum(cityHash64(tuple({names}))) AS hash_sum, '
                               f'groupBitXor(cityHash64(tuple({names}))) AS hash_xor FROM {table}')[0]

    def create(self,table,key,granularity=8192):
        if int(self.client.scalar(f'EXISTS TABLE {table}')):
            raise RuntimeError(f'Table already exists: {table}; no automatic truncate/reload')
        sql=ddl(table,self.p,key,granularity)
        self.path('ddl',table.split('.')[1]+'.sql').write_text(sql+';\n')
        self.client.execute(sql)
        actual_ddl, _ = self.client.execute(f'SHOW CREATE TABLE {table} FORMAT TSVRaw')
        self.path('ddl',table.split('.')[1]+'.actual.sql').write_text(actual_ddl.strip()+';\n')

    def load(self,table,paths,batch_rows,limit_rows=None):
        count=0
        log=[]
        started=None
        finished=None
        for i,payload in enumerate(fixed_batches(paths,self.row_bytes,batch_rows,limit_rows)):
            query_id='mtr_insert_'+uuid.uuid4().hex
            before=time.perf_counter()
            if started is None:
                started=before
            _,elapsed=self.client.execute(f'INSERT INTO {table} FORMAT RowBinary',query_id,payload)
            finished=time.perf_counter()
            n=len(payload)//self.row_bytes
            count+=n
            log.append(dict(query_id=query_id,batch=i,rows=n,client_ms=elapsed))
        if not count:
            raise RuntimeError('Empty input')
        return dict(rows=count,ingest_ack_s=finished-started,throughput_rows_s=count/(finished-started),batches=log)

    def build(self,experiment,scale):
        paths,n=self.inputs(scale)
        reference=None
        for variant,key,g in self.variants(experiment):
            table=self.name(experiment,scale,variant)
            print(f'Build {table}: {n:,} rows',flush=True)
            self.quiet()
            self.create(table,key,g)
            loaded=self.load(table,paths,1000000)
            save(self.path('setup',table.split('.')[1]+'_load.json'),loaded)
            # Controlled read experiment: equalize to one part. This is setup,
            # not a recommendation for production or a measure of natural merges.
            _,elapsed=self.client.execute(f'OPTIMIZE TABLE {table} FINAL')
            wait=self.stable(table,table.split('.')[1])
            snap=self.snapshot(table)
            if len(snap)!=1:
                raise RuntimeError('Controlled read experiment requires exactly one active Wide part')
            if snap[0]['part_type']!='Wide':
                raise RuntimeError('Expected Wide part')
            fingerprint=self.fingerprint(table)
            if int(fingerprint['n'])!=n or reference is not None and reference!=fingerprint:
                raise RuntimeError('Input count/content fingerprint mismatch')
            reference=fingerprint
            label=table.split('.')[1]
            save(self.path('checks',label+'_built.json'),dict(table=table,n=n,fingerprint=fingerprint,
                 parts=snap,optimize_setup_ms=elapsed,observed_stable_wait_s=wait,created_at=utc()))
            if variant==self.variants(experiment)[0][0]:
                profile={
                    'summary':self.client.rows(f'SELECT count() AS n,min(EventDate) AS first_day,max(EventDate) AS last_day, '
                        f'uniqExact(CounterID) AS counters,uniqExact(RegionID) AS regions FROM {table}'),
                    'by_date':self.client.rows(f'SELECT EventDate,count() AS n FROM {table} GROUP BY EventDate ORDER BY EventDate'),
                    'by_counter':self.client.rows(f'SELECT CounterID,count() AS n FROM {table} GROUP BY CounterID ORDER BY n DESC,CounterID'),
                    'by_region':self.client.rows(f'SELECT RegionID,count() AS n FROM {table} GROUP BY RegionID ORDER BY n DESC,RegionID')}
                save(self.path('checks',f'{experiment}_{scale}_profile.json'),profile)
            self.explain(experiment,scale,variant)
        print('Build verified. Setup timings are not benchmark observations.',flush=True)

    def explain(self,experiment,scale,variant):
        table=self.name(experiment,scale,variant)
        label=table.split('.')[1]
        if not self.path('checks',label+'_built.json').exists():
            raise RuntimeError('Build receipt missing')
        records=[]
        for case,sql in workloads(table,self.p['parameters']).items():
            self.path('sql',label+'_'+case+'.sql').write_text(sql+';\n')
            estimates=self.client.rows('EXPLAIN ESTIMATE '+sql)
            text,_=self.client.execute('EXPLAIN indexes=1 '+sql)
            self.path('explain',label+'_'+case+'_indexes.txt').write_text(text)
            record=dict(experiment=experiment,scale=scale,variant=variant,case=case,
                        estimated_rows=sum(int(x['rows']) for x in estimates),
                        selected_marks=sum(int(x['marks']) for x in estimates),
                        selected_parts=sum(int(x['parts']) for x in estimates),
                        total_marks=sum(int(x['marks']) for x in self.snapshot(table)),raw=estimates)
            records.append(record)
        save(self.path('explain',label+'.json'),records)
        return records

    def query_logs(self,ids):
        self.client.execute('SYSTEM FLUSH LOGS')
        result=[]
        for start in range(0,len(ids),200):
            values=','.join(quote(x) for x in ids[start:start+200])
            result.extend(self.client.rows("SELECT query_id,query_duration_ms,read_rows,read_bytes,memory_usage,"
                "ProfileEvents,Settings FROM system.query_log WHERE type='QueryFinish' AND is_initial_query "
                f'AND query_id IN ({values})'))
        mapping={r['query_id']:r for r in result}
        if len(result)!=len(ids) or set(mapping)!=set(ids):
            raise RuntimeError('Missing/duplicate QueryFinish records; keep journal and investigate logging')
        return mapping

    def queries(self,experiment,scale):
        label=f'{experiment}_{scale}'
        journal=self.path('queries',label+'_journal.jsonl')
        if journal.exists():
            raise RuntimeError('Measurement journal already exists; never overwrite/rerun selected observations')
        if experiment=='keys' and scale=='30m':
            forecast=read(self.path('model','forecast.json'))
            if forecast['protocol_hash']!=self.c['protocol_hash']:
                raise RuntimeError('Freeze forecasts before any 30M measured queries')
            if sha(self.path('model','model.json'))!=forecast['model_sha256']:
                raise RuntimeError('Frozen model changed')
            for variant,digest in forecast['explain_sha256'].items():
                if sha(self.path('explain',f'keys_30m_{variant}.json'))!=digest:
                    raise RuntimeError('Target estimates changed after forecast')
        cases=[]
        before={}
        references={}
        for variant,_,_ in self.variants(experiment):
            table=self.name(experiment,scale,variant)
            built=read(self.path('checks',table.split('.')[1]+'_built.json'))
            before[variant]=self.snapshot(table)
            if before[variant]!=built['parts']:
                raise RuntimeError('Parts changed after EXPLAIN/build; use a new run')
            for case,sql in workloads(table,self.p['parameters']).items():
                answer=self.client.rows(sql)[0]
                if int(answer['matched'])==0:
                    raise RuntimeError(f'{case} matches no rows; revise protocol parameters before formal measurements')
                if case in references and references[case]!=answer:
                    raise RuntimeError('Query result mismatch across layouts')
                references[case]=answer
                cases.append((variant,case,sql))
        save(self.path('checks',label+'_answers.json'),references)
        self.quiet()
        rng=random.Random(self.p['seed'])
        records=[]
        with journal.open('x',encoding='utf-8') as out:
            for round_id in range(-self.p['warmups'],self.p['query_rounds']):
                order=list(cases)
                rng.shuffle(order)
                for position,(variant,case,sql) in enumerate(order):
                    self.quiet()
                    qid='mtr_query_'+uuid.uuid4().hex
                    stamp=utc()
                    try:
                        _,elapsed=self.client.execute(sql+' FORMAT Null',qid)
                    except Exception as exc:
                        failed=dict(experiment=experiment,scale=scale,variant=variant,case=case,
                                    round=round_id,position=position,query_id=qid,started_at=stamp,
                                    warmup=round_id<0,status='error',error=str(exc))
                        out.write(json.dumps(failed)+'\n')
                        out.flush()
                        raise
                    record=dict(experiment=experiment,scale=scale,variant=variant,case=case,
                                round=round_id,position=position,query_id=qid,started_at=stamp,
                                warmup=round_id<0,client_ms=elapsed)
                    out.write(json.dumps(record)+'\n')
                    out.flush()
                    if round_id>=0:
                        records.append(record)
        self.quiet()
        for variant,_,_ in self.variants(experiment):
            if self.snapshot(self.name(experiment,scale,variant))!=before[variant]:
                raise RuntimeError('Parts changed during timing; journal preserved, batch invalid')
        logs=self.query_logs([r['query_id'] for r in records])
        save(self.path('queries',label+'_query_log.json'),list(logs.values()))
        for row in records:
            log=logs[row['query_id']]
            row.update(server_ms=log['query_duration_ms'],read_rows=log['read_rows'],
                       read_bytes=log['read_bytes'],memory_bytes=log['memory_usage'])
        csv_write(self.path('queries',label+'.csv'),records)
        print(f'Valid {label}: {len(records)} measured queries + warmups',flush=True)

    def ingest(self,scale):
        paths,n=self.inputs(scale)
        if not int(self.client.scalar("EXISTS TABLE system.part_log")):
            raise RuntimeError('system.part_log is required; enable the supplied config and restart before starting a run')
        journal=self.path('ingest',f'{scale}_journal.jsonl')
        if journal.exists():
            raise RuntimeError('Ingestion journal already exists; keep partial results and use a new run ID')
        batches=self.p['batch_rows']
        results=[]
        reference=None
        # Latin rotation: each of three batch sizes occupies each order position.
        with journal.open('x',encoding='utf-8') as log:
            for repeat in range(self.p['ingest_rounds']):
                order=batches[repeat%len(batches):]+batches[:repeat%len(batches)]
                for position,batch in enumerate(order):
                    self.quiet()
                    short=f'ingest_{scale}_b{batch}_r{repeat}'
                    table=f'{self.db}.{short}'
                    self.create(table,self.p['keys']['k1'])
                    table_uuid=self.client.scalar(f"SELECT uuid FROM system.tables WHERE database={quote(self.db)} AND name={quote(short)}")
                    trace=[]
                    stop=threading.Event()
                    started=time.perf_counter()
                    # Low-rate monitoring has overhead; it is identical for all cases.
                    def observe():
                        monitor=Client(self.p['settings'],self.args.client_config)
                        while not stop.is_set():
                            try:
                                row=monitor.rows("SELECT count() AS parts,sum(bytes_on_disk) AS bytes FROM system.parts "
                                    f"WHERE active AND database={quote(self.db)} AND table={quote(short)}")[0]
                                trace.append(dict(elapsed_s=time.perf_counter()-started,**row))
                            except Exception as exc:
                                trace.append(dict(elapsed_s=time.perf_counter()-started,error=str(exc)))
                            stop.wait(1)
                        monitor.conn.close()
                    worker=threading.Thread(target=observe,daemon=True)
                    worker.start()
                    try:
                        loaded=self.load(table,paths,batch)
                    finally:
                        stop.set()
                        worker.join(timeout=35)
                        save(self.path('ingest',short+'_timeline.json'),trace)
                    if worker.is_alive() or any('error' in row for row in trace):
                        raise RuntimeError('Monitoring failed; preserve logs and investigate before accepting this ingestion case')
                    log.write(json.dumps(dict(table=table,phase='ack',**loaded))+'\n')
                    log.flush()
                    save(self.path('ingest',short+'_batches.json'),loaded['batches'])
                    at_ack=self.snapshot(table)
                    wait=self.stable(table,short)
                    final=self.snapshot(table)
                    fp=self.fingerprint(table)
                    if int(fp['n'])!=n or reference is not None and fp!=reference:
                        raise RuntimeError('Ingestion count/fingerprint mismatch')
                    reference=fp
                    save(self.path('checks',short+'_fingerprint.json'),fp)
                    self.client.execute('SYSTEM FLUSH LOGS')
                    events=self.client.rows("SELECT event_type,event_time_microseconds,duration_ms,rows,read_rows,"
                        "read_bytes,bytes_uncompressed,size_in_bytes,peak_memory_usage,merged_from,error,exception "
                        f"FROM system.part_log WHERE table_uuid=toUUID({quote(table_uuid)}) ORDER BY event_time_microseconds")
                    save(self.path('ingest',short+'_part_log.json'),events)
                    if any(int(e['error'])!=0 for e in events):
                        raise RuntimeError('Part log contains failures')
                    merges=[e for e in events if e['event_type']=='MergeParts']
                    record=dict(scale=scale,repeat=repeat,position=position,batch_rows=batch,rows=n,
                         ingest_ack_s=loaded['ingest_ack_s'],throughput_rows_s=loaded['throughput_rows_s'],
                         observed_stable_wait_s=wait,parts_at_ack=len(at_ack),parts_stable=len(final),
                         active_bytes_at_ack=sum(int(x['bytes_on_disk']) for x in at_ack),
                         active_bytes_stable=sum(int(x['bytes_on_disk']) for x in final),
                         merge_events=len(merges),merge_duration_sum_ms=sum(int(x['duration_ms']) for x in merges),
                         merge_read_rows=sum(int(x['read_rows']) for x in merges),
                         merge_row_amplification=sum(int(x['read_rows']) for x in merges)/n,
                         new_part_events=sum(e['event_type']=='NewPart' for e in events))
                    results.append(record)
                    save(self.path('ingest',short+'_storage.json'),dict(at_ack=at_ack,stable=final))
                    csv_write(self.path('ingest',f'{scale}.csv'),results)
                    print(f'{short}: ACK {loaded["ingest_ack_s"]:.3f}s, {len(final)} stable parts',flush=True)
                    # Deliberately keep tables for audit. No automatic deletion.
        save(self.path('ingest',f'{scale}_complete.json'),dict(cases=len(results),completed_at=utc()))
