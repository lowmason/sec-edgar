"""Offline reconcile workflow: shared runner, refreshed quarterly selection, corrections and gates."""
from network_guard import install
install()

import unittest
from unittest.mock import patch

from support_reconcile import A, B, C, X, ReconcileFixture
from sec_edgar_ingest.etl.manifest import read_manifest
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.workflows.checked import Dispatcher


class ReconcileWorkflowTests(ReconcileFixture):
    def baseline(self):
        h = self.harness((A, B))
        code, _, report = self.run_phase(h, 'backfill', 'base')
        self.assertEqual((code, report.outcome), (0, 'success'), h.calls[-1])
        return h, report

    def test_unchanged_reconcile_refreshes_through_the_shared_runner(self):
        h, baseline = self.baseline()
        pointers = {quarter: EtlState(h.store).pointer(quarter) for quarter in ('2026Q3', '2026Q4')}
        code, message, report = self.run_phase(h, 'reconcile', 'same', (A, B))
        self.assertEqual((code, report.outcome), (0, 'unchanged'), h.calls[-1])
        self.assertEqual(message['result_ref'], 'runs/sec/same/reconcile/a/result.json')
        self.assertEqual((report.context.command, report.context.priority), ('reconcile', 'reconciliation'))
        self.assertEqual(report.requested_quarters, ('2026Q3', '2026Q4'))
        self.assertEqual((report.counts['published_quarters'], report.counts['unchanged_quarters']), (0, 2))
        calls = report.to_mapping()['intent']['child_calls']
        discovery = calls[0]
        self.assertEqual((discovery['intent']['mode'], discovery['intent']['refresh'],
                          discovery['intent']['discovery_id'], discovery['context']['priority']),
                         ('quarterly', True, 'workflow-reconcile-same', 'backfill'))
        self.assertEqual({call['context']['command'] for call in calls},
                         {'discover', 'collect', 'transform', 'publish'})
        self.assertIs(baseline.to_mapping()['intent']['child_calls'][0]['intent']['refresh'], False)
        self.assertEqual({quarter: EtlState(h.store).pointer(quarter) for quarter in pointers}, pointers)
        with self.assertRaises(SystemExit):
            h.invoke('reconcile', ('--refresh',), run='public-refresh')

    def test_corrections_update_and_add_while_open_quarter_absence_is_retained(self):
        h, _ = self.baseline()
        revised = ('123456', 'A Revised', *A[2:])
        code, _, report = self.run_phase(h, 'reconcile', 'fix', (revised, B, C), (X,))
        self.assertEqual((code, report.outcome), (0, 'success'), h.calls[-1])
        closed = read_manifest(h.capture('2026Q3')[0], h.objects)
        self.assertEqual((closed.updated, closed.added, closed.withdrawn, closed.gate), (1, 1, 0, 'clear'))
        self.assertEqual(self.names(h, '2026Q3'), ['A Revised', 'B', 'C'])
        opened = read_manifest(h.capture('2026Q4')[0], h.objects)
        self.assertEqual((opened.quarter_mode, opened.unresolved_absence, opened.withdrawn), ('open', 1, 0))
        self.assertEqual(self.names(h, '2026Q4'), ['X', 'Y'])

    def test_closed_withdrawal_beside_an_unchanged_quarter_awaits_approval(self):
        h, _ = self.baseline()
        before = EtlState(h.store).pointer('2026Q3')
        code, _, report = self.run_phase(h, 'reconcile', 'gate', (A,))
        self.assertEqual((code, report.outcome), (10, 'awaiting_approval'), h.calls[-1])
        self.assertEqual((report.counts['awaiting_approval_quarters'], report.counts['pending_sources'],
                          report.counts['complete_sources']), (1, 1, 1))
        self.assertEqual(EtlState(h.store).pointer('2026Q3'), before)
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B'])

    def test_invalid_correction_keeps_the_prior_generation_and_names_its_quarter(self):
        h, _ = self.baseline()
        before = EtlState(h.store).pointer('2026Q3')
        conflict = ('123456', 'Conflict', *A[2:])
        code, _, report = self.run_phase(h, 'reconcile', 'invalid', (A, conflict, B))
        self.assertEqual((code, report.outcome), (3, 'incomplete'), h.calls[-1])
        self.assertEqual(report.counts['quarantined_sources'], 1)
        self.assertEqual([member.source.period for member in report.members if member.quarantined], ['2026Q3'])
        self.assertEqual(EtlState(h.store).pointer('2026Q3'), before)

    def test_selection_requires_refresh_exactly_for_reconcile(self):
        execute = Dispatcher.execute

        def flipped(dispatcher, command, step_id, settings, flags):
            if command == 'discover':
                flags = (tuple(flag for flag in flags if flag != '--refresh') if '--refresh' in flags
                         else (*flags, '--refresh'))
            return execute(dispatcher, command, step_id, settings, flags)

        h = self.harness((A, B))
        with patch.object(Dispatcher, 'execute', flipped):
            for command in ('backfill', 'reconcile'):
                with self.subTest(command=command):
                    code, message = h.invoke(command, run='flipped-' + command)
                    self.assertEqual((code, message['outcome']), (9, 'state_conflict'), h.calls[-1])
                    self.assertIn('refresh differs from its workflow command', h.calls[-1]['stderr'])


if __name__ == '__main__':
    unittest.main()
