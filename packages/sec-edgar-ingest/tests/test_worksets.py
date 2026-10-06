import copy
import importlib
import importlib.util
import json
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from support import fixture_context, fixture_settings, fixture_source, fixture_workset


class WorksetTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("sec_edgar_ingest.worksets"),
                             "Immutable workset identity must be enforced")
        self.worksets = importlib.import_module("sec_edgar_ingest.worksets")
        self.models = importlib.import_module("sec_edgar_ingest.models")

    def snapshot(self, source, digest="b" * 64):
        return self.models.Snapshot(source.source_id, digest,
                                    f"raw/{source.source_id}/{digest}/master.zip", 12,
                                    fixture_context().started_at, {"etag": "abc"}, "zip", "sec-quarterly-envelope-v1")

    def tamper(self, workset, edit, decoder=None):
        value = json.loads(self.worksets.encode_workset(workset))
        edit(value)
        value["workset_id"] = self.worksets.workset_digest({key: item for key, item in value.items() if key != "workset_id"})
        with self.assertRaises(ValueError):
            (decoder or self.worksets.decode_source_workset)(self.worksets.canonical_json(value))

    def test_member_order_does_not_change_workset_identity(self):
        a, b = fixture_source("2015Q1"), fixture_source("2015Q2")
        first = fixture_workset((a, b))
        second = fixture_workset((b, a))
        self.assertEqual(first.workset_id, second.workset_id)
        self.assertEqual(self.worksets.decode_source_workset(self.worksets.encode_workset(first)), first)
        changed = replace(first, pinned_end_quarter="2026Q3")
        with self.assertRaisesRegex(ValueError, "identity"):
            self.worksets.decode_source_workset(self.worksets.encode_workset(changed))

    def test_changed_context_or_content_changes_identity(self):
        source = fixture_source()
        first = fixture_workset((source,))
        changed = self.worksets.make_source_workset(replace(first.context, execution_id="different"),
                  first.pinned_end_quarter, first.discovery_id, first.members, first.directories, first.overlap_from)
        self.assertNotEqual(first.workset_id, changed.workset_id)
        refreshed = self.worksets.make_source_workset(replace(first.context, command="refresh"),
                  first.pinned_end_quarter, first.discovery_id, first.members, first.directories, first.overlap_from)
        self.assertEqual(refreshed.acquisition_mode, "refresh")
        self.assertNotEqual(first.workset_id, refreshed.workset_id)
        one = self.worksets.make_snapshot_workset(first, (self.snapshot(source),))
        two = self.worksets.make_snapshot_workset(first, (self.snapshot(source, "c" * 64),))
        self.assertNotEqual(one.workset_id, two.workset_id)
        self.assertEqual(self.worksets.decode_snapshot_workset(self.worksets.encode_workset(one)), one)

    def test_detached_serializers_and_deep_immutability(self):
        source = fixture_source()
        workset = fixture_workset((source,))
        context_mapping = workset.context.to_mapping()
        context_mapping["effective_config"]["sec"]["user_agent"] = "mutated"
        self.assertEqual(workset.context.effective_config["sec"]["requests_per_second"], 3)
        with self.assertRaises(TypeError):
            workset.context.effective_config["sec"]["requests_per_second"] = 9
        with self.assertRaises(FrozenInstanceError):
            source.period = "changed"
        error_input = {"nested": {"items": ["first"]}}
        error = self.models.Error("guard", "rejected", False, source.source_id, error_input)
        error_input["nested"]["items"].append("second")
        self.assertEqual(error.details["nested"]["items"], ("first",))
        with self.assertRaises(TypeError):
            error.details["nested"]["new"] = True
        exported = error.to_mapping()
        exported["details"]["nested"]["items"].append("third")
        self.assertEqual(error.details["nested"]["items"], ("first",))
        snapshot = self.snapshot(source)
        with self.assertRaises(TypeError):
            snapshot.validators["etag"] = "changed"

    def test_duplicate_sources_and_directory_identity_are_refused(self):
        source = fixture_source()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            fixture_workset((source, source))
        workset = fixture_workset((source,))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.worksets.make_source_workset(workset.context, workset.pinned_end_quarter, workset.discovery_id,
                                             workset.members, workset.directories * 2, workset.overlap_from)
        self.tamper(workset, lambda value: value["directories"][0].update(source_ids=[]))
        self.tamper(workset, lambda value: value["members"][0].update(source_id="d" * 64))

    def test_empty_complete_requires_successful_directory_evidence(self):
        empty = fixture_workset(())
        self.assertTrue(empty.discovery_complete)
        self.assertEqual(self.worksets.decode_source_workset(self.worksets.encode_workset(empty)), empty)
        failed = fixture_workset((), discovery_complete=False)
        self.assertFalse(failed.discovery_complete)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.worksets.make_snapshot_workset(failed, ())
        self.tamper(empty, lambda value: value.update(directories=[]))
        self.tamper(failed, lambda value: value.update(discovery_complete=True))

    def test_decoder_rejects_versions_unknown_fields_timestamps_and_hashes(self):
        workset = fixture_workset((fixture_source(),))
        cases = [
            ("version", lambda value: value.update(format_version="sec-acquisition-v2")),
            ("unknown", lambda value: value.update(latest="current")),
            ("naive UTC", lambda value: value["context"].update(started_at="2026-10-06T00:00:00")),
            ("offset UTC", lambda value: value["context"].update(started_at="2026-10-06T01:00:00+01:00")),
            ("schema", lambda value: value["context"].update(schema_version="sec-index-v2")),
            ("config SHA", lambda value: value["context"].update(config_sha256="f" * 64)),
            ("nonhex", lambda value: value["directories"][0].update(listing_sha256="Z" * 64)),
            ("unpinned", lambda value: value.update(pinned_end_quarter="open")),
            ("future", lambda value: value.update(pinned_end_quarter="2027Q1")),
            ("mutable config", lambda value: value["context"]["effective_config"]["sec"].update(requests_per_second=8)),
        ]
        for name, edit in cases:
            with self.subTest(name=name):
                self.tamper(workset, edit)
        body = self.worksets.encode_workset(workset)
        with self.assertRaises(ValueError):
            self.worksets.decode_source_workset(body.replace(b'"format_version":', b'"format_version":"sec-acquisition-v1","format_version":'))
        with self.assertRaises(ValueError):
            self.worksets.decode_source_workset(b'{"value":NaN}')

    def test_snapshot_requires_exact_members_and_immutable_raw_reference(self):
        a, b = fixture_source("2015Q1"), fixture_source("2015Q2")
        source = fixture_workset((a, b))
        with self.assertRaisesRegex(ValueError, "member"):
            self.worksets.make_snapshot_workset(source, (self.snapshot(a),))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.worksets.make_snapshot_workset(source, (self.snapshot(a), self.snapshot(a)))
        with self.assertRaises(ValueError):
            self.snapshot(a, "not-a-hash")
        with self.assertRaises(ValueError):
            replace(self.snapshot(a), raw_path="raw/latest/master.zip")
        with self.assertRaises(ValueError):
            replace(self.snapshot(a), raw_path="../raw/" + "b" * 64)
        with self.assertRaises(ValueError):
            replace(self.snapshot(a), representation="idx")
        snapshot = self.worksets.make_snapshot_workset(source, (self.snapshot(b), self.snapshot(a)))
        self.assertEqual(snapshot.source_workset_id, source.workset_id)
        self.assertEqual(snapshot.directories, source.directories)
        self.assertEqual(snapshot.overlap_from, source.overlap_from)
        self.assertEqual(snapshot.pinned_end_quarter, source.pinned_end_quarter)
        self.tamper(snapshot, lambda value: value["snapshots"].pop(), self.worksets.decode_snapshot_workset)
        self.tamper(snapshot, lambda value: value["snapshots"][0].update(raw_path="raw/latest"), self.worksets.decode_snapshot_workset)

    def test_common_records_have_complete_detached_mapping_round_trips(self):
        context = fixture_context()
        source = fixture_source()
        error = self.models.Error("failure", "details", True, source.source_id, {"nested": [1]})
        records = [
            source, context, error, self.snapshot(source),
            self.models.Binding("a" * 64, source.source_id, "b" * 64),
            self.models.Versioned({"nested": {"list": [1]}}, 'W/"actual-etag"'),
            self.models.QueueTicket("ticket", "owner", "daily", context.started_at, context.deadline),
            self.models.Permit("owner", 1, "request", context.started_at, context.deadline,
                               context.deadline + timedelta(seconds=2), 10., 100.),
            self.models.BodyReceipt(source.canonical_url, 200, {"ETag": "abc"}, Path("staging/body"),
                                    context.started_at, 12, "b" * 64, True, None),
            self.models.CommandResult(context, "incomplete", None, None, 1, 0, 0, 1, 0, 0,
                                      (error,), context.started_at, context.deadline),
        ]
        records.append(self.models.ValidatedBody(records[-2], "zip", "sec-quarterly-envelope-v1", 20))
        for record in records:
            with self.subTest(record=type(record).__name__):
                self.assertEqual(type(record).from_mapping(record.to_mapping()), record)
        versioned = records[5]
        with self.assertRaises(TypeError):
            versioned.value["nested"]["list"] = ()

    def test_common_records_reject_mutable_wrong_typed_fields(self):
        context = fixture_context()
        constructors = [
            ("context mapping", lambda: replace(fixture_workset(()), context=context.to_mapping())),
            ("mutable members", lambda: replace(fixture_workset(()), members=({"source_id": "a" * 64},))),
            ("mutable errors", lambda: self.models.CommandResult(context, "failure", None, None,
                                     0, 0, 0, 0, 1, 0, ({"code": "bad"},), context.started_at, context.deadline)),
            ("wrong receipt", lambda: self.models.ValidatedBody({"complete": True}, "zip", "sec-quarterly-envelope-v1", 1)),
        ]
        for name, constructor in constructors:
            with self.subTest(name=name):
                try:
                    constructor()
                except Exception as error:
                    self.assertIsInstance(error, ValueError, "invalid typed record must report a contract error")
                else:
                    self.fail("invalid typed record accepted")
        workset = fixture_workset((fixture_source(),))
        self.assertEqual(copy.deepcopy(workset), workset)

    def test_version_and_directory_content_are_part_of_identity(self):
        first = fixture_workset((fixture_source(),))
        changed_directory = replace(first.directories[0], listing_sha256="d" * 64)
        second = self.worksets.make_source_workset(first.context, first.pinned_end_quarter, first.discovery_id,
                    first.members, (changed_directory,), first.overlap_from)
        self.assertNotEqual(first.workset_id, second.workset_id)
        settings = fixture_settings(etl={"parser_version": "fixture-envelope-v2"})
        context = replace(first.context, parser_version=settings.etl.parser_version,
                          config_sha256=settings.config_sha256)
        config = importlib.import_module("sec_edgar_ingest.config")
        context = config.pin_context(settings, context, context.started_at.date())[0]
        third = self.worksets.make_source_workset(context, first.pinned_end_quarter, first.discovery_id,
                                                 first.members, first.directories, first.overlap_from)
        self.assertNotEqual(first.workset_id, third.workset_id)

    def test_body_receipt_and_snapshot_envelopes_are_explicit(self):
        source = fixture_source()
        snapshot = self.snapshot(source)
        self.assertEqual(snapshot.envelope_version, "sec-quarterly-envelope-v1")
        for name, changes in [
            ("unknown envelope", {"envelope_version": "latest"}),
            ("wrong representation envelope", {"envelope_version": "sec-daily-envelope-v1"}),
            ("wrong timestamp", {"received_at": datetime(2026, 10, 6)}),
        ]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                replace(snapshot, **changes)
        workset = fixture_workset((source,))
        with self.assertRaises(ValueError):
            self.worksets.decode_source_workset(self.worksets.encode_workset(workset).decode().encode("utf-16"))
