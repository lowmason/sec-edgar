import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'packages/sec-edgar-ingest/tests'))
from support_workflow_evidence import EvidenceFixture
from datetime import date, datetime, timezone
from sec_edgar_ingest.models import canonical_json, to_mapping_value

class FixtureClockDiagnostic(unittest.TestCase):
    def test_retained_fixed_clock_revision_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            f = EvidenceFixture(Path(directory) / '.fixture-state')
            try:
                with f.h.leases.store._connection() as connection:
                    journal = connection.execute('SELECT value FROM sentinel_journal').fetchall()
                before = f.h.clock.now()
                parent = f.h.run('quarterly', date(2026, 10, 6), 'completion-new', refresh=True)
                evidence = {'wall_clock': datetime.now(timezone.utc).isoformat(),
                            'harness_clock_before': before.isoformat(),
                            'harness_clock_after': f.h.clock.now().isoformat(),
                            'journal_before': [row[0] for row in journal],
                            'failed_parent': parent.to_mapping()}
                path = Path('specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-4/fixture-clock-mismatch.json')
                path.write_bytes(canonical_json(to_mapping_value(evidence)))
                self.assertFalse(parent.discovery_complete)
                self.assertEqual(parent.members, ())
            finally:
                f.close()
