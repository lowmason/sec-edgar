"""The sec-index-v2 row contract, its Arrow layouts and the schema version registry (Stage 2a)."""
import hashlib
import itertools
import json
import tempfile
import unittest
from contextlib import closing
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

import support_catalog
from support import fixture_context, fixture_snapshot, fixture_source
from support_catalog import Lane
from support_etl import etl_context, seed_snapshot, v1_writable
from support_workflows import idx
from sec_edgar_ingest.etl import catalog
from sec_edgar_ingest.etl.columnar import quarter_observations
from sec_edgar_ingest.etl import parser
from sec_edgar_ingest.etl.manifest import validate_candidate_content
from sec_edgar_ingest.etl.parser import ParseError, iter_observations, parse_fields
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.etl.transform import (BATCH_ROWS, _remember_observation, _seen_database, read_observations,
                                            transform_workset)
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.etl.contracts import (
    ORIGINAL_FIELD_COUNT, IndexRow, IndexRowV2, arrow_row, business_fields, canonical_schema, change_schema,
    conflict_payload, decode_row, merge_rows, observation_schema, row_type, update_fields, upgrade_row,
)
from sec_edgar_ingest import models
from sec_edgar_ingest.models import SCHEMA_V1, SCHEMA_V2, canonical_json

NGM_NAME = 'NGM BIOPHARMACEUTICALS INC'
# The 2024Q1 NGM key of spec §4.2: one accession listed under SC TO-T and SC 13E3.
NGM = dict(cik='0001426332', archive_path='edgar/data/1426332/0001140361-24-012376.txt',
           filing_date=date(2024, 3, 8), accession_number='0001140361-24-012376',
           source_id='a' * 64, source_sha256='b' * 64)
# A synthetic UPLOAD letter of the rename class (spec §1.1): one key, old and new company names.
RENAME = dict(cik='0001551986', archive_path='edgar/data/1551986/0000000000-22-001234.txt',
              filing_date=date(2022, 4, 5), accession_number='0000000000-22-001234',
              source_id='a' * 64, source_sha256='b' * 64)
OLD_NAME, NEW_NAME = '9 METERS BIOPHARMA, INC.', 'INNOVATE BIOPHARMACEUTICALS, INC.'
WRITER = dict(version='2.6', compression='snappy', use_dictionary=False, use_compliant_nested_type=False)


def v1_row(form='SC 13E3', name=NGM_NAME, key=NGM, **changes):
    values = dict(key, company_name=name, form_type=form, parser_version='sec-index-parser-v1',
                  schema_version='sec-index-v1')
    return IndexRow(**{**values, **changes})


def v2_row(forms=('SC 13E3',), names=(NGM_NAME,), key=NGM, **changes):
    values = dict(key, company_names=names, form_types=forms, parser_version='sec-index-parser-v2',
                  schema_version='sec-index-v2')
    return IndexRowV2(**{**values, **changes})


# Today's (1c) schema functions, copied verbatim as the v1 byte-identity oracle.
def _oracle_canonical_schema() -> pa.Schema:
    names = ('cik', 'company_name', 'form_type', 'archive_path', 'filing_date',
             'accession_number', 'source_id', 'source_sha256', 'parser_version', 'schema_version')
    return pa.schema([pa.field(name, pa.date32() if name == 'filing_date' else pa.string(),
                               nullable=name == 'accession_number') for name in names])


def _oracle_observation_schema() -> pa.Schema:
    return pa.schema([*_oracle_canonical_schema(),
                      pa.field('original_fields', pa.list_(pa.field('item', pa.string(), nullable=False), ORIGINAL_FIELD_COUNT), nullable=False),
                      pa.field('line_number', pa.int64(), nullable=False)])


def _oracle_change_schema() -> pa.Schema:
    return pa.schema([pa.field('change_type', pa.string(), nullable=False),
                      pa.field('cik', pa.string(), nullable=False),
                      pa.field('archive_path', pa.string(), nullable=False),
                      pa.field('before', pa.struct(_oracle_canonical_schema()), nullable=True),
                      pa.field('after', pa.struct(_oracle_canonical_schema()), nullable=True),
                      pa.field('reason', pa.string(), nullable=True)])


class RowContractTests(unittest.TestCase):
    def test_v2_row_requires_sorted_distinct_nonempty_lists(self):
        for field in ('form_types', 'company_names'):
            for value in (('SC TO-T', 'SC 13E3'), ('SC 13E3', 'SC 13E3'), (), ('',)):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, field + ' must be sorted distinct non-empty strings'):
                        replace(v2_row(), **{field: value})
        row = v2_row(forms=('SC 13E3', 'SC TO-T'))
        self.assertEqual(row.form_types, ('SC 13E3', 'SC TO-T'))
        self.assertEqual(row.company_names, (NGM_NAME,))

    def test_v2_row_accepts_v1_versions(self):
        row = v2_row(parser_version='sec-index-parser-v1', schema_version='sec-index-v1')
        self.assertEqual((row.parser_version, row.schema_version), ('sec-index-parser-v1', 'sec-index-v1'))

    def test_unknown_schema_is_refused(self):
        for build in (lambda: v2_row(schema_version='sec-index-v3'),
                      lambda: v1_row(schema_version='sec-index-v3'),
                      lambda: replace(fixture_context(), schema_version='sec-index-v3'),
                      lambda: v1_row(schema_version='sec-index-v2')):
            with self.assertRaisesRegex(ValueError, 'unsupported schema_version'):
                build()

    def test_upgrade_row_keeps_every_field_and_version(self):
        row = v1_row()
        upgraded = upgrade_row(row)
        self.assertIs(type(upgraded), IndexRowV2)
        self.assertEqual(upgraded.form_types, ('SC 13E3',))
        self.assertEqual(upgraded.company_names, (NGM_NAME,))
        for name in ('cik', 'archive_path', 'filing_date', 'accession_number', 'source_id', 'source_sha256',
                     'parser_version', 'schema_version'):
            self.assertEqual(getattr(upgraded, name), getattr(row, name), name)
        self.assertEqual((upgraded.parser_version, upgraded.schema_version), ('sec-index-parser-v1', 'sec-index-v1'))

    def test_merge_rows_unions_both_lists_in_any_order(self):
        tender, schedule = v2_row(forms=('SC TO-T',)), v2_row(forms=('SC 13E3',))
        merged = [merge_rows(order) for order in itertools.permutations((tender, schedule, schedule))]
        for row in merged:
            self.assertEqual(row.form_types, ('SC 13E3', 'SC TO-T'))
            self.assertEqual(row.company_names, (NGM_NAME,))
            self.assertEqual(canonical_json(row.to_mapping()), canonical_json(merged[0].to_mapping()))
        old, new = v2_row(names=(OLD_NAME,), forms=('UPLOAD',), key=RENAME), v2_row(names=(NEW_NAME,), forms=('UPLOAD',), key=RENAME)
        for order in ((old, new), (new, old)):
            row = merge_rows(order)
            self.assertEqual(row.company_names, (OLD_NAME, NEW_NAME))
            self.assertEqual(row.form_types, ('UPLOAD',))
        both = merge_rows(iter((v2_row(names=('B NAME',), forms=('SC TO-T',)), v2_row(names=('A NAME',), forms=('SC 13E3',)))))
        self.assertEqual((both.company_names, both.form_types), (('A NAME', 'B NAME'), ('SC 13E3', 'SC TO-T')))
        self.assertEqual(merge_rows([v1_row(), v1_row()]), v1_row())

    def test_merge_rows_refuses_other_differences(self):
        with self.assertRaisesRegex(ValueError, 'rows differ outside form types and company names'):
            merge_rows([v2_row(forms=('SC TO-T',)), v2_row(filing_date=date(2024, 3, 9))])
        with self.assertRaisesRegex(ValueError, 'rows differ outside form types and company names'):
            merge_rows([v1_row(), v1_row(form='SC TO-T')])
        for rows in ([], [v1_row(), upgrade_row(v1_row())], [upgrade_row(v1_row()), v1_row()]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                merge_rows(rows)

    def test_conflict_payload_drops_only_the_lists(self):
        self.assertEqual(conflict_payload(v1_row()), canonical_json(v1_row().to_mapping()))
        mapping = v2_row().to_mapping()
        del mapping['form_types'], mapping['company_names']
        self.assertEqual(conflict_payload(v2_row(forms=('SC TO-T',), names=('OTHER',))), canonical_json(mapping))

    def test_row_type_and_decode_row_follow_the_layout(self):
        self.assertIs(row_type(SCHEMA_V1), IndexRow)
        self.assertIs(row_type(SCHEMA_V2), IndexRowV2)
        for layout, row in ((SCHEMA_V1, v1_row()), (SCHEMA_V2, v2_row(forms=('SC 13E3', 'SC TO-T')))):
            with self.subTest(layout=layout):
                self.assertEqual(decode_row(row.to_mapping(), layout), row)
                table = pa.Table.from_pylist([arrow_row(row.to_mapping(), layout)], schema=canonical_schema(layout))
                self.assertEqual(decode_row(table.to_pylist()[0], layout), row)
        with self.assertRaises(ValueError):
            decode_row(v1_row().to_mapping(), SCHEMA_V2)
        with self.assertRaises(ValueError):
            decode_row(v2_row().to_mapping(), SCHEMA_V1)
        for call in (lambda: row_type('sec-index-v3'), lambda: canonical_schema('sec-index-v3')):
            with self.assertRaisesRegex(ValueError, 'unsupported schema_version'):
                call()

    def test_v1_schemas_are_unchanged(self):
        for actual, oracle in ((canonical_schema(SCHEMA_V1), _oracle_canonical_schema()),
                               (observation_schema(SCHEMA_V1), _oracle_observation_schema()),
                               (change_schema(SCHEMA_V1), _oracle_change_schema())):
            self.assertTrue(actual.equals(oracle, check_metadata=True))
            self.assertEqual(actual.serialize().to_pybytes(), oracle.serialize().to_pybytes())

    def test_v2_schemas_round_trip_through_parquet(self):
        texts = pa.list_(pa.field('item', pa.string(), nullable=False))
        schema = canonical_schema(SCHEMA_V2)
        self.assertEqual(schema.names[:3], ['cik', 'company_names', 'form_types'])
        for name in ('company_names', 'form_types'):
            self.assertEqual(schema.field(name), pa.field(name, texts, nullable=False))
        before, after = v2_row(), v2_row(forms=('SC 13E3', 'SC TO-T'))
        change = {'change_type': 'updated', 'cik': after.cik, 'archive_path': after.archive_path,
                  'before': arrow_row(before.to_mapping(), SCHEMA_V2), 'after': arrow_row(after.to_mapping(), SCHEMA_V2),
                  'reason': None}
        with tempfile.TemporaryDirectory() as directory:
            for name, schema, value in (('data', canonical_schema(SCHEMA_V2), arrow_row(after.to_mapping(), SCHEMA_V2)),
                                        ('changes', change_schema(SCHEMA_V2), change)):
                with self.subTest(name=name):
                    path = Path(directory) / (name + '.parquet')
                    with pq.ParquetWriter(path, schema, **WRITER) as writer:
                        writer.write_table(pa.Table.from_pylist([value], schema=schema))
                    with pq.ParquetFile(path) as parquet:
                        self.assertTrue(parquet.schema_arrow.equals(schema, check_metadata=True))
                        self.assertEqual(parquet.read().to_pylist(), [value])

    def test_business_and_update_fields(self):
        self.assertEqual(business_fields(SCHEMA_V1),
                         ('cik', 'company_name', 'form_type', 'archive_path', 'filing_date', 'accession_number'))
        self.assertEqual(business_fields(SCHEMA_V2),
                         ('cik', 'company_names', 'form_types', 'archive_path', 'filing_date', 'accession_number'))
        self.assertEqual(update_fields(SCHEMA_V1), ('company_name', 'form_type', 'filing_date', 'accession_number'))
        self.assertEqual(update_fields(SCHEMA_V2), ('company_names', 'form_types', 'filing_date', 'accession_number'))

    def test_v1_member_result_still_validates(self):
        from sec_edgar_ingest.workflows.contracts import MemberResult
        for parser_version, schema_version in (('sec-index-parser-v1', 'sec-index-v1'),
                                               ('sec-index-parser-v2', 'sec-index-v2')):
            with self.subTest(schema_version=schema_version):
                member = MemberResult(
                    'a' * 64, fixture_source(), 'worksets/sec/source/sha256=' + 'b' * 64 + '/workset.json',
                    'worksets/sec/snapshot/sha256=' + 'c' * 64 + '/workset.json',
                    'worksets/sec/transformed/sha256=' + 'd' * 64 + '/workset.json',
                    ('runs/sec/r/collect/a/result.json',), 'success', True, True, False, (), (),
                    parser_version, schema_version)
                self.assertEqual(MemberResult.from_mapping(member.to_mapping()), member)


class VersionRegistryTests(unittest.TestCase):
    def test_registry_values(self):
        self.assertEqual((models.SCHEMA_V1, models.SCHEMA_V2), ('sec-index-v1', 'sec-index-v2'))
        self.assertEqual(models.KNOWN_SCHEMAS, ('sec-index-v1', 'sec-index-v2'))
        self.assertEqual(models.SCHEMA_VERSION, 'sec-index-v1')
        from sec_edgar_ingest.etl import parser
        self.assertFalse(hasattr(parser, 'SCHEMA_VERSION'))

    def test_writable_schemas_are_read_at_call_time(self):
        from unittest.mock import patch
        from support_etl import v1_writable
        with patch.object(models, 'WRITABLE_SCHEMAS', frozenset({SCHEMA_V2})):
            models.require_writable_schema(SCHEMA_V2)
            with self.assertRaisesRegex(ValueError, 'unsupported schema_version'):
                models.require_writable_schema(SCHEMA_V1)
            models.require_known_schema(SCHEMA_V1)
            with v1_writable():
                models.require_writable_schema(SCHEMA_V1)
                models.require_writable_schema(SCHEMA_V2)
            with self.assertRaisesRegex(ValueError, 'unsupported schema_version'):
                models.require_writable_schema(SCHEMA_V1)
        for check in (models.require_known_schema, models.require_writable_schema):
            for version in ('sec-index-v3', None, ['sec-index-v1']):
                with self.subTest(check=check.__name__, version=version):
                    with self.assertRaisesRegex(ValueError, 'unsupported schema_version'):
                        check(version)


class WriteSiteMessageTests(unittest.TestCase):
    """Each write site keeps its own refusal text. `RunContext` and `Settings` cannot hold `sec-index-v3`, so the
    command and CLI sites see a known schema that is not writable, as v1 will be after Task 6."""

    def assertRefused(self, message, call):
        with self.assertRaises(ValueError) as caught:
            call()
        self.assertEqual(str(caught.exception), message)

    def test_config_refuses_an_unknown_schema_with_its_own_text(self):
        from support import local_config_mapping
        from sec_edgar_ingest.config import Settings
        value = local_config_mapping()
        value['etl']['schema_version'] = 'sec-index-v3'
        self.assertRefused('unsupported etl.schema_version', lambda: Settings.from_mapping(value))

    def test_publish_refuses_an_unwritable_context_with_its_own_text(self):
        # `pin_context` revalidates the settings, so the config check would answer first; pass the pin to reach
        # the command's own check.
        from unittest.mock import patch
        from support_etl import etl_context
        from sec_edgar_ingest.etl import commands
        with tempfile.TemporaryDirectory() as directory:
            settings, context = etl_context(command='publish', root=Path(directory))
            ref = 'worksets/sec/transformed/sha256=' + 'a' * 64 + '/workset.json'
            with patch.object(commands, 'pin_context', return_value=(context, None)), \
                 patch.object(models, 'WRITABLE_SCHEMAS', frozenset({SCHEMA_V2})):
                self.assertRefused('unsupported ETL schema version',
                                   lambda: commands.run_publish(ref, context, settings, None, None))

    def test_cli_refuses_an_unwritable_config_with_its_own_text(self):
        from unittest.mock import patch
        from support import fixture_settings
        from sec_edgar_ingest import cli
        common = ['--config', 'unused.json', '--run-id', 'r', '--execution-id', 'e', '--attempt-id', 'a',
                  '--deadline', '2026-10-06T01:00:00+00:00']
        cases = ((cli._validate, ['transform', *common, '--workset',
                                  'worksets/sec/snapshot/sha256=' + 'a' * 64 + '/workset.json']),
                 (cli._validate_workflow, ['backfill', *common]))
        settings = fixture_settings(etl={'parser_version': 'fixture-index-parser-v1'})
        for validate, argv in cases:
            with self.subTest(validate=validate.__name__), \
                 patch.object(cli, 'load_config', return_value=settings), \
                 patch.object(models, 'WRITABLE_SCHEMAS', frozenset({SCHEMA_V2})):
                args = cli._parser().parse_args(argv)
                self.assertRefused('unsupported ETL schema version', lambda: validate(args))


def listing_row(kind, form, name=NGM_NAME, filed=date(2024, 3, 8), key=NGM):
    """One index line of `kind` for `key`, with the filing date spelt as that family spells it."""
    text = filed.isoformat() if kind == 'quarterly' else f'{filed:%Y%m%d}'
    return (key['cik'].lstrip('0'), name, form, text, key['archive_path'])


class ParserV2Tests(unittest.TestCase):
    FIELDS = ('1426332', NGM_NAME, 'SC 13E3', '2024-03-08', NGM['archive_path'])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def transform(self, kind, rows, label, *, schema_version=SCHEMA_V2, filed=date(2024, 3, 8)):
        """Transform one source of `rows` under its own store. Returns the result, the objects and the store root."""
        root = self.root / label
        root.mkdir()
        quarter = f'{filed.year}Q{(filed.month - 1) // 3 + 1}'
        source = fixture_source(quarter if kind == 'quarterly' else filed.isoformat(), kind)
        settings, context = etl_context(root=root, schema_version=schema_version)
        store, objects, origin = seed_snapshot(root, source, idx(rows, kind))
        self.addCleanup(store.close)
        path = f'worksets/sec/snapshot/sha256={origin.workset_id}/workset.json'
        result = transform_workset(path, context, settings, objects, EtlState(store), AcquisitionState(store))
        return result, objects, root

    def test_v2_observation_has_one_item_lists(self):
        source = fixture_source('2024Q1', 'quarterly')
        snapshot = fixture_snapshot(source, b'fixture')
        for parser_version in (parser.PARSER_V2, 'fixture-index-parser-v1'):
            with self.subTest(parser_version=parser_version):
                obs = parse_fields(self.FIELDS, source, snapshot, line_number=7, parser_version=parser_version,
                                   schema_version=SCHEMA_V2)
                self.assertIs(type(obs.row), IndexRowV2)
                self.assertEqual(obs.row.form_types, ('SC 13E3',))
                self.assertEqual(obs.row.company_names, (NGM_NAME,))
                self.assertEqual((obs.row.parser_version, obs.row.schema_version), (parser_version, SCHEMA_V2))
                self.assertEqual((obs.row.cik, obs.row.filing_date, obs.row.accession_number),
                                 (NGM['cik'], NGM['filing_date'], NGM['accession_number']))
                self.assertEqual((obs.original_fields, obs.line_number), (self.FIELDS, 7))

    def test_v1_path_still_emits_v1_rows(self):
        source = fixture_source('2024Q1', 'quarterly')
        snapshot = fixture_snapshot(source, b'fixture')
        obs = parse_fields(self.FIELDS, source, snapshot, line_number=7, parser_version='sec-index-parser-v1',
                           schema_version=SCHEMA_V1)
        expected = IndexRow(NGM['cik'], NGM_NAME, 'SC 13E3', NGM['archive_path'], NGM['filing_date'],
                            NGM['accession_number'], source.source_id, snapshot.sha256, 'sec-index-parser-v1',
                            SCHEMA_V1)
        self.assertIs(type(obs.row), IndexRow)
        self.assertEqual(obs.row, expected)
        self.assertEqual((obs.original_fields, obs.line_number), (self.FIELDS, 7))

    def test_pairs(self):
        self.assertEqual((parser.PARSER_V1, parser.PARSER_V2), ('sec-index-parser-v1', 'sec-index-parser-v2'))
        for parser_version, schema_version in (('sec-index-parser-v2', SCHEMA_V1), ('sec-index-parser-v1', SCHEMA_V2)):
            with self.subTest(parser_version=parser_version, schema_version=schema_version):
                for fixture in (False, True):
                    with self.assertRaisesRegex(ValueError, '^parser and schema versions do not pair$'):
                        parser.supported_pair(parser_version, schema_version, fixture=fixture)
        parser.supported_pair('sec-index-parser-v1', SCHEMA_V1, fixture=False)
        parser.supported_pair('sec-index-parser-v2', SCHEMA_V2, fixture=False)
        for parser_version in ('fixture-index-parser-v1', 'fixture-index-parser-v2'):
            for schema_version in (SCHEMA_V1, SCHEMA_V2):
                parser.supported_pair(parser_version, schema_version, fixture=True)
                with self.assertRaisesRegex(ValueError, 'unsupported parser version'):
                    parser.supported_pair(parser_version, schema_version, fixture=False)
        with self.assertRaisesRegex(ValueError, 'unsupported schema version: sec-index-v3'):
            parser.supported_pair('sec-index-parser-v2', 'sec-index-v3', fixture=False)
        parser.supported_parser('sec-index-parser-v1', fixture=False)
        parser.supported_parser('sec-index-parser-v2', fixture=False)
        with self.assertRaisesRegex(ValueError, 'unsupported parser version'):
            parser.supported_parser('sec-index-parser-v3', fixture=True)

    def test_unpaired_versions_refuse_before_any_row_or_file_is_read(self):
        from unittest.mock import patch
        source = fixture_source('2024Q1', 'quarterly')
        snapshot = fixture_snapshot(source, b'fixture')
        for parser_version, schema_version in (('sec-index-parser-v2', SCHEMA_V1), ('sec-index-parser-v1', SCHEMA_V2)):
            with self.subTest(parser_version=parser_version, schema_version=schema_version):
                with self.assertRaisesRegex(ValueError, 'parser and schema versions do not pair'):
                    parse_fields(self.FIELDS, source, snapshot, line_number=7, parser_version=parser_version,
                                 schema_version=schema_version)
                with patch.object(Path, 'open', side_effect=AssertionError('opened')):
                    with self.assertRaisesRegex(ValueError, 'parser and schema versions do not pair'):
                        list(iter_observations(Path('/does-not-exist'), source, snapshot,
                                               parser_version=parser_version, schema_version=schema_version))

    def test_combined_filing_transforms_in_both_families(self):
        for kind in ('quarterly', 'daily'):
            with self.subTest(kind=kind):
                rows = [listing_row(kind, 'SC TO-T'), listing_row(kind, 'SC 13E3')]
                result, objects, _ = self.transform(kind, rows, kind)
                self.assertTrue(result.complete, result.failures)
                ref = result.observations[0]
                self.assertEqual((ref.source_row_count, ref.distinct_key_count), (2, 1))
                self.assertEqual(dict(ref.quarter_counts), {'2024Q1': 2})
                observed = list(read_observations(ref, objects))
                self.assertEqual([type(obs.row) for obs in observed], [IndexRowV2, IndexRowV2])
                self.assertEqual([(obs.line_number, obs.row.form_types) for obs in observed],
                                 [(3, ('SC TO-T',)), (4, ('SC 13E3',))])
                self.assertEqual([obs.original_fields[2] for obs in observed], ['SC TO-T', 'SC 13E3'])

    def test_company_rename_transforms_in_both_families(self):
        key = dict(RENAME, archive_path='edgar/data/1551986/0000000000-26-000001.txt')
        filed = date(2026, 1, 5)
        for kind in ('quarterly', 'daily'):
            with self.subTest(kind=kind):
                rows = [listing_row(kind, 'UPLOAD', OLD_NAME, filed, key),
                        listing_row(kind, 'UPLOAD', NEW_NAME, filed, key)]
                result, objects, _ = self.transform(kind, rows, kind, filed=filed)
                self.assertTrue(result.complete, result.failures)
                ref = result.observations[0]
                self.assertEqual((ref.source_row_count, ref.distinct_key_count), (2, 1))
                observed = list(read_observations(ref, objects))
                self.assertEqual([obs.row.company_names for obs in observed], [(OLD_NAME,), (NEW_NAME,)])
                self.assertEqual({obs.row.accession_number for obs in observed}, {'0000000000-26-000001'})

    def test_filing_date_conflict_still_refuses_the_source(self):
        later = date(2024, 3, 9)
        reason = 'conflicting duplicate logical key'
        body = idx([listing_row('daily', 'SC 13E3'), listing_row('daily', 'SC 13E3', filed=later)], 'daily')
        source = fixture_source('2024-03-08', 'daily')
        path = self.root / 'master.idx'
        path.write_bytes(body)
        with closing(_seen_database(self.root / 'seen.sqlite')) as db, self.assertRaises(ParseError) as raised:
            for obs in iter_observations(path, source, fixture_snapshot(source, body),
                                         parser_version='sec-index-parser-v2', schema_version=SCHEMA_V2):
                _remember_observation(db, obs)
        self.assertEqual((raised.exception.line_number, raised.exception.reason), (4, reason))
        for kind in ('quarterly', 'daily'):
            with self.subTest(kind=kind):
                rows = [listing_row(kind, 'SC 13E3'), listing_row(kind, 'SC 13E3', filed=later)]
                result, _, root = self.transform(kind, rows, kind)
                self.assertFalse(result.complete)
                self.assertEqual(result.observations, ())
                self.assertEqual((result.failures[0].details['line_number'], result.failures[0].details['reason']),
                                 (4, reason))
                retained = [json.loads(item.read_bytes()) for item in (root / 'objects/quarantine').rglob('error.json')]
                self.assertEqual(len(retained), 1)
                self.assertEqual((retained[0]['details']['line_number'], retained[0]['details']['reason']), (4, reason))

    def test_v1_form_or_name_repeat_still_refuses_the_source(self):
        for kind in ('quarterly', 'daily'):
            for differs, other in (('form', listing_row(kind, 'SC TO-T')),
                                   ('name', listing_row(kind, 'SC 13E3', 'OTHER INC'))):
                with self.subTest(kind=kind, differs=differs):
                    result, _, _ = self.transform(kind, [listing_row(kind, 'SC 13E3'), other], kind + differs,
                                                  schema_version=SCHEMA_V1)
                    self.assertFalse(result.complete)
                    self.assertEqual(result.failures[0].details['reason'], 'conflicting duplicate logical key')
                    self.assertEqual(result.failures[0].details['line_number'], 4)

    def test_columnar_and_full_readers_decode_v2_alike(self):
        rows = [listing_row('quarterly', 'SC TO-T'), listing_row('quarterly', 'SC 13E3')]
        result, objects, _ = self.transform('quarterly', rows, 'columnar')
        ref = result.observations[0]
        expected = list(read_observations(ref, objects))
        self.assertTrue(all(type(obs.row) is IndexRowV2 for obs in expected))
        self.assertEqual(list(quarter_observations(ref, objects, '2024Q1')), expected)
        keys = {(NGM['cik'], NGM['archive_path'])}
        self.assertEqual(list(quarter_observations(ref, objects, '2024Q1', keys)), expected)
        self.assertEqual(list(quarter_observations(ref, objects, '2024Q2')), [])


NGM_QUARTER = '2024Q1'
# The rename class filed in 2024Q1, so that one quarterly source of that quarter lists both keys.
RENAME_Q1 = dict(RENAME, archive_path='edgar/data/1551986/0000000000-24-000001.txt', filing_date=date(2024, 3, 5),
                 accession_number='0000000000-24-000001')


def line(form, name=NGM_NAME, key=NGM):
    """One index line of `key`, dated ISO. `Lane.observation` re-spells the date for a daily source."""
    return ('|'.join(listing_row('quarterly', form, name, key['filing_date'], key)) + '\n').encode()


def reversed_read(ref, objects):
    """`read_observations` with the snapshot's observations in reverse line order."""
    yield from reversed(list(read_observations(ref, objects)))


class CatalogV2Tests(unittest.TestCase):
    """The full build and the full validator merge both lists within the source that precedence selects."""

    def lane(self, schema_version=SCHEMA_V2):
        lane = Lane(schema_version=schema_version)
        self.addCleanup(lane.close)
        return lane

    def build(self, lane, refs, previous=None, quarter=NGM_QUARTER):
        candidate = lane.build(refs, previous, quarter)
        validate_candidate_content(candidate, lane.objects)
        return candidate

    def reversed_build(self, lane, refs, previous=None, quarter=NGM_QUARTER):
        """`build`, with the full build reading every source's observations in reverse line order."""
        load = catalog._load_observations
        with patch.object(catalog, '_load_observations',
                          side_effect=lambda *args: load(*args, read=reversed_read)) as loaded:
            candidate = self.build(lane, refs, previous, quarter)
        self.assertEqual(loaded.call_count, 1)
        return candidate

    @staticmethod
    def files(lane, candidate):
        return {ref.role: lane.path(ref.path).read_bytes() for ref in candidate.manifest.files}

    @staticmethod
    def forge(lane, candidate, values):
        """Rewrite the data and changes files with `values`, and the manifest with their hashes, lengths and counts."""
        files = []
        for ref in candidate.manifest.files:
            schema = canonical_schema(SCHEMA_V2) if ref.role == 'data' else change_schema(SCHEMA_V2)
            path = lane.path(ref.path)
            with pq.ParquetWriter(path, schema, **WRITER) as writer:
                writer.write_table(pa.Table.from_pylist(values[ref.role], schema=schema))
            body = path.read_bytes()
            files.append(replace(ref, sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body),
                                 row_count=len(values[ref.role])))
        manifest = replace(candidate.manifest, files=tuple(files))
        body = canonical_json(manifest.to_mapping())
        lane.path(candidate.manifest_ref).write_bytes(body)
        return replace(candidate, manifest=manifest, manifest_sha256=hashlib.sha256(body).hexdigest(),
                       manifest_bytes=len(body))

    def test_combined_filing_and_rename_publish_one_row_each(self):
        lane = self.lane()
        body = (line('SC TO-T') + line('SC 13E3') + line('UPLOAD', OLD_NAME, RENAME_Q1)
                + line('UPLOAD', NEW_NAME, RENAME_Q1))
        candidate = self.build(lane, [lane.observation(NGM_QUARTER, 'quarterly', body)])
        self.assertEqual(candidate.manifest.schema_version, SCHEMA_V2)
        self.assertEqual((candidate.manifest.row_count, candidate.manifest.added), (2, 2))
        ngm, rename = (decode_row(value, SCHEMA_V2) for value in lane.rows(candidate))
        self.assertEqual((ngm.cik, ngm.company_names, ngm.form_types, ngm.filing_date, ngm.archive_path),
                         ('0001426332', ('NGM BIOPHARMACEUTICALS INC',), ('SC 13E3', 'SC TO-T'), date(2024, 3, 8),
                          'edgar/data/1426332/0001140361-24-012376.txt'))
        self.assertEqual((rename.cik, rename.company_names, rename.form_types),
                         (RENAME_Q1['cik'], (OLD_NAME, NEW_NAME), ('UPLOAD',)))
        self.assertEqual([decode_row(change['after'], SCHEMA_V2) for change in lane.rows(candidate, 'changes')],
                         [ngm, rename])

    def test_permuted_lines_give_byte_identical_generations(self):
        # A reordered raw body is another snapshot, and every row carries its snapshot hash. So the permutation
        # is of one snapshot's observations, as the full build reads them (D5: the same observations in any order).
        body = (line('SC TO-T') + line('UPLOAD', OLD_NAME, RENAME_Q1) + line('SC 13E3')
                + line('UPLOAD', NEW_NAME, RENAME_Q1))
        forward, backward = self.lane(), self.lane()
        first = self.build(forward, [forward.observation(NGM_QUARTER, 'quarterly', body)])
        second = self.reversed_build(backward, [backward.observation(NGM_QUARTER, 'quarterly', body)])
        self.assertEqual(first.manifest.generation_id, second.manifest.generation_id)
        self.assertEqual(self.files(forward, first), self.files(backward, second))
        self.assertEqual([value['form_types'] for value in forward.rows(first)], [['SC 13E3', 'SC TO-T'], ['UPLOAD']])

    def test_triple_repeat_across_batch_boundary_is_order_independent(self):
        rows = [support_catalog.row(number=number) for number in range(1, 9001)]
        repeat = support_catalog.row(number=9001)
        # File lines 1 and 2 are the header, so file line L holds rows[L - 3].
        rows[8190 - 3] = rows[8193 - 3] = repeat
        rows[8197 - 3] = support_catalog.row(number=9001, form='10-K/A')
        path = 'edgar/data/123456/0000123456-26-009001.txt'
        forward, backward = self.lane(), self.lane()
        first_ref, second_ref = (lane.observation('2026-10-01', 'daily', b''.join(rows)) for lane in (forward, backward))
        lines = [obs.line_number for obs in read_observations(first_ref, forward.objects) if obs.row.archive_path == path]
        self.assertEqual(lines, [8190, 8193, 8197])
        self.assertEqual([(number - 3) // BATCH_ROWS for number in lines], [0, 0, 1])
        first = self.build(forward, [first_ref], quarter='2026Q4')
        second = self.reversed_build(backward, [second_ref], quarter='2026Q4')
        self.assertEqual(first.manifest.row_count, 8998)
        merged = [value for value in forward.rows(first) if value['archive_path'] == path]
        self.assertEqual([value['form_types'] for value in merged], [['10-K', '10-K/A']])
        self.assertEqual(first.manifest.generation_id, second.manifest.generation_id)
        self.assertEqual(self.files(forward, first), self.files(backward, second))

    def test_merge_never_crosses_sources(self):
        lane = self.lane()
        daily = lane.observation('2024-03-08', 'daily', line('SC 13E3'))
        quarterly = lane.observation(NGM_QUARTER, 'quarterly', line('SC TO-I'))
        candidate = self.build(lane, [daily, quarterly])
        [row] = (decode_row(value, SCHEMA_V2) for value in lane.rows(candidate))
        self.assertEqual(row.form_types, ('SC TO-I',))
        self.assertEqual((row.source_id, row.source_sha256), (quarterly.source.source_id, quarterly.snapshot.sha256))
        self.assertEqual(len(candidate.manifest.sources), 2)

    def test_v2_candidate_on_v1_base_counts_provenance_refresh(self):
        day = date(2026, 10, 7)
        with v1_writable():
            lane = self.lane(SCHEMA_V1)
            lines = b''.join(support_catalog.row(number=number) for number in (1, 2, 3))
            base = self.build(lane, [lane.observation('2026-10-01', 'daily', lines)], quarter='2026Q4')
        self.assertEqual(base.manifest.schema_version, SCHEMA_V1)
        lane.context = replace(lane.context, schema_version=SCHEMA_V2)
        lane.pin(day)
        changed = lane.observation('2026-10-02', 'daily', support_catalog.row(number=3, form='10-K/A'))
        candidate = self.build(lane, [changed], base, quarter='2026Q4')
        manifest = candidate.manifest
        self.assertEqual(manifest.schema_version, SCHEMA_V2)
        self.assertEqual((manifest.provenance_refreshed, manifest.updated, manifest.added, manifest.withdrawn,
                          manifest.unresolved_absence), (2, 1, 0, 0, 0))
        [change] = lane.rows(candidate, 'changes')
        self.assertEqual(change['change_type'], 'updated')
        self.assertEqual((change['before']['form_types'], change['before']['schema_version']), (['10-K'], SCHEMA_V1))
        self.assertEqual((change['after']['form_types'], change['after']['schema_version']), (['10-K/A'], SCHEMA_V2))

    def test_dropped_form_type_is_updated_with_clear_gate(self):
        lane = self.lane()
        base = self.build(lane, [lane.observation(NGM_QUARTER, 'quarterly', line('SC TO-T') + line('SC 13E3'))])
        self.assertEqual([value['form_types'] for value in lane.rows(base)], [['SC 13E3', 'SC TO-T']])
        newer = lane.observation(NGM_QUARTER, 'quarterly', line('SC TO-T'), seconds=1)
        candidate = self.build(lane, [newer], base)
        manifest = candidate.manifest
        self.assertEqual((manifest.quarter_mode, manifest.updated, manifest.withdrawn, manifest.gate),
                         ('closed', 1, 0, 'clear'))
        self.assertIsNone(candidate.candidate_ref)
        [change] = lane.rows(candidate, 'changes')
        self.assertEqual((change['change_type'], change['before']['form_types'], change['after']['form_types']),
                         ('updated', ['SC 13E3', 'SC TO-T'], ['SC TO-T']))

    def test_validator_refuses_a_cross_source_merge(self):
        lane = self.lane()
        daily = lane.observation('2024-03-08', 'daily', line('SC 13E3'))
        quarterly = lane.observation(NGM_QUARTER, 'quarterly', line('SC TO-I'))
        candidate = self.build(lane, [daily, quarterly])
        [value] = lane.rows(candidate)

        def generation(row):
            added = {'change_type': 'added', 'cik': row['cik'], 'archive_path': row['archive_path'],
                     'before': None, 'after': row, 'reason': None}
            return {'data': [row], 'changes': [added]}

        # The forge itself is sound: the built row, rewritten, still validates.
        validate_candidate_content(self.forge(lane, candidate, generation(value)), lane.objects)
        union = self.forge(lane, candidate, generation({**value, 'form_types': ['SC 13E3', 'SC TO-I']}))
        with self.assertRaisesRegex(ValueError, '^canonical row is not a selected observation or exact retained row$'):
            validate_candidate_content(union, lane.objects)


if __name__ == '__main__':
    unittest.main()
