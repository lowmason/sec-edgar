"""Check retained bytes and native ZIP decode without parsing SEC rows."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

MAX_EXPANDED_BYTES = 512 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024

def inspect(entry, root):
    digest = entry['original_sha256']
    archive = entry['derivative_sha256'] is not None
    path = root / (digest + ('.zip' if archive else '.idx'))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert path.stat().st_size == entry['original_bytes']
    if archive:
        with zipfile.ZipFile(path) as container:
            members = container.infolist()
            assert len(members) == 1
            member = members[0]
            assert member.filename == 'master.idx'
            assert not member.flag_bits & 1
            assert member.compress_type == zipfile.ZIP_DEFLATED
            assert member.file_size <= MAX_EXPANDED_BYTES
            assert member.file_size == entry['expanded_bytes']
            with container.open(member) as stream:
                decoded_hash, total, counts = check_stream(stream)
            # Reading the complete member validates its CRC in zipfile.
            assert decoded_hash == entry['derivative_sha256']
            assert total == member.file_size
    else:
        with path.open('rb') as stream:
            decoded_hash, total, counts = check_stream(stream)
        assert decoded_hash == digest
    assert total == entry['expanded_bytes']
    assert counts == entry['newline_counts'], (counts, entry['newline_counts'])
    return {'evidence_id': entry['evidence_id'], 'role': entry['role'],
            'original_sha256': digest, 'decoded_sha256': decoded_hash,
            'bytes': total, 'strict_encoding': 'ascii', 'newline_counts': counts,
            'codec': 'ZIP DEFLATE; complete CRC-validated native read' if archive else 'plain IDX; no archive decoder needed'}

def check_stream(stream):
    digest = hashlib.sha256()
    total = crlf = lf = cr = 0
    prior_cr = False
    while chunk := stream.read(CHUNK_BYTES):
        total += len(chunk)
        assert total <= MAX_EXPANDED_BYTES
        chunk.decode('ascii', errors='strict')
        digest.update(chunk)
        crlf += chunk.count(b'\r\n') + int(prior_cr and chunk.startswith(b'\n'))
        lf += chunk.count(b'\n')
        cr += chunk.count(b'\r')
        prior_cr = chunk.endswith(b'\r')
    return digest.hexdigest(), total, {'crlf': crlf, 'lone_lf': lf-crlf, 'lone_cr': cr-crlf}

if __name__ == '__main__':
    root = Path(sys.argv[1])
    matrix = json.loads((root / 'matrix.json').read_text())
    print(json.dumps({'selected': [inspect(entry, root) for entry in matrix['matrix']],
                      'unselected_codecs': '.sit/.z/.Z/.gz unsupported; no test claimed'}, indent=2))
