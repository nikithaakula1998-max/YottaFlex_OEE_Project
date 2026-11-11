import tempfile, unittest
from pathlib import Path
from src.main import build
class PipelineTest(unittest.TestCase):
 def test_reproducible(self):
  with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
   x,v=build(Path(a),days=1,machines=2,events=100,records=100,seed=42)
   y,w=build(Path(b),days=1,machines=2,events=100,records=100,seed=42)
   self.assertEqual(x['sha256'],y['sha256'])
   self.assertEqual(v['status'],'PASS')
   self.assertEqual(v['labelled_anomalies'],5)
if __name__=='__main__':unittest.main()
