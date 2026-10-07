# Offline evidence locations

Stage 2 completion receipt: specs/evidence/sec-filing-index-ingestion/stage-2/verification/completion-checkpoint/completion-receipt.json
Final fixture proof: specs/evidence/sec-filing-index-ingestion/stage-2/verification/sec-edgar-stage-2-46bhxh8j/ (96 payloads).
Final installed proof: specs/evidence/sec-filing-index-ingestion/stage-2/verification/sec-edgar-wheel-n0zc5qlc/ (78 payloads).
Retained reviewed source receipt: specs/evidence/sec-filing-index-ingestion/stage-2/verification/completion-checkpoint/sdd/completion-evidence/tested-reviewed-source-equality.json (88 files).
Preflight verified these hashes/payloads; read actual retained bundles rather than an ephemeral Stage 2 .sdd.

Stage 1 ten complete receipts: specs/evidence/sec-filing-index-ingestion/stage-1/specimens/matrix.json; SEC-0141 through SEC-0150 inspection JSONs in the same directory. Each original_path is relative to stage-1 evidence root and resolves beneath specimens/; separately retained receipt bodies are listings/SEC-0141.body through SEC-0150.body. Matrix fields include role, url, evidence_id, inspection, original_bytes, original_sha256, row_count, filing_date_bounds, text_family. IDs 0141..0145 are quarterly ZIP/ISO/CRLF/Filename; IDs 0146..0150 are daily IDX/compact dates/LF/File Name. This bounds observed evidence to ten receipts, not entire ranges.
Existing retained fixture manifest: packages/sec-edgar-ingest/tests/fixtures/retained-manifest.json (83 records).
Existing verifier: packages/sec-edgar-ingest/tests/test_validation.py::ValidationTests.test_all_ten_hash_checked_retained_originals_validate.
Exact original hashes/counts/dates must be read from retained inputs when proving parser behavior; this lookup did not run the parser.
