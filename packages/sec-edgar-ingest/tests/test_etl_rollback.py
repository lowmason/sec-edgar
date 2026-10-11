"""Offline recorded pointer rollback within one quarter's exact lineage."""
from network_guard import install
install()

import json
import unittest

from support import Faults
from support_approval import GateFixture, operator_cli, row
from sec_edgar_ingest.etl.approval import approve
from sec_edgar_ingest.etl.contracts import QuarterRollback
from sec_edgar_ingest.etl.rollback import rollback, rollback_ref
from sec_edgar_ingest.models import canonical_json
from sec_edgar_ingest.storage.contracts import table_for


class RollbackTests(GateFixture):
    def lineage_of_two(self):
        """Publish G1 {1, 2} then G2 {1 Renamed, 2} in the open 2026Q4."""
        first = self.observation(rows=row() + row(number=2))
        self.assertEqual(self.publish(first).outcome, 'published')
        older = self.capture()
        second = self.observation(rows=row('Renamed') + row(number=2), seconds=1)
        self.assertEqual(self.publish(second).outcome, 'published')
        return older, self.capture(), second

    def rollback(self, source, target, operator='Lowell Mason', reason='SEC correction withdrawn', **kwargs):
        return rollback('2026Q4', source, target, operator, reason, self.objects, self.state, **kwargs)

    def test_rollback_records_then_restores_an_earlier_lineage_generation(self):
        older, newer, _ = self.lineage_of_two()
        before = self.state.pointer('2026Q4')
        result = self.rollback(newer.generation_id, older.generation_id)
        self.assertEqual((result.outcome, result.active), ('success', older))
        self.assertEqual(self.capture(), older)
        self.assertEqual(self.rows(), [(1, 'Example'), (2, 'Example')])
        record = result.rollback
        self.assertEqual((record.quarter, record.from_generation_id, record.to_generation_id,
                          record.from_pointer_version, record.operator, record.reason, record.format_version),
                         ('2026Q4', newer.generation_id, older.generation_id, before.version, 'Lowell Mason',
                          'SEC correction withdrawn', 'sec-pointer-rollback-v1'))
        self.assertEqual((record.to_manifest_ref, record.to_manifest_sha256, record.to_manifest_bytes),
                         (older.manifest_ref, older.manifest_sha256, older.manifest_bytes))
        ref = rollback_ref(record)
        self.assertEqual(ref, 'approvals/sec/filing_index/year=2026/quarter=4/rollback='
                         + record.rollback_id + '/rollback.json')
        self.assertEqual(self.objects.read(ref), canonical_json(record.to_mapping()))
        self.assertEqual(QuarterRollback.from_mapping(record.to_mapping()), record)
        self.assertEqual(self.state.rollbacks('2026Q4'), (record,))
        self.assertEqual(table_for('QuarterRollback'), 'Approvals')
        pointer = self.state.pointer('2026Q4')
        again = self.rollback(newer.generation_id, older.generation_id, reason='repeated')
        self.assertEqual((again.outcome, again.active, again.rollback), ('unchanged', older, None))
        self.assertEqual(self.state.pointer('2026Q4'), pointer)
        self.assertEqual(self.state.rollbacks('2026Q4'), (record,))

    def test_rollback_is_not_a_pin_and_never_rolls_forward(self):
        older, newer, second = self.lineage_of_two()
        self.assertEqual(self.rollback(newer.generation_id, older.generation_id).outcome, 'success')
        forward = self.rollback(older.generation_id, newer.generation_id)
        self.assertEqual((forward.outcome, forward.error.code), ('rollback_refused', 'rollback_refused'))
        self.assertEqual(self.capture(), older)
        # Receipt-ordered selection rebuilds the same deterministic generation from the restored base.
        self.assertEqual(self.publish(second).outcome, 'published')
        self.assertEqual(self.capture(), newer)

    def test_refusals_and_stale_requests_write_nothing(self):
        older, newer, _ = self.lineage_of_two()
        pointer = self.state.pointer('2026Q4')
        cases = {
            'same generation': ('2026Q4', newer.generation_id, newer.generation_id, 'Lowell Mason', 'x'),
            'unknown target': ('2026Q4', newer.generation_id, 'f' * 64, 'Lowell Mason', 'x'),
            'invalid hash text': ('2026Q4', newer.generation_id, 'not-a-hash', 'Lowell Mason', 'x'),
            'invalid quarter': ('2026Q5', newer.generation_id, older.generation_id, 'Lowell Mason', 'x'),
            'invalid operator': ('2026Q4', newer.generation_id, older.generation_id, 'two\nlines', 'x'),
            'long reason': ('2026Q4', newer.generation_id, older.generation_id, 'Lowell Mason', 'r' * 1025),
            'no pointer': ('2026Q3', newer.generation_id, older.generation_id, 'Lowell Mason', 'x'),
        }
        for label, args in cases.items():
            with self.subTest(label):
                result = rollback(*args, self.objects, self.state)
                self.assertEqual((result.outcome, result.error.code), ('rollback_refused', 'rollback_refused'))
                self.assertIsNone(result.rollback)
        stale = rollback('2026Q4', 'e' * 64, older.generation_id, 'Lowell Mason', 'x', self.objects, self.state)
        self.assertEqual((stale.outcome, stale.error.details['active_generation_id']),
                         ('rollback_stale', newer.generation_id))
        self.assertEqual(self.state.pointer('2026Q4'), pointer)
        self.assertEqual(self.state.rollbacks('2026Q4'), ())

    def test_an_approved_gated_generation_is_a_valid_target(self):
        _, revised, candidate = self.gated()
        approved = approve('2026Q4', candidate.manifest.generation_id, revised.snapshot.sha256, 'Lowell Mason',
                           self.objects, self.state)
        self.assertEqual(approved.outcome, 'success')
        returned = self.observation(rows=row() + row('Returned', number=2), seconds=2)
        self.assertEqual(self.publish(returned).outcome, 'published')
        latest = self.capture()
        result = self.rollback(latest.generation_id, candidate.manifest.generation_id)
        self.assertEqual((result.outcome, self.capture().generation_id),
                         ('success', candidate.manifest.generation_id))
        self.assertEqual(self.rows(), [(1, 'Example')])

    def test_a_lost_pointer_race_is_stale_and_keeps_its_attempt_record(self):
        older, newer, _ = self.lineage_of_two()
        third = self.observation(rows=row('Third') + row(number=2), seconds=2)
        faults = Faults()
        faults.at('rollback.before_pointer', lambda: self.assertEqual(self.publish(third).outcome, 'published'))
        result = self.rollback(newer.generation_id, older.generation_id, observer=faults)
        self.assertEqual((result.outcome, result.error.details['from_generation_id']),
                         ('rollback_stale', newer.generation_id))
        self.assertNotIn(self.capture().generation_id, (older.generation_id, newer.generation_id))
        attempt, = self.state.rollbacks('2026Q4')
        self.assertEqual((attempt.from_generation_id, attempt.to_generation_id),
                         (newer.generation_id, older.generation_id))

    def test_rollback_cli_maps_named_outcomes_to_exit_codes(self):
        older, newer, _ = self.lineage_of_two()
        command = ('rollback', '--config', str(self.write_config()), '--state-dir', str(self.root),
                   '--quarter', '2026Q4', '--operator', 'Lowell Mason', '--reason', 'bad correction')
        code, message, _ = operator_cli(*command, '--from-generation', 'e' * 64,
                                        '--to-generation', older.generation_id)
        self.assertEqual((code, message['outcome'], message['rollback_ref']), (11, 'rollback_stale', None))
        code, message, events = operator_cli(*command, '--from-generation', newer.generation_id,
                                             '--to-generation', older.generation_id)
        self.assertEqual((code, message['outcome'], message['active']['generation_id']),
                         (0, 'success', older.generation_id))
        self.assertEqual(message['rollback_ref'], rollback_ref(QuarterRollback.from_mapping(message['rollback'])))
        self.assertEqual(json.loads(events.splitlines()[-1])['event'], 'quarter_rollback')
        code, message, _ = operator_cli(*command, '--from-generation', newer.generation_id,
                                        '--to-generation', older.generation_id)
        self.assertEqual((code, message['outcome']), (0, 'unchanged'))
        code, message, _ = operator_cli(*command, '--from-generation', older.generation_id,
                                        '--to-generation', newer.generation_id)
        self.assertEqual((code, message['outcome']), (2, 'rollback_refused'))


if __name__ == '__main__':
    unittest.main()
