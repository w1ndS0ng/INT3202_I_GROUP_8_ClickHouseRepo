"""Download a fixed file subset and export 12 unchanged fields to fixed RowBinary."""
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request

from .common import ROOT, object_sha, quote, read, save, sha, utc

BASE_URL = 'https://datasets.clickhouse.com/hits_compatible/athena_partitioned'
KNOWN_SHA256 = {
    0: 'fa134fe101e68324e0de851146fda69624f5cbb707d387141d1c2a88a219a16d',
    10: '2205196b258c76db80945aaf54e2f6c80b77ded8a619c5b67387211baff42f6a',
    20: '88c0e1ea725ff815a0ea45fbf5b01eae389426181fddc02a08fc9e6145b4c634',
    30: 'd9476120f3ea3f42d1d4d17ea76a1c3abc10b3b88761a212813dcbff376ae80a',
    40: 'a703c7d331ca6040c488a58155402538ba2b056858e2ec61510fe39c079835b2',
    50: '639618352b58a0d968f8dd2d3914b8f2ae120fc030925056e07baa98fca6edb3',
    60: 'ad3885c4314042a4968bb01099eceac45bc9f34115d09a8b856dba3f5b13f231',
    70: 'ee09cd2a3056898fba78064e7c486592cf74ad385373f879296cc6d2d65b87fb',
    80: '409606171d5ec63afba99fc89bc4bcf576f21eac1525bdb6cee9753b05a393f9',
    90: 'c7e7493b834efad5cf49aeef2e7617a661b2b13ccbdf684cf24c8b200b0c3a9a',
}


def make_samples(dest, manifest):
    """Nested systematic samples over the fixed 30-file concatenation.

    Keep row ordinal mod30 <1/<3/<10. All file regions contribute. This is a
    reproducible systematic sample, not a statistical claim of random sampling.
    """
    outputs={scale:dest/f'sample_{scale}.rowbinary' for scale in ['1m','3m','10m']}
    receipt=dest/'samples.json'
    input_hash=object_sha(manifest['files'])
    if receipt.exists():
        old=read(receipt)
        if old['input_hash']!=input_hash or any(sha(outputs[k])!=old['samples'][k]['sha256'] for k in outputs):
            raise RuntimeError('Existing systematic samples changed; prepare into a new data directory')
        return old['samples']
    if any(p.exists() for p in outputs.values()):
        raise RuntimeError('Sample output exists without its receipt')
    handles={k:p.with_suffix('.tmp').open('wb') for k,p in outputs.items()}
    buffers={k:bytearray() for k in outputs}
    row_bytes=manifest['row_bytes']
    ordinal=0
    try:
        for item in manifest['files']:
            with (dest/f'hits_{item["shard"]}.rowbinary').open('rb') as source:
                while chunk:=source.read(row_bytes*30000):
                    if len(chunk)%row_bytes:
                        raise RuntimeError('Truncated fixed-width input')
                    for pos in range(0,len(chunk),row_bytes):
                        residue=ordinal%30
                        if residue<10:
                            row=chunk[pos:pos+row_bytes]
                            buffers['10m'].extend(row)
                            if residue<3:
                                buffers['3m'].extend(row)
                            if residue<1:
                                buffers['1m'].extend(row)
                        ordinal+=1
                    for k in handles:
                        if len(buffers[k])>=2**20:
                            handles[k].write(buffers[k])
                            buffers[k].clear()
        for k in handles:
            handles[k].write(buffers[k])
    finally:
        for handle in handles.values():
            handle.close()
    samples={}
    for k,path in outputs.items():
        path.with_suffix('.tmp').replace(path)
        samples[k]=dict(filename=path.name,sha256=sha(path),rows=path.stat().st_size//row_bytes)
    save(receipt,dict(input_hash=input_hash,rule='global row ordinal modulo30 < 1/3/10',samples=samples))
    return samples


def download(url, dest):
    temp = dest.with_suffix(dest.suffix + '.download')
    if shutil.which('curl'):
        subprocess.run(['curl','-fLsS','--retry','3','--retry-delay','2','--continue-at','-',
                        '--connect-timeout','30','--max-time','1800','--output',str(temp),url],check=True)
    else:
        with urllib.request.urlopen(url, timeout=120) as response, temp.open('wb') as out:
            shutil.copyfileobj(response, out, 2**20)
    temp.replace(dest)


def prepare(args, protocol):
    dest = Path(args.data).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    schema_hash = object_sha(protocol['schema'])
    row_bytes = sum(c[2] for c in protocol['schema'])
    lock = read(args.lock) if args.lock else None
    if lock and lock['schema_hash'] != schema_hash:
        raise RuntimeError('Schema differs from shared manifest')
    rows = []
    exe = shutil.which('clickhouse-local')
    if not exe:
        raise RuntimeError('Install matching clickhouse-client/local before dataset preparation')
    for shard in protocol['shards'][:args.shards]:
        name = f'hits_{shard}.parquet'
        path = dest/name
        if not path.exists() and args.reuse_dir and (Path(args.reuse_dir)/name).exists():
            src = (Path(args.reuse_dir)/name).resolve()
            try:
                os.link(src, path)
            except OSError:
                shutil.copyfile(src, path)
        if not path.exists():
            print(f'Download {name}', flush=True)
            download(f'{BASE_URL}/{name}', path)
        digest = sha(path)
        wanted = KNOWN_SHA256.get(shard)
        shared = next((x for x in lock['files'] if x['shard']==shard), None) if lock else None
        if lock and not shared:
            raise RuntimeError(f'{name} missing from shared manifest')
        if shared:
            wanted = shared['parquet_sha256']
        if wanted and digest != wanted:
            raise RuntimeError(f'Checksum mismatch: {path}')
        binary = dest/f'hits_{shard}.rowbinary'
        receipt = dest/f'hits_{shard}.conversion.json'
        if binary.exists():
            if not receipt.exists():
                raise RuntimeError(f'Existing binary has no conversion receipt: {binary}')
            old = read(receipt)
            if old['parquet_sha256'] != digest or old['schema_hash'] != schema_hash or old['rowbinary_sha256'] != sha(binary):
                raise RuntimeError(f'Existing binary or conversion recipe changed: {binary}')
        else:
            fields = []
            for col, typ, _ in protocol['schema']:
                expr = f'assumeNotNull(`{col}`)'
                if typ == 'Date':
                    expr = f'toDate({expr})'
                elif typ.startswith('DateTime'):
                    expr = f'toDateTime({expr}, \'UTC\')'
                else:
                    expr = f'CAST({expr}, {quote(typ)})'
                fields.append(f'{expr} AS `{col}`')
            sql = 'SELECT ' + ', '.join(fields) + f' FROM file({quote(path)}, Parquet) FORMAT RowBinary'
            temp = binary.with_suffix('.rowbinary.tmp')
            print(f'Convert {name} (12 columns)', flush=True)
            with temp.open('wb') as out:
                subprocess.run([exe, '--max_threads=1', '--max_memory_usage=1000000000',
                                '--input_format_parquet_memory_high_watermark=134217728',
                                '--input_format_parquet_max_block_size=16384', '--query', sql],
                               stdout=out, check=True)
            if temp.stat().st_size != 1000000 * row_bytes:
                raise RuntimeError(f'{name}: expected exactly 1M rows; got {temp.stat().st_size/row_bytes}')
            temp.replace(binary)
            save(receipt, dict(parquet_sha256=digest, schema_hash=schema_hash,
                               rowbinary_sha256=sha(binary), converted_at=utc(), sql=sql))
        item = dict(shard=shard, url=f'{BASE_URL}/{name}', parquet_sha256=digest,
                    parquet_bytes=path.stat().st_size, rowbinary_sha256=sha(binary),
                    rowbinary_bytes=binary.stat().st_size, rows=binary.stat().st_size//row_bytes)
        if shared and any(item[k] != shared[k] for k in ('rowbinary_sha256','rows')):
            raise RuntimeError('Normalized content differs from the shared manifest')
        rows.append(item)
        save(dest/'manifest.json', dict(schema_hash=schema_hash, row_bytes=row_bytes,
             clickbench_commit=protocol['clickbench_commit'], files=rows, created_at=utc()))
        print(f'Verified {name}: {item["rows"]:,} rows', flush=True)
    manifest = read(dest/'manifest.json')
    if args.shards==30:
        manifest['samples']=make_samples(dest,manifest)
        if lock and manifest['samples']!=lock.get('samples'):
            raise RuntimeError('Systematic sample hashes differ from the shared manifest')
        save(dest/'manifest.json',manifest)
    if args.publish_lock:
        output = Path(args.publish_lock)
        if output.exists():
            raise RuntimeError('Refusing to replace an existing shared lock; review a versioned new file')
        save(output, manifest)
    print(f'Ready: {sum(x["rows"] for x in rows):,} rows; {dest / "manifest.json"}')
