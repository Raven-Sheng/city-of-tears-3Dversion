"""Actual temporary sequences exercise accepted and rejected resume boundaries."""
import sys,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/render'))
from render_identity import bind_sequence

class ResumeIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.identity={'source':'scene-v1','renderer':'script-v1','settings':{'samples':8,'seed':0,'denoiser':'OPTIX'}}
    def test_new_sequence_then_same_identity_resume(self):
        bind_sequence(self.folder,self.identity,False)
        frame=self.folder/'f0001.png';frame.write_bytes(b'kept frame')
        bind_sequence(self.folder,self.identity,True)
        self.assertEqual(frame.read_bytes(),b'kept frame')
        self.assertEqual(json.loads((self.folder/'sequence_identity.json').read_text()),self.identity)
    def test_changed_source_renderer_or_samples_refused(self):
        bind_sequence(self.folder,self.identity,False)
        for identity in [{'source':'scene-v2',**{k:v for k,v in self.identity.items() if k!='source'}},
                         {'renderer':'script-v2',**{k:v for k,v in self.identity.items() if k!='renderer'}},
                         {**self.identity,'settings':{**self.identity['settings'],'samples':128}}]:
            with self.subTest(identity=identity),self.assertRaisesRegex(ValueError,'changed'):
                bind_sequence(self.folder,identity,True)
        self.assertEqual(json.loads((self.folder/'sequence_identity.json').read_text()),self.identity)
    def test_unbound_legacy_frames_refused(self):
        frame=self.folder/'f0001.png';frame.write_bytes(b'old 8-sample frame')
        with self.assertRaisesRegex(ValueError,'no verified'):
            bind_sequence(self.folder,self.identity,True)
        self.assertEqual(frame.read_bytes(),b'old 8-sample frame')
        self.assertFalse((self.folder/'sequence_identity.json').exists())

if __name__=='__main__':unittest.main()
