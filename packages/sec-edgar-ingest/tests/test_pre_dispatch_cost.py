"""Stage 2a1 pre-dispatch cost: record type-hints cache (H6) and per-phase selection checks (H2, H3)."""
import dataclasses
import importlib
import inspect
import pkgutil
import tempfile
import typing
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import sec_edgar_ingest
from sec_edgar_ingest import models
from sec_edgar_ingest.etl.contracts import decode_transformed
from sec_edgar_ingest.models import Binding, CommandResult, Error, RunContext, Source, record_type_hints
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.storage.contracts import Conflict
from sec_edgar_ingest.storage.local import LocalObjectStore
from sec_edgar_ingest.workflows import completion, legacy, members, provenance, selection_checks
from sec_edgar_ingest.workflows.contracts import LOCAL_CONTRACT
from sec_edgar_ingest.workflows.selection_checks import SelectionChecks
from support import fixture_context, fixture_source
from support_process import checked_dispatcher, checked_fault
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
