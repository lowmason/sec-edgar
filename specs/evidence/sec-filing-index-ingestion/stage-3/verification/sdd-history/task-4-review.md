Spec Compliance: FAIL. Task Quality: Needs fixes.
Reviewer: task4_review, capable gpt-6-astra. BASE 1f6726d66f7cd13af377c2cd8f9e3d52c741e99b HEAD 9f47166ca318b0a9f8e8cf6bb428e49bfb8e4486.

Strengths: prescribed source revision selection/current-version raw replay (catalog.py:26,198); SQLite quarterly membership/conservative absences/business vs provenance counts (catalog.py:114); bounded 8192 Arrow batches with 8193-row test (catalog.py:150, test_etl_catalog.py:348); substantive exact captures/canonical hashes/schemas/origins/precedence (manifest.py:26,88,189); gate index after validation/no pointer writes (catalog.py:178,198, test:280).

Critical: none. Minor: none.

Important I1: Delta validation can accept an ungated candidate that withdraws active filings. manifest.py:171,189,251,267 reads previous only when retained_from_generation exists; closed withdrawals normally do not retain it. Validator checks supplied counts/shapes/current membership/after values but never recomputes delta against exact base. Counterexample: empty correctly schemed changes.parquet, update its hashes/length/count, set withdrawn=0/gate=clear, update manifest hash/length and candidate_ref=None. Same selected-source fingerprint/generation identity and correct current membership; supplied empty change counts agree; first-generation safeguard doesn't apply. validate_candidate and immutable adoption (catalog.py:198) accept ungated removal.
Required remediation: preserve exact base capture for every noninitial candidate, compare exact base/output rows independently to verify complete changes set, before values, added/updated/withdrawn/unresolved counts and provenance refresh before gate acceptance. Add adversarial suppressed-withdrawal-with-consistent-hashes/counts and forged/omitted updates tests.
Supporting retained-base sidecar is reasonable strict-contract preservation but insufficient for general delta verification at current scope.

Cannot verify: acquisition guards/deadlines/quarantine/conflicting duplicates/atomic storage/exact pins -> earlier reviewed Tasks 1–3/full Task 7 check. Publication CAS/pointer/approval -> Task 5; integrated Linux Stage 7 remains reserved. Named unchanged checks: GenerationManifest construction lacks delta semantics; Snapshot fingerprint fields don't fix I1.
Evidence: green-final.json 26 tests exit 0/no warnings; no rerun. Truncated diff recovered from same package; no separate changed-file reads. Three created files match scope; support_etl unchanged/real-store tests.
