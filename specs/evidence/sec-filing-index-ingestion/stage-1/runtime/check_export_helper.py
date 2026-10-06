"""Check complete exports and reject truncated, corrupt or unsafe evidence."""
import base64
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

def frame(name='overall.json'):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as bundle:
        body = b'{"exit_code":0}'
        member = tarfile.TarInfo(name)
        member.size = len(body)
        bundle.addfile(member,io.BytesIO(body))
    body = buffer.getvalue()
    digest = hashlib.sha256(body).hexdigest()
    return ['TASK4_BEGIN '+json.dumps({'bytes':len(body),'sha256':digest,'chunks':1}),
            'TASK4_CHUNK 0 '+base64.b64encode(body).decode('ascii'), 'TASK4_END '+digest]

class ExportChecks(unittest.TestCase):
    def run_export(self, lines):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root/'log.txt').write_text('\n'.join(lines)+'\n')
            result = subprocess.run([sys.executable,str(Path(__file__).with_name('extract_artifacts.py')),str(root/'log.txt'),str(root/'out')],capture_output=True)
            return result.returncode

    def test_complete(self):
        self.assertEqual(self.run_export(frame()),0)

    def test_missing_chunk(self):
        lines = frame()
        self.assertNotEqual(self.run_export([lines[0],lines[2]]),0)

    def test_tampered_hash(self):
        lines = frame()
        lines[-1] = 'TASK4_END '+'0'*64
        self.assertNotEqual(self.run_export(lines),0)

    def test_path_traversal(self):
        self.assertNotEqual(self.run_export(frame('../overall.json')),0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
