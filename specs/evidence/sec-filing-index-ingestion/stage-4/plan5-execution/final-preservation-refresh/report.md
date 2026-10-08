# Plan 5 final preservation refresh

Result: **PENDING OWNER PRESERVATION DISPOSITION** for the missing planning checkout. All other requested preservation comparisons pass freshly. This audit does not answer the pending owner question and does not claim either missing checkout restored.

This independent refresh follows accepted runtimefix6528a4e while verification/evidence bookkeeping continues. No project imports, tests/builds, network, cache/input writes, primary writes, Git mutations, cleanup, restoration or subagents occurred. Only create-only refresh evidence and the designated .sdd report were written. Verification-before-completion was applied.

## Fresh exact inventories

| Root | Before | After | Exact matching | Result |
|---|---:|---:|---:|---|
| `/Users/lowell/Projects/sec-edgar` | 30078 | 30078 | 30078 | PASS |
| `/private/tmp/sec-edgar-stage3-merged-closeout-hhgufen8` | 6 | 6 | 6 | PASS |
| `/private/tmp/sec-edgar-stage4-reconcile-9mbg9qog` | 19098 | 19098 | 19098 | PASS |
| `/private/tmp/sec-edgar-primary-reconcile-1t9zru9x` | 28804 | 28804 | 28804 | PASS |
| `/private/tmp/sec-edgar-stage4-execution-preservation-bm3tc33_` | 30017 | 30017 | 30017 | PASS |
| `/private/tmp/sec-edgar-stage4-replanning-ubszs55d` | 3 | 3 | 3 | PASS |
| `/private/tmp/sec-stage4-ignored-recovery-phpsldej` | 1556 | 1556 | 1556 | PASS |
| `/private/tmp/sec-stage4-plan5-independent-th0wqyvh` | 28876 | 28876 | 28876 | PASS |

All 138,438 records match: 138,432 regular files by complete byte size and SHA-256, and six literal symlink targets. Every root has zero added, missing, changed or special-file records. All original 30,007 primary records match and all 71 recovery additions remain preserved. Complete after inventories and baseline SHA-256s are retained in results/audit.json and results/*-after.json.

## Git, refs and checkpoint

Primary HEAD and local origin/main remain fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd. Index SHA-256 remains 739086e5194794b7845942dfe0699994f0845f7a28bdb2518e8f8318f5f52f60. Exact porcelain status equals preflight; all four required legacy package paths remain absent. Fresh successful Git commands, complete stdout/stderr and exits are retained in read-only-git-command-receipts.json.

Protected stopped branch refs/heads/codex/sec-edgar-stage-4 and archive ref refs/codex/snapshots/44e1d887f038bc90b963848b95a277c13f57f9d9 remain e870a7318d47699c0e4a76ab59fba72781b0debe. Planning branch refs/heads/codex/sec-edgar-stage-4-replan remains b788b44a84d077817a4a3cb24378157c0e1b163c. All three exact checks pass.

Independent checkpoint /private/tmp/sec-stage4-plan5-independent-th0wqyvh/checkpoint: all 28,873 tracked commit blobs at b788b44a84d077817a4a3cb24378157c0e1b163c compare byte-for-byte, zero mismatches. This is a preserved tracked export comparison, not a planning-working-tree verification.

Read-only worktree-list exits 0 and registers primary and execution only; execution HEAD at that observation is cea1ef2542e6e9d7ef5e7eeae34c616ed8557960. The execution tree actively receives verification/evidence bookkeeping and its entire inventory is outside this protected-root audit.

## Authorities and approved stopped baseline

Sixteen source/snapshot authority checks pass across execution and independent checkpoint: Stage 4 spec/source/snapshot, Plan 4 source/snapshot, original roadmap snapshot, original owner receipt, and Plan 5 source/snapshot. Plan 5 owner receipts in both locations also match SHA-256 8b7870434000331d6995520b1b85d240aeade8843b9b099a7dfed0e1b8ddc7ab. Exact paths, expected hashes and actual hashes are retained in results/audit.json and results/supplement.json. Expectations derive from retained replanning verification, not guessed approvals.

Original stopped checkout /Users/lowell/.codex/worktrees/sec-edgar-stage-4/sec-edgar remains absent under the existing owner-approved independent checkpoint/recovered ignored evidence disposition recorded by preflight. Ignored-recovery root has all 1,556 records exact; receipt SHA-256 remains a1ccf73e2032ed2dd18f9f441c96f365d08f8f94496010d34f4c6c2f306a3597. The 433 original unmatched runtime/bytecode records remain under approved offline regeneration disposition. No restoration claim is made.

## Unresolved planning gate and exits

Protected planning checkout /Users/lowell/.codex/worktrees/sec-edgar-stage-4-replan/sec-edgar remains absent and unregistered. Its HEAD, status, index and eight planning authority reads are unavailable. No complete planning ignored-file baseline or original planning-index hash was supplied. The branch and exported checkpoint do not establish preservation of the missing working tree.

The audit subprocess exits **1** with **14 error entries**, all attributable to this known absence: four Git exit-128 failures with full stderr, one absent-path record, one planning result record, and eight unavailable authority records. Full errors remain unsuppressed. The outer capture wrapper exits 0 because it successfully captured the audit failure; audit-command.json records actual audit exit 1. Supplement exits **0** and passed=true. The preservation gate remains false; no new owner disposition was supplied.

## Method, evidence and limitations

Retained audit and supplement scripts were copied to this new root with only their fixed output path changed. derivation.json records source/destination SHA-256s and exact old/new output values. Every prior final-preservation manifest entry was freshly verified unchanged in prior-evidence-immutability.json. Exact commands/full stdout/stderr/exits are in audit-command.json and supplement-command.json, with separate full text outputs.

The checker uses stdlib os.walk(followlinks=False), excluding entries named .git consistently with baseline; complete regular bytes are hashed and symlink targets are literal os.readlink values. Read-only Git uses --no-optional-locks and GIT_OPTIONAL_LOCKS=0. Directory membership/modes/mtime/permissions are outside this audit. Observations are point-in-time; no implementation or acceptance verdict is made.

input-sha256.json binds prior evidence and all preflight baseline inputs. evidence-sha256.json inventories this refresh evidence only, excluding only its own exact path to avoid self-reference; it separately binds the designated .sdd report. This evidence root is outside all eight protected roots, so no protected-root inventory excludes it.

Ancillary errors are retained in ancillary-errors.json: a sandbox-denied read-only process inspection was not retried; a report-generation quoting SyntaxError occurred before any write and was corrected. Neither affected preservation checks.
