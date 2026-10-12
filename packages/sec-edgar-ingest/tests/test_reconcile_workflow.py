"""Offline reconcile workflow: shared runner, refreshed quarterly selection, corrections and gates."""
from network_guard import install
install()

import unittest
from datetime import datetime
from unittest.mock import patch

from support_approval import GateFixture, row
from support_etl import etl_context
from support_reconcile import A, B, C, X, Y, ReconcileFixture
from support_reconcile import sha
from sec_edgar_ingest.etl.approval import approve
from sec_edgar_ingest.etl.contracts import processing_key
from sec_edgar_ingest.etl.history import withdrawal_candidates
from sec_edgar_ingest.etl.manifest import approval_ref, read_manifest
from sec_edgar_ingest.etl.reader import capture_from_pointer
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.etl.transform import transform_member
from sec_edgar_ingest.models import parse_json
from sec_edgar_ingest.storage.contracts import Conflict
from sec_edgar_ingest.workflows.checked import Dispatcher
from sec_edgar_ingest.workflows.completion import accounts_for
from sec_edgar_ingest.workflows.results import _validate_selection
from sec_edgar_ingest.workflows.runner import source_revert_gaps


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
            for command in ('backfill', 'daily', 'reconcile'):
                with self.subTest(command=command):
                    code, message = h.invoke(command, run='flipped-' + command)
                    self.assertEqual((code, message['outcome']), (9, 'state_conflict'), h.calls[-1])
                    self.assertIn('refresh differs from its workflow command', h.calls[-1]['stderr'])



class SupersessionRuleTests(GateFixture):
    def test_accounts_for_exact_or_strictly_later_same_source_observation(self):
        first = self.observation(rows=row() + row(number=2))
        later = self.observation(rows=row(), seconds=1)
        # Strictly later, different bytes and the same versions: only the source differs from `later`.
        daily = self.observation(period='2026-10-02', kind='daily', rows=row(), seconds=1)
        # Same source and receipt time as `first` but different bytes: only the strict `>` rejects it.
        simultaneous = self.observation(rows=row('Other'))
        self.assertTrue(accounts_for(first, first))
        self.assertTrue(accounts_for(later, first))
        self.assertFalse(accounts_for(first, later))
        self.assertFalse(accounts_for(None, first))
        self.assertFalse(accounts_for(daily, first))
        self.assertFalse(accounts_for(simultaneous, first))
        settings, context = etl_context('fixture-index-parser-v2', command='publish')
        upgraded = transform_member(later.source, later.snapshot, context, settings, self.objects, self.state)
        self.assertFalse(accounts_for(upgraded, first))


class SupersessionWorkflowTests(ReconcileFixture):
    def test_superseded_gated_member_completes_on_the_following_reconcile(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        code, _, first = self.run_phase(h, 'reconcile', 'gate-1', (A,))
        self.assertEqual((code, first.counts['awaiting_approval_quarters']), (10, 1), h.calls[-1])
        # Both gated members stay pending in this run whatever their processing order.
        code, _, second = self.run_phase(h, 'reconcile', 'gate-2', (A, C))
        self.assertEqual((code, second.outcome), (10, 'awaiting_approval'), h.calls[-1])
        latest = next(candidate for candidate in self.candidates(h)
                      if candidate.manifest.membership_source.snapshot.sha256 == sha((A, C)))
        approved = approve('2026Q3', latest.manifest.generation_id, sha((A, C)), 'Lowell Mason',
                           h.objects, EtlState(h.store))
        self.assertEqual(approved.outcome, 'success')
        code, _, report = self.run_phase(h, 'reconcile', 'after-approval', (A, C))
        self.assertEqual((code, report.outcome), (0, 'unchanged'), h.calls[-1])
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'C'])

    def test_revert_to_older_bytes_is_reported_not_published(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        code, _, added = self.run_phase(h, 'reconcile', 'add', (A, B, C))
        self.assertEqual((code, added.outcome), (0, 'success'), h.calls[-1])
        active = EtlState(h.store).pointer('2026Q3')
        code, _, report = self.run_phase(h, 'reconcile', 'revert', (A, B))
        self.assertEqual((code, report.outcome), (3, 'incomplete'), h.calls[-1])
        gap, = [gap for gap in report.gaps if gap.code == 'source_reverted']
        self.assertTrue(gap.retryable)
        self.assertEqual((gap.details['quarter'], gap.details['observed_sha256'], gap.details['active_sha256']),
                         ('2026Q3', sha((A, B)), sha((A, B, C))))
        source_id = next(m.source.source_id for m in report.members if m.source.period == '2026Q3')
        self.assertEqual((gap.source_id, gap.details['generation_id']),
                         (source_id, capture_from_pointer(active).generation_id))
        first, held, observed = (datetime.fromisoformat(gap.details[name])
                                 for name in ('first_received_at', 'active_received_at', 'observed_at'))
        self.assertLess(first, held)
        self.assertLess(held, observed)
        self.assertEqual(EtlState(h.store).pointer('2026Q3'), active)
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B', 'C'])

    def test_gated_then_reverted_member_is_superseded_by_the_later_download(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        base = EtlState(h.store).pointer('2026Q3')
        code, _, gated = self.run_phase(h, 'reconcile', 'gate', (A,))
        self.assertEqual((code, gated.outcome), (10, 'awaiting_approval'), h.calls[-1])
        # A plain backfill binds its member to the gated bytes by reuse: pending too, with no download receipt.
        code, _, plain = self.run_phase(h, 'backfill', 'plain', (A,))
        self.assertEqual((code, plain.outcome), (10, 'awaiting_approval'), h.calls[-1])
        # The SEC reverts to the base bytes; that download completes during this run, so the gate still holds it.
        code, _, first = self.run_phase(h, 'reconcile', 'revert-1', (A, B))
        self.assertEqual((code, first.outcome), (10, 'awaiting_approval'), h.calls[-1])
        code, _, report = self.run_phase(h, 'reconcile', 'revert-2', (A, B))
        self.assertEqual((code, report.outcome, report.counts['awaiting_approval_quarters']), (0, 'unchanged', 0),
                         h.calls[-1])
        self.assertEqual(report.intent['unresolved_before'], 0)
        selection = parse_json(h.objects.read(report.intent['selection']['ref']))
        self.assertEqual(selection['format_version'], 'sec-workflow-selection-v2')
        held = sorted({member.member_id for member in (*gated.members, *plain.members)
                       if member.outcome == 'awaiting_approval'})
        self.assertEqual(len(held), 2)  # the gated download and the reuse-bound backfill member
        # Same period and source, so the frozen order reduces to member id.
        self.assertEqual([entry['member']['member_id'] for entry in selection['superseded']], held)
        for entry in selection['superseded']:
            self.assertIn(entry['by']['member_id'], [member.member_id for member in first.members])
            self.assertLess(datetime.fromisoformat(entry['downloaded_at']),
                            datetime.fromisoformat(entry['by_downloaded_at']))
        # Both are dated by the gated bytes' newest download, the reuse-bound member having none of its own.
        self.assertEqual(len({entry['downloaded_at'] for entry in selection['superseded']}), 1)
        self.assertFalse(set(held) & {member.member_id for member in report.members})
        entry = selection['superseded'][0]
        self.assertEqual(EtlState(h.store).pointer('2026Q3'), base)
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B'])
        # Forgeries: a superseding download no later than the pending one, and a pending time never recorded.
        for label, forgery in (('not later', {'by_downloaded_at': entry['downloaded_at']}),
                               ('unrecorded', {'downloaded_at': '2000-01-01T00:00:00+00:00'})):
            forged = {**selection, 'superseded': [{**entry, **forgery}, *selection['superseded'][1:]]}
            with self.subTest(label), self.assertRaisesRegex(Conflict, 'lacks its later completed download'):
                _validate_selection(forged, report.context, selection['invocation'], h.store, h.objects)

    def test_a_retry_keeps_its_own_discovered_member_even_when_superseded(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        self.assertEqual(self.run_phase(h, 'reconcile', 'gate', (A,))[0], 10, h.calls[-1])
        self.assertEqual(self.run_phase(h, 'reconcile', 'revert', (A, B))[0], 10, h.calls[-1])
        # A retry of the gated run reuses its discovery session, so it discovers the same gated member again;
        # dropping it would leave a discovered projection unselected and fail every retry with exit 9.
        h.pack = self.pack((A,), (X, Y))
        code, message = h.invoke('reconcile', run='gate', attempt='b')
        self.assertEqual((code, message['outcome']), (10, 'awaiting_approval'), h.calls[-1])

    def test_a_corrupt_pending_member_is_not_superseded(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        code, _, gated = self.run_phase(h, 'reconcile', 'gate', (A,))
        self.assertEqual(code, 10, h.calls[-1])
        self.assertEqual(self.run_phase(h, 'reconcile', 'revert-1', (A, B))[0], 10, h.calls[-1])
        held, = [member for member in gated.members if member.outcome == 'awaiting_approval']
        # Corrupt the gated bytes' Processing identity: evaluate_member now reports state_conflict.
        key = processing_key(held.source.source_id, sha((A,)), held.parser_version, held.schema_version)
        row = h.store.get('Processing', key)
        h.store.replace('Processing', key, {**row.value, 'processing_key': 'f' * 64}, row.version)
        code, message = h.invoke('reconcile', run='revert-2')
        self.assertNotEqual(code, 0, h.calls[-1])
        selection = parse_json(h.objects.read('runs/sec/revert-2/reconcile/a/selection.json'))
        self.assertNotIn(held.member_id, [entry['member']['member_id'] for entry in selection['superseded']])

    def test_a_candidate_whose_source_moved_on_is_listed_superseded_and_refused(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        self.assertEqual(self.run_phase(h, 'reconcile', 'gate', (A,))[0], 10, h.calls[-1])
        listed, = withdrawal_candidates(h.objects, EtlState(h.store))
        self.assertEqual((listed['status'], listed['latest_observed_sha256']), ('pending', sha((A,))))
        self.assertEqual(self.run_phase(h, 'reconcile', 'revert', (A, B))[0], 10, h.calls[-1])
        listed, = withdrawal_candidates(h.objects, EtlState(h.store))
        self.assertEqual((listed['status'], listed['quarterly_sha256'], listed['latest_observed_sha256']),
                         ('superseded', sha((A,)), sha((A, B))))
        before = EtlState(h.store).pointer('2026Q3')
        result = approve('2026Q3', listed['generation_id'], sha((A,)), 'Lowell Mason', h.objects, EtlState(h.store))
        self.assertEqual((result.outcome, result.error.details['latest_observed_sha256']),
                         ('approval_stale', sha((A, B))))
        self.assertEqual(EtlState(h.store).pointer('2026Q3'), before)
        self.assertIsNone(EtlState(h.store).approval(listed['generation_id']))
        with self.assertRaises(FileNotFoundError):
            h.objects.read(approval_ref('2026Q3', listed['generation_id']))
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B'])

    def test_revert_detection_reads_the_active_generation_through_full_validation(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        code, _, added = self.run_phase(h, 'reconcile', 'add', (A, B, C))
        self.assertEqual(code, 0, h.calls[-1])
        capture = capture_from_pointer(EtlState(h.store).pointer('2026Q3'))
        data = next(ref for ref in read_manifest(capture, h.objects).files if ref.role != 'changes')
        with open(h.objects.directory / data.path, 'ab') as handle:
            handle.write(b'x')
        with self.assertRaises(Conflict):
            source_revert_gaps(added.members, h.store, h.objects)


if __name__ == '__main__':
    unittest.main()
