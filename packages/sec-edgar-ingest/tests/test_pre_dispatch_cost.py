"""Stage 2a1 pre-dispatch cost: record type-hints cache (H6)."""
import dataclasses
import importlib
import pkgutil
import typing
import unittest
from unittest import mock

import sec_edgar_ingest
from sec_edgar_ingest import models
from sec_edgar_ingest.models import CommandResult, Error, RunContext, Source, record_type_hints
from support import fixture_context, fixture_source


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
