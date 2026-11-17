import base64
import csv
import datetime as dt
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import statistics
import time
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def object_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def csv_write(path, rows):
    if not rows:
        raise ValueError(f'No rows for {path}')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def csv_read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def distribution(values):
    if not values:
        raise ValueError('No observations')
    q1, _, q3 = statistics.quantiles(values, n=4, method='inclusive') if len(values) > 1 else values * 3
    return dict(n=len(values), median=statistics.median(values), q1=q1, q3=q3, iqr=q3-q1)


def identifier(value):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,39}', value):
        raise ValueError('Use 1-40 lowercase letters/digits/underscore, beginning with a letter')
    return value


def quote(value):
    return "'" + str(value).replace('\\', '\\\\').replace("'", "\\'") + "'"


class Client:
    """Local HTTP; no credentials in argv, results, SQL, or exported settings."""
    def __init__(self, settings, xml=None):
        xml = xml or os.environ.get('CH_CONFIG')
        user, password = os.environ.get('CH_USER', 'default'), os.environ.get('CH_PASSWORD', '')
        if xml:
            root = ET.parse(Path(xml).expanduser()).getroot()
            user, password = root.findtext('user', user), root.findtext('password', password)
        host = os.environ.get('CH_HOST', '127.0.0.1')
        port = int(os.environ.get('CH_HTTP_PORT', '8123'))
        self.conn = http.client.HTTPConnection(host, port, timeout=1800)
        self.headers = {'Authorization': 'Basic ' + base64.b64encode(f'{user}:{password}'.encode()).decode()}
        self.settings = dict(settings)
        self.last_end = 0

    def execute(self, sql, query_id=None, payload=None, overrides=None):
        params = dict(self.settings)
        params.update(overrides or {})
        params.update(query=sql, wait_end_of_query=1)
        if query_id:
            params['query_id'] = query_id
        if time.perf_counter() - self.last_end > 2:
            self.conn.close()
        headers = dict(self.headers, **{'Content-Length': str(len(payload) if payload else 0)})
        start = time.perf_counter()
        self.last_start = start
        # No automatic retry: an INSERT may have committed before a disconnect.
        self.conn.request('POST', '/?' + urllib.parse.urlencode(params), body=payload, headers=headers)
        response = self.conn.getresponse()
        data = response.read()
        self.last_end = time.perf_counter()
        elapsed_ms = (self.last_end-start)*1000
        if response.status != 200 or data.startswith(b'Code:'):
            raise RuntimeError(f'HTTP {response.status}: {data.decode(errors="replace")[:2500]}')
        return data.decode(), elapsed_ms

    def rows(self, sql, overrides=None):
        text, _ = self.execute(sql + ' FORMAT JSONEachRow', overrides=overrides)
        return [json.loads(line) for line in text.splitlines() if line]

    def scalar(self, sql):
        return self.execute(sql)[0].strip()


def fixed_batches(paths, row_bytes, batch_rows, limit_rows=None):
    """Same byte sequence across all batch sizes, including file boundaries."""
    buffer = bytearray()
    remaining = limit_rows * row_bytes if limit_rows is not None else None
    size = row_bytes * batch_rows
    for path in paths:
        with Path(path).open('rb') as f:
            while remaining is None or remaining > 0:
                need = size-len(buffer)
                block = f.read(need if remaining is None else min(need, remaining))
                if not block:
                    break
                buffer.extend(block)
                if remaining is not None:
                    remaining -= len(block)
                if len(buffer) == size:
                    yield bytes(buffer)
                    buffer.clear()
        if remaining == 0:
            break
    if buffer:
        if len(buffer) % row_bytes:
            raise RuntimeError('Truncated RowBinary input')
        yield bytes(buffer)
    if remaining not in (None, 0):
        raise RuntimeError('Input shorter than requested limit')
