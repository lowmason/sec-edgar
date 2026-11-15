"""Stage 2a1 spec §5 item 7 (H7), with two real releases: the 2a release and the current code.

Stage 2a1 changes no format. The current release continues work that the 2a release left pending,
and the 2a release continues work that the current release left pending.
"""
from network_guard import install
install()

import os
import tempfile
import unittest
from pathlib import Path


class TwoReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from support_release import TWO_A_REVISION, origin_release, proof_releases
        from sec_edgar_ingest.runtime import preflight
        project = Path(__file__).resolve().parents[3]
        cache = project / 'releases/artifact-cache'
        # P9: the gate builds the 2a application from its revision. The evidence run sets
        # SEC_LOCAL_2A_RELEASE to the installed release.json of e49d3ba8… instead.
        installed = os.environ.get('SEC_LOCAL_2A_RELEASE')
        cls.two_a = preflight(Path(installed)) if installed else origin_release(project, cache, revision=TWO_A_REVISION)
        cls.current = proof_releases(project, cache)[1]

    def assert_continues(self, a, b):
        """`upgrade_sequence` with `a` leaving work pending and `b`, the installed release, continuing it."""
        from workflow_proof import upgrade_sequence
        with tempfile.TemporaryDirectory() as directory:
            report = upgrade_sequence(Path(directory), a.directory / 'release.json', b.directory / 'release.json')
            self.assertEqual(report['exit'], 0)
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
                self.assertEqual(selected, expected, 'upgrade must exercise actual 2a-origin and current processes')
                for record in records:
                    guard = record['checkout_guard']
                    self.assertEqual(guard['pid'], record['pid'])
                    self.assertFalse(guard['application_imported'])
                    self.assertEqual(guard['denied'], [True] * 6)
                    self.assertEqual(guard['policy']['releases'], case['release_directories'])

    def test_new_release_continues_2a_origin_pending_work(self):
        """H7: the current release, as B, continues work that the 2a release left pending."""
        self.assert_continues(self.two_a, self.current)

    def test_2a_release_continues_new_origin_pending_work(self):
        """H7: the 2a release, as B, continues work that the current release left pending."""
        self.assert_continues(self.current, self.two_a)


if __name__ == '__main__':
    unittest.main()
