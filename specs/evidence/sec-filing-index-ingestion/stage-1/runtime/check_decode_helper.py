"""Offline guard regression checks for observational archive helper."""
import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

import decode_specimens as probe

class DecodeChecks(unittest.TestCase):
    def test_newline_chunk_boundary(self):
        original = probe.CHUNK_BYTES
        probe.CHUNK_BYTES = 2
        try:
            body = b'a\r\nb\nc\r'
            digest, size, counts = probe.check_stream(io.BytesIO(body))
            self.assertEqual(digest, hashlib.sha256(body).hexdigest())
            self.assertEqual(size, len(body))
            self.assertEqual(counts, {'crlf': 1, 'lone_lf': 1, 'lone_cr': 1})
        finally:
            probe.CHUNK_BYTES = original

    def test_non_ascii_rejected(self):
        with self.assertRaises(UnicodeDecodeError):
            probe.check_stream(io.BytesIO(b'\xff'))

    def test_actual_expansion_bound(self):
        original = probe.MAX_EXPANDED_BYTES
        probe.MAX_EXPANDED_BYTES = 3
        try:
            with self.assertRaises(AssertionError):
                probe.check_stream(io.BytesIO(b'abcd'))
        finally:
            probe.MAX_EXPANDED_BYTES = original

    def test_crc_and_unsafe_member_rejected(self):
        body = b'a\r\n'
        for member, corrupt_crc in [('master.idx', True), ('../master.idx', False)]:
            with tempfile.TemporaryDirectory() as scratch:
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr(member, body)
                original = bytearray(buffer.getvalue())
                if corrupt_crc:
                    central = original.index(b'PK\x01\x02')
                    original[central + 16] ^= 1
                digest = hashlib.sha256(original).hexdigest()
                root = Path(scratch)
                (root / (digest + '.zip')).write_bytes(original)
                entry = {'original_sha256': digest, 'original_bytes': len(original), 'expanded_bytes': len(body),
                         'derivative_sha256': hashlib.sha256(body).hexdigest()}
                with self.assertRaises((AssertionError, zipfile.BadZipFile)):
                    probe.inspect(entry, root)

if __name__ == '__main__':
    unittest.main(verbosity=2)
