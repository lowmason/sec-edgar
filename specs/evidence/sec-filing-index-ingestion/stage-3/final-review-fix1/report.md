# Whole-branch repair round 1 combined proof

Status: DONE_WITH_CONCERNS. Capability proofs pass at code HEAD `2343f39f0e21adc2ad401a9346a8c9ffa0509040`, following documentation commit `d3c46768321de9a973f1b82258f1e224506848e5`. Stage 3 source acceptance remains blocked and owner policy pending. No completion stamp, roadmap change, integration, retirement or cleanup occurred. All 22 Stage 7 integrated checks remain reserved.

## Commands and outcomes

Exact argv/cwd/native dependencies/exit/wall timings and complete stdout/stderr are retained in each command directory. The unchanged logger source is copied as `command-logger.py`; `execution-environment.json` records process/timeout retention environment. Native Python 3.14.0/macOS arm64, PyArrow25.0.1 and frozen cached lock dependencies were used. Network/provider guards install before package imports. No production source, tests, configs, README or runbook changed during this proof turn or after the full check.

| Command | Outcome | Wall time |
| --- | --- | ---: |
| `runbook-proof.py .../runbook` | exit0; actual documented transform and publish both exit0 | 0.361s |
| `scripts/check-sec-edgar-ingest.sh` | exit0; 452 tests in163.537s, wheel/sdist/help/version/compile/whitespace pass | 164.112s |
| `etl_proof.py sequence --output .../sequence` | exit0; raw lifecycle, replay/no-op, gates, real races and deaths | 5.989s |
| `etl_proof.py installed --output .../installed` | exit0; isolated installed full sequence and help | 9.875s |
| `python3 .../audit-proof.py` | exit0; frozen tree, copied receipts, proof inventories, wheel/source/README equality | retained audit.json |

Full full-check stdout/stderr were inspected:452 successful test entries, no unexpected warnings/errors/skips; expected mocked SDK wire diagnostics are offline assertions. Installed subprocess outputs all exit0. No specimen re-scan was performed.

## Documented sample

`runbook-proof.py` explicitly uses actual `support_etl.seed_snapshot`, immutable source/snapshot worksets, Snapshot and Binding storage, and the valid synthetic daily body retained in its source. It calls actual `cli.main` through `etl_proof.invoke`; that recorded test-only wrapper installs network guard and denies Coordinator/BoundedSender/RequestClient constructors. This is CLI argument semantics, not an unguarded external console invocation. Exact documented config path, substituted state base, future aware deadline, IDs and workset refs appear in `runbook/transform.json` and `publish.json`.

Snapshot workset `4e059646c4a441d804d74d7056127cdda28691385dbe5a67886f5ad805290303` retains original `fixture-envelope-v1` acquisition provenance. Returned transformed workset `019071ce36ed75bdd4797445451dfb2239f86b3fe7c5129ea13bd4a712825d89` uses `fixture-index-parser-v1` and feeds publish exactly. Raw SHA is `a28834a72d3eb2445d36c0f57958f35681ff41e2354e288a537fc049c926326c`. Published Q4 generation `9b8d0c273d9b498a80645999aface1c739b11143a40426394ead13f6ef146860` captures one row, CIK0000123456/path edgar/data/123456/0000123456-26-000001.txt. Full context/result objects, Attempt/Processing/Binding/Snapshot/PublicationReceipt/pointer records and manifest/data bytes remain retained. TransportAttempt count is zero.

Acquisition config remains byte-equal:1397bytes, SHA dd50a930e09e840d38109e0953b4b9e0cc1ff3253845d8649d9242fc63192a3a. New ETL config1401bytes SHA b96a00a21fdb58f851d26e82509f7967e70760d7b193d5aebe81ceec22a4f173; effective configSHA017bc4992404b2849e530e2c59939a0d719bae3db941e285e9c73bd7abe5ec7a. Raw bytes/pins unchanged. Parser/config preliminary validation is copied exactly in doc-evidence.

## Process and recovery evidence

`process-summary.json` retains all three independent sets of actual PIDs/CAS bases/versions/exceptions/results and frozen-intent hashes; full child stdout/stderr, stores, generation files and detailed traces remain under each proof. Fresh sequence insert PIDs37110/37111 aligned on absent base;37111 lost AlreadyExists and rebuilt. Replacement37119/37120 aligned on one actual version;37119 lost Conflict and rebuilt. Distinct daily keys survive. Gate37138/37139 aligned on absent base;37139 lost and rebuilt to awaiting_approval against the winner's added key.

Deaths at candidate.after_data37148, publication.before_pointer37158, publication.after_pointer37167, etl_result.after_object37178 all exited73. Exact frozen-intent recovery and repeat checks pass, without an extra post-CAS pointer advance. Full-check and isolated installed children independently prove the same cases. New recovery regressions additionally cover source quarter movement after a pointer commit without a receipt, corrupt prior authority, and ordinary post-commit ancillary exceptions; their meaningful red/green and complete covering evidence is preserved in code-evidence.

Timeout receipts show PIDs38190/38191 both dead with exits-9/-15; partial start38196 dead/-15 while the second child remained unstarted. Actual subprocess timeout retains exitnull/outcome timeout,1.006s, exact23-byte stdout and stderr .bin files. No invented subprocess exit code or lost sibling remains.

## Wheel and preservation audit

Current wheel111195bytes SHA eb8bb3b318b3b1a4fe1983291efb92161e22fac998f86230b5f2b7f3cf15c3ab. All28 package Python source bytes match current checkout, archive and isolated installed site-packages. Current package README matches wheel METADATA. Installed cwd is outside checkout, PYTHONPATH removed, native isolated venv, exact hashed offline lock dependencies, no network fallback or interpreter fetching.

`audit.json` verifies exact unchanged frozen verification tree:7525 payloads/72546066bytes and original2277373-byte inventory SHA4554adb90acdda3e44bffac01bb878d3391d4ae523e0c4439aa4e1ab2c612b6b. Its442-test check and110438-byte wheel SHA7d370cbe94d82254ae2095e8bcb8993ebef939651fc788181fc6b90906d1cfdc remain historical HEAD3c evidence. New sample21, sequence279 and installed292 payload inventories independently verify; exact code1210 and doc18 file copies preserve worker evidence. Current source/test/docs/lock/script hashes are recorded. Primary files were not written; controller owns final primary preservation audit and review checkpoint.

Unchanged retained specimen acceptance remains actual historical exit1 over970622rows with51 conflicting observations:SEC0141/0142/0143 have21/24/6. This proof does not supersede that refusal or choose winners. Native fixture/local CAS and mocked SDK behavior establish no Linux3.14.8 worker, live Azure/ETag/identity, memory/scratch capacity or history-wide acceptance. Saved reader/repair historical evidence remains in frozen verification; current captured reader and repair regression suites/process recovery are verified here.

## Self-review and whitespace

The new scripts orchestrate existing production APIs and helpers; they implement no alternative publication, identity or recovery algorithm. Audit outputs bind real files with safe relative SHA/length inventory excluding only itself. Full check ran before staging historical review evidence. Separate staged implementation/prose and full evidence whitespace command receipts are retained in whitespace.json. Exact copied unified diff context whitespace is preserved, never normalized; no full-diff-clean claim is made. Scoped implementation/prose check exited0. Full staged evidence check exited2, exclusively for preserved blank context lines in code-evidence/owned.diff and doc-evidence/owned-before-commit.diff. Exact output is in whitespace.json. Final SHA inventory binds all added proof payloads, including this report.
