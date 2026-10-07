## Global Constraints

The following are copied verbatim from Stage 3 spec §3; every task inherits them:

- The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.
- ETL reads those bytes from ADLS and makes no SEC requests.
- ETL never silently follows a mutable “latest”.
- Original bytes are retained.
- Downloaded, transformed and published are different states.
- Refuse malformed rows rather than silently dropping them; quarantine the source and report the line and reason.
- An unrecognized legacy format does not by itself invalidate a usable index row.
- Never deduplicate on company name and filing date alone.
- An identical input fingerprint and unchanged versions are a no-op.
- A forced replay may rebuild output, but cannot create a second logical filing.
- A gated candidate is `awaiting_approval`, not current.
- A conflict requires rereading the active generation and rebuilding; never overwrite a newer pointer with stale work.
- The pointer update is the publication boundary.
- There is no assumed transaction spanning Blob Storage and Table Storage.
- Per-source published flags are recoverable indexes, not a second commit authority.
- Atomicity is **per quarter**, not across the entire historical dataset.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.

Exact values: Python >=3.14; PyArrow 25.0.1; Requests 2.34.2; Identity 1.26.0; Blob 12.31.0/API 2026-04-06; Tables 12.7.0/API 2020-12-06; canonical schema `sec-index-v1`; received-byte guard 67,108,864; expanded-byte guard 536,870,912; exchange deadline 90 seconds; batches 8,192 rows; CAS_ATTEMPTS 5. Retain accepted settings and pins, one ingest package and indefinite development evidence retention. Stage 7 measures actual Linux amd64/Python 3.14.8 worker memory, runtime and scratch; native proofs establish no deployed capacity.

Live SEC, Azure, authentication, compute, provisioning and deployment authorizations remain closed. Use cached libraries and retained evidence only. No auto-fetch fallback, optional codec selection, approval bypass, image build, workflow/schedule activation or later-stage routing belongs to this plan.

---

### Task 2: Strict row parsing and independent golden fixtures

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/parser.py`, `packages/sec-edgar-ingest/tests/test_etl_parser.py`, and `packages/sec-edgar-ingest/tests/fixtures/etl/{quarterly.idx,daily.idx,legacy.idx,expected.json,fixture-manifest.json}`. ZIP fixture is generated deterministically from quarterly.idx during tests; retained original ZIPs are separately replayed in Task 7. Do not alter Stage 1/2 receipts.

**Interfaces:** Consumes IndexRow/Observation and acquisition validation/constants. Produces ParseError, supported_parser, parse_fields and iter_observations signatures above. Duplicate conflict detection belongs to Task 3's source-wide scratch index, not parser row state.

- [ ] **Step 1: Write golden and refusal tests, run red.** Include this complete first test using existing fixture helpers:

```python
import unittest
from sec_edgar_ingest.etl.parser import parse_fields
from support import fixture_source, fixture_snapshot

class EtlParserTests(unittest.TestCase):
    def test_daily_date_chooses_older_output_quarter(self):
        source = fixture_source(kind='daily', period='2026-09-30')
        snapshot = fixture_snapshot(source, b'fixture-only')
        fields = ('123456', 'Example Corp', '10-K/A', '20250825',
                  'edgar/data/123456/0000123456-25-000001.txt')
        obs = parse_fields(fields, source, snapshot, line_number=12,
                           parser_version='fixture-index-parser-v1',
                           schema_version='sec-index-v1')
        self.assertEqual(obs.row.cik, '0000123456')
        self.assertEqual(obs.row.filing_date.isoformat(), '2025-08-25')
        self.assertEqual(obs.row.accession_number, '0000123456-25-000001')
        self.assertEqual(obs.row.form_type, '10-K/A')
        self.assertEqual(obs.original_fields, fields)
```

`fixture_source(period: str = "2015Q1", kind: str = "quarterly")` is the existing validated builder. Run focused test_etl_parser.py; expect missing parser or golden assertion failure.

- [ ] **Step 2: Implement the parser core and exact fixture bytes.** Register `sec-index-parser-v1` and local-only fixture aliases v1/v2; no arbitrary label may pretend to have a tested parser. `fixture-envelope-v1` is acquisition provenance only. Reject unsupported schema/parser before storage opens. parse_fields uses:

```python
# Within parse_fields, after requiring exactly five string fields:
original_fields = fields
cik, company, form, text_date, path = (value.strip() for value in fields)
if not re.fullmatch(r'[0-9]{1,10}', cik) or not company or not form:
    raise ParseError(line_number, 'invalid CIK or empty company/form')
normalized_cik = cik.zfill(10)
pattern = r'[0-9]{4}-[0-9]{2}-[0-9]{2}' if source.kind == 'quarterly' else r'[0-9]{8}'
if not re.fullmatch(pattern, text_date):
    raise ParseError(line_number, 'unsupported filing-date spelling')
try:
    filing_date = date.fromisoformat(text_date)
except ValueError as error:
    raise ParseError(line_number, 'invalid calendar date') from error
if any(char in path for char in ('\\', '%', '?', '#')):
    raise ParseError(line_number, 'unsafe archive path')
safe_relative_path(path, 'archive_path')
segments = path.split('/')
if (len(segments) >= 4 and segments[:2] == ['edgar', 'data'] and
        re.fullmatch(r'[0-9]{1,10}', segments[2]) and
        segments[2].zfill(10) != normalized_cik):
    raise ParseError(line_number, 'archive path CIK mismatch')
match = re.fullmatch(r'edgar/data/[0-9]{1,10}/([0-9]{10}-[0-9]{2}-[0-9]{6})\.txt', path)
accession = match.group(1) if match else None
row = IndexRow(normalized_cik, company, form, path, filing_date, accession,
               source.source_id, snapshot.sha256, parser_version, schema_version)
return Observation(row, original_fields, line_number)
```

Catch safe-path/record validation errors as ParseError with physical line number, never silently skip. iter_observations streams selected ZIP member/plain source, checks ASCII/line endings/header/separator and parses every subsequent nonempty row; a blank row within the data section is refused. Use acquisition validation for archive/member/CRC/size/denial checks at transform time and keep parsing independently strict. Source receipt without any rows is invalid. Preamble/footer cannot swallow data or repeated headers. Nullable legacy example is `edgar/data/123456/legacy-annual.txt`; preserve original path case and report its synthetic nature.

Create quarterly golden with ISO dates, CRLF and exact Filename header; daily with compact dates, LF and exact File Name header. Store hand-authored expected normalized rows in expected.json, including two paths with same company/date and distinct amendments. Manifest records exact fixture hashes and synthetic provenance; expected output is not generated by the production parser.

- [ ] **Step 3: Complete the refusal/boundary matrix and green.** Cases: decimal CIK length/zeros; leap/non-leap days; impossible compact/ISO dates; blank fields; four/six columns; absolute/traversal/double slash/backslash/escaped/query/fragment/control paths; CIK mismatch; safe legacy null including a nested/unrecognized safe path; case-preserving path; final newline/no final newline; bad ASCII/newline/header/separator; malformed last row after valid rows; amendments and cross-quarter daily filing date. Assert line/reason and unchanged originals. Run guarded test_etl_parser.py and existing test_validation.py; expect OK.

- [ ] **Step 4: Commit owned parser/tests/fixtures.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/parser.py packages/sec-edgar-ingest/tests/test_etl_parser.py packages/sec-edgar-ingest/tests/fixtures/etl
git commit -m 'feat: parse retained index rows with strict golden contracts'
```
