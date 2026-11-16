import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from verify_originals import verify

class VerifySourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.path=self.root/"evidence.txt"
        self.path.write_bytes(b"synthetic original")
        self.index={"files":[{"path":"evidence.txt","bytes":len(self.path.read_bytes()),
                              "sha256":hashlib.sha256(self.path.read_bytes()).hexdigest()}]}
    def test_matching_original(self):
        self.assertEqual(verify(self.root,self.index)["status"],"LOCAL_BYTES_MATCH")
    def test_mutated_source(self):
        self.path.write_bytes(b"tampered")
        self.assertEqual(verify(self.root,self.index)["status"],"FAIL")
    def test_missing_source(self):
        self.path.unlink()
        self.assertEqual(verify(self.root,self.index)["status"],"FAIL")
    def test_duplicate_manifest_path(self):
        self.index["files"].append(self.index["files"][0])
        self.assertEqual(verify(self.root,self.index)["status"],"FAIL")
    def test_path_traversal(self):
        self.index["files"][0]["path"]="../evidence.txt"
        self.assertEqual(verify(self.root,self.index)["status"],"FAIL")
    def test_empty_manifest(self):
        self.assertEqual(verify(self.root,{"files":[]})["status"],"FAIL")
if __name__=="__main__":
    unittest.main()
