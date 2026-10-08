from network_guard import install
install()
from sec_edgar_ingest.models import to_mapping_value
import hashlib, io, zipfile
from pathlib import Path
from sec_edgar_ingest.models import canonical_json
BASE = 'https://www.sec.gov/Archives/edgar/'

def listing(url, children):
    return canonical_json(to_mapping_value({'directory': {'name': url[len(BASE):-len('index.json')],
        'parent-dir': '../', 'item': [
            {'name': name, 'href': name + ('/' if kind == 'dir' else ''), 'type': kind,
             'size': '1', 'last-modified': 'synthetic'} for name, kind in children]}}))

def idx(rows, kind):
    ending, title = ('\r\n', 'Filename') if kind == 'quarterly' else ('\n', 'File Name')
    body = ('CIK|Company Name|Form Type|Date Filed|' + title + ending + '-----' + ending +
            ending.join('|'.join(row) for row in rows) + ending).encode('ascii')
    if kind == 'daily':
        return body
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        info = zipfile.ZipInfo('master.idx', (2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, body)
    return output.getvalue()

def build_pack(root, listings, bodies, overrides=None, repeats=8):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    (root / 'bodies').mkdir()
    merged = {url: listing(url, children) for url, children in listings.items()}
    merged.update(bodies)
    responses = {}
    for url, body in sorted(merged.items()):
        digest = hashlib.sha256(body).hexdigest()
        relative = 'bodies/' + digest + '.body'
        target = root / relative
        if not target.exists():
            target.write_bytes(body)
        spec = {'status': 200, 'headers': {'Content-Length': str(len(body)), 'X-Fixture': 'synthetic'},
                'body_path': relative, 'body_sha256': digest}
        responses[url] = [dict(spec) for _ in range(repeats)]
    responses.update(overrides or {})
    path = root / 'manifest.json'
    path.write_bytes(canonical_json(to_mapping_value({'fixture_version': 'sec-acquisition-fixture-v1',
                                    'provenance': 'synthetic', 'responses': responses})))
    return path

from sec_edgar_ingest.models import to_mapping_value
import contextlib, io, json
from datetime import datetime, timedelta, timezone
from support import fixture_settings
from sec_edgar_ingest.cli import main
from sec_edgar_ingest.storage import open_stores
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState

class CommandHarness:
    def __init__(self, root, pack, settings=None):
        self.root, self.pack = Path(root), Path(pack)
        self.settings = settings or fixture_settings(
            backfill={'start_quarter': '2026Q3', 'end_quarter': 'open'},
            etl={'parser_version': 'fixture-index-parser-v1'},
            fixture={'allow_clock_override': True, 'allow_deadline_override': False})
        self.config = self.root / 'config.json'
        self.config.write_bytes(canonical_json(to_mapping_value(self.settings.to_mapping())))
        self.deadline = datetime.now(timezone.utc) + timedelta(seconds=1800)
        self.opened = open_stores(self.settings, base_path=self.root)
        self.store, self.objects, self.leases = self.opened
        self.calls = []

    def invoke(self, command, flags=(), run='r', attempt='a', today='2026-10-07', deadline=None):
        argv = [command, '--config', str(self.config), '--run-id', run, '--execution-id', 'manual',
                '--attempt-id', attempt, '--deadline', (deadline or self.deadline).isoformat(),
                '--state-dir', str(self.root), '--today', today, *flags]
        if command in ('discover', 'collect', 'backfill', 'daily'):
            argv += ['--fixture-pack', str(self.pack)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        message = json.loads(stdout.getvalue())
        self.calls.append({'argv': argv, 'exit': code, 'stdout': message, 'stderr': stderr.getvalue()})
        return code, message

    def capture(self, quarter):
        value = capture_quarter(quarter, self.objects, EtlState(self.store))
        if value is None:
            raise AssertionError('expected published quarter ' + quarter)
        return value, tuple(row.to_mapping() for row in read_quarter(value, self.objects))

    def close(self):
        for resource in reversed(self.opened):
            if hasattr(resource, 'close'):
                resource.close()

def simple_pack(root, *, empty=False, conflicting=False):
    listings, bodies = {}, {}
    for family in ('full-index', 'daily-index'):
        base = BASE + family + '/'
        listings[base + 'index.json'] = [('2026', 'dir')]
        listings[base + '2026/index.json'] = [('QTR3', 'dir'), ('QTR4', 'dir')]
        for quarter in (3, 4):
            leaf = base + f'2026/QTR{quarter}/'
            listings[leaf + 'index.json'] = []
            if empty or (family == 'daily-index' and quarter == 3):
                continue
            kind = 'quarterly' if family == 'full-index' else 'daily'
            filename = 'master.zip' if kind == 'quarterly' else 'master.20261001.idx'
            listings[leaf + 'index.json'] = [(filename, 'file')]
            filed = ('2026-09-30' if quarter == 3 else '2026-10-01') if kind == 'quarterly' else '20261001'
            path = f'edgar/data/123456/0000123456-26-00000{quarter}.txt'
            row = ('123456', 'Example', '10-K', filed, path)
            rows = (row, ('123456', 'Changed', '10-K', filed, path)) if conflicting else (row,)
            bodies[leaf + filename] = idx(rows, kind)
    return build_pack(root, listings, bodies)
