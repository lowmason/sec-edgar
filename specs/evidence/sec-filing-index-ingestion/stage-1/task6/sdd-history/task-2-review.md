# Task 2 review

Reviewed Task 2 brief and Global Constraints, report, supplied review diff, retained validator/offline command results, local helper and representative retained listing metadata. Base/head remains `321c93af`; evidence is uncommitted. No SEC or Azure access, production edits, suite reruns or artifact regeneration occurred. One stdlib-only in-memory transport reproduction was used for the finding below.

## Spec verdict: PASS for the inventory accounting checkpoint

The checkpoint supplies 68 unique requested-quarter summaries for 2010Q1–2026Q4 and the correct 48-unit development subset from 2015Q1. All requested full-index year/quarter directories have successful listing evidence, with actual discovered master representation children. Root/year-QTR similarity remains an explicit body-comparison question. Retained listing dates/sizes are preserved; listing sizes are appropriately distinguished from actual bytes and expansion.

Daily discovery covers all 17 requested years, first/last available quarters of each year, the current and preceding quarters, required 2026-10-01 handoff, and an actual published 2026-10-02 candidate. The report correctly distinguishes 35 inspected quarter listings from 33 listed but uninspected middle quarters. The validator's `available: 36` includes the daily root; it does not contradict the 35-quarter report. D-14 makes the recovery limitation actionable without inferring an accepted range revision. Listings establish receipt-time availability, not ingestion completeness or arbitrary outage recovery.

The exact retained output and root's independent exit-0 verification support the 140-attempt/1,689,512-byte/zero-specimen accounting, evidence hashes and sequential spacing. Attempt identity, raw listing entity bytes, headers, schema/children and selection decisions remain linked. Successful responses needed no fallback. Production package binding and resource/runtime decisions remain outside Task 2, including the separately accepted temporary Azure exception.

Manual novelty disposition is explicit and acceptable for this checkpoint: `.sit`/`.z` are unselected optional codec alternatives with unknown contents, not newly established selected content families. No automated novelty detector is implemented or claimed tested. Root has paused access pending review. Task 3 must preserve the manual stop on newly observed selected body format, row/path family or expanded sampling; this checkpoint does not authorize a new window or expand the budget. Candidate transition rows are actual retained children, and Task 3 must make and record its final specimen selection.

## Quality verdict: CHANGES REQUIRED before shared-helper reuse

### P2 — Retain and account for partial chunked response bytes before retry

**Location:** `specs/evidence/sec-filing-index-ingestion/stage-1/investigation-tools/sec_inventory.py:180–189`.

`response.read()` can raise `http.client.IncompleteRead` after consuming complete chunks, exposing those bytes in `exc.partial`. The generic exception handler records only the exception string. Those partial bytes never reach the original body, digest, per-attempt count or shared byte counter, and the subsequent error-based retry can issue another request. This breaks exact failed-response preservation and shared received-byte accounting. It can also discard an access-denial marker in the partial body before denial detection.

Grounding: a local stdlib-only `HTTPResponse` over `BytesIO`, given a 200 chunked response containing the complete four-byte `DATA` chunk followed by EOF before the next chunk header, raises `IncompleteRead(partial=b'DATA')`. Inspection of `_read_chunked` confirms this is consumed response data. The existing successful listing receipts are unaffected; the failure is in the helper's future error path.

**Remediation:** handle `IncompleteRead` where the body handle is still open; preserve and hash its available partial entity bytes and add them to attempt/shared counts, keeping the response failed. Preserve original evidence and pass the partial body through denial handling. If a transport failure leaves the total received-byte accounting unknowable, halt for root reconciliation instead of silently treating it as zero and retrying. Add a bounded offline regression proving partial retention/hash/counts, failed outcome and shared-budget/denial behavior. Do not re-fetch existing evidence.

## Task 3 checkpoint disposition

The inventory checkpoint supports Task 3 specimen planning and actual-child selection. Live reuse of the shared helper should wait for the P2 fix and scoped offline verification/re-review. The original deadline, state, ledger, lock and remaining attempt/byte/specimen budgets remain authoritative. D-14 and all unsupported representation/body claims remain open; this is not Stage 1 readiness approval.

## Scoped repair re-review — P2 ADDRESSED

Reviewed `task-2-fix-review.diff`, the appended Task 2 repair report, final helper/read-loop code, added offline regression cases, retained RED/GREEN receipts and root's independent offline output at `/private/tmp/sec-edgar-root-incomplete-read-verification.txt`. No network requests or further suite reruns occurred in this re-review.

The helper now catches `IncompleteRead` while the original body handle remains open, collects both the direct partial and the real stdlib chained current-chunk partial, and sends those bytes through the existing write, digest and attempt/shared accounting path. Re-raising preserves the failed response outcome and prevents completed-specimen increments. The existing retained-body denial scan now sees these partial bytes. Normal successful reads and request controls are unchanged.

The regression evidence demonstrates the direct case's original RED failure, an additional real-stdlib chained-partial RED failure, and final full offline GREEN exit 0 plus compile exit 0. Direct partial retention/hash/counts pass with sufficient and exact remaining-byte budgets; the real `HTTPResponse` truncated chunk retains all ten available entity bytes, records failure and leaves completed specimens at zero. Root's independent 23:51:34 UTC output corroborates these cases. Current helper and check-script hashes match the retained repair command receipt.

**Updated quality verdict: PASS for the reviewed Task 2 checkpoint and scoped repair; no outstanding actionable findings or new regressions identified.** The inventory spec verdict remains PASS. Task 2 supports proceeding to Task 3 within the original authorized window and shared limits, subject to root's final specimen selection and manual novelty control. No new deadline, sampling allowance, body support, historical ingestion coverage, production binding or Stage 1 readiness is approved by this review. Earlier quality/Task 3 restrictions above describe the pre-repair state and are superseded by this disposition.
