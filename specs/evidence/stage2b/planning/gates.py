"""Plan 8 planning fact (read-only, scratch copy): predicted withdrawal gates per quarter.

For each quarter, compare the active generation's keys with the keys of its retained quarterly master.idx.
A closed quarter's first quarterly publish withdraws active keys that the quarterly file lacks (parent §4.4).
"""
import io, json, sys, time, zipfile
from pathlib import Path
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.storage.contracts import REGISTRY_PATH
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore

root, sources_path = Path(sys.argv[1]), Path(sys.argv[2])
binding = json.loads((root / 'objects' / REGISTRY_PATH).read_bytes())
objects = LocalObjectStore(root, binding=binding, create=False)
store = LocalStateStore(root, binding=binding, create=False)
state = EtlState(store)
sources = json.loads(sources_path.read_text())['sources']
raw_files = {p.name: p for p in (root / 'objects' / 'raw').rglob('*') if p.is_file()}

def raw_path(sha):
    hits = [p for p in (root / 'objects' / 'raw').rglob('*') if p.is_file() and sha in str(p)]
    if len(hits) != 1:
        raise SystemExit('raw object not unique for ' + sha + ': ' + str(hits))
    return hits[0]

def quarterly_keys(sha):
    with zipfile.ZipFile(raw_path(sha)) as archive:
        text = archive.read('master.idx').decode('latin-1')
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith('-----')) + 1
    keys = set()
    for line in lines[start:]:
        if not line.strip():
            continue
        cik, _, _, _, path = line.split('|')
        keys.add((cik.zfill(10), path))
    return keys

out = []
for item in sources:
    if item['kind'] != 'quarterly':
        continue
    quarter = item['period']
    began = time.monotonic()
    capture = capture_quarter(quarter, objects, state)
    base = set() if capture is None else {(row.cik, row.archive_path) for row in read_quarter(capture, objects)}
    qkeys = quarterly_keys(item['raw_sha256'])
    out.append({'quarter': quarter, 'base_keys': len(base), 'quarterly_keys': len(qkeys),
                'base_absent_from_quarterly': len(base - qkeys), 'seconds': round(time.monotonic() - began, 1)})
    print(json.dumps(out[-1]), file=sys.stderr)
print(json.dumps(out, indent=1))
