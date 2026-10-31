"""The sec-index-v2 row contract, its Arrow layouts and the schema version registry (Stage 2a)."""
import itertools
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from support import fixture_context, fixture_source
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


if __name__ == '__main__':
    unittest.main()
