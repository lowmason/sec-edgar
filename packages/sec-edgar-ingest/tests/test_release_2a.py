"""Stage 2a spec §5 item 9 (D10, D11) and item 5 on the new release, with two real releases: 1c and the current code.

The 1c release refuses a v2 config. The current release continues work that the 1c release left pending,
and it reads a generation that the 1c release wrote exactly as the 1c release reads it.
"""
from network_guard import install
install()

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from support import FIXTURE_CONFIG, fixture_settings
from support_process import CheckedRunner
from support_workflows import BASE, idx, replace_pack_body, simple_pack
from sec_edgar_ingest.config import Settings
from sec_edgar_ingest.models import canonical_json, to_mapping_value
from sec_edgar_ingest.runtime import isolated_environment, native_python_argv

QUARTER_ROWS = (('123456', 'Example', '10-K', '2026-09-30', 'edgar/data/123456/0000123456-26-000003.txt'),
                ('234567', 'Second Example Inc', '8-K', '2026-08-14', 'edgar/data/234567/0000234567-26-000011.txt'),
                ('345678', 'Third Example LLC', '10-Q', '2026-07-01', 'edgar/data/345678/0000345678-26-000021.txt'))

# One quarter read in a release's own interpreter. Stdout holds only canonical_json of each read_quarter row.
# The sidecar file holds the capture, the manifest's schema and producer, the import origin and each row's type.
# A capture given as JSON is read as given; '-' captures the quarter's current pointer.
READ = '''
import json, sys
from pathlib import Path
import sec_edgar_ingest
from sec_edgar_ingest.config import load_config
from sec_edgar_ingest.etl.contracts import GenerationCapture
from sec_edgar_ingest.etl.manifest import read_manifest
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.models import canonical_json
from sec_edgar_ingest.storage import open_stores
config, quarter, given, sidecar = sys.argv[1:]
opened = open_stores(load_config(Path(config)), access='operator')
store, objects, _ = opened
try:
    capture = (capture_quarter(quarter, objects, EtlState(store)) if given == '-'
               else GenerationCapture.from_mapping(json.loads(given)))
    manifest = read_manifest(capture, objects)
    rows = list(read_quarter(capture, objects))
finally:
    for resource in reversed(opened):
        if hasattr(resource, 'close'): resource.close()
for row in rows:
    sys.stdout.buffer.write(canonical_json(row.to_mapping()) + b'\\n')
Path(sidecar).write_text(json.dumps({'origin': sec_edgar_ingest.__file__, 'capture': capture.to_mapping(),
    'schema_version': manifest.schema_version, 'producer': manifest.runtime['release_sha256'],
    'types': [type(row).__module__ + '.' + type(row).__qualname__ for row in rows]}))
'''


class TwoReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from support_release import ONE_C_REVISION, origin_release, proof_releases
        from sec_edgar_ingest.runtime import preflight
        project = Path(__file__).resolve().parents[3]
        cache = project / 'releases/artifact-cache'
        # P9: the gate builds the 1c application from its revision. The evidence run sets
        # SEC_LOCAL_1C_RELEASE to the installed release.json of c4de77b8… instead.
        installed = os.environ.get('SEC_LOCAL_1C_RELEASE')
        cls.one_c = preflight(Path(installed)) if installed else origin_release(project, cache, revision=ONE_C_REVISION)
        cls.current = proof_releases(project, cache)[1]

    def scratch(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def config(self, root, release, schema):
        """A native config for `release` on the shared store under `root`, with `schema` as etl.schema_version."""
        value = fixture_settings(root=root / 'data', backfill={'start_quarter': '2026Q3', 'end_quarter': 'open'},
            etl={'parser_version': 'fixture-index-parser-v1', 'schema_version': schema},
            fixture={'allow_clock_override': True, 'allow_deadline_override': False}).to_mapping()
        value['runtime'] = {'kind': 'native', 'release_manifest': str(release.directory / 'release.json')}
        path = root / (schema + '-config.json')
        path.write_bytes(canonical_json(to_mapping_value(Settings.from_mapping(value).to_mapping())))
        return path

    def read(self, release, config, quarter, given='-'):
        """READ in the release's own interpreter: (stdout row bytes, sidecar mapping)."""
        sidecar = config.parent / (config.stem + '-' + quarter + '-read.json')
        done = subprocess.run([*native_python_argv(release.python), '-c', READ, str(config), quarter, given,
                               str(sidecar)], cwd=config.parent, env=isolated_environment(),
                              capture_output=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr.decode())
        side = json.loads(sidecar.read_text())
        self.assertTrue(Path(side['origin']).is_relative_to(release.directory), side['origin'])
        return done.stdout, side

    def test_1c_release_refuses_the_v2_config(self):
        """D10: the 1c interpreter's own load_config refuses the v2 fixture config."""
        self.assertEqual(json.loads(FIXTURE_CONFIG.read_text())['etl']['schema_version'], 'sec-index-v2')
        code = ('import sys; from pathlib import Path; import sec_edgar_ingest; '
                'print(sec_edgar_ingest.__file__, flush=True); '
                'from sec_edgar_ingest.config import load_config; load_config(Path(sys.argv[1]))')
        done = subprocess.run([*native_python_argv(self.one_c.python), '-c', code, str(FIXTURE_CONFIG)],
                              cwd=self.scratch(), env=isolated_environment(), capture_output=True, text=True,
                              timeout=60)
        self.assertTrue(Path(done.stdout.strip()).is_relative_to(self.one_c.directory), done.stdout)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('unsupported etl.schema_version', done.stderr)

    def test_v2_release_continues_1c_origin_pending_work(self):
        """D11: the current release, as B, continues 1c-origin pending work and repairs a 1c publication."""
        from workflow_proof import upgrade_sequence
        with tempfile.TemporaryDirectory() as directory:
            report = upgrade_sequence(Path(directory), self.one_c.directory / 'release.json',
                                      self.current.directory / 'release.json', a_schema='sec-index-v1')
            self.assertEqual(report['exit'], 0)
            destination = os.environ.get('SEC_LOCAL_2A_UPGRADE_EVIDENCE')
            if destination:
                shutil.copytree(Path(directory), destination)
            for case in report['cases']:
                self.assertEqual(case['b_exit'], 0)
                self.assertGreater(case['rows'], 0)
                # Member order: as in test_release_upgrade (plan Decisions R2, fallback).
                self.assertEqual(case['a_child_expected'],
                                 case['scenario'] == 'repair' or any(case['a_first'].values()))
                self.assertEqual(case['a_child_under_b_parent'], case['a_child_expected'])
                records = [case['parent'], *case['children']]
                selected = sorted({str(Path(item['python']).parents[2]) for item in records})
                expected = (case['release_directories'] if case['a_child_expected']
                            else [str(Path(case['parent']['python']).parents[2])])
                self.assertEqual(selected, expected, 'upgrade must exercise actual 1c-origin and current processes')
                for record in records:
                    guard = record['checkout_guard']
                    self.assertEqual(guard['pid'], record['pid'])
                    self.assertFalse(guard['application_imported'])
                    self.assertEqual(guard['denied'], [True] * 6)
                    self.assertEqual(guard['policy']['releases'], case['release_directories'])
            # The current release published the pending quarter: its generation manifest, bound by the
            # reported capture's hash, is v2 (D9).
            pending = next(case for case in report['cases'] if case['scenario'] == 'pending')
            capture = pending['reader']
            body = (Path(directory) / 'pending/data/objects' / capture['manifest_ref']).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(), capture['manifest_sha256'])
            self.assertEqual(json.loads(body)['schema_version'], 'sec-index-v2')

    def test_v2_reads_the_1c_generation_unchanged(self):
        """Spec §5 item 5 on the new release: a 1c-written generation reads back byte-equal, as v1 rows (D7)."""
        root = self.scratch()
        pack = simple_pack(root / 'pack')
        replace_pack_body(pack, BASE + 'full-index/2026/QTR3/master.zip', idx(QUARTER_ROWS, 'quarterly'))
        one_c_config = self.config(root, self.one_c, 'sec-index-v1')
        deadline = datetime.now(timezone.utc) + timedelta(seconds=1800)
        argv = [*native_python_argv(self.one_c.python), '-m', 'sec_edgar_ingest', 'backfill',
                '--config', str(one_c_config), '--run-id', 'one-c', '--execution-id', 'manual', '--attempt-id', 'a',
                '--deadline', deadline.isoformat(), '--today', '2026-10-07', '--fixture-pack', str(pack)]
        done = CheckedRunner()(self.one_c.python, argv, deadline=deadline, environ=isolated_environment())
        self.assertEqual(done.returncode, 0, done.stderr.decode())
        reference, written = self.read(self.one_c, one_c_config, '2026Q3')
        self.assertEqual((written['schema_version'], written['producer']), ('sec-index-v1', self.one_c.release_id))
        self.assertEqual(len(reference.splitlines()), len(QUARTER_ROWS))
        current_config = self.config(root, self.current, 'sec-index-v2')
        rows, read = self.read(self.current, current_config, '2026Q3', json.dumps(written['capture']))
        self.assertEqual(rows, reference)
        self.assertEqual(read['types'], ['sec_edgar_ingest.etl.contracts.IndexRow'] * len(QUARTER_ROWS))


if __name__ == '__main__':
    unittest.main()
