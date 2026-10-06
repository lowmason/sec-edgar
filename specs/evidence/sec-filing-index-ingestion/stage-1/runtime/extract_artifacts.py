"""Extract bounded reviewed ACR stdout evidence without tar path traversal."""
import base64
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

log = Path(sys.argv[1]).read_text()
lines = log.splitlines()
starts = [line.split('TASK4_BEGIN ',1)[1] for line in lines if 'TASK4_BEGIN ' in line]
ends = [line.split('TASK4_END ',1)[1].strip() for line in lines if 'TASK4_END ' in line]
assert len(starts) == len(ends) == 1, 'Expected one complete export frame'
record = json.loads(starts[0])
assert 1 <= record['chunks'] <= 1400
chunks = {}
for line in lines:
    if 'TASK4_CHUNK ' in line:
        index_text, chunk = line.split('TASK4_CHUNK ',1)[1].split(' ',1)
        index = int(index_text)
        assert index not in chunks and len(chunk) <= 4096
        chunks[index] = chunk
assert sorted(chunks) == list(range(record['chunks']))
assert ends[0] == record['sha256']
body = base64.b64decode(''.join(chunks[index] for index in range(record['chunks'])),validate=True)
assert len(body) <= 4*1024*1024 and len(body) == record['bytes']
assert hashlib.sha256(body).hexdigest() == record['sha256']
destination = Path(sys.argv[2])
destination.mkdir(exist_ok=False)
total = 0
hashes = {}
with tarfile.open(fileobj=io.BytesIO(body),mode='r:gz') as bundle:
    for member in bundle:
        assert member.isfile() and Path(member.name).name == member.name and member.name not in ('.','..')
        assert member.name not in hashes
        total += member.size
        assert total <= 32*1024*1024
        stream = bundle.extractfile(member)
        assert stream is not None
        artifact = stream.read(member.size+1)
        assert len(artifact) == member.size
        (destination/member.name).write_bytes(artifact)
        hashes[member.name] = hashlib.sha256(artifact).hexdigest()
(destination/'export-receipt.json').write_text(json.dumps({'source_log':sys.argv[1],'bundle_sha256':record['sha256'],'bundle_bytes':len(body),'artifacts':hashes},indent=2)+'\n')
print(json.dumps({'destination':str(destination),'artifacts':len(hashes),'overall':json.loads((destination/'overall.json').read_text())},indent=2))
