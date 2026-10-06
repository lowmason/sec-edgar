# Stage 2 acquisition verification

Independent Task 8 implementation, full offline check and fresh installed-wheel fixture proof are ready for review. **The prescribed combined Step 4 sequence remains pending the owner’s daily endpoint choice.** No Task 8 Spec/Quality PASS or Stage 2 completion stamp is asserted here. Stage 2 stays unticked; all22 Stage7 checks are reserved.

Source BASE/last upstream reviewed revision: `73ea758e37f6b6ed78103b2a731b2f125bd96a96`, branch `codex/sec-edgar-stage-2`. [Source/config/lock/prior review SHA inventory](verification/source-revisions.json) records current candidate bytes and every retained Task1–7 full/scoped review receipt SHA. Task7 full receipt SHA `c69f810230e7cb7ec75c85ab250b96141ed771b1874085bfc3a626f8ca32a117`, scoped receipt SHA `5b1e0894379692b58eab780b7cc96d63a0d09d4de2a23b2a46d1ae826a22c816`. Actual Task8 reviewed HEAD/receipts will be added by the controller after the named commit/fresh review; no future revision is fabricated. Config-file SHA `dd50a930e09e840d38109e0953b4b9e0cc1ff3253845d8649d9242fc63192a3a`; uv.lock SHA `7a1b45b2944241e9b8fda35b5e87977c6ec189a3c72f4ca1f3f861661220f42c`. Accepted F1/Stage1 manifest remain `939a724eccf22147015a59d5940ed57f02cc4e9fe9d942a9cd78ae73c34615ff` / `124e96041548daba8216aa495fc69021751555b0f0e4c890ac85e934f512a131`.

## Current commands and exits

| Command | Actual result | Retained proof |
| --- | --- | --- |
| scripts/check-sec-edgar-ingest.sh | exit0;282 tests/94.734s, wheel+sdist, help, module0.1.0, compileall, whitespace | [Complete log](verification/sdd-history/task-8-final-check.txt), [all307-line/282-record inspection](verification/sdd-history/task-8-final-check-inspection.json) |
| uv run --offline --frozen --package sec-edgar-ingest python .../fixture-sequence.py | exit0 for independent quarterly/replay sequence; original closed-quarter daily2; combined Step4 pending | [sec-edgar-stage-2-ajod3d_r](verification/sec-edgar-stage-2-ajod3d_r/sequence-summary.json), [argv and root map](verification/sec-edgar-stage-2-ajod3d_r/retention-map.json) |
| uv run --offline --frozen --package sec-edgar-ingest python .../installed-wheel-proof.py | exit0; cached20 pins/site-packages import/actual installed fixture commands/4 requests and no new replay requests | [Commands](verification/sec-edgar-wheel-5ufv5ml9/commands.json), [wheel receipt](verification/sec-edgar-wheel-5ufv5ml9/wheel-proof-summary.json) |
| .venv/bin/python .sdd/.../verify_primary.py | exit0; zero1673 protected-file drift, original4 deletions+untracked roadmap preserved | [Separate primary receipt](verification/sdd-history/task-8-primary-preservation.json) |

The full check log SHA is `6387624674edb1a6f0dcfd68d4e8f0751344e51d58aa1a29db40d0ff5189090f`. Its console presentation was truncated, but the full47241-byte log and every-line inspection are retained. Its CRLF equivalent is explicitly `git -c core.whitespace=cr-at-eol diff --check`, without changing repo config. The final package/source/test implementation was checked once; only proof/report/inventory records were produced afterward. The unexecuted wheel proof query correction used the actual namespace and explicitly required4 transports before asserting no new replay requests. All historical RED/intermediate failures remain with their actual exits; `task-8-process-green.txt` is historical exit1, followed by focused corrected timer exit0 and the current full4-process-test pass.

## Fixture sequence, hashes and counters

The pack is explicitly synthetic v1, file SHA `c96e76610f6a218eb27f647abafe538991330bffa0f471c11e890ce3eeac5a97`, with canonical SEC URL mappings, SHA-addressed local body files and no live fallback. Unreferenced earlier synthetic bodies are preserved, not selected by the manifest. The quarterly archive SHA is `68b0e0e1c09010a02e45ac0d0adc2621f23d61a84448064d15d0cee9e5aab399` (261 bytes); daily handoff IDX SHA `4dc2efcff18a472cac890b5a3e4cc38a1f78a6fd9e672e0a8dababec4a91e6c0` (230 bytes), delayed IDX `258e0245ed05b9340e156bc1572f88425962b0bcb9b25eca60ecb8c6052815c9` (230 bytes). These are envelope fixtures; no row parser or semantic row-date coverage is implied.

| Current independent quarterly result | Discovered | Downloaded | Unchanged | Pending | Failed | Quarantined |
| --- | --- | --- | --- | --- | --- | --- |
| discover-1 success | 1 | 0 | 0 | 0 | 0 | 0 |
| collect-1 success | 1 | 1 | 0 | 0 | 0 | 0 |
| collect-2 success | 1 | 0 | 1 | 0 | 0 | 0 |

Source workset: `worksets/sec/source/sha256=ac957982f44124a5e49dffad65f4dc7393a226aac8c0fe788ae882ae990550bb/workset.json`. Snapshot workset: `worksets/sec/snapshot/sha256=a20aa8ff3e9df909dba90ddbf88ab83721b652e5d076261571748f16ed74e218/workset.json`. Both replay forms preserve original pins/snapshot and issue no HTTP. Result context is the current collecting execution; snapshot workset origin remains the immutable discovery context. The original absolute storage.root example is refused2; corrected relative `.fixture-state` plus explicit absolute state-dir base and explicit synthetic date/deadline markers are routine controller-authorized driver corrections. Effective quarterly config SHA `a8b1ebc0e3e64c56d9aad5e7b4b15ca111495885c2a9849dbc96721c203ab856`. The proposed separate daily end=open config SHA `6bf4c06fd8d4891aad27fbeb1221dbfb08920a670d79462233c3fbff83d4ac6f` remains unexecuted in the prescribed sequence. [Prepared concrete two-config commands](verification/sec-edgar-stage-2-ajod3d_r/prepared-two-config-commands.json) are available for owner review.

The accepted strict endpoint/hash contract refuses October2026 daily discovery under closed2015Q1. The owner’s pending choice is separate daily config vs a revised pin contract; retries and elapsed time do not answer it. Ordinary already-authorized valid open-daily tests passed: first incomplete3 with downloaded1/pending1, completed failed-result replay no HTTP, new attempt success0 with downloaded1/unchanged1/pending0, final pin reuse no HTTP. Their full durable roots/command logs/pins/response cursors are retained under [current CLI files](verification/sdd-history/task-8-final-traces/task8/cli-files). They do not discharge the combined Step4 gate.

## Actual process evidence

[Three-collector trace](verification/sdd-history/task-8-final-traces/task8/three-collector-race.json):3 independent PIDs/shared stores/clients,3 actual inserts after3 barrier-forced absent reads,1 winner/2 conflicts, one issuer per request interval and shared >=1/3s start spacing. Winner217-byte SHA `7f4f306b51ee21ede9c9d9a03b5a647de6eb35d42a2d71933d288b46c450171b`; restart sender is forbidden, snapshot/raw/result exact bytes remain stable. This race uses explicit scripted synthetic response bodies and real local coordination/state/processes.

[Integrated held-socket trace](verification/sdd-history/task-8-final-traces/task8/integrated-takeover.json) and [retained process files](verification/sdd-history/task-8-final-traces/task8/integrated-takeover-files): actual bounded loopback HTTP and old parent exit-15, default-fatal old child/socket drain/orphan ps receipt, actual durable epoch/request/journal guard, 92 zero-successor observations through stored unsafe-until `2026-10-06T20:55:57.623519+00:00`, independent daily/backfill successor exit0, then4 actual server starts in daily,daily,daily,backfill order. Minimum actual successor wire spacing 0.680565000s. Actual synthetic parameters .8s exchange/2s lease/1s renewal/.05s uncertainty; production90s/60s/20s/2s/3RPS defaults remain intact. Old child exact exit is not reaped by its killed parent; the separate deadline proof captures actual -14.

[Independent child timer](verification/sdd-history/task-8-final-traces/task8/independent-child-deadline.json): stalled supervisor, actual fatal exit-14, 98 prefix bytes SHA `9b4ebbf27e774709b0e27357b252b7e621d86e89fceb6b60c1913038bbf46aa8`, socket closed. [Stale dispatch](verification/sdd-history/task-8-final-traces/task8/stale-dispatch.json): zero actual server requests. Those .4s local tests establish hard lifetime/stale-start mechanics, not default90s or Linux performance.

Four `result-crash-*.json` current traces plus [full CLI roots](verification/sdd-history/task-8-final-traces/task8/cli-files) capture actual CLI result-object/Attempt boundary process exits74 and same-context repair0 with original canonical result bytes/no added transports. Task7's earlier7 crash/race/two-source/quarantine proofs are separately retained. Earlier logical-clock coordination and scripted Azure traces are labelled in original reports; they are not represented as actual wire timestamps or live Azure behavior. All retained Permit/retry monotonic values belong to their historical originating host; persisted UTC/fencing, not those old values, authorize restart scheduling.

## Build and installed runtime

Wheel `sec_edgar_ingest-0.1.0-py3-none-any.whl` (77150 bytes), SHA `46deb58c54bb35cc79283f03ebf9ae4060ba23b2af5bbb8856ab0308c4913bb0`; sdist `sec_edgar_ingest-0.1.0.tar.gz` (65543 bytes), SHA `dac15ddd67184480a9df0810d4e41a0a6c181c24e64608451a2156af36b3643d`. [Metadata/member inspection](verification/sec-edgar-wheel-5ufv5ml9/artifact-inspection.json) confirms>=3.14, four pinned direct dependencies and `sec_edgar_ingest.cli:main`, with other scaffolds excluded. Original artifact bytes are retained under its build-artifacts directory. Lock export with hashes plus Task1 cached native wheels drove offline/no-index fresh-venv installs; uv pip/build do not have --frozen but used the exact accepted hash/pin constraints. Actual console discovery/collection/replay commands ran in the temporary cwd without PYTHONPATH/PYTHONHOME and imported only the fresh site-packages distribution. The mapped disposable venv is excluded; all installation inputs/receipts/artifacts/config/state/body bytes remain.

Local OS `macOS-26.6.2-arm64-arm-64bit-Mach-O`; Darwin25.6.0 arm64; Python `3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]`. [Exact installed version receipt](verification/sec-edgar-wheel-5ufv5ml9/installed-versions.json):

| Distribution | Installed version |
| --- | --- |
| PyJWT | 2.15.1 |
| azure-core | 1.41.0 |
| azure-data-tables | 12.7.0 |
| azure-identity | 1.26.0 |
| azure-storage-blob | 12.31.0 |
| certifi | 2026.7.22 |
| cffi | 2.1.1 |
| charset-normalizer | 3.5.2 |
| cryptography | 50.0.2 |
| idna | 3.20 |
| isodate | 0.7.2 |
| msal | 1.39.0 |
| msal-extensions | 1.3.1 |
| multidict | 7.0.0 |
| propcache | 0.5.4 |
| pycparser | 3.0 |
| requests | 2.34.2 |
| sec-edgar-ingest | 0.1.0 |
| typing_extensions | 4.16.0 |
| urllib3 | 2.8.0 |
| yarl | 1.25.1 |

The20 native/runtime artifact versions match accepted constraints; macOS native wheel hashes/platform differ from Stage1 Linux amd64 archives as already documented, and those actual Task1 native archives are preserved in the full history.

## Retention and reserved work

[History root map](verification/sdd-retention-map.json), [whole-bundle SHA manifest](verification/sha256-manifest.json), and [file/byte inventory](verification/evidence-inventory.json) make copied evidence inspectable without rewriting historical absolute references. Original complete history, failures, full+scoped reviews, reports/diffs/REDGREEN/trace bytes, cached wheels, preflight1673 protected paths/1584 accepted records, audit/progress/shared contracts/Minor ledger and controller receipts are preserved as original bytes. No recursive copy or self-hash cycle is used. No SDD cleanup/native archive happened before retention. Historical Task7 truncated probe output remains an exact command/decisive-field receipt, not fabricated complete output. Other documented historical wrapper limitations in proof-inventory.md remain visible.

Runbook documents conservative full Azure unsafe-guard retention on clean release and waiting without lease break; owner-wide unrepresentable Retry-After latch/raw reason/deferred5 with no reset/expiry/new-run escape; current vs historical context, immutable result repair, new-attempt recovery, failed-directory new worksets, pending older work, quarantine/raw retention and shared owner budget.

No live SEC/Azure/auth/registry/compute work, Linux/default90s performance measurement, workers/schedules/provisioning, historical/global format coverage or SLA is claimed. S7-11/12/14/18/19 and **all remaining17 of the22 Stage7 checks are reserved**, including actual owner-wide effective behavior, Azure lease/inflight/CAS/HNS, identities/network, worker measurements and integrated live smoke/replay. The pending owner endpoint answer, actual approved combined sequence, fresh Task8 review and final GPT-6.1 Max review/completion protocol must resolve before Stage2 stamp/tick/retirement. Stage3 is outside this work.
