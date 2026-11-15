"""Stage 2a1 pre-dispatch cost: record type-hints cache (H6), per-phase selection checks (H2, H3), the
source filter in reuse (H5), and `select_work`'s use of the checks (H1, H2, H4)."""
import contextlib
import dataclasses
import importlib
import inspect
import json
import pkgutil
import shutil
import sqlite3
import sys
import tempfile
import typing
import unittest
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import sec_edgar_ingest
from sec_edgar_ingest import models
from sec_edgar_ingest.etl.contracts import decode_transformed
from sec_edgar_ingest.models import (Binding, CommandResult, Error, RunContext, Source, canonical_json, error_text,
                                     record_type_hints)
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.storage.contracts import Conflict, deployment_binding, identity, table_for
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.workflows import completion, legacy, members, provenance, runner, selection_checks
from sec_edgar_ingest.workflows.checked import Dispatcher
from sec_edgar_ingest.workflows.contracts import LOCAL_CONTRACT
from sec_edgar_ingest.workflows.members import WorkflowMembers
from sec_edgar_ingest.workflows.provenance import read_member, transfer_binding
from sec_edgar_ingest.workflows.results import freeze_selection, write_workflow_result
from sec_edgar_ingest.workflows.selection_checks import SelectionChecks
from support import fixture_context, fixture_snapshot, fixture_source
from support_process import checked_dispatcher, checked_fault
import support_selection
from support_selection import (DISCOVERY_FAILURE, SCENARIOS, refusal_twice, registered_store, scenario,
                               select_twice, workflow_start)
# A module object, so that the loader does not collect its test cases here.
import test_workflow_drain as drain
from support_workflow_evidence import EvidenceFixture, quarterly_bytes
from support_workflows import CommandHarness, simple_pack


def package_record_types() -> set[type]:
    """Every dataclass defined at module level anywhere under sec_edgar_ingest."""
    found = set()
    for info in pkgutil.walk_packages(sec_edgar_ingest.__path__, prefix="sec_edgar_ingest."):
        module = importlib.import_module(info.name)
        for value in vars(module).values():
            if (isinstance(value, type) and dataclasses.is_dataclass(value)
                    and value.__module__ == module.__name__):
                found.add(value)
    return found


class TypeHintsCacheTests(unittest.TestCase):
    def test_cached_hints_equal_get_type_hints_for_every_record_type(self):
        record_types = package_record_types()
        self.assertGreater(len(record_types), 30)
        for record_type in sorted(record_types, key=lambda item: (item.__module__, item.__qualname__)):
            with self.subTest(record_type=f"{record_type.__module__}.{record_type.__qualname__}"):
                self.assertEqual(dict(record_type_hints(record_type)), typing.get_type_hints(record_type))

    def test_cached_hints_cannot_be_changed(self):
        with self.assertRaises(TypeError):
            record_type_hints(Source)["x"] = str

    def test_hints_are_computed_once_per_type(self):
        mapping = fixture_source().to_mapping()
        record_type_hints.cache_clear()
        with mock.patch.object(models, "get_type_hints", wraps=models.get_type_hints) as counted:
            for _ in range(3):
                Source.from_mapping(mapping)
        self.assertEqual(counted.call_args_list, [mock.call(Source)])

    def test_refusal_text_is_unchanged_after_the_cache_is_warm(self):
        context = fixture_context()
        wrong_type = context.to_mapping()
        wrong_type["run_id"] = 7
        error = Error(code="fixture", message="fixture", retryable=False, source_id=None, details={})
        nested_error = error.to_mapping()
        nested_error["unexpected"] = True
        result = CommandResult(
            format_version="sec-local-command-result-v1", context=context, outcome="success",
            source_workset_ref=None, snapshot_workset_ref=None, discovered=0, downloaded=0,
            unchanged=0, pending=0, failed=0, quarantined=0, gaps=(error,),
            started_at=context.started_at, ended_at=context.started_at)
        nested = result.to_mapping()
        nested["gaps"] = [nested_error]
        record_type_hints.cache_clear()

        def refusal(record_type, value):
            with self.assertRaises(ValueError) as caught:
                record_type.from_mapping(value)
            return str(caught.exception)

        cold = (refusal(RunContext, wrong_type), refusal(CommandResult, nested))
        warm = (refusal(RunContext, wrong_type), refusal(CommandResult, nested))
        self.assertEqual(cold, warm)
        self.assertEqual(cold[0], "run_id has an invalid type")
        self.assertIn("Error unknown keys: ['unexpected']", cold[1])

    def test_nested_record_refusal_is_unchanged_once_its_own_hints_are_cached(self):
        context = fixture_context()
        error = Error(code="fixture", message="fixture", retryable=False, source_id=None, details={})
        wrong_type = error.to_mapping()
        wrong_type["retryable"] = "no"
        result = CommandResult(
            format_version="sec-local-command-result-v1", context=context, outcome="success",
            source_workset_ref=None, snapshot_workset_ref=None, discovered=0, downloaded=0,
            unchanged=0, pending=0, failed=0, quarantined=0, gaps=(error,),
            started_at=context.started_at, ended_at=context.started_at)
        nested = result.to_mapping()
        nested["gaps"] = [wrong_type]
        record_type_hints.cache_clear()

        def refusal():
            with self.assertRaises(ValueError) as caught:
                CommandResult.from_mapping(nested)
            return str(caught.exception)

        with mock.patch.object(models, "get_type_hints", wraps=models.get_type_hints) as counted:
            cold = refusal()
            warm = refusal()
        self.assertEqual(cold, warm)
        self.assertEqual(cold, "retryable has an invalid type")
        self.assertEqual(counted.call_args_list.count(mock.call(Error)), 1)


class Crash(BaseException):
    pass


def fresh_publish_calls(store, objects):
    """Today's publish-call authority, with each call's decoded transformed input."""
    return tuple((call, decode_transformed(objects.read(call["input_ref"])))
                 for call in completion._publish_calls(store, objects))


def fails_once(real):
    """A computation that raises Conflict on its first call and then runs the real one."""
    failures = [Conflict("fixture: uncertain authority")]

    def compute(*args):
        if failures:
            raise failures.pop()
        return real(*args)
    return compute


class SelectionChecksTests(unittest.TestCase):
    """Spec §4.1, §4.3 and §5 item 3: kept checks for one phase of one selection (H2, H3, H4)."""

    def harness(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        h = CommandHarness(root, simple_pack(root / "pack"))
        self.addCleanup(h.close)
        return h

    def discovered(self):
        """A store with one discovered parent and no publish call."""
        h = self.harness()
        code, message = h.invoke("discover", ("--mode", "daily", "--discovery-id", "selection-checks"))
        self.assertEqual(code, 0, message)
        return h, message["source_workset_ref"]

    def backfilled(self):
        """A store with checked publish calls and registered members, from one backfill workflow."""
        h = self.harness()
        code, message = h.invoke("backfill", run="r1", attempt="a1")
        self.assertEqual(code, 0, message)
        values = tuple(row.to_mapping()["value"] for row in h.store.scan("WorkflowMember", {}))
        self.assertTrue(values)
        return h, values

    def test_each_listed_function_takes_an_optional_keyword_only_checks(self):
        """The `checks` keyword defaults to None, and the signature still resolves for `mock.create_autospec`."""
        for function in (completion._obligations, completion.outstanding_repairs, completion.evaluate_member,
                         completion.capture_member_provenance, completion.capture_parent_provenance,
                         provenance.read_member, provenance.project_member, provenance.transfer_binding,
                         members.WorkflowMembers.inventory, members.WorkflowMembers.completed,
                         legacy.reconstruct_parent, legacy.bootstrap_legacy):
            with self.subTest(function.__qualname__):
                checks = inspect.signature(function).parameters["checks"]
                self.assertEqual((checks.kind, checks.default), (inspect.Parameter.KEYWORD_ONLY, None))
                mock.create_autospec(function)

    def test_publish_calls_are_kept_until_renew(self):
        h, _ = self.backfilled()
        expected = fresh_publish_calls(h.store, h.objects)
        self.assertTrue(expected)
        checks = SelectionChecks(h.store, h.objects)
        with mock.patch.object(completion, "_publish_calls", wraps=completion._publish_calls) as computed:
            kept = checks.publish_calls()
            self.assertIs(checks.publish_calls(), kept)
            self.assertEqual(computed.call_count, 1)
            checks.renew()
            renewed = checks.publish_calls()
            self.assertEqual(computed.call_count, 2)
        self.assertIsNot(renewed, kept)
        self.assertEqual(kept, expected)
        self.assertEqual(renewed, expected)

    def test_an_empty_publish_call_list_is_kept_and_reused(self):
        """Spec §4.4 item 3: a store with no publish calls keeps the empty list and reuses it."""
        h, _ = self.discovered()
        checks = SelectionChecks(h.store, h.objects)
        with mock.patch.object(completion, "_publish_calls", wraps=completion._publish_calls) as computed:
            self.assertEqual(checks.publish_calls(), ())
            self.assertEqual(checks.publish_calls(), ())
        self.assertEqual(computed.call_count, 1)

    def test_parents_are_kept_by_ref_until_renew(self):
        h, ref = self.discovered()
        checks = SelectionChecks(h.store, h.objects)
        with mock.patch.object(provenance, "read_parent", wraps=provenance.read_parent) as computed:
            kept = checks.parent(ref)
            self.assertIs(checks.parent(ref), kept)
            self.assertEqual(computed.call_args_list, [mock.call(ref, h.store, h.objects)])
            checks.renew()
            renewed = checks.parent(ref)
            self.assertEqual(computed.call_args_list, [mock.call(ref, h.store, h.objects)] * 2)
        self.assertIsNot(renewed, kept)
        self.assertEqual(kept, provenance.read_parent(ref, h.store, h.objects))
        self.assertEqual(renewed, kept)

    def test_a_failed_computation_is_not_kept(self):
        h, values = self.backfilled()
        ref = values[0]["parent_ref"]
        checks = SelectionChecks(h.store, h.objects)
        with self.subTest("publish_calls"), mock.patch.object(
                completion, "_publish_calls", side_effect=fails_once(completion._publish_calls)) as computed:
            with self.assertRaisesRegex(Conflict, "^fixture: uncertain authority$"):
                checks.publish_calls()
            kept = checks.publish_calls()
            self.assertIs(checks.publish_calls(), kept)
            self.assertEqual(computed.call_count, 2)
        self.assertEqual(kept, fresh_publish_calls(h.store, h.objects))

        checks.renew()
        with self.subTest("decoded input"), \
                mock.patch.object(completion, "_publish_calls", wraps=completion._publish_calls) as computed, \
                mock.patch.object(selection_checks, "decode_transformed",
                                  side_effect=fails_once(selection_checks.decode_transformed)):
            with self.assertRaisesRegex(Conflict, "^fixture: uncertain authority$"):
                checks.publish_calls()
            kept = checks.publish_calls()
            self.assertIs(checks.publish_calls(), kept)
            self.assertEqual(computed.call_count, 2)
        self.assertEqual(kept, fresh_publish_calls(h.store, h.objects))

        with self.subTest("parent"), mock.patch.object(
                provenance, "read_parent", side_effect=fails_once(provenance.read_parent)) as computed:
            with self.assertRaisesRegex(Conflict, "^fixture: uncertain authority$"):
                checks.parent(ref)
            kept = checks.parent(ref)
            self.assertIs(checks.parent(ref), kept)
            self.assertEqual(computed.call_count, 2)
        self.assertEqual(kept, provenance.read_parent(ref, h.store, h.objects))

    def test_kept_values_equal_fresh_ones_after_each_write_kind(self):
        """Spec §4.3 and §5 item 3. Each child execution renews the kept values before the next write."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        f = EvidenceFixture(Path(temp.name) / ".fixture-state")
        self.addCleanup(f.close)
        parser, schema = f.workflow.parser_version, f.workflow.schema_version
        code, _, result = f.invoke("transform", f.snapshot_input(quarterly_bytes("2026-07-01")))
        self.assertEqual(code, 0)
        transformed = result.transformed_workset_ref
        with checked_fault(f.root):
            code, _, result = f.invoke("publish", transformed)
        self.assertEqual((code, result), (9, None))
        checks = SelectionChecks(f.store, f.objects)
        refs = [f.parent_ref]

        def keep():
            return checks.publish_calls(), {ref: checks.parent(ref) for ref in refs}

        def assert_kept_and_fresh(kept):
            calls, parents = kept
            self.assertIs(checks.publish_calls(), calls)
            self.assertEqual(calls, fresh_publish_calls(f.store, f.objects))
            for ref, parent in parents.items():
                self.assertIs(checks.parent(ref), parent)
                self.assertEqual(parent, provenance.read_parent(ref, f.store, f.objects))

        # `_obligations` writes the repair authority object and its WorkflowRepairObligation row.
        kept = keep()
        self.assertEqual(len(kept[0]), 1)
        evaluation = completion.evaluate_member(f.value, parser, schema, f.store, f.objects, checks=checks)
        self.assertEqual(len(evaluation.obligations), 1)
        self.assertEqual(len(tuple(f.store.scan("WorkflowRepairObligation", {}))), 1)
        assert_kept_and_fresh(kept)

        # The fresh publish is a child execution, so the kept values are renewed after it.
        f.workflow = dataclasses.replace(f.workflow, attempt_id="fresh-workflow")
        code, fresh_call, _ = f.invoke("publish", transformed)
        self.assertEqual(code, 0)
        checks.renew()
        kept = keep()
        self.assertEqual(len(kept[0]), 2)
        completion.resolve_repair(evaluation.obligations[0], fresh_call, f.store, f.objects)
        self.assertEqual(len(tuple(f.store.scan("WorkflowRepairResolution", {}))), 1)
        assert_kept_and_fresh(kept)
        self.assertTrue(completion.evaluate_member(f.value, parser, schema, f.store, f.objects, checks=checks).complete)
        assert_kept_and_fresh(kept)

        # A new discovery is a child execution too. Its parent gives `project_member` a new member to write.
        dispatcher = checked_dispatcher(f.workflow, f.settings, f.pack, f.root.parent, f.store, f.objects)
        found = dispatcher.execute("discover", "selection-checks-discovery", f.settings,
                                   ("--mode", "quarterly", "--discovery-id", "selection-checks-revision", "--refresh"))
        checks.renew()
        refs.append(found.result.source_workset_ref)
        kept = keep()
        # The parent is kept, so a write that takes its read from `checks` computes no `read_parent`.
        with mock.patch.object(provenance, "read_parent", wraps=provenance.read_parent) as computed:
            value = provenance.project_member(refs[1], f.source.source_id, f.store, f.objects, checks=checks)
        self.assertEqual(computed.call_count, 0)
        self.assertEqual(f.store.get("WorkflowMember", value["member_id"]).to_mapping()["value"], value)
        assert_kept_and_fresh(kept)

        # `transfer_binding` writes the new member's Binding row.
        acquisition = AcquisitionState(f.store)
        pin = acquisition.binding(f.value["member_id"], f.source.source_id)
        self.assertIsNone(acquisition.binding(value["member_id"], f.source.source_id))
        snapshot = acquisition.snapshot(f.source.source_id, pin.snapshot_sha256)
        with mock.patch.object(provenance, "read_parent", wraps=provenance.read_parent) as computed:
            provenance.transfer_binding(value, snapshot, f.store, f.objects, checks=checks)
        self.assertEqual(computed.call_count, 0)
        self.assertEqual(acquisition.binding(value["member_id"], f.source.source_id),
                         Binding(value["member_id"], f.source.source_id, pin.snapshot_sha256))
        assert_kept_and_fresh(kept)

    def test_a_recovered_parent_passes_on_the_next_read(self):
        """Spec §5 item 3, setup of test_workflow_legacy.test_crash_before_parent_write_recovers_all_original_units."""
        h = self.harness()
        original_put = LocalObjectStore.put_once

        def stop_parent(objects, path, body):
            if path.startswith("worksets/sec/source/"):
                raise Crash("before original parent-object write")
            return original_put(objects, path, body)
        with mock.patch.object(LocalObjectStore, "put_once", stop_parent), self.assertRaises(Crash):
            h.invoke("discover", ("--mode", "daily", "--discovery-id", "interrupted"))
        checks = SelectionChecks(h.store, h.objects)
        refused, real_immutable = [], legacy.immutable

        def before_recovery_row(store, kind, key, value):
            if kind == "WorkflowParentRecovery":
                ref = "worksets/sec/source/sha256=" + key + "/workset.json"
                with self.assertRaisesRegex(
                        Conflict, "^parent is neither retained discovery revision nor validated recovery$"):
                    checks.parent(ref)
                refused.append(ref)
            return real_immutable(store, kind, key, value)
        # `legacy` binds its own `read_parent` name at import: a call site there that bypasses `checks` raises.
        bypass = AssertionError("a legacy read_parent call site bypassed the kept checks")
        with mock.patch.object(legacy, "immutable", before_recovery_row), \
                mock.patch.object(legacy, "read_parent", side_effect=bypass), \
                mock.patch.object(provenance, "read_parent", wraps=provenance.read_parent) as computed:
            self.assertEqual(legacy.bootstrap_legacy(h.store, h.objects, checks=checks), ())
        [ref] = refused
        # One refused read before the row, one passing read after it, then every read reuses the kept parent.
        self.assertEqual(computed.call_args_list, [mock.call(ref, h.store, h.objects)] * 2)
        self.assertIs(checks.parent(ref), checks.parent(ref))
        self.assertEqual(checks.parent(ref), provenance.read_parent(ref, h.store, h.objects))
        values = tuple(row.to_mapping()["value"] for row in h.store.scan("WorkflowMember", {}))
        self.assertEqual([value["parent_ref"] for value in values], [ref])

        # The session still names no workset, so the next pass calls `reconstruct_parent` again. Its retained-row
        # branch writes no recovery row, and every read in the pass reuses the kept parent.
        no_row = AssertionError("the retained-row branch wrote a recovery row")
        with mock.patch.object(legacy, "immutable", side_effect=no_row), \
                mock.patch.object(legacy, "read_parent", side_effect=bypass), \
                mock.patch.object(provenance, "read_parent", wraps=provenance.read_parent) as computed:
            self.assertEqual(legacy.bootstrap_legacy(h.store, h.objects, checks=checks), ())
        self.assertEqual(computed.call_count, 0)

    def test_a_non_text_parent_ref_gives_the_same_gaps_with_and_without_checks(self):
        """H1: a corrupt WorkflowMember row whose `parent_ref` is a JSON array or object is refused with today's
        message. Such a ref cannot be a key of the kept parents (review round 1, finding 1)."""
        h = self.harness()
        values = []
        for digit, parent_ref in (("1", ["worksets", "corrupt"]), ("2", {"ref": "worksets/corrupt"})):
            member_id = digit * 64
            value = {"contract_version": LOCAL_CONTRACT, "member_id": member_id, "source": fixture_source().to_mapping(),
                     "parent_ref": parent_ref, "member_ref": "worksets/sec/source/sha256=" + member_id + "/workset.json"}
            h.store.insert("WorkflowMember", member_id, value)
            values.append(value)
        registry = members.WorkflowMembers(h.store, h.objects)
        parser, schema = h.settings.etl.parser_version, h.settings.etl.schema_version

        def run(**checks):
            return (registry.inventory(**checks), legacy.bootstrap_legacy(h.store, h.objects, **checks),
                    [completion.evaluate_member(value, parser, schema, h.store, h.objects, **checks) for value in values])
        today = run()
        self.assertEqual([(gap.code, gap.message) for gap in today[0][1]],
                         [("legacy_member_unresolved", "object path must be a nonempty safe string")] * 2)
        self.assertEqual(run(checks=SelectionChecks(h.store, h.objects)), today)

    def test_without_checks_each_call_recomputes(self):
        """H4: without `checks`, every evaluation computes the publish-call authority again."""
        h, values = self.backfilled()
        parser, schema = h.settings.etl.parser_version, h.settings.etl.schema_version
        with mock.patch.object(completion, "_publish_calls", wraps=completion._publish_calls) as computed:
            first = completion.evaluate_member(values[0], parser, schema, h.store, h.objects)
            second = completion.evaluate_member(values[0], parser, schema, h.store, h.objects)
        self.assertEqual(computed.call_count, 2)
        self.assertTrue(first.complete, first.gaps)
        self.assertEqual(second, first)

    def test_a_stop_iteration_from_a_decode_is_the_same_gap_on_both_paths(self):
        """H4 and H1: `evaluate_member` reports a StopIteration as today's state_conflict gap, with or without
        `checks`. A generator frame around the decode would turn it into a RuntimeError (PEP 479)."""
        h, values = self.backfilled()
        parser, schema = h.settings.etl.parser_version, h.settings.etl.schema_version
        with mock.patch.object(completion, "decode_transformed", side_effect=StopIteration):
            today = completion.evaluate_member(values[0], parser, schema, h.store, h.objects)
        self.assertEqual([(gap.code, gap.message, gap.details["type"]) for gap in today.gaps],
                         [("state_conflict", "StopIteration", "StopIteration")])
        checks = SelectionChecks(h.store, h.objects)
        with mock.patch.object(selection_checks, "decode_transformed", side_effect=StopIteration):
            kept = completion.evaluate_member(values[0], parser, schema, h.store, h.objects, checks=checks)
        self.assertEqual(kept, today)

    def test_every_threaded_function_takes_its_checks_from_the_kept_values(self):
        """H2: with `checks`, the listed functions compute the publish calls once and each parent once.

        A call site that bypasses `checks` raises from the patched module names, or counts a second read.
        """
        h, values = self.backfilled()
        parser, schema = h.settings.etl.parser_version, h.settings.etl.schema_version
        registry = members.WorkflowMembers(h.store, h.objects)
        parent_refs = {value["parent_ref"] for value in values}

        def run(**checks):
            return (
                registry.inventory(**checks),
                [registry.completed(value, parser, schema, **checks) for value in values],
                [completion.evaluate_member(value, parser, schema, h.store, h.objects, **checks) for value in values],
                [completion.outstanding_repairs(value, h.store, h.objects, **checks) for value in values],
                [completion.capture_member_provenance(value, h.store, h.objects, **checks) for value in values],
                [completion.capture_parent_provenance(ref, h.store, h.objects, **checks) for ref in sorted(parent_refs)],
                [provenance.read_member(value, h.store, h.objects, **checks) for value in values],
                [provenance.project_member(value["parent_ref"], value["source"]["source_id"], h.store, h.objects,
                                           **checks) for value in values],
                legacy.bootstrap_legacy(h.store, h.objects, **checks),
            )
        expected = run()
        checks = SelectionChecks(h.store, h.objects)
        bypass = AssertionError("a read_parent call site bypassed the kept checks")
        with mock.patch.object(completion, "read_parent", side_effect=bypass), \
                mock.patch.object(members, "read_parent", side_effect=bypass), \
                mock.patch.object(legacy, "read_parent", side_effect=bypass), \
                mock.patch.object(provenance, "read_parent", wraps=provenance.read_parent) as parents, \
                mock.patch.object(completion, "_publish_calls", wraps=completion._publish_calls) as calls:
            actual = run(checks=checks)
        self.assertEqual(actual, expected)
        self.assertEqual(calls.call_count, 1)
        self.assertEqual(Counter(call.args[0] for call in parents.call_args_list), Counter(dict.fromkeys(parent_refs, 1)))


def _reuse_today(value: Mapping, store, objects) -> tuple[Error, ...]:
    """The H5 oracle: `runner.reuse_exact_binding` as at commit 003c516 (runner.py:25-61), copied verbatim.

    It calls the repo's own helpers, and keeps today's full registry check (`inventory()`) and its source filter.
    """
    acquisition = AcquisitionState(store)
    member = read_member(value, store, objects)
    identity = value['source']['source_id']
    if acquisition.binding(member.workset_id, identity) is not None or member.acquisition_mode == 'refresh':
        return ()
    gaps = []
    source = acquisition.get_source(identity)
    if source is None:
        return ()
    try:
        if source.value['needs_acquisition']:
            return ()
    except (ValueError, KeyError, TypeError) as error:
        return (Error('legacy_member_unresolved', 'source reuse evidence is corrupt: ' + error_text(error),
                      False, identity, {'member_id': value['member_id']}),)
    candidates = {}
    verified, _ = WorkflowMembers(store, objects).inventory()
    # select_work has already retained inventory gaps; reuse cannot hide them.
    for other in verified:
        if other['source'] != value['source']:
            continue
        try:
            pin = acquisition.binding(other['member_id'], identity)
            if pin is None:
                continue
            snapshot = acquisition.snapshot(identity, pin.snapshot_sha256)
            objects.verify(snapshot.raw_path, snapshot.sha256, snapshot.byte_count)
            candidates[snapshot.sha256] = snapshot
        except (ValueError, OSError, Conflict, KeyError, TypeError) as error:
            gaps.append(Error('legacy_member_unresolved', 'retained reuse pin is corrupt: ' + error_text(error),
                              False, identity, {'member_id': other['member_id']}))
    if len(candidates) != 1:
        return tuple(gaps)  # Ordinary checked collection establishes its exact binding.
    # Keep winner refusal outside candidate isolation; never overwrite a divergent binding.
    transfer_binding(value, next(iter(candidates.values())), store, objects)
    return tuple(gaps)


def remember(store, objects, source: Source, body: bytes):
    """A downloaded snapshot of `source`, remembered as `EvidenceFixture.snapshot_input` remembers one."""
    snapshot = fixture_snapshot(source, body)
    objects.put_once(snapshot.raw_path, body)
    return AcquisitionState(store).remember_snapshot(snapshot)


def pin(store, value, snapshot):
    AcquisitionState(store).bind_once(Binding(value["member_id"], snapshot.source_id, snapshot.sha256))


def insert_raw(store, kind, key, body: str):
    """Write a state row's JSON text directly, past the store's own refusal of a value it cannot write."""
    partition, key = identity(kind, key)
    with contextlib.closing(sqlite3.connect(store.database)) as database:
        database.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?)",
                         (table_for(kind), partition, key, body, "malformed-row"))
        database.commit()


def binding_rows(store):
    return tuple(row.to_mapping()["value"] for row in store.scan("Binding", {}))


class ReuseSourceFilterTests(unittest.TestCase):
    """Spec §4.4 items 6-7 and §5 item 5: reuse reads only the registered members of the value's own source (H5).

    Each case runs today's function (`_reuse_today`) and the new one on two copies of one fixture store. It compares
    the gap mappings in order and the Binding rows after the call.
    """

    @classmethod
    def setUpClass(cls):
        """Five discovered parents, each with the sources 2026Q3 and 2026Q4. The value's source, 2026Q3, is
        registered from the first three parents and 2026Q4 from all five: 3 members of the value's source and 5 of
        another source. No member is pinned, and no source has a download yet."""
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        cls.registry = Path(temp.name) / "registry"
        cls.registry.mkdir()
        h = CommandHarness(cls.registry, simple_pack(Path(temp.name) / "pack"))
        try:
            cls.binding = deployment_binding(h.settings)
            cls.parents, own, other = [], [], []
            for number in range(5):
                code, message = h.invoke("discover", ("--mode", "quarterly", "--discovery-id", f"reuse-{number}"),
                                         run=f"reuse-{number}")
                if code != 0:
                    raise AssertionError(message)
                ref = message["source_workset_ref"]
                sources = {source.period: source for source in provenance.read_parent(ref, h.store, h.objects).members}
                if set(sources) != {"2026Q3", "2026Q4"}:
                    raise AssertionError(f"discovery {number} lost a listing: {sorted(sources)}")
                cls.source = sources["2026Q3"]
                cls.parents.append(ref)
                if number < 3:
                    own.append(provenance.project_member(ref, cls.source.source_id, h.store, h.objects))
                other.append(provenance.project_member(ref, sources["2026Q4"].source_id, h.store, h.objects))
            cls.own, cls.other = tuple(own), tuple(other)
        finally:
            h.close()

    def reopen(self, root, binding):
        """The stores of a copied fixture root. A copy keeps the deployment binding recorded at its first path."""
        store = LocalStateStore(root / ".fixture-state", binding=binding)
        self.addCleanup(store.close)
        return store, LocalObjectStore(root / ".fixture-state", binding=binding)

    def case(self):
        """A copy of the registry fixture for one case's own setup, and its stores."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "case"
        shutil.copytree(self.registry, root)
        return (root, *self.reopen(root, self.binding))

    def assert_reaches_the_registry(self, store, value):
        """Reuse passes its early returns: the value is unbound and its source has a download."""
        acquisition = AcquisitionState(store)
        self.assertIsNone(acquisition.binding(value["member_id"], self.source.source_id))
        self.assertIs(acquisition.get_source(self.source.source_id).value["needs_acquisition"], False)

    def on_copy(self, root, name, reuse, value):
        """`reuse(value, store, objects)` on a fresh copy of the case store: its gap mappings in order, or the error
        it raised, and the Binding rows after the call."""
        copy = root.parent / name
        shutil.copytree(root, copy)
        store, objects = self.reopen(copy, self.binding)
        try:
            outcome = [gap.to_mapping() for gap in reuse(value, store, objects)]
        except Exception as error:
            outcome = {"raised": type(error).__name__, "message": str(error)}
        return outcome, binding_rows(store)

    def assert_same_as_today(self, root, value):
        today = self.on_copy(root, "today", _reuse_today, value)
        self.assertEqual(self.on_copy(root, "new", runner.reuse_exact_binding, value), today)
        return today

    def bound(self, value, snapshot):
        return Binding(value["member_id"], self.source.source_id, snapshot.sha256).to_mapping()

    def test_same_result_with_a_corrupt_member_of_another_source(self):
        """Spec §5 item 5. Today's registry check reads and skips both corrupt rows. Reuse now never reads them."""
        root, store, objects = self.case()
        *siblings, value = self.own
        snapshot = remember(store, objects, self.source, quarterly_bytes("2026-07-01"))
        pin(store, siblings[0], snapshot)
        # The corrupt row of test_workflow_runner.test_corrupt_retained_registry_and_receipt_do_not_block_valid_siblings,
        # and a changed copy of a registered member of the other source, which has no exact registry row.
        store.insert("WorkflowMember", "broken-member-row", {"source": {"source_id": "bad"}})
        store.insert("WorkflowMember", "changed-other-member",
                     {**self.other[0], "member_ref": self.other[1]["member_ref"]})
        self.assertEqual(len(WorkflowMembers(store, objects).inventory()[1]), 2)
        self.assert_reaches_the_registry(store, value)
        gaps, rows = self.assert_same_as_today(root, value)
        self.assertEqual(gaps, [])
        self.assertIn(self.bound(value, snapshot), rows)

    def test_same_result_with_a_corrupt_member_of_the_same_source(self):
        """Spec §5 item 5. Reuse reads each corrupt row of its own source and skips it, as today's registry check
        does. Two corrupt rows are pinned to a second snapshot: a reuse that kept them would bind nothing."""
        root, store, objects = self.case()
        *siblings, value = self.own
        kept = remember(store, objects, self.source, quarterly_bytes("2026-07-01"))
        stray = remember(store, objects, self.source, quarterly_bytes("2026-07-02"))
        pin(store, siblings[0], kept)
        corrupt = (
            # An exact registry row whose member ref is another member's projection (Conflict).
            {**siblings[0], "member_id": "1" * 64},
            # A non-text parent ref (ValueError), as in test_a_non_text_parent_ref_gives_the_same_gaps_with_and_without_checks.
            {**siblings[0], "member_id": "2" * 64, "parent_ref": ["worksets", "corrupt"]},
        )
        for row in corrupt:
            store.insert("WorkflowMember", row["member_id"], row)
            pin(store, row, stray)
        # A changed copy of a registered member of the value's source, which has no exact registry row (Conflict).
        store.insert("WorkflowMember", "changed-own-member", {**siblings[1], "member_ref": siblings[0]["member_ref"]})
        self.assertEqual(len(WorkflowMembers(store, objects).inventory()[1]), 3)
        self.assert_reaches_the_registry(store, value)
        gaps, rows = self.assert_same_as_today(root, value)
        self.assertEqual(gaps, [])
        self.assertIn(self.bound(value, kept), rows)

    def test_same_result_with_a_corrupt_reuse_pin(self):
        """Spec §5 item 5: each corrupt pin of the value's source gives the same `retained reuse pin is corrupt: …`
        gap, in the same order. An exact copy of a registered member under another key is read twice in both."""
        root, store, objects = self.case()
        *siblings, value = self.own
        # Two more members of the value's source, from the parents that registered only the other source.
        extra = [provenance.project_member(ref, self.source.source_id, store, objects) for ref in self.parents[3:]]
        kept = remember(store, objects, self.source, quarterly_bytes("2026-07-01"))
        pin(store, extra[1], kept)
        source_id = self.source.source_id
        # A pin to a snapshot that was never remembered (Conflict).
        store.insert("Binding", siblings[0]["member_id"] + ":" + source_id,
                     Binding(siblings[0]["member_id"], source_id, "f" * 64).to_mapping())
        # A pin to a remembered snapshot whose raw object is missing (OSError).
        missing = AcquisitionState(store).remember_snapshot(fixture_snapshot(self.source, quarterly_bytes("2026-07-03")))
        pin(store, siblings[1], missing)
        # A Binding row that does not decode.
        store.insert("Binding", extra[0]["member_id"] + ":" + source_id, {"source_workset_id": extra[0]["member_id"]})
        store.insert("WorkflowMember", "copy-of-member", siblings[0])
        self.assert_reaches_the_registry(store, value)
        gaps, rows = self.assert_same_as_today(root, value)
        self.assertEqual(Counter(gap["details"]["member_id"] for gap in gaps),
                         Counter({siblings[0]["member_id"]: 2, siblings[1]["member_id"]: 1, extra[0]["member_id"]: 1}))
        for gap in gaps:
            self.assertEqual(gap["code"], "legacy_member_unresolved")
            self.assertRegex(gap["message"], "^retained reuse pin is corrupt: .")
        self.assertIn(self.bound(value, kept), rows)

    def test_same_result_with_a_malformed_member_row(self):
        """Spec §4.4 item 7: the source filter reads a row's `source` only when the row's value is a dict."""
        *siblings, value = self.own
        with self.subTest("a list value in the state database"):
            root, store, objects = self.case()
            snapshot = remember(store, objects, self.source, quarterly_bytes("2026-07-01"))
            pin(store, siblings[0], snapshot)
            insert_raw(store, "WorkflowMember", "list-row", canonical_json(["source", value["source"]]).decode())
            # The store refuses to read the row, so today's registry check raises before it reads any member.
            with self.assertRaisesRegex(ValueError, "^value must be a mapping$"):
                WorkflowMembers(store, objects).inventory()
            self.assert_reaches_the_registry(store, value)
            outcome, rows = self.assert_same_as_today(root, value)
            self.assertEqual(outcome, {"raised": "ValueError", "message": "value must be a mapping"})
            self.assertEqual(rows, (self.bound(siblings[0], snapshot),))
        with self.subTest("dict values with no readable member of the source"):
            root, store, objects = self.case()
            snapshot = remember(store, objects, self.source, quarterly_bytes("2026-07-01"))
            pin(store, siblings[0], snapshot)
            for key, row in (("no-source", {"member_id": "no-source"}), ("list-source", {"source": [value["source"]]}),
                             ("text-source", {"source": "source"}), ("bare-source", {"source": value["source"]})):
                store.insert("WorkflowMember", key, row)
            self.assertEqual(len(WorkflowMembers(store, objects).inventory()[1]), 4)
            self.assert_reaches_the_registry(store, value)
            gaps, rows = self.assert_same_as_today(root, value)
            self.assertEqual(gaps, [])
            self.assertIn(self.bound(value, snapshot), rows)
        with self.subTest("a row of the source whose gap cannot be hashed"):
            root, store, objects = self.case()
            snapshot = remember(store, objects, self.source, quarterly_bytes("2026-07-01"))
            pin(store, siblings[0], snapshot)
            # A changed member ref holding an escaped lone surrogate: the read refuses the row, and today's gap for
            # it (its record_sha256) cannot be encoded, so today's registry check raises.
            body = canonical_json({**siblings[1], "member_ref": "MARKER"}).decode().replace("MARKER", "\\ud800")
            insert_raw(store, "WorkflowMember", "surrogate-row", body)
            with self.assertRaises(UnicodeEncodeError):
                WorkflowMembers(store, objects).inventory()
            self.assert_reaches_the_registry(store, value)
            outcome, rows = self.assert_same_as_today(root, value)
            self.assertEqual(outcome["raised"], "UnicodeEncodeError")
            self.assertEqual(rows, (self.bound(siblings[0], snapshot),))
        with self.subTest("simulated: a store that yields a list value"):
            root, store, objects = self.case()
            snapshot = remember(store, objects, self.source, quarterly_bytes("2026-07-01"))
            pin(store, siblings[0], snapshot)
            self.assert_reaches_the_registry(store, value)
            real_scan = LocalStateStore.scan

            def scan(state, kind, filters):
                yield from real_scan(state, kind, filters)
                if kind == "WorkflowMember":
                    yield SimpleNamespace(to_mapping=lambda: {"value": ["source", value["source"]],
                                                              "version": "simulated"})
            with mock.patch.object(LocalStateStore, "scan", scan):
                self.assertEqual(len(WorkflowMembers(store, objects).inventory()[1]), 1)
                gaps, rows = self.assert_same_as_today(root, value)
            self.assertEqual(gaps, [])
            self.assertIn(self.bound(value, snapshot), rows)

    def test_two_pins_of_one_source_bind_nothing_as_today(self):
        """Review Focus 3: two members of one source pinned to different snapshots, and a third member unbound."""
        root, store, objects = self.case()
        *siblings, value = self.own
        for sibling, day in zip(siblings, ("2026-07-01", "2026-07-02")):
            pin(store, sibling, remember(store, objects, self.source, quarterly_bytes(day)))
        before = binding_rows(store)
        self.assertEqual(len(before), 2)
        self.assert_reaches_the_registry(store, value)
        self.assertEqual(self.assert_same_as_today(root, value), ([], before))

    def test_reuse_validates_only_its_own_source(self):
        """H5: with 3 members of the value's source and 5 of another, reuse reads the value, then the 3 members of
        its source. Today it reads the value, then all 8. No member is pinned, so no transfer reads the value again."""
        root, store, objects = self.case()
        *siblings, value = self.own
        remember(store, objects, self.source, quarterly_bytes("2026-07-01"))
        self.assert_reaches_the_registry(store, value)
        real = provenance.read_member
        modules = [module for module in tuple(sys.modules.values())
                   if getattr(module, "__dict__", {}).get("read_member") is real]
        self.assertLessEqual({provenance, members, runner, sys.modules[__name__]}, set(modules))
        counted = mock.Mock(wraps=real)
        with contextlib.ExitStack() as patches:
            for module in modules:
                patches.enter_context(mock.patch.object(module, "read_member", counted))
            today = self.on_copy(root, "today", _reuse_today, value)
            read_today = counted.call_count
            counted.reset_mock()
            new = self.on_copy(root, "new", runner.reuse_exact_binding, value)
        self.assertEqual(new, today)
        self.assertEqual(today, ([], ()))
        self.assertEqual(read_today, 1 + 8)
        self.assertEqual(counted.call_count, 4)
        self.assertEqual(Counter(call.args[0]["member_id"] for call in counted.call_args_list),
                         Counter({value["member_id"]: 2, siblings[0]["member_id"]: 1, siblings[1]["member_id"]: 1}))

    def test_with_checks_the_result_is_unchanged_and_each_parent_is_read_once(self):
        """Task 4 passes `checks` here: every member read of reuse, `transfer_binding`'s included, takes its parent
        from the kept checks."""
        root, store, objects = self.case()
        *siblings, value = self.own
        snapshot = remember(store, objects, self.source, quarterly_bytes("2026-07-01"))
        pin(store, siblings[0], snapshot)
        self.assert_reaches_the_registry(store, value)

        def kept(value, store, objects):
            return runner.reuse_exact_binding(value, store, objects, checks=SelectionChecks(store, objects))
        today = self.on_copy(root, "today", _reuse_today, value)
        with mock.patch.object(provenance, "read_parent", wraps=provenance.read_parent) as parents:
            self.assertEqual(self.on_copy(root, "new", kept, value), today)
        self.assertIn(self.bound(value, snapshot), today[1])
        self.assertEqual(Counter(call.args[0] for call in parents.call_args_list),
                         Counter({member["parent_ref"]: 1 for member in self.own}))

    def test_the_new_checks_keywords_are_optional_and_keyword_only(self):
        for function in (members.WorkflowMembers.of_source, runner.reuse_exact_binding):
            with self.subTest(function.__qualname__):
                checks = inspect.signature(function).parameters["checks"]
                self.assertEqual((checks.kind, checks.default), (inspect.Parameter.KEYWORD_ONLY, None))
                mock.create_autospec(function)

    def test_sibling_completion_never_runs_the_full_inventory(self):
        """Spec §4.4 item 6: `sibling_completion` calls reuse without `checks`, and the source filter removes its
        full registry check. A complete sibling still gives the member today's processed result and binding."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "case"
        root.mkdir()
        h = CommandHarness(root, simple_pack(Path(temp.name) / "pack"))
        try:
            code, message = h.invoke("backfill", run="r1", attempt="a1")
            self.assertEqual(code, 0, message)
            code, message = h.invoke("discover", ("--mode", "quarterly", "--discovery-id", "sibling"), run="sibling")
            self.assertEqual(code, 0, message)
            ref = message["source_workset_ref"]
            source = provenance.read_parent(ref, h.store, h.objects).members[0]
            sibling = provenance.project_member(ref, source.source_id, h.store, h.objects)
            self.assertIsNone(AcquisitionState(h.store).binding(sibling["member_id"], source.source_id))
            context = fixture_context("backfill", settings=h.settings)
            binding = deployment_binding(h.settings)
        finally:
            h.close()
        completed = frozenset({source.source_id})
        outcomes = []
        for name in ("today", "new"):
            copy = root.parent / name
            shutil.copytree(root, copy)
            store, objects = self.reopen(copy, binding)
            if name == "today":
                patched = mock.patch.object(runner, "reuse_exact_binding", _reuse_today)
            else:
                full = AssertionError("sibling completion ran the full registry check")
                patched = mock.patch.object(WorkflowMembers, "inventory", side_effect=full)
            with patched:
                processed = runner.sibling_completion(sibling, None, completed, context, store, objects)
            outcomes.append((processed, binding_rows(store)))
        (expected, expected_rows), (processed, rows) = outcomes
        self.assertIsNotNone(processed)
        self.assertEqual((processed.result.member_id, processed.result.outcome, processed.result.child_refs),
                         (sibling["member_id"], "unchanged", ()))
        self.assertEqual((processed, rows), (expected, expected_rows))


def temporary_root(test):
    temp = tempfile.TemporaryDirectory()
    test.addCleanup(temp.cleanup)
    return Path(temp.name)


# The command of each scenario's selection. The superseded members are those of a reconcile.
SCENARIO_COMMANDS = {'superseded': 'reconcile'}


def unresolved(selection):
    """The first 50 characters of each `legacy_member_unresolved` gap message, sorted."""
    return sorted(gap['message'][:50] for gap in selection['gaps'] if gap['code'] == 'legacy_member_unresolved')


# Each case's marker: the feature under test, which both selections must hold, so that equal selections are not
# equal by both lacking it (D4).
MARKERS = {
    ('finished', False): (lambda s: (len(s['members']), s['discovered_sources'], len(s['already_complete'])), (1, 1, 0)),
    ('pending', False): (lambda s: (len(s['members']), s['discovered_sources']), (3, 1)),
    ('pending', True): (lambda s: (len(s['members']), s['halted'], s['parent_ref'], s['discovery_error']['code']),
                        (3, True, None, 'internal_error')),
    ('superseded', False): (lambda s: len(s['superseded']), 2),
    ('repair_obligation', False): (lambda s: len(s['jobs']), 2),
    ('corrupt_member', False): (unresolved, ['retained completion receipt is corrupt: unsupporte',
                                             *['unsupported local workflow contract'] * 2]),
    ('corrupt_parent', False): (unresolved, ['parent changes frozen origin'] * 4),
    ('corrupt_publish_call', False): (unresolved, ['legacy publish frozen command differs from exact A',
                                                   *['retained completion receipt is corrupt: checked pu'] * 2,
                                                   'unfinished publish Attempt differs from checked ca']),
    ('empty', False): (lambda s: (len(s['members']), s['discovered_sources']), (2, 1)),
}


class SelectionEqualityTests(unittest.TestCase):
    """Spec §5 item 1 (H1): `select_work` returns the same selection with kept values as without them."""

    def harness(self, name):
        h = scenario(temporary_root(self) / name, name)
        self.addCleanup(h.close)
        return h

    def test_selection_equal_with_and_without_kept_values(self):
        for name, discovery_fails in (*((name, False) for name in SCENARIOS), ('pending', True)):
            with self.subTest(scenario=name, discovery_fails=discovery_fails):
                kept, today = select_twice(self.harness(name), SCENARIO_COMMANDS.get(name, 'daily'),
                                           discovery_fails=discovery_fails)
                self.assertEqual(kept, today)
                marker, expected = MARKERS[name, discovery_fails]
                for path, selection in (('checks', kept), ('NO_CHECKS', today)):
                    with self.subTest(path=path):
                        self.assertEqual(marker(json.loads(selection)), expected)
        with self.subTest(scenario='corrupt_parent', corruption='registered'):
            # Spec §4.4 item 1: the computation raises as today.
            kept, today = refusal_twice(self.harness('corrupt_registration'), 'daily')
            self.assertEqual(kept, today)
            self.assertEqual(kept, ('Conflict', 'captured discovery session identity or registration differs'))

    def test_daily_and_reconcile_selections_equal_without_kept_values(self):
        """Review Focus 1: `daily` and `reconcile` run the same `select_work`, and only `backfill` was timed."""
        h = self.harness('pending')
        for command in ('daily', 'reconcile'):
            with self.subTest(command=command):
                kept, today = select_twice(h, command)
                self.assertEqual(kept, today)
                self.assertEqual(json.loads(kept)['context']['command'], command)


def phase_tally(events):
    """The `_publish_calls` computations of one phase, and its `read_parent` calls by ref."""
    calls = sum(1 for event in events if event[0] == '_publish_calls')
    return calls, Counter(event[1] for event in events if event[0] == 'read_parent')


def phases(events):
    """One selection's events, split at the dispatcher's `discover` entry and return: before, during and after."""
    entry, back = events.index(('discover', 'entry')), events.index(('discover', 'return'))
    return events[:entry], events[entry + 1:back], events[back + 1:]


def count_events(patches, events):
    """Record, in order: the dispatcher's `discover` entry and return, each `_publish_calls` computation, each
    `read_parent` call by ref in every module that binds it (provenance, completion, members, legacy, runner), each
    `SelectionChecks.publish_calls()` request and each `renew()`. Returns the spy on `SelectionChecks.renew`."""
    real_execute, real_calls, real_parent = Dispatcher.execute, completion._publish_calls, provenance.read_parent
    real_kept, real_renew = SelectionChecks.publish_calls, SelectionChecks.renew

    def execute(dispatcher, command, *args):
        if command == 'discover':
            events.append(('discover', 'entry'))
        try:
            return real_execute(dispatcher, command, *args)
        finally:
            if command == 'discover':
                events.append(('discover', 'return'))

    def publish_calls(*args):
        events.append(('_publish_calls',))
        return real_calls(*args)

    def read_parent(ref, *args):
        events.append(('read_parent', ref))
        return real_parent(ref, *args)

    def kept(checks):
        events.append(('publish_calls',))
        return real_kept(checks)

    def renew(checks):
        events.append(('renew',))
        return real_renew(checks)

    patches.enter_context(mock.patch.object(Dispatcher, 'execute', execute))
    patches.enter_context(mock.patch.object(completion, '_publish_calls', publish_calls))
    for module in (provenance, completion, members, legacy, runner):
        patches.enter_context(mock.patch.object(module, 'read_parent', read_parent))
    patches.enter_context(mock.patch.object(SelectionChecks, 'publish_calls', autospec=True, side_effect=kept))
    return patches.enter_context(mock.patch.object(SelectionChecks, 'renew', autospec=True, side_effect=renew))


class SelectionCountTests(unittest.TestCase):
    """Spec §5 item 2 (H2) and H3: one `_publish_calls` computation per phase, and one `read_parent` per parent ref
    per phase. The phases split at the dispatcher's `discover` entry and return."""

    def counted_selection(self, h, run, *, discovery_fails=False):
        """One `daily` selection: its events split into before, during and after the discovery child, the selection,
        and the spy on `SelectionChecks.renew`."""
        context, intent, dispatcher = workflow_start(h, 'daily', run)
        events = []
        with contextlib.ExitStack() as patches:
            renew = count_events(patches, events)
            if discovery_fails:
                patches.enter_context(checked_fault(h.root, point=DISCOVERY_FAILURE))
            selection = runner.select_work(context, h.settings, intent, dispatcher, h.store, h.objects)
        self.assertEqual(events.count(('discover', 'entry')), 1)
        return phases(events), selection, renew

    def assert_once_per_phase(self, split):
        before, during, after = split
        self.assertEqual(during, [])
        for name, events in (('before discovery', before), ('after discovery', after)):
            with self.subTest(phase=name):
                calls, parents = phase_tally(events)
                self.assertEqual(calls, 1)
                self.assertTrue(parents)
                self.assertEqual(set(parents.values()), {1}, parents)

    def test_counts_per_phase_at_1_10_50_members(self):
        totals = {}
        for size in (1, 10, 50):
            with self.subTest(members=size):
                h = registered_store(temporary_root(self) / f'members-{size}', size)
                self.addCleanup(h.close)
                split, selection, _ = self.counted_selection(h, 'counted')
                self.assertEqual(selection['discovered_sources'], size, selection['gaps'])
                self.assertEqual(len(selection['members']), 2 * size)
                self.assert_once_per_phase(split)
                before, _, after = split
                totals[size] = tuple((calls, sum(parents.values())) for calls, parents in map(phase_tally, (before, after)))
        # The totals do not grow with the number of members.
        self.assertEqual(len(set(totals.values())), 1, totals)

    def test_empty_store_selection_equal_and_counted(self):
        """Review Focus 4: no registered member and no publish history. The empty call list is computed once per
        phase and reused."""
        h = scenario(temporary_root(self) / 'empty', 'empty')
        self.addCleanup(h.close)
        events = []
        real_select = support_selection.select_work

        def select(*args):
            events.append(('select',))
            return real_select(*args)
        with contextlib.ExitStack() as patches:
            count_events(patches, events)
            patches.enter_context(mock.patch.object(support_selection, 'select_work', select))
            kept, today = select_twice(h, 'daily')
        self.assertEqual(kept, today)
        # The primed discovery runs before the first selection; each selection's events follow its marker.
        first, second = (index for index, event in enumerate(events) if event == ('select',))
        checked, unchecked = phases(events[first + 1:second]), phases(events[second + 1:])
        counts = {'checks': [phase_tally(phase)[0] for phase in checked],
                  'NO_CHECKS': [phase_tally(phase)[0] for phase in unchecked]}
        self.assertEqual(counts['checks'], [1, 0, 1], counts)
        for phase in (checked[0], checked[2]):
            # Each phase asks for the kept list more than once, and it is the empty list.
            self.assertGreater(phase.count(('publish_calls',)), 1)
        self.assertEqual(completion._publish_calls(h.store, h.objects), ())
        # Without kept values, a phase computes the empty list more than once: the checked run reused it.
        self.assertTrue(any(calls >= 2 for calls in counts['NO_CHECKS']), counts)

    def test_renew_runs_when_discovery_returns_and_when_it_raises(self):
        """H3: every kept value is dropped when the discovery child returns or raises."""
        h = scenario(temporary_root(self) / 'pending', 'pending')
        self.addCleanup(h.close)
        for discovery_fails in (False, True):
            with self.subTest(discovery_fails=discovery_fails):
                (before, _, after), selection, renew = self.counted_selection(
                    h, 'renew-raises' if discovery_fails else 'renew-returns', discovery_fails=discovery_fails)
                self.assertEqual(selection['discovery_error'] is not None, discovery_fails)
                self.assertEqual(renew.call_count, 1)
                self.assertEqual(after[:1], [('renew',)])
                self.assertIn(('_publish_calls',), before)
                self.assertIn(('publish_calls',), after)
                first = after.index(('publish_calls',))
                self.assertEqual(after[first + 1], ('_publish_calls',))


RECORDED = ('evaluate_member', 'read_member', '_obligations', 'reuse_exact_binding', 'read_parent')


class UnchangedPathTests(unittest.TestCase):
    """Spec §5 item 4 (H4): outside `select_work`, no check receives a kept value."""

    def record_checks(self, patches, phase):
        """Wrap each RECORDED function in every module under sec_edgar_ingest.workflows that binds it by name.
        Each call records the phase it ran in, its name and its `checks` argument."""
        calls = []
        homes = {'evaluate_member': completion, '_obligations': completion, 'read_member': provenance,
                 'read_parent': provenance, 'reuse_exact_binding': runner}

        def recorder(name, real):
            def record(*args, **kwargs):
                calls.append((phase[0], name, kwargs.get('checks')))
                return real(*args, **kwargs)
            return record
        for name in RECORDED:
            real = getattr(homes[name], name)
            wrapped = recorder(name, real)
            modules = [module for key, module in sorted(sys.modules.items())
                       if key.startswith('sec_edgar_ingest.workflows') and getattr(module, '__dict__', {}).get(name) is real]
            self.assertIn(homes[name], modules)
            for module in modules:
                patches.enter_context(mock.patch.object(module, name, wrapped))
        return calls

    def test_dispatch_and_finish_use_no_kept_value(self):
        root = temporary_root(self)
        h = CommandHarness(root, simple_pack(root / 'pack'))
        self.addCleanup(h.close)
        context, intent, dispatcher = workflow_start(h, 'backfill', 'unchanged-paths')
        phase = ['selection']

        def observer(point):
            if point == 'workflow.after_selection':
                phase[0] = 'dispatch'
        with contextlib.ExitStack() as patches:
            calls = self.record_checks(patches, phase)
            report = runner.run_workflow(context, h.settings, intent, dispatcher, h.store, h.objects, observer=observer)
            write_workflow_result(report, h.store, h.objects)
            self.assertEqual((report.outcome, report.counts['complete_sources']), ('success', 2))
            phase[0] = 'low-level'
            member = report.members[0]
            code, transformed = h.invoke('transform', ('--workset', member.snapshot_ref), run='unchanged-transform')
            self.assertEqual(code, 0, h.calls[-1])
            code, _ = h.invoke('publish', ('--workset', transformed['transformed_workset_ref']), run='unchanged-publish')
            self.assertEqual(code, 0, h.calls[-1])
        after = [(name, checks) for when, name, checks in calls if when == 'dispatch']
        self.assertLessEqual({'evaluate_member', 'read_member'}, {name for name, _ in after})
        self.assertEqual([(name, checks) for name, checks in after if checks is not None], [])
        low_level = [(name, checks) for when, name, checks in calls if when == 'low-level']
        self.assertEqual([(name, checks) for name, checks in low_level if checks is not None], [])
        # Control: the recorder sees a kept value where one is passed, in the selection before the event.
        self.assertTrue(any(isinstance(checks, SelectionChecks) for when, _, checks in calls if when == 'selection'))

    def watch_kept_values(self, patches):
        """Label each use of a kept value with the path that it ran in.

        Every use of a kept value goes through `SelectionChecks.parent` or `SelectionChecks.publish_calls`, so a spy
        on each class attribute sees a kept value in any path, a new `SelectionChecks` included. The label is
        'selection' while `runner.select_work` runs and 'after' once it returns or raises. `freeze_selection`,
        `process_member` and `sibling_completion` set their own name while they run, and the caller sets a label for
        each low-level command. Each call of a watched runner name is recorded as (label at entry, name, result).
        Child commands run in their own processes, so the spies see the parent process only.
        """
        seen = SimpleNamespace(label=['before'], uses=[], calls=[])

        def spy(name, real):
            def use(checks, *args):
                seen.uses.append((seen.label[0], name))
                return real(checks, *args)
            return use
        for name in ('parent', 'publish_calls'):
            patches.enter_context(mock.patch.object(SelectionChecks, name, spy(name, getattr(SelectionChecks, name))))

        def watch(name, real, label):
            def call(*args, **kwargs):
                outer = seen.label[0]
                if label is not None:
                    seen.label[0] = label
                try:
                    result = real(*args, **kwargs)
                finally:
                    if label is not None:
                        seen.label[0] = 'after' if name == 'select_work' else outer
                seen.calls.append((outer, name, result))
                return result
            return call
        for name, label in (('select_work', 'selection'), ('freeze_selection', 'freeze_selection'),
                            ('process_member', 'process_member'), ('sibling_completion', 'sibling_completion'),
                            ('reuse_exact_binding', None), ('evaluate_member', None)):
            patches.enter_context(mock.patch.object(runner, name, watch(name, getattr(runner, name), label)))
        return seen

    def assert_no_kept_value_after_select_work(self, seen):
        self.assertEqual([use for use in seen.uses if use[0] != 'selection'], [])
        # Control: the spies see both kept values in use while `select_work` runs.
        self.assertEqual({name for label, name in seen.uses if label == 'selection'}, {'parent', 'publish_calls'})

    def test_no_path_after_select_work_uses_a_kept_value(self):
        """Spec §5 item 4 (H4): this test fails if `freeze_selection`, `process_member`, `sibling_completion`, the
        finish step or a low-level command uses a kept value. It also proves that each of these paths runs.

        The drain fixture of test_workflow_drain.SiblingCompletionTests.pair gives each source a retained and a new
        member. The first member of each source runs `process_member`. The second one completes in
        `sibling_completion` through `reuse_exact_binding` and `evaluate_member`, with no child work. The `superseded`
        scenario gives `freeze_selection` and the finish step two superseded entries to validate.
        """
        def watched(seen, name):
            return [(label, result) for label, called, result in seen.calls if called == name]

        root = temporary_root(self)
        held = scenario(root / 'superseded', 'superseded')
        self.addCleanup(held.close)
        (root / 'drain').mkdir()
        h = drain.harness(root / 'drain', drain.widen(simple_pack(root / 'drain' / 'pack'), 4))
        self.addCleanup(h.close)
        drain.run(h, 'h4-0', allowed=0)

        with self.subTest(fixture='drain'):
            with contextlib.ExitStack() as patches:
                seen = self.watch_kept_values(patches)
                report, _ = drain.run(h, 'h4-1', allowed=10)
                member = next(member for member in report.members if member.snapshot_ref is not None)
                seen.label[0] = 'transform'
                code, transformed = h.invoke('transform', ('--workset', member.snapshot_ref), run='h4-transform')
                self.assertEqual(code, 0, h.calls[-1])
                seen.label[0] = 'publish'
                code, _ = h.invoke('publish', ('--workset', transformed['transformed_workset_ref']), run='h4-publish')
                self.assertEqual(code, 0, h.calls[-1])
            self.assertEqual([label for label, _ in watched(seen, 'select_work')], ['before'])
            self.assertEqual([label for label, _ in watched(seen, 'freeze_selection')], ['after'])
            self.assertEqual([label for label, _ in watched(seen, 'process_member')], ['after'] * 2)
            skipped = [label for label, processed in watched(seen, 'sibling_completion') if processed is not None]
            self.assertEqual(skipped, ['after'] * 2)
            self.assertEqual(len([member for member in report.members if not member.child_refs]), 2)
            inside = Counter(name for label, name, _ in seen.calls if label == 'sibling_completion')
            self.assertEqual(inside, Counter({'reuse_exact_binding': 2, 'evaluate_member': 2}))
            self.assert_no_kept_value_after_select_work(seen)

        with self.subTest(fixture='superseded'):
            context, intent, dispatcher = workflow_start(held, 'reconcile', 'h4-superseded')
            with contextlib.ExitStack() as patches:
                seen = self.watch_kept_values(patches)
                report = runner.run_workflow(context, held.settings, intent, dispatcher, held.store, held.objects)
                write_workflow_result(report, held.store, held.objects)
            [(label, frozen)] = watched(seen, 'freeze_selection')
            self.assertEqual((label, len(frozen['superseded'])), ('after', 2))
            self.assert_no_kept_value_after_select_work(seen)

    def test_resumed_attempt_builds_no_selection_checks(self):
        """Review Focus 2: an attempt whose selection.json exists freezes it and builds no `SelectionChecks`."""
        root = temporary_root(self)
        h = CommandHarness(root, simple_pack(root / 'pack'))
        self.addCleanup(h.close)
        context, intent, dispatcher = workflow_start(h, 'backfill', 'resumed')
        selection = runner.select_work(context, h.settings, intent, dispatcher, h.store, h.objects)
        freeze_selection(context, selection, h.store, h.objects)
        built = AssertionError('a resumed attempt built SelectionChecks')
        with mock.patch.object(runner, 'SelectionChecks', side_effect=built):
            report = runner.run_workflow(context, h.settings, intent, dispatcher, h.store, h.objects)
        self.assertEqual((report.outcome, report.counts['complete_sources']), ('success', 2))
