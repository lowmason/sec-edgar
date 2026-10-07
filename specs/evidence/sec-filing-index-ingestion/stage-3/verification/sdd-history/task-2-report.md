# Task 2 implementation report

Status: DONE
Commit: 3b2c03a4f129d88d1bb4cd7f9ada314fb895ad85
Base: 966bd9e6bc8d5ce3803c0db7e95a4011e94e2ee9
Worktree: /Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar

## Scope and produced interfaces

Only the seven assigned parser/test/fixture files were committed. Evidence and this report are retained in the assigned ignored .sdd directory. No other checkout, Settings, dependency pin, live endpoint, client, credential, original or earlier evidence was changed.

```python
ParseError(line_number: int, reason: str)  # ValueError subclass; line_number/reason attributes
supported_parser(version: str, *, fixture: bool) -> None
parse_fields(fields: tuple[str,str,str,str,str], source: Source, snapshot: Snapshot, *, line_number: int, parser_version: str, schema_version: str) -> Observation
iter_observations(path: Path, source: Source, snapshot: Snapshot, *, parser_version: str, schema_version: str) -> Iterator[Observation]
```

The production parser version is sec-index-parser-v1; explicit fixture-only registrations are fixture-index-parser-v1/v2. supported_parser rejects fixture aliases when fixture=False. Parse entrypoints permit registered fixture aliases for offline orchestration, and validate versions/schema before opening sources. fixture-envelope-v1 is never registered as a parser.

Rows keep ten-digit CIKs, trimmed normalized values, the exact original five strings, physical line numbers, safe case-preserving legacy paths with null accession, source identity/hash and versions. Daily compact dates determine the filing's actual quarter independently of the daily source period. Duplicates are yielded without parser-global conflict state; Task 3 owns source-wide duplicate conflicts.

The parser streams selected ZIP/plain input, independently recognizes exact family headers and newline conventions, requires the dashed separator, rejects blank/repeated-header/footer/malformed-final rows, non-ASCII/control bytes, and preheader content outside recognized SEC metadata labels. Acquisition's archive/CRC/size/denial validation remains authoritative at transform time.

## Retained test evidence

Each retained command JSON includes argv, cwd and exit; separate files retain complete stdout and stderr.

- 01-red and 02-matrix-red: missing parser module, exit 1, explicitly permitted initial missing-feature RED.
- 03-green: intermediate exit 1; Unicode CIK refusal used generic text reason before CIK validation. Reordered the existing CIK validation before generic field text validation.
- 04-preamble-red: actual assertion failure, exit 1; malformed preheader text was swallowed. Added recognized metadata label gating.
- 05-green and 17-committed-green: parser plus existing validation, 19 tests OK, exit 0. Seven parser tests contain extensive subtest matrices; validation's retained ten-original envelope proof passed without parsing their observation rows.
- 06-diff-check, 07-status, 08-owned-diff: retained self-review.
- 09-add, 10-staged-check: staged diff flagged intentional CRLF as trailing whitespace, exit 2. Bytes preserved; no repository config changed.
- 13-staged-crlf-check: command-local cr-at-eol whitespace handling, exit 0.
- 14-commit, 15-head, 16-status: explicit owned-file commit, exact hash, clean checkout.

All uv commands used --offline --frozen and all tests used tests/network_guard.py. No installation/native baseline was repeated. Stage 7 full retained-observation replay remains reserved. Read-only inspection of the ten retained preambles established the five allowed metadata labels; no specimen data rows were parsed by the new parser in that inspection.

## Fixture provenance and hashes

All three index files are compact hand-authored synthetic fixtures, including the legacy examples. expected.json's normalized values and original strings were authored explicitly before implementation, independently of the production parser. quarterly.idx uses exact CRLF and Filename; daily/legacy use LF and File Name. The deterministic test ZIP uses fixed 2000-01-01 member timestamp, master.idx, and DEFLATE from quarterly.idx; no ZIP fixture was committed. Manifest records byte counts and SHA-256 for the three indexes and independent expected JSON.

- daily.idx: 140 bytes; SHA-256 `99a4d772a4dbe78d023137d4e4ca5af3c50b404a223c4283c5c81944c02d5329`
- expected.json: 2263 bytes; SHA-256 `67a0efd1b91805b8be16ffe8af44f2011c05876ff8756b6731504a37e0501d58`
- legacy.idx: 197 bytes; SHA-256 `8eb7edfa8740d2a3a0d23c13f4e6a86bd249c1b743cb26be3eeca9a6f813831a`
- quarterly.idx: 260 bytes; SHA-256 `a442b38e07b4f0161f9dfccb0465d9f8721adc4012309904ccccd10a8a6982c9`

## Self-review and clean-code application

Reviewed produced interfaces, full owned parser diff, fixture originals and goldens, refusal paths, registration/preopen failures and duplicate preservation against the brief. Applied N1/N4 to descriptive parsing/state names; G25 to parser/schema/field-count and metadata-label constants; G30/G34 to separating physical text validation from row normalization and source opening; T1/T5/T6 to exhaustive boundaries and the focused preamble regression. No adjacent cleanup was performed. C3 keeps only module intent docstrings; no explanatory implementation comments or speculative abstractions were added.

Concerns: none blocking. Native worker memory/runtime/scratch capacity and full retained observation replay are not claimed here; their reserved Stage 7 proofs are untouched. No user code contribution was requested because every behavior was prescribed. No subagent reviewer was spawned.
