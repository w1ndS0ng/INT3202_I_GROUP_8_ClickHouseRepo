from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mtstudy.common import ROOT, read, sha
from mtstudy.comparison import (Digest, ROW, PG_FIELDS, PG_HEADER, canonical_line,
                                convert_input, digest_lines, pg_binary_row,
                                pg_ddl, pg_workloads, schedule, convert_inputs,
                                locked_inputs, selected_marks, scan_nodes)


class ComparisonTests(unittest.TestCase):
    def test_binary_conversion_preserves_signed_fields_and_epoch(self):
        values=(-9223372036854775808,9223372036854775807,-123,0,0,-44,-32768,1,1920,1080,0,2147483647)
        encoded=pg_binary_row(values)
        self.assertEqual(struct.unpack_from('!h',encoded)[0],12)
        decoded=[];pos=2
        for fmt in PG_FIELDS:
            size=struct.unpack_from('!i',encoded,pos)[0];pos+=4
            self.assertEqual(size,struct.calcsize('!'+fmt))
            decoded.append(struct.unpack_from('!'+fmt,encoded,pos)[0]);pos+=size
        decoded[3]+=10957;decoded[4]=decoded[4]//1000000+946684800
        self.assertEqual(tuple(decoded),values)
        self.assertEqual(ROW.size,44)

    def test_conversion_and_fingerprint_handle_duplicates_and_chunk_boundaries(self):
        rows=[(1,2,3,15908,1374451200,229,0,1,1920,1080,0,40)]*2
        other=(2,3,4,15909,1374537600,1,0,0,1024,768,1,-1)
        rows.append(other)
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'input';target=Path(directory)/'copy'
            source.write_bytes(b''.join(ROW.pack(*r) for r in rows))
            expected=convert_input(source,target)
            data=b''.join(canonical_line(r) for r in reversed(rows))
            self.assertEqual(digest_lines([data[:17],data[17:35],data[35:]]),expected)
            self.assertTrue(target.read_bytes().startswith(PG_HEADER))
            self.assertEqual(target.read_bytes()[-2:],b'\xff\xff')
            self.assertNotEqual(digest_lines([canonical_line(rows[0]),canonical_line(other)]),expected)
            source.write_bytes(b'bad')
            with self.assertRaisesRegex(RuntimeError,'Truncated'):
                convert_input(source,Path(directory)/'broken')

    def test_queries_and_schema_keep_cross_database_semantics(self):
        base=read(ROOT/'configs/protocol.json')
        sql=pg_ddl('cmp_test.pg0',base['schema'])
        self.assertIn('WatchID bigint NOT NULL',sql)
        self.assertIn('EventTime timestamp with time zone NOT NULL',sql)
        self.assertNotIn('PRIMARY KEY',sql)
        queries=pg_workloads('cmp_test.pg0',base['parameters'])
        self.assertIn('count(*)',queries['w0'])
        self.assertIn("DATE('2013-07-23')",queries['w2'])
        self.assertIn('RegionID=229',queries['w4'])

    def test_schedule_preserves_all_replicates_without_replacing_outliers(self):
        config=read(ROOT/'configs/comparison.json')
        order=schedule(config)
        self.assertEqual(order,schedule(config))
        self.assertIsNone(config['psycopg_prepare_threshold'])
        self.assertEqual(sum(r['warmup'] for r in order),50)
        self.assertEqual(sum(not r['warmup'] for r in order),250)
        for variant in ['ch0','ch1','pg0','pg1','pg2']:
            for case in ['w0','w1','w2','w3','w4']:
                cell=[r for r in order if r['variant']==variant and r['case']==case]
                self.assertEqual(sum(r['warmup'] for r in cell),2)
                self.assertEqual(sum(not r['warmup'] for r in cell),10)

    def test_base_protocol_is_pinned(self):
        config=read(ROOT/'configs/comparison.json')
        self.assertEqual(sha(ROOT/config['base_protocol']),config['base_protocol_sha256'])

    def test_multifile_copy_preserves_order_and_all_rows(self):
        rows=[(i,-i,3,15908,1374451200,229,0,1,1920,1080,0,40) for i in range(4)]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);paths=[root/'a',root/'b']
            paths[0].write_bytes(b''.join(ROW.pack(*r) for r in rows[:2]))
            paths[1].write_bytes(b''.join(ROW.pack(*r) for r in rows[2:]))
            result=convert_inputs(paths,root/'out')
            self.assertEqual((root/'out').read_bytes(),PG_HEADER+b''.join(pg_binary_row(r) for r in rows)+b'\xff\xff')
            self.assertEqual(result,digest_lines([b''.join(canonical_line(r) for r in rows)]))
            with self.assertRaisesRegex(RuntimeError,'30M requires'):
                locked_inputs({'files':[]},{'shards':list(range(30))},root,'30m')

    def test_plan_metrics_do_not_double_count_buffers_or_parallel_loops(self):
        self.assertEqual(selected_marks('Parts: 1 | Granules: 3663'),3663)
        self.assertEqual(selected_marks('Granules: 3663/3663\nPrimaryKey\nGranules: 6/3663'),6)
        with self.assertRaises(RuntimeError):selected_marks('unrecognized')
        plan={'Node Type':'Gather','Plans':[{'Node Type':'Bitmap Heap Scan','Relation Name':'pg1',
              'Actual Rows':33.5,'Actual Loops':4,'Shared Hit Blocks':1154,'Lossy Heap Blocks':1152,
              'Plans':[{'Node Type':'Bitmap Index Scan','Shared Hit Blocks':2}]}]}
        nodes=scan_nodes(plan)
        self.assertEqual(len(nodes),1)
        self.assertEqual(nodes[0]['Shared Hit Blocks'],1154)
        self.assertEqual(nodes[0]['Actual Rows'],33.5)
        self.assertNotIn('Exact Heap Blocks',nodes[0])


if __name__=='__main__':
    unittest.main()
