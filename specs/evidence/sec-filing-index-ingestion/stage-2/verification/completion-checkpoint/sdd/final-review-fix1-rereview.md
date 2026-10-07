# Stage 2 final whole-branch fix1: scoped re-review

All three original findings are ADDRESSED. No new Critical, Important or Minor finding was identified in this fix range. Scoped specification review: PASS. Scoped code quality review: PASS. The fixes resolve the original whole-branch review's W-I1/W-I2/W-M1 objections; the controller can compose that resolution with the completed original review and perform the remaining completion protocol. This report does not itself issue a Stage 2 completion stamp, plan tick, retirement, integration or Stage 3 approval.

Review BASE: `9098fe9b664d9f44a663fdd8357e34030c37e932`.
Review HEAD: `e458010ead6709c16e992fa22a33997d3aa36ef0`.
Checkout: `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar`.
Reviewer route: `gpt-6.1-sol`, reasoning effort `max` (GPT-6.1 Max), fresh scoped context. The dispatch's disclosed default-role fallback retained the named review rubric, model, effort, freshness and read-only contract. No nested reviewer, additional agent or alternate Codex CLI seat was used.

Scope was ONLY the original findings copied verbatim in the brief and defects introduced by their fixes, including the test-only midnight correction. The prior whole-branch audit was not repeated. The complete authored view was read in bounded passes; the truncated portion of the first display was recovered from the stated file. All eight authored diff blocks were independently compared byte-for-byte with their corresponding blocks in the full standard package.

## Original findings

### W-I1 — ADDRESSED

Original Important finding: **[P2] A supported historical discovery cannot fit Azure’s single string payload.**

Relevant exact hunks are the Azure import/constants hunk `@@ -12,27 +12,53 @@`, backend hunk `@@ -42,111 +68,152 @@`, factory hunk `@@ -417,14 +484,14 @@`, and the complete new 301-line adapter test file.

Current anchors:

- [azure.py:39](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py:39): emitted entity bounds.
- [azure.py:77](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py:77): optional compatible shared-object constructor.
- [azure.py:96](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py:96): inline/content representation and publication order.
- [azure.py:118](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py:118): complete value decoding and identity validation.
- [azure.py:176](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py:176): whole-entity conditional REPLACE.
- [azure.py:193](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py:193): logical-value scan filtering.
- [azure.py:489](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py:489): factory supplies the same existing AzureObjectStore.
- [test_azure_state_payloads.py:140](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/tests/test_azure_state_payloads.py:140): actual intended-history registration, reopened reads, scans and whole-record CAS; the seven following tests cover the remaining representation and recovery cases.

Small values retain the original PartitionKey, quoted RowKey, StableKey and canonical JSON Payload fields. The 64 KiB UTF-16LE threshold is checked against the emitted string, including non-BMP characters. Large values become one six-property Table descriptor naming a complete immutable canonical UTF-8 envelope by full SHA-256 and byte count. The envelope contains exactly format_version, partition, key and value. Its partition binds both the existing namespace and record kind; its key binds the complete stable identity. The internal content path is derived from the validated hash under the existing worksets container.

The backend checks all emitted string properties, key lengths, property names, scalar allowance and total entity size before publication. The whole-entity calculation includes StableKey and quoted RowKey, counts Timestamp, and reserves 1,024 bytes for system overhead. The four/six-property shapes remain within the specified service limits.

The object is written immutably and verified before any descriptor create or replace. REPLACE still uses the actual response ETag with IfNotModified and UpdateMode.REPLACE. There is one authoritative Table row for each complete logical value. A losing or failed candidate can remain as unreferenced immutable content; it cannot select or overwrite the winning Table version. No multi-row boundary split, truncation, narrowed history or cross-store transaction assumption was introduced.

Decoding checks the actual Table version and stable identity, supported descriptor format, digest, nonnegative integer byte count, exact content length/hash, exact envelope fields, canonical bytes, namespace/kind/key agreement and JSON-object value. Unsupported or ambiguous inline/content rows, missing or corrupt objects, and correctly rehashed envelopes with conflicting identities fail closed. Existing inline rows and inline-to-content-to-inline transitions remain covered. Get/insert/replace/scan return paths use the same complete decoder, and the existing SourceState/Attempts routing is unchanged. The retained layout helper also inserts and reads an oversized Attempt in the Attempts Table.

The corrected retained RED reproduces PropertyValueTooLarge through the actual pinned SDK serializer and a service-limit-enforcing offline transport. It fails on actual _inventory/begin_discovery registration for 2010Q1 through open 2026Q4, with 86 units. This regression fixture produces **83,022 UTF-16LE bytes**, while the original reviewer probe produced **82,334** because its context/identities differ. They are not identical inputs; both exceed the same property ceiling.

All eight adapter cases appear as `ok` in the final complete 302-test log. The separate retained layout proof was inspected, and its saved envelope bytes/hashes/identity/canonical representation and entity calculations were independently checked without executing production code. Its three emitted entities have maximum string size **23,360 UTF-16LE bytes** and maximum conservative entity bound **24,786 bytes**. The original/winning boundary envelopes retain 86/85 complete gaps. A distinct stale-CAS candidate retains 86 gaps plus its losing-only marker, while the winner stays at its actual service ETag and references a different hash. The 1,200,011-byte logical Attempt uses a 1,200,128-byte complete envelope and a small descriptor.

This addresses the accepted-history representability failure while preserving complete-record CAS, old inline compatibility, fixed resources, existing client lifecycle and request-budget contracts. It is offline adapter evidence, not an observed live Azure service acceptance.

### W-I2 — ADDRESSED

Original Important finding: **[P2] Snapshot decoding omits the exact source-period validation performed by its producer.**

Relevant exact hunks are `@@ -1,20 +1,21 @@`, `@@ -86,59 +87,80 @@`, and `@@ -151,21 +173,17 @@` in worksets.py, plus the new workset regressions.

Current anchors:

- [worksets.py:97](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/worksets.py:97): shared immediate-directory, source-quarter and pinned-endpoint checks.
- [worksets.py:109](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/worksets.py:109): shared exact SourceID/raw-path/representation/envelope validation.
- [worksets.py:148](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/worksets.py:148): decoder reconstructs and validates the canonical Source.
- [worksets.py:174](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/worksets.py:174): producer uses the same semantic validator.
- [test_worksets.py:152](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/tests/test_worksets.py:152): rehashed wrong-period and identity/address/kind/envelope rejection cases.
- [test_worksets.py:190](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/tests/test_worksets.py:190): compatible multiple-member daily day-labelled directory.

The decoder now derives the sole supported source child from the declared immediate listing and exact raw period: master.zip for a quarterly member, or master.YYYYMMDD.idx for a daily member. The unchanged Source constructor validates the canonical URL hierarchy, exact URL-derived SourceID, period and representation. The shared directory validator establishes immediate-directory membership, matching source/directory quarter and pinned endpoint; the shared snapshot validator checks the full raw address, SourceID, representation and envelope. This prevents the original 2015Q1 SourceID/directory with a 2015Q2 raw path even when the outer workset digest is recomputed correctly.

Historical daily listing labels that use one member's ISO day are compared by quarter only. Stored labels are not changed, and each actual raw day and URL-derived SourceID remains exact. This preserves a day-labelled listing with multiple valid same-quarter daily members without admitting the wrong day for a particular SourceID.

The original rehashed RED retains 18 tests and six behavioral assertion failures with zero helper errors. The isolated daily-label compatibility RED is retained. All four new workset cases are `ok` in the final complete check. The retained compatibility inspection compares BASE and current encodings for quarterly, leap-day daily and two-member daily snapshots; it also decodes and byte-identically re-encodes the four historical combined worksets. Its method and saved results were inspected. Neither canonical serialization, SourceID generation nor source/snapshot address/identity format changed.

The exact persisted/public semantic mismatch is therefore resolved without changing existing valid bytes or IDs.

### W-M1 — ADDRESSED

Original Minor finding: **[P3] The current runbook still describes the approved two-config sequence as awaiting an owner decision.**

Relevant hunk: `@@ -105,23 +105,27 @@`.
Current anchor: [sec-edgar-ingest-acquisition.md:115](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/docs/runbooks/sec-edgar-ingest-acquisition.md:115).

The operative paragraph now states the approved separate quarterly start=end2015Q1 and daily end=open workflow and links the actual owner Yes receipt and completed combined sequence. Both links resolve to retained files. The Yes receipt's SHA-256 is `f9720b21df9f56135386496f39bb2ec4d310614410b1b5f8645fdc07a7b963ac`. The linked historical combined summary has SHA-256 `70bbe89ad9f125df78c985fd4f8d376365abe726075824ba04e605e9ec629bc9`.

The complete linked/current summaries were parsed. Their actual quarterly download/reuse and daily incomplete/recovery/final-reuse outcomes support the paragraph. All seven result contexts in each summary retain the approved durable state root, coordination namespace and 3 requests/second / one active collector settings. The daily endpoint is open; the quarterly endpoint remains 2015Q1. Earlier pending-status records remain history.

W-M1 is fixed, with no deferral or renewed owner approval needed.

## New findings

**Critical: none.**
**Important: none.**
**Minor: none.**

The introduced midnight helper fix and regression were reviewed specifically within this section's scope. [support.py:762](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/tests/support.py:762) now uses the same captured actual UTC `now` for started_at, the existing ten-second deadline and pinned_on. [test_acquisition_processes.py:17](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/tests/test_acquisition_processes.py:17) deterministically supplies 2026-10-07 and checks the unchanged pin_context guard without enabling clock override.

The retained initial complete check actually has 301 test records, 130.023 seconds and one error. The diagnostic context pins October 6 while starting on October 7; the actual date guard rejects the mismatch before begin_attempt. The retained diagnostic child tracebacks then reject result publication without a begun Attempt. All three children, PIDs 49257/49258/49259, exit 1, leave no Attempt rows, and terminate with unbroken barriers. The deterministic regression has a retained RED for that same guard. The first GREEN's optional-fixture assertion correction is preserved, followed by five process cases OK in 12.990 seconds and all five OK again in the final 302-test check.

The fix changes only test helper date data and its regression. Production guards, exchange/lease/request behavior, process deadlines and timeouts remain unchanged. The current retained process inspection records PIDs 50088/50089/50090 all exit 0, one Binding winner/two conflicts and replay downloaded=0/unchanged=1. The takeover, timer, crash and guard summaries remain retained; no broader coordinator audit or capacity conclusion was inferred from them.

## Evidence, verification and inspection limits

The exact package receipt and actual bytes agree:

| Package | Bytes | SHA-256 |
| --- | ---: | --- |
| Standard review-9098fe9..e458010.diff | 17,483,590 | 24dbdd30133e7f860fcf7d67c884697e117754a7631ae0c20eb5de66c6ef4ece |
| Complete authored-final-review-fix1-9098fe9..e458010.diff | 66,294 | 47755a79e16a121074fea3238e265f91126446ee835207de5a2cd49d0c56a908 |
| Exact final-review-fix1-changed-paths-9098fe9..e458010.json | 2,890,892 | 5c258c052e6782c718c2453c91fd3be5ccdde09d0b0eac5cf308bf8cd0ba3c98 |

The standard package records the actual five commits through HEAD. Independent read-only file inspection verified all **5,218** changed-path size/hash records, including all **5,210** payload/control omissions from the authored view. The authored eight blocks exactly equal the selected standard hunks. The checkpoint's **5,208** manifest records were independently hash-verified. Every one of the **5,013** retention-map originals and copies matched; all **nine** gzip records decompressed to their exact original size/hash. Both fresh bundle manifests and physical file/byte totals matched. No payload omission was waived.

The latest prescribed retained command is exactly `scripts/check-sec-edgar-ingest.sh`, cwd the frozen checkout, exit 0 and wrapper duration 106.99618458282202 seconds. The full stderr was parsed: exactly **302** test records, every one ending `... ok`, footer `Ran 302 tests in 106.619s`, `OK`, followed only by successful source-distribution/wheel build records. Full stdout contains CLI help and version 0.1.0. The unchanged script also requires compileall and CRLF-equivalent diff whitespace validation before its successful exit. Stderr is 49,948 bytes, SHA-256 `dbd06ab5e7211f84abbb04ead35838721937e0ec54abe914cd20896403a6273a`; stdout is 239 bytes, SHA-256 `ba27b3d9a4d1a3c5ca3a96921f0a6905567cb342878a6040211c3f49ecd2a4f3`. Retained covering runs are 146/19.746 seconds and 146/20.004 seconds, both OK.

The fresh installed bundle sec-edgar-wheel-n0zc5qlc has 79 files / 489,607 bytes / 78 inner manifest records. Its manifest hash is `126a1c3c666e1e41f63d37f68ec95ec145f55a28ec6a1ea97676fa9941caff47`. The independent command/argv/exit-receipt inspection confirms all eleven commands exit 0. The import and CLI paths belong to the fresh environment's site-packages/bin outside source cwd; twenty runtime pins and package version 0.1.0 are recorded. Four transports and exact replay reuse remain evidenced.

The approved combined bundle sec-edgar-stage-2-46bhxh8j has 97 files / 502,536 bytes / 96 inner manifest records. Its manifest hash is `beee194e1a67f1870c2b1d948c9ea29044f6ba0b6d9da0008443ccb13a8d4ab7`. All eleven actual command/argv/expected-exit receipts match **2/0/0/0/0/2/0/3/3/0/0**. The complete retained inspection records the matching seven Attempts, three Bindings, eleven TransportAttempts, ten cursors, exact complete/incomplete replay equality, 404-to-200 recovery and final reuse. Its actual starts on October 7 are distinguished from immutable source discovery origins and explicitly labelled historical fixture pins.

Both retained archives were independently read without extracting or installing them. All **nineteen** production/typing sources match the current checkout byte-for-byte in both wheel and sdist; README is exact. Current wheel is 79,085 bytes, SHA-256 `349b9524fca4963de4a2ffdf3fb96f28708c01dba49564594a92944cc3ee5d28`; sdist is 67,566 bytes, SHA-256 `fce247b48d02155eed403ff0456f5e5bc246cde244534e6eb428c9a44d361b30`. Only Azure and worksets are changed production sources in this range. Retained source-revision controls record unchanged configuration, dependency lock/pins, guard, drivers and 27 inspected SDK hashes.

Corrected inspection assumptions were kept explicit. The accepted-history logical byte count is context-dependent, so this fixture's 83,022 bytes is not represented as identical to the original 82,334-byte input. Build-normalized pyproject.toml was compared as parsed TOML semantics, with actual archive/source bytes checked separately. Actual proof roots came from retained receipts. In this review, guessed metadata filenames were resolved via the recorded helper path and manifest inventory; installed command receipts use commands.json and omit the combined driver's expected field. The initial read-only schema assumption raised KeyError, was corrected to the recorded schemas, and the complete receipt inspection then passed. These were inspection-helper corrections, not acquisition failures or reruns.

Reviewer actions were limited to reads and bounded stdlib file/hash/JSON/gzip/archive inspections using the checkout's `.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1`. No production module or provider client was executed, and no credential, live SEC/Azure, auth, compute, install, test suite, build or acquisition sequence was invoked. No concrete introduced risk required an additional guarded production/stub probe. The only authorized write is this UTF-8 report outside the checkout; source, docs, proof, index, HEAD and worktree state were not mutated.

The evidence is local macOS 26.6.2 arm64 / Python 3.14.0, with scripted Azure SDK transports and explicitly selected local fixtures. It does not establish live Azure/SEC/auth/registry/compute behavior, accepted Linux amd64 / Python 3.14.8 / default-90-second worker measurements, a recovery horizon or global format/capacity coverage. **All 22 Stage 7 checks remain reserved.**

Assessment: **ready for the controller's completion protocol with respect to this scoped final fix review; no further fix required in this scope.**
