# Development history

## 9-sec-filing-index-pre-dispatch-cost — 2026-11-15
Plan: specs/plans/completed/9-sec-filing-index-pre-dispatch-cost.md · Spec: specs/completed/sec-filing-index-pre-dispatch-cost.md (retired) · Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 2a1

Differences from the design:
- Ruling, contradicts spec (Task 3): concern 1 (spec :183-185 says a malformed WorkflowMember row "is skipped, as `inventory()` skips it today"; on the real LocalStateStore a list-valued row makes `scan` raise ValueError('value must be a mapping'), so neither today's reuse nor inventory() skips it) stays as built — deciding spec sentence (specs/sec-filing-index-pre-dispatch-cost.md:97): "It finds the same candidates, returns the same gaps in the same order, and writes the same binding as today." — new and old reuse raise the same ValueError and bind nothing, so H5 holds; the isinstance(dict) guard is reachable only from a simulated store — if wrong, nothing in production differs; spec :183-185 wording is imprecise for the real store (note for the final review, no spec edit).
- Ruling (Task 6): finding 3 (freeze had no factor-2 check): controller chose a sixth timed function pair (results.validate_member_provenance, results.validate_capture) over failing closed — P4 (plan line 101) says each slope is "checked against the median per-member call time of its phase" — if wrong, the freeze check is looser than P4 intends.
- Deviation: the worktree was made with `git worktree add`, not `EnterWorktree`. Source: plan, header.
- Deviation (Task 4): D4: `select_twice` primes one discovery before the store copy, so the equality tests cover a primed discovery only. Source: plan, Task 4.
- Deviation (Task 4): D5: the drain test's `reuse` stand-in takes `**kwargs`. Source: plan, Task 4.
- Deviation (Task 6): after the task review, the path refusal compares file identity (`os.path.samefile`). Source: plan, Task 6.
- Deviation (Task 6): D6: `diff` assigns the 3 added `Failure` rows by `run_id` plus `discovery_id`. Source: plan, Task 6.
- Deviation (Task 8): the `.venv` link pointed at `/tmp/s2a1-venv`, so the gate tested the worktree's code. Source: plan, Task 8.
- Deviation (Task 8): the final review found one Important test gap (the H4 test), fixed in `20ac48b`; a test only, so the gate did not run again. Source: plan, Task 8.
- Deviation (Task 9): the Step 4 commands ran from a temporary script with `set -e`. Source: plan, Task 9.
- Deviation (Task 10): Steps 3 and 4 ran as one background chain that stops at the first non-zero exit. Source: plan, Task 10.
- Deviation (Task 10): `project` exited 4 for `before_discovery`; the owner accepted a hand-worked bound of 281.2 s (D9). Source: plan, Task 10.
- Deviation (Task 11): `walls` ran from a temporary script that sampled the load. Source: plan, Task 11.
- Deviation (Task 11): the longest wall, 1,074.9 s, is above 1,056 s; the owner raised the reserve under the Stage 1b rule (D10). Source: plan, Task 11.
- Deviation (Task 12): the reserve changed from 1800 to 1824 as well as the release (D10, D11). Source: plan, Task 12.
- Deviation (Task 12): `release.md` elides `sec.user_agent` in the binding, because it holds the owner's contact address. Source: plan, Task 12.
- Deviation (Task 13): beyond spec §7's list: the 2a release's 3,200 s selection time, a reserve of 1824 in the runbook example, and the gap name in the 2a1 spec §4.4 item 1 (D12). Source: plan, Task 13.
- Deferred: 3 items. Source: specs/deferred_items.md, § 9-sec-filing-index-pre-dispatch-cost.

## 10-sec-filing-data-stage-1 — 2026-11-17
Plan: specs/plans/completed/10-sec-filing-data-stage-1.md · Spec: none · Roadmap: specs/sec-filing-data-roadmap.md, Stage 1

Differences from the design:
- Ruling (Task 3): DEVIATION from plan :139 "Wire bytes come from response.raw.tell()". urllib3 2.8 leaves raw.tell() at 0 for Transfer-Encoding: chunked (probe .sdd/10-sec-filing-data-stage-1/scratch/task-3-chunked-tell-probe.py). GC :21 (5 GB = bytes on the wire) governs. Option A: read raw.stream(1 MiB, decode_content=False), count len() of each raw piece as wire bytes, decode gzip/deflate with zlib.decompressobj + max_length (loop unconsumed_tail), map urllib3 ProtocolError->ChunkedEncodingError, ReadTimeoutError->ConnectionError, SSLError->requests SSLError (as iter_content does), non-eof decompressor at end = truncated -> retry, unexpected Content-Encoding -> failed. Fake responses now expose raw.stream (not iter_content/tell) -> Task 5's fake session must too.
- Ruling (Task 3): redirects off (allow_redirects=False); 3xx -> failed. Tests reach requests exceptions via sec_filing_data.client.requests (no direct import, GC :31).
- Ruling (Task 3): 3xx body bytes uncounted -> accept (<1 KB, URLs final). Guard before the end-of-stream read -> accept (safe side). zlib.error -> outcome failed, no retry, no propagation (content fault of one response); sent back to the implementer before review.
- Ruling (Task 5): last response ok but file missing -> outcome failed, reason "ok response, but <path> is missing" -> accept. Departs from the literal plan :198; the roadmap Exit ("on disk ... or a recorded reason why not") governs.
- Ruling (Task 8): pilot SEC-extracted instances already use the XBRL instance namespace as the default (root <xbrl xmlns="http://www.xbrl.org/2003/instance">). So test_instance_with_default_namespace compares the fixture as filed (default namespace) with the fixture rewritten so the instance namespace carries an xbrli: prefix; facts must be equal. Same equivalence as plan :276, opposite rewrite direction. Fixture source: vicr-20260630_htm.xml in 0001193125-26-322462 (10-Q; has xsi:nil, divide, explicit and typed members).
- Ruling (Task 8): fixture moves the divide-unit par-value fact (F_434685c2) into kept instant context C_a5fd0091, and dei:DocumentType (F_c7d7b702) into kept duration context C_801f4d44 -> accept. With the plan's 2 kept contexts, no real fact of either shape exists there; values stay as filed and the report records provenance.
- Deviation (Task 3): the fake responses expose `raw.stream(...)`, not `iter_content` and `raw.tell()`. Source: plan, Task 3.
- Deviation (Task 3): wire bytes come from raw pieces, redirects are off, an undecodable body is `failed` (`970ce75`), and each file is fsynced before its `ok` record (`b8a84d1`). Source: plan, Task 3.
- Deviation (Task 5): an `ok` record whose file is missing gives `failed`. Source: plan, Task 5.
- Deviation (Task 7): the fetch findings were committed after Task 8's code commit. Source: plan, Task 7.
- Deviation (Task 8): Step 0 did not run, because every pilot 10-K and 10-Q held an instance. Source: plan, Task 8.
- Deviation (Task 8): the default-namespace test runs the other way, and the fixture moves 2 facts into the kept contexts. Source: plan, Task 8.
- Deviation (Tasks 8, 9 and 10): each code commit came before its live run, and the findings went into separate docs commits. Source: plan, Tasks 8, 9 and 10.
- Deviation (Task 9): `noSecuritiesOwned` gives reason `no securities owned`. Source: plan, Task 9.
- Deviation (Task 10): `xml_document` removes a leading UTF-8 byte-order mark (`e7b3775`). Source: plan, Task 10.
- Deferred: 6 items. Source: specs/deferred_items.md, § 10-sec-filing-data-stage-1.

Closed earlier deferred items:
- "Stage 6, evidence campaign and finding (parked roadmap, Stage 6 entry; platform spec V1–V12, R30): a bounded live" (deferred by sec-filing-platform-roadmap).

## 11-sec-filing-data-stage-2-provenance-and-timing — 2026-11-18
Plan: specs/plans/completed/11-sec-filing-data-stage-2-provenance-and-timing.md · Spec: specs/completed/sec-filing-data-stage-2-provenance-and-timing.md (retired) · Roadmap: specs/sec-filing-data-roadmap.md, Stage 2

Differences from the design:
- Ruling (final review): a re-run of `refetch` for an accession whose request has no response returns exit 5 before it walks the accessions, not exit 0 — spec 6.3: "So a refetch interrupted mid-request spends the whole Stage 2 byte budget in the count, and later refetches are refused." — after a kill, a re-run would print a request line that looks like a good run if wrong.
- Ruling (final review): the report's Times section has one more line, `- filings with an unreadable filed_as_of_date: <n>`, with one sub-line per accession — plan C9: "The report shows each of these cases." conflicts with Task 7's shorter line list; C9 is a requirement and the extra line removes no listed line — a later quarter's fallback to `accepted_at` alone is invisible if wrong. The expected Times lines of the plan tests gained exactly that line.
- Deviation (Task 3): two extra tests for `last_modified_at` on an unparsed `ok` filing and for the `private_to_public` and `no_acceptance` rules. Source: plan, Task 3.
- Deviation (Task 6): the CLI refuses only on a new `UnknownAccession` error, so an error after a request record exists is not reported as a refusal. Source: plan, Task 6.
- Deviation (Task 7): three existing tests moved their section index by one line (C11). Source: plan, Task 7.
- Deviation (Task 8): `check_stage1` exits 1 for an empty `tables-stage1` folder and names the missing frozen columns instead of raising. Source: plan, Task 8.
- Deviation (Task 9): the live run came before the final review, so two review fixes landed after it and `report` was run again. Source: plan, Task 9.
- Deferred: 4 items. Source: specs/deferred_items.md, § 11-sec-filing-data-stage-2-provenance-and-timing.

Closed earlier deferred items:
- "Refetch for V6 (plan 10 findings, Platform checks, V6 line): refetch `9999999995-26-002992` (form `EFFECT`, filed" (deferred by 10-sec-filing-data-stage-1).
- "SEC documentation checks for V7 and V8 (plan 10 findings, Platform checks; parked platform spec V7, V8): what the" (deferred by 10-sec-filing-data-stage-1).
