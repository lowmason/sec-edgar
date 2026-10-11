"""Offline withdrawal approval evidence, reader acceptance and the approve operation."""
from network_guard import install
install()

import hashlib
import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from support_approval import GateFixture, operator_cli, row
from sec_edgar_ingest.etl.contracts import Candidate, WithdrawalApproval
from sec_edgar_ingest.etl.manifest import approval_for, approval_ref, read_approval, read_manifest
from sec_edgar_ingest.etl.publication import pointer_value, repair_publication
from sec_edgar_ingest.models import canonical_json
from sec_edgar_ingest.storage.contracts import Conflict, blob_address, table_for

APPROVED_AT = datetime(2027, 1, 2, tzinfo=timezone.utc)


class ApprovalEvidenceTests(GateFixture):
    def test_approval_binds_the_exact_candidate_and_validates_its_fields(self):
        base, revised, candidate = self.gated()
        approval = approval_for(candidate, 'Lowell Mason', APPROVED_AT)
        manifest = candidate.manifest
        self.assertEqual((approval.quarter, approval.generation_id, approval.base_generation_id),
                         ('2026Q4', manifest.generation_id, base.generation_id))
        self.assertEqual(approval.quarterly_sha256, revised.snapshot.sha256)
        self.assertEqual(approval.gate_sha256,
                         hashlib.sha256(self.objects.read(candidate.candidate_ref)).hexdigest())
        self.assertEqual((approval.manifest_ref, approval.format_version),
                         (candidate.manifest_ref, 'sec-withdrawal-approval-v1'))
        self.assertEqual(WithdrawalApproval.from_mapping(approval.to_mapping()), approval)
        ref = approval_ref('2026Q4', manifest.generation_id)
        self.assertEqual(ref, 'approvals/sec/filing_index/year=2026/quarter=4/generation='
                         + manifest.generation_id + '/approval.json')
        self.assertEqual(blob_address(ref), ('approvals', ref.removeprefix('approvals/')))
        for approver in ('', '   ', 'two\nlines', 'tab\there', 'x' * 257, 'zero​width'):
            with self.subTest(approver=approver), self.assertRaises(ValueError):
                approval_for(candidate, approver, APPROVED_AT)
        self.assertEqual(approval_for(candidate, 'x' * 256, APPROVED_AT).approver, 'x' * 256)
        with self.assertRaises(ValueError):
            approval_for(candidate, 'Lowell Mason', APPROVED_AT.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            replace(approval, format_version='sec-withdrawal-approval-v0')
        clear = Candidate(read_manifest(base, self.objects), base.manifest_ref, base.manifest_sha256,
                          base.manifest_bytes, None)
        with self.assertRaisesRegex(ValueError, 'exact awaiting-approval candidate'):
            approval_for(clear, 'Lowell Mason', APPROVED_AT)

    def test_reader_accepts_an_awaiting_approval_pointer_only_with_its_exact_approval(self):
        _, _, candidate = self.gated()
        self.state.commit_pointer('2026Q4', pointer_value(candidate), self.state.pointer('2026Q4'))
        with self.assertRaisesRegex(ValueError, 'awaiting-approval'):
            self.capture()
        with self.assertRaisesRegex(ValueError, 'awaiting-approval'):
            repair_publication('2026Q4', self.objects, self.state)
        approval = approval_for(candidate, 'Lowell Mason', APPROVED_AT)
        ref = approval_ref('2026Q4', candidate.manifest.generation_id)
        self.objects.put_once(ref, canonical_json(approval.to_mapping()))
        self.assertEqual(self.rows(), [(1, 'Example')])
        repair_publication('2026Q4', self.objects, self.state)
        self.assertEqual(read_approval(candidate, self.objects), approval)
        path = self.object_path(ref)
        path.write_bytes(json.dumps(approval.to_mapping(), indent=1).encode())
        with self.assertRaisesRegex(ValueError, 'canonical JSON'):
            self.capture()
        path.write_bytes(canonical_json(replace(approval, quarterly_sha256='0' * 64).to_mapping()))
        with self.assertRaisesRegex(ValueError, 'not bound'):
            self.capture()

    def test_approval_index_is_immutable_and_routes_to_the_approvals_table(self):
        _, _, candidate = self.gated()
        approval = approval_for(candidate, 'Lowell Mason', APPROVED_AT)
        self.assertIsNone(self.state.approval(approval.generation_id))
        self.state.record_approval(approval)
        self.state.record_approval(approval)
        self.assertEqual(self.state.approval(approval.generation_id), approval)
        with self.assertRaises(Conflict):
            self.state.record_approval(replace(approval, approver='Someone Else'))
        self.assertEqual(table_for('WithdrawalApproval'), 'Approvals')


if __name__ == '__main__':
    unittest.main()
