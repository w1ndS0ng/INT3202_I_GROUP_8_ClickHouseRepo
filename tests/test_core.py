import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mtstudy.common import fixed_batches, identifier, distribution, read, ROOT
from mtstudy.model import fit,predict
from mtstudy.runner import ddl,workloads
from mtstudy.dataset import make_samples


class MethodTests(unittest.TestCase):
    def test_batches_preserve_bytes_across_boundaries(self):
        original=bytes(range(240))
        with tempfile.TemporaryDirectory() as temp:
            paths=[Path(temp)/'a',Path(temp)/'b']
            paths[0].write_bytes(original[:84])
            paths[1].write_bytes(original[84:])
            for size in [1,5,13,50]:
                pieces=list(fixed_batches(paths,4,size))
                self.assertEqual(b''.join(pieces),original)
                self.assertTrue(all(len(p)%4==0 for p in pieces))
            self.assertEqual(b''.join(fixed_batches(paths,4,7,10)),original[:40])
            with self.assertRaises(RuntimeError):
                list(fixed_batches(paths,4,7,100))

    def test_model_recovers_known_intercept_and_slope(self):
        model=fit([1e6,3e6,10e6],[5,9,23])
        self.assertAlmostEqual(model['alpha_ms'],3)
        self.assertAlmostEqual(model['beta_ms_per_row'],.000002)
        self.assertAlmostEqual(predict(model,30e6),63)

    def test_samples_nested_and_cover_every_shard(self):
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)
            files=[]
            for shard in range(30):
                (dest/f'hits_{shard}.rowbinary').write_bytes(bytes(range(30)))
                files.append({'shard':shard})
            samples=make_samples(dest,{'row_bytes':1,'files':files})
            self.assertEqual([samples[s]['rows'] for s in ['1m','3m','10m']],[30,90,300])
            self.assertEqual((dest/'sample_1m.rowbinary').read_bytes(),bytes([0])*30)
            self.assertEqual((dest/'sample_3m.rowbinary').read_bytes(),bytes([0,1,2])*30)

    def test_unidentifiable_and_no_negative_time(self):
        self.assertFalse(fit([8192]*3,[2,3,2])['identifiable'])
        model=fit([1,3,10],[10,5,1])
        self.assertGreaterEqual(model['alpha_ms'],0)
        self.assertGreaterEqual(model['beta_ms_per_row'],0)
        self.assertTrue(model['boundary_fit'])

    def test_schema_and_identifiers(self):
        p=read(ROOT/'configs/protocol.json')
        self.assertEqual(sum(c[2] for c in p['schema']),44)
        self.assertEqual(len(set(p['shards'])),30)
        self.assertIn('index_granularity_bytes=0',ddl('mtr_test.t',p,'tuple()'))
        self.assertIn('sum(ResolutionWidth)',workloads('mtr_test.t',p['parameters'])['w0'])
        with self.assertRaises(ValueError):
            identifier('anything; DROP DATABASE ch3')
        self.assertEqual(distribution([1,2,3,4])['iqr'],1.5)


if __name__=='__main__':
    unittest.main()
