"""Raw-only command boundaries exercised with real retained fixture objects."""
from network_guard import install
install()

import contextlib
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from support import fixture_source
from support_etl import etl_context, seed_snapshot
from sec_edgar_ingest.cli import main
from sec_edgar_ingest.models import canonical_json


class EtlCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.settings, self.context = etl_context()
        self.config = self.root / 'config.json'
        self.config.write_bytes(canonical_json(self.settings.to_mapping()))
        self.source = fixture_source('2026-10-01', 'daily')
        self.body = (b'CIK|Company Name|Form Type|Date Filed|File Name\n-----\n'
                     b'123456|Example|10-K|20261001|edgar/data/123456/0000123456-26-000001.txt\n')
        self.store, self.objects, snapshot = seed_snapshot(self.root / '.fixture-state', self.source, self.body)
        self.addCleanup(self.store.close)
        self.snapshot_ref = f'worksets/sec/snapshot/sha256={snapshot.workset_id}/workset.json'
        self.calls = []
        self.addCleanup(self.retain)

    def retain(self):
        destination = os.environ.get('SEC_EDGAR_TASK6_PROOF_DIR')
        if destination:
            target = Path(destination) / self.id().rsplit('.', 1)[-1]
            target.mkdir(parents=True, exist_ok=True)
            (target / 'calls.json').write_bytes(canonical_json(self.calls))
            records = {kind: [row.to_mapping() for row in self.store.scan(kind, {})]
                       for kind in ('Attempt', 'Processing', 'PublicationReceipt', 'QuarterPublication', 'Candidate')}
            (target / 'state-records.json').write_bytes(canonical_json(records))
            self.store.close()
            shutil.copytree(self.root, target / 'files', dirs_exist_ok=True)
            hashes = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in target.rglob('*') if p.is_file()}
            (target / 'hashes.json').write_bytes(canonical_json(hashes))

    def argv(self, command='transform', ref=None, attempt=None):
        return [command, '--config', str(self.config), '--run-id', 'etl-cli', '--execution-id', 'execution',
                '--attempt-id', attempt or command, '--deadline', self.context.deadline.isoformat(),
                '--state-dir', str(self.root), '--workset', ref or self.snapshot_ref]

    def invoke(self, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        code = None
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr), \
                 patch('sec_edgar_ingest.cli.Coordinator', side_effect=AssertionError('ETL constructed SEC coordinator')), \
                 patch('sec_edgar_ingest.cli.BoundedSender', side_effect=AssertionError('ETL constructed SEC sender')), \
                 patch('sec_edgar_ingest.cli.RequestClient', side_effect=AssertionError('ETL constructed SEC request client')):
                try:
                    code = main(argv)
                except SystemExit as error:
                    code = error.code
        finally:
            self.calls.append({'argv': argv, 'cwd': str(Path.cwd()), 'exit': code, 'interrupted': code is None,
                               'stdout': stdout.getvalue(), 'stderr': stderr.getvalue()})
        return code, json.loads(stdout.getvalue()) if stdout.getvalue().startswith('{') else None

    def checkpoint(self, name):
        records = {kind: [row.to_mapping() for row in self.store.scan(kind, {})]
                   for kind in ('Attempt', 'Processing', 'PublicationReceipt', 'QuarterPublication', 'Candidate')}
        root = self.root / '.fixture-state/objects'
        objects = {path.relative_to(root).as_posix(): {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                   'bytes_hex': path.read_bytes().hex()} for path in root.rglob('*.json')}
        target = self.root / 'checkpoints'
        target.mkdir(exist_ok=True)
        (target / (name + '.json')).write_bytes(canonical_json({'state': records, 'objects': objects}))

    def test_help_lists_all_four_commands(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main([]), 0)
        for command in ('discover', 'collect', 'transform', 'publish'):
            self.assertIn(command, output.getvalue())

    def test_real_transform_and_publish_without_acquisition_construction(self):
        code, transformed = self.invoke(self.argv())
        self.assertEqual(code, 0, self.calls[-1])
        code, published = self.invoke(self.argv('publish', transformed['transformed_workset_ref']))
        self.assertEqual(code, 0, self.calls[-1])
        self.assertEqual(published['outcome'], 'success')
        self.assertEqual(len(list(self.store.scan('QuarterPublication', {}))), 1)
        self.assertEqual(len(list(self.store.scan('TransportAttempt', {}))), 0)

    def test_validation_happens_before_open_stores(self):
        for flag in ('--config', '--run-id', '--execution-id', '--attempt-id', '--deadline', '--workset'):
            argv = self.argv()
            index = argv.index(flag)
            del argv[index:index + 2]
            with self.subTest(missing=flag), patch('sec_edgar_ingest.cli.open_stores', side_effect=AssertionError('opened stores')):
                self.assertEqual(self.invoke(argv)[0], 2)
        for invalid in ('../escape', 'latest', 'worksets/sec/source/sha256=' + 'a' * 64 + '/workset.json'):
            with self.subTest(ref=invalid), patch('sec_edgar_ingest.cli.open_stores', side_effect=AssertionError('opened stores')):
                self.assertEqual(self.invoke(self.argv(ref=invalid))[0], 2)
        for extra in (['--fixture-pack', 'unused.json'], ['--today', 'not-a-date']):
            with patch('sec_edgar_ingest.cli.open_stores', side_effect=AssertionError('opened stores')):
                self.assertEqual(self.invoke(self.argv() + extra)[0], 2)
        for field, value in (('parser_version', 'unknown'), ('schema_version', 'unknown')):
            config = self.settings.to_mapping()
            config['etl'][field] = value
            self.config.write_bytes(canonical_json(config))
            with patch('sec_edgar_ingest.cli.open_stores', side_effect=AssertionError('opened stores')):
                self.assertEqual(self.invoke(self.argv())[0], 2)

    def transform(self, attempt='transform'):
        code, result = self.invoke(self.argv(attempt=attempt))
        self.assertEqual(code, 0, self.calls[-1])
        return result

    def test_completed_replay_is_exact_and_flag_changes_refuse(self):
        first = self.transform()
        path = self.root / '.fixture-state/objects' / first['result_ref']
        before = path.read_bytes()
        attempts = [row.to_mapping() for row in self.store.scan('Attempt', {})]
        self.assertEqual(self.invoke(self.argv()), (0, first))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual([row.to_mapping() for row in self.store.scan('Attempt', {})], attempts)
        for change in ('force', 'workset', 'execution', 'deadline', 'image', 'parser', 'config'):
            argv = self.argv()
            config = self.settings.to_mapping()
            if change == 'force': argv.append('--force')
            elif change == 'workset': argv[-1] = 'worksets/sec/snapshot/sha256=' + 'f' * 64 + '/workset.json'
            elif change == 'execution': argv[argv.index('--execution-id') + 1] = 'other'
            elif change == 'deadline': argv[argv.index('--deadline') + 1] = self.context.deadline.replace(microsecond=0).isoformat()
            elif change == 'image': config['worker']['image_digest'] = 'sha256:' + 'f' * 64
            elif change == 'parser': config['etl']['parser_version'] = 'fixture-index-parser-v2'
            else: config['sec']['requests_per_second'] = 2
            self.config.write_bytes(canonical_json(config))
            with self.subTest(change=change): self.assertEqual(self.invoke(argv)[0], 9, self.calls[-1])
        self.assertEqual(path.read_bytes(), before)

    def test_new_attempt_replays_parser_with_original_acquisition_context(self):
        first = self.transform()
        config = self.settings.to_mapping()
        config['etl']['parser_version'] = 'fixture-index-parser-v2'
        self.config.write_bytes(canonical_json(config))
        second = self.transform('v2')
        from sec_edgar_ingest.etl.contracts import decode_transformed
        old = decode_transformed(self.objects.read(first['transformed_workset_ref']))
        new = decode_transformed(self.objects.read(second['transformed_workset_ref']))
        self.assertEqual(old.origin_context, new.origin_context)
        self.assertNotEqual(old.context.parser_version, new.context.parser_version)

    def test_expired_completed_replay_but_new_expired_refusal(self):
        first = self.transform()
        with patch('sec_edgar_ingest.cli.Clock.now', return_value=datetime(2100, 1, 1, tzinfo=timezone.utc)):
            self.assertEqual(self.invoke(self.argv()), (0, first))
            self.assertEqual(self.invoke(self.argv(attempt='new'))[0], 2)

    def test_begun_intent_resumes_original_start_and_pin(self):
        from sec_edgar_ingest.state import attempt_key
        with patch('sec_edgar_ingest.cli.run_transform', side_effect=RuntimeError('interrupted command')):
            self.assertEqual(self.invoke(self.argv())[0], 9)
        before = next(self.store.scan('Attempt', {})).to_mapping()['value']['context']
        result = self.transform()
        from sec_edgar_ingest.etl.commands import read_etl_result
        saved = read_etl_result(result['result_ref'], self.objects)
        self.assertEqual(saved.context.to_mapping(), before)
        self.assertEqual(self.store.get('Attempt', attempt_key(saved.context)).value['outcome'], 'success')

    def test_result_object_crash_repairs_attempt_exactly(self):
        from sec_edgar_ingest.etl.commands import write_etl_result, read_etl_result
        from sec_edgar_ingest.state import attempt_key
        from support import Faults, CollectionCrash
        for point in ('etl_result.after_object', 'etl_result.after_attempt'):
            faults = Faults()
            def crash(): raise CollectionCrash()
            faults.at(point, crash)
            argv = self.argv(attempt=point.replace('.', '-'))
            def writer(result, objects, acquisition):
                return write_etl_result(result, objects, acquisition, observer=faults)
            with patch('sec_edgar_ingest.cli.write_etl_result', side_effect=writer), self.assertRaises(CollectionCrash):
                self.invoke(argv)
            path = f'runs/sec/etl-cli/transform/{argv[argv.index("--attempt-id") + 1]}/result.json'
            frozen = self.objects.read(path)
            self.checkpoint(point.replace('.', '-') + '-before-replay')
            self.assertEqual(self.invoke(argv)[0], 0, self.calls[-1])
            self.assertEqual(self.objects.read(path), frozen)
            self.checkpoint(point.replace('.', '-') + '-after-replay')
            result = read_etl_result(path, self.objects)
            self.assertEqual(self.store.get('Attempt', attempt_key(result.context)).to_mapping()['value']['result'], result.to_mapping())

    def test_publish_noop_and_result_crash_do_not_advance_twice(self):
        from sec_edgar_ingest.etl.commands import write_etl_result
        from support import Faults, CollectionCrash
        ref = self.transform()['transformed_workset_ref']
        faults = Faults()
        def crash(): raise CollectionCrash()
        faults.at('etl_result.after_object', crash)
        def writer(result, objects, acquisition): return write_etl_result(result, objects, acquisition, observer=faults)
        with patch('sec_edgar_ingest.cli.write_etl_result', side_effect=writer), self.assertRaises(CollectionCrash):
            self.invoke(self.argv('publish', ref))
        pointer = [row.to_mapping() for row in self.store.scan('QuarterPublication', {})]
        self.checkpoint('publish-result-before-replay')
        self.assertEqual(self.invoke(self.argv('publish', ref))[0], 0)
        self.assertEqual(self.invoke(self.argv('publish', ref, attempt='noop'))[1]['outcome'], 'unchanged')
        self.assertEqual([row.to_mapping() for row in self.store.scan('QuarterPublication', {})], pointer)
        self.checkpoint('publish-result-after-replay')

    def test_strict_separate_result_codec(self):
        from sec_edgar_ingest.etl.commands import read_etl_result
        from sec_edgar_ingest.results import read_result
        from sec_edgar_ingest.storage.contracts import Conflict
        first = self.transform()
        path = first['result_ref']
        original = self.objects.read(path)
        result = read_etl_result(path, self.objects)
        self.assertEqual(result.format_version, 'sec-etl-result-v1')
        with self.assertRaises(ValueError): read_result(path, self.objects)
        for mutation in ('format', 'counter', 'unknown', 'outcome', 'input', 'start', 'canonical', 'missing'):
            invalid = json.loads(original)
            if mutation == 'format': invalid['format_version'] = 'future'
            elif mutation == 'counter': invalid['published'] = 1
            elif mutation == 'unknown': invalid['surprise'] = 1
            elif mutation == 'outcome': invalid['outcome'] = 'published'
            elif mutation == 'input': invalid['input_ref'] = 'latest'
            elif mutation == 'start': invalid['started_at'] = '2026-10-01T00:00:00+00:00'
            elif mutation == 'missing': del invalid['format_version']
            body = json.dumps(invalid).encode() if mutation == 'canonical' else canonical_json(invalid)
            with self.subTest(mutation=mutation), patch.object(self.objects, 'read', return_value=body):
                with self.assertRaises((ValueError, Conflict)):
                    read_etl_result(path, self.objects)

    def seed_members(self, members):
        from support import fixture_snapshot, fixture_workset
        from sec_edgar_ingest.models import Binding
        from sec_edgar_ingest.state import AcquisitionState
        from sec_edgar_ingest.worksets import make_snapshot_workset, encode_workset
        sources = fixture_workset(tuple(source for source, body in members))
        self.objects.put_once(f'worksets/sec/source/sha256={sources.workset_id}/workset.json', encode_workset(sources))
        snapshots = []
        acquisition = AcquisitionState(self.store)
        for source, body in members:
            snapshot = fixture_snapshot(source, body)
            snapshots.append(snapshot)
            self.objects.put_once(snapshot.raw_path, body)
            acquisition.remember_snapshot(snapshot)
            acquisition.bind_once(Binding(sources.workset_id, source.source_id, snapshot.sha256))
        workset = make_snapshot_workset(sources, tuple(snapshots))
        ref = f'worksets/sec/snapshot/sha256={workset.workset_id}/workset.json'
        self.objects.put_once(ref, encode_workset(workset))
        return ref

    def transformed_members(self, members, attempt):
        ref = self.seed_members(members)
        code, output = self.invoke(self.argv(ref=ref, attempt=attempt))
        self.assertEqual(code, 0, self.calls[-1])
        return output['transformed_workset_ref']

    def observation_workset(self, refs, attempt):
        # Each ref was produced by the real transform; build only its strict envelope.
        from dataclasses import replace
        from sec_edgar_ingest.etl.contracts import TransformedWorkset, TRANSFORMED_FORMAT, encode_transformed, transformed_ref
        context = replace(self.context, attempt_id=attempt)
        workset = TransformedWorkset('0' * 64, self.snapshot_ref, self.context, context, tuple(refs), (), True)
        value = {'format_version': TRANSFORMED_FORMAT, **workset.to_mapping()}
        del value['workset_id']
        workset = replace(workset, workset_id=hashlib.sha256(canonical_json(value)).hexdigest())
        ref = transformed_ref(workset)
        self.objects.put_once(ref, encode_transformed(workset))
        return ref

    def read_output(self, output):
        from sec_edgar_ingest.etl.commands import read_etl_result
        return read_etl_result(output['result_ref'], self.objects)

    def test_partial_transform_retains_success_and_publish_changes_no_pointer(self):
        bad_source = fixture_source('2026-10-02', 'daily')
        bad = self.body.replace(b'123456|Example', b'invalid|Example')
        ref = self.seed_members(((self.source, self.body), (bad_source, bad)))
        code, output = self.invoke(self.argv(ref=ref, attempt='partial'))
        self.assertEqual(code, 3, self.calls[-1])
        result = self.read_output(output)
        self.assertEqual((result.transformed, result.failed, result.quarantined), (1, 1, 1))
        self.assertEqual(result.gaps[0].details['line_number'], 3)
        with patch('sec_edgar_ingest.etl.commands.publish_quarter', side_effect=AssertionError('partial published')):
            code, output = self.invoke(self.argv('publish', result.transformed_workset_ref))
        self.assertEqual(code, 3, self.calls[-1])
        self.assertFalse(list(self.store.scan('QuarterPublication', {})))

    def test_invalid_source_is_exit_seven(self):
        ref = self.seed_members(((fixture_source('2026-10-02', 'daily'), self.body.replace(b'123456|Example', b'invalid|Example')),))
        code, output = self.invoke(self.argv(ref=ref))
        self.assertEqual(code, 7, self.calls[-1])
        self.assertEqual(self.read_output(output).outcome, 'invalid_source')

    def test_empty_complete_transform_and_publish_are_unchanged(self):
        ref = self.transformed_members((), 'empty')
        code, output = self.invoke(self.argv('publish', ref))
        self.assertEqual(code, 0, self.calls[-1])
        result = self.read_output(output)
        self.assertEqual((result.outcome, result.published, result.quarters), ('unchanged', 0, ()))

    def test_multiple_quarters_gate_continues_other_quarter_and_complete_receipts(self):
        from support_etl import seed_observation
        from sec_edgar_ingest.etl.state import EtlState
        state = EtlState(self.store)
        rows = (b'123456|A|10-K|2026-07-01|edgar/data/123456/a.txt\n'
                b'123456|B|10-K|2026-07-02|edgar/data/123456/b.txt\n'
                b'123456|C|10-K|2026-10-01|edgar/data/123456/c.txt\n')
        old = seed_observation(self.objects, state, self.context, self.settings, period='2026Q3', rows=rows)
        code, output = self.invoke(self.argv('publish', self.observation_workset((old,), 'old'), 'old'))
        self.assertEqual(code, 0, self.calls[-1])
        self.assertTrue(state.processing(old).value['published'])
        pointer = state.pointer('2026Q3')
        new = seed_observation(self.objects, state, self.context, self.settings, period='2026Q3', rows=rows.split(b'\n', 1)[1], seconds=1)
        ref = self.observation_workset((new,), 'new')
        code, output = self.invoke(self.argv('publish', ref, 'gate'))
        self.assertEqual(code, 10, self.calls[-1])
        result = self.read_output(output)
        self.assertEqual((result.awaiting_approval, result.published), (1, 1))
        self.assertEqual(state.pointer('2026Q3'), pointer)
        self.assertFalse(state.processing(new).value.get('published', False))
        self.assertEqual(set(state.processing(new).value['publications']), {'2026Q4'})

    def test_persistent_conflict_retains_attempted_manifest_and_exit_nine(self):
        from sec_edgar_ingest.etl.state import EtlState
        from sec_edgar_ingest.storage.contracts import Conflict, CAS_ATTEMPTS
        ref = self.transform()['transformed_workset_ref']
        with patch.object(EtlState, 'commit_pointer', side_effect=Conflict('forced real candidate CAS loss')) as commits:
            code, output = self.invoke(self.argv('publish', ref))
        self.assertEqual(code, 9, self.calls[-1])
        self.assertEqual(commits.call_count, CAS_ATTEMPTS)
        result = self.read_output(output)
        self.assertEqual(result.quarters[0].outcome, 'publication_conflict')
        self.assertIsNone(result.quarters[0].generation_id)
        self.assertEqual(result.gaps[0].details['attempted_manifest_ref'], result.quarters[0].manifest_ref)
        self.assertFalse(list(self.store.scan('QuarterPublication', {})))

    def test_changed_filing_date_visits_prior_receipt_quarter(self):
        from support_etl import seed_observation
        from sec_edgar_ingest.etl.state import EtlState
        state = EtlState(self.store)
        rows = b'123456|A|10-K|2026-07-01|edgar/data/123456/a.txt\n'
        old = seed_observation(self.objects, state, self.context, self.settings, period='2026-10-02', kind='daily', rows=rows)
        code, _ = self.invoke(self.argv('publish', self.observation_workset((old,), 'old-date'), 'old-date'))
        self.assertEqual(code, 0, self.calls[-1])
        new = seed_observation(self.objects, state, self.context, self.settings, period='2026-10-02', kind='daily',
                               rows=rows.replace(b'2026-07-01', b'2026-10-01'), seconds=1)
        code, output = self.invoke(self.argv('publish', self.observation_workset((new,), 'new-date'), 'new-date'))
        self.assertEqual(code, 0, self.calls[-1])
        self.assertEqual({quarter.quarter for quarter in self.read_output(output).quarters}, {'2026Q3', '2026Q4'})

    def test_pointer_crash_resumes_without_another_advance_and_repairs_receipts(self):
        from sec_edgar_ingest.etl.commands import run_publish
        from support import Faults, CollectionCrash
        ref = self.transform()['transformed_workset_ref']
        faults = Faults()
        def crash(): raise CollectionCrash()
        faults.at('publication.after_pointer', crash)
        def publisher(*args): return run_publish(*args, observer=faults)
        with patch('sec_edgar_ingest.cli.run_publish', side_effect=publisher), self.assertRaises(CollectionCrash):
            self.invoke(self.argv('publish', ref))
        before = [row.to_mapping() for row in self.store.scan('QuarterPublication', {})]
        self.assertFalse(list(self.store.scan('PublicationReceipt', {})))
        self.checkpoint('pointer-before-replay')
        code, _ = self.invoke(self.argv('publish', ref))
        self.assertEqual(code, 0, self.calls[-1])
        self.assertEqual([row.to_mapping() for row in self.store.scan('QuarterPublication', {})], before)
        self.assertEqual(len(list(self.store.scan('PublicationReceipt', {}))), 1)
        self.checkpoint('pointer-after-replay')

    def test_begun_intent_refuses_changed_image_execution_and_config(self):
        with patch('sec_edgar_ingest.cli.run_transform', side_effect=RuntimeError('interrupt before work')):
            self.assertEqual(self.invoke(self.argv())[0], 9)
        before = [row.to_mapping() for row in self.store.scan('Attempt', {})]
        for change in ('image', 'execution', 'parser', 'force', 'workset'):
            config = self.settings.to_mapping()
            argv = self.argv()
            if change == 'image': config['worker']['image_digest'] = 'sha256:' + 'f' * 64
            elif change == 'execution': argv[argv.index('--execution-id') + 1] = 'different'
            elif change == 'parser': config['etl']['parser_version'] = 'fixture-index-parser-v2'
            elif change == 'force': argv.append('--force')
            else: argv[-1] = 'worksets/sec/snapshot/sha256=' + 'f' * 64 + '/workset.json'
            self.config.write_bytes(canonical_json(config))
            with self.subTest(change=change):
                self.assertEqual(self.invoke(argv)[0], 9, self.calls[-1])
        # Refused invocations cannot create independent attempts for the same intent path.
        self.assertEqual(len(list(self.store.scan('Attempt', {}))), len(before))

    def test_publish_empty_rejects_context_version_mismatch(self):
        ref = self.transformed_members((), 'empty-version')
        config = self.settings.to_mapping()
        config['etl']['parser_version'] = 'fixture-index-parser-v2'
        self.config.write_bytes(canonical_json(config))
        self.assertEqual(self.invoke(self.argv('publish', ref))[0], 9, self.calls[-1])

    def test_failure_quarter_requires_matching_gap_and_valid_counters(self):
        from sec_edgar_ingest.etl.commands import read_etl_result
        from sec_edgar_ingest.etl.state import EtlState
        from sec_edgar_ingest.storage.contracts import Conflict
        ref = self.transform()['transformed_workset_ref']
        with patch.object(EtlState, 'commit_pointer', side_effect=Conflict('CAS loss')):
            code, output = self.invoke(self.argv('publish', ref))
        self.assertEqual(code, 9)
        path = output['result_ref']
        original = json.loads(self.objects.read(path))
        for mutation in ('missing-gap', 'unknown-gap', 'excess-conflicts'):
            value = json.loads(canonical_json(original))
            if mutation == 'missing-gap':
                value['quarters'][0]['manifest_ref'] = None
                value['gaps'] = []
                value['failed'] = 0
            elif mutation == 'unknown-gap': value['gaps'][0]['code'] = 'invented'
            else: value['quarters'][0]['conflicts'] = 6
            with self.subTest(mutation=mutation), patch.object(self.objects, 'read', return_value=canonical_json(value)):
                with self.assertRaises((ValueError, Conflict)): read_etl_result(path, self.objects)

    def test_harder_failure_dominates_gate_but_preserves_both_quarters(self):
        from support_etl import seed_observation
        from sec_edgar_ingest.etl.state import EtlState
        from sec_edgar_ingest.storage.contracts import Conflict
        state = EtlState(self.store)
        rows = (b'123456|A|10-K|2026-07-01|edgar/data/123456/a.txt\n'
                b'123456|B|10-K|2026-07-02|edgar/data/123456/b.txt\n'
                b'123456|C|10-K|2026-10-01|edgar/data/123456/c.txt\n')
        old = seed_observation(self.objects, state, self.context, self.settings, period='2026Q3', rows=rows)
        self.assertEqual(self.invoke(self.argv('publish', self.observation_workset((old,), 'base-hard'), 'base-hard'))[0], 0)
        new = seed_observation(self.objects, state, self.context, self.settings, period='2026Q3', rows=rows.split(b'\n', 1)[1], seconds=1)
        with patch.object(EtlState, 'commit_pointer', side_effect=Conflict('Q4 blocked')):
            code, output = self.invoke(self.argv('publish', self.observation_workset((new,), 'hard-gate'), 'hard-gate'))
        self.assertEqual(code, 9, self.calls[-1])
        result = self.read_output(output)
        self.assertEqual((result.outcome, result.awaiting_approval, result.failed), ('publication_conflict', 1, 1))
        self.assertEqual([q.outcome for q in result.quarters], ['awaiting_approval', 'publication_conflict'])

    def test_forced_transform_rebuild_preserves_logical_publication(self):
        first = self.transform()
        ref = first['transformed_workset_ref']
        self.assertEqual(self.invoke(self.argv('publish', ref))[0], 0)
        before = [row.to_mapping() for row in self.store.scan('QuarterPublication', {})]
        code, forced = self.invoke(self.argv(attempt='forced') + ['--force'])
        self.assertEqual(code, 0, self.calls[-1])
        self.assertEqual(self.read_output(forced).transformed, 1)
        code, output = self.invoke(self.argv('publish', forced['transformed_workset_ref'], 'forced-publish'))
        self.assertEqual(code, 0, self.calls[-1])
        self.assertEqual(self.read_output(output).outcome, 'unchanged')
        self.assertEqual([row.to_mapping() for row in self.store.scan('QuarterPublication', {})], before)

    def test_wrong_payload_path_refuses(self):
        first = self.transform()
        for kind, path in (('snapshot', self.snapshot_ref), ('transformed', first['transformed_workset_ref'])):
            body = self.objects.read(path)
            wrong = f'worksets/sec/{kind}/sha256=' + 'a' * 64 + '/workset.json'
            self.objects.put_once(wrong, body)
            command = 'transform' if kind == 'snapshot' else 'publish'
            self.assertEqual(self.invoke(self.argv(command, wrong, 'wrong-' + kind))[0], 9, self.calls[-1])
        self.assertFalse(list(self.store.scan('QuarterPublication', {})))

    def test_result_write_requires_exact_begun_attempt_and_rejects_changed_result(self):
        from dataclasses import replace
        from sec_edgar_ingest.etl.commands import run_transform, write_etl_result
        from sec_edgar_ingest.state import AcquisitionState
        from sec_edgar_ingest.storage.contracts import Conflict
        context = self.context
        with contextlib.redirect_stderr(io.StringIO()):
            result = run_transform(self.snapshot_ref, context, self.settings, self.objects, self.store)
        acquisition = AcquisitionState(self.store)
        with self.assertRaises(Conflict): write_etl_result(result, self.objects, acquisition)
        acquisition.begin_attempt(context)
        write_etl_result(result, self.objects, acquisition)
        with self.assertRaises(Conflict):
            write_etl_result(replace(result, transformed=result.transformed + 1), self.objects, acquisition)

    def test_result_codec_refuses_forged_context_and_orphan_error(self):
        from sec_edgar_ingest.etl.commands import read_etl_result
        from sec_edgar_ingest.storage.contracts import Conflict
        output = self.transform()
        path = output['result_ref']
        body = self.objects.read(path)
        for mutation in ('hash', 'config', 'pin', 'execution'):
            value = json.loads(body)
            if mutation == 'hash': value['context']['config_sha256'] = 'f' * 64
            elif mutation == 'config': value['context']['effective_config'] = {}
            elif mutation == 'pin': value['context']['pinned_on'] = None
            else: value['context']['execution_id'] = '../unsafe'
            with self.subTest(mutation=mutation), patch.object(self.objects, 'read', return_value=canonical_json(value)):
                with self.assertRaises((ValueError, Conflict)): read_etl_result(path, self.objects)
        _, output = self.invoke(self.argv('publish', output['transformed_workset_ref']))
        path = output['result_ref']
        value = json.loads(self.objects.read(path))
        value['gaps'] = [{'code': 'internal_error', 'message': 'orphan', 'retryable': False, 'source_id': None, 'details': {}}]
        value['failed'] = 1
        value['outcome'] = 'internal_error'
        with patch.object(self.objects, 'read', return_value=canonical_json(value)):
            with self.assertRaises((ValueError, Conflict)): read_etl_result(path, self.objects)

    def test_invalid_source_logs_source_and_raw_correlation(self):
        source = fixture_source('2026-10-02', 'daily')
        body = self.body.replace(b'123456|Example', b'invalid|Example')
        ref = self.seed_members(((source, body),))
        self.assertEqual(self.invoke(self.argv(ref=ref))[0], 7)
        events = [json.loads(line) for line in self.calls[-1]['stderr'].splitlines()]
        failures = [event for event in events if event['event'] == 'source_transform_failed']
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]['fields']['source_id'], source.source_id)
        self.assertEqual(failures[0]['fields']['raw_sha256'], hashlib.sha256(body).hexdigest())
