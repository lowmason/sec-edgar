"""Offline withdrawal approval requests and per-quarter generation lineage."""
from network_guard import install
install()

import unittest

from support_approval import GateFixture, operator_cli, row
from sec_edgar_ingest.etl.approval import approve
from sec_edgar_ingest.etl.history import quarter_history, withdrawal_candidates


class HistoryTests(GateFixture):
    def approve(self, candidate, revised):
        result = approve('2026Q4', candidate.manifest.generation_id, revised.snapshot.sha256, 'Lowell Mason',
                         self.objects, self.state)
        self.assertEqual(result.outcome, 'success')
        return result

    def test_history_walks_the_exact_lineage_with_approval_evidence(self):
        base, revised, candidate = self.gated()
        approved = self.approve(candidate, revised)
        returned = self.observation(rows=row() + row('Returned', number=2), seconds=2)
        self.assertEqual(self.publish(returned).outcome, 'published')
        history = quarter_history('2026Q4', self.objects, self.state)
        self.assertEqual([entry['gate'] for entry in history], ['clear', 'awaiting_approval', 'clear'])
        self.assertEqual([entry['generation_id'] for entry in history[1:]],
                         [candidate.manifest.generation_id, base.generation_id])
        self.assertEqual(history[0]['base_generation_id'], candidate.manifest.generation_id)
        self.assertEqual((history[0]['added'], history[1]['withdrawn'], history[2]['row_count']), (1, 1, 2))
        self.assertEqual(history[1]['approval'], approved.approval.to_mapping())
        self.assertEqual(history[1]['membership_sha256'], revised.snapshot.sha256)
        self.assertEqual((history[2]['approval'], history[2]['base_generation_id']), (None, None))
        self.assertTrue(history[1]['changes']['path'].endswith('/changes.parquet'))
        self.assertEqual(quarter_history('2026Q3', self.objects, self.state), ())

    def test_candidates_report_status_approval_and_withdrawn_rows(self):
        base, revised, candidate = self.gated()
        listed, = withdrawal_candidates(self.objects, self.state)
        self.assertEqual((listed['status'], listed['approved'], listed['quarterly_sha256']),
                         ('pending', False, revised.snapshot.sha256))
        self.assertEqual((listed['base_generation_id'], listed['candidate_ref']),
                         (base.generation_id, candidate.candidate_ref))
        self.assertEqual([item['archive_path'] for item in listed['withdrawn']],
                         ['edgar/data/123456/0000123456-26-000002.txt'])
        # seed_observation records no acquisition state; the CLI acceptance covers observed hashes.
        self.assertEqual((listed['latest_observed_sha256'], listed['latest_observed_at']), (None, None))
        self.approve(candidate, revised)
        listed, = withdrawal_candidates(self.objects, self.state)
        self.assertEqual((listed['status'], listed['approved']), ('active', True))
        self.publish(self.observation(rows=row() + row('Returned', number=2), seconds=2))
        listed, = withdrawal_candidates(self.objects, self.state)
        self.assertEqual(listed['status'], 'stale')

    def test_candidates_cli_prints_the_listing(self):
        _, _, candidate = self.gated()
        code, message, _ = operator_cli('candidates', '--config', str(self.write_config()),
                                        '--state-dir', str(self.root))
        self.assertEqual((code, message['outcome'], message['error']), (0, 'success', None))
        self.assertEqual([entry['generation_id'] for entry in message['candidates']],
                         [candidate.manifest.generation_id])
        self.assertEqual(operator_cli('candidates', '--config', str(self.root / 'missing.json'))[:2], (2, None))


if __name__ == '__main__':
    unittest.main()
