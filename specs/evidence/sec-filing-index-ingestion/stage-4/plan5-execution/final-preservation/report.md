# Plan 5 final preservation audit

Result: **PENDING OWNER PRESERVATION DISPOSITION**. Primary and all seven retained roots pass exact full regular-file/symlink inventories. The protected planning checkout is absent; this audit cannot claim it preserved or restored. No direct owner disposition for its absence was supplied to this auditor.

This read-only audit ran independently of Task 11 implementation. No project imports, tests, builds, Git writes, staging, stash/reset, network, restoration, cleanup or subagents occurred. Outputs are create-only controller preservation evidence. Verification-before-completion was applied.

## Exact comparison results

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

Every root has zero missing, added, changed or special-file records: 138,438 records total, comprising 138,432 regular files and six literal symlink targets. The fresh primary comparison preserves all 30,007 original records and 71 recovery additions. SHA-256 hashing covers complete regular bytes, including every retained archive, inventory, receipt and evidence payload.

Primary HEAD and local origin/main remain `fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd`; index SHA-256 remains `739086e5194794b7845942dfe0699994f0845f7a28bdb2518e8f8318f5f52f60`. Exact porcelain status equals preflight. All four required legacy package paths remain absent. Primary Git checks pass.

- `refs/heads/codex/sec-edgar-stage-4`: `e870a7318d47699c0e4a76ab59fba72781b0debe`; expected `e870a7318d47699c0e4a76ab59fba72781b0debe`; PASS.
- `refs/codex/snapshots/44e1d887f038bc90b963848b95a277c13f57f9d9`: `e870a7318d47699c0e4a76ab59fba72781b0debe`; expected `e870a7318d47699c0e4a76ab59fba72781b0debe`; PASS.
- `refs/heads/codex/sec-edgar-stage-4-replan`: `b788b44a84d077817a4a3cb24378157c0e1b163c`; expected `b788b44a84d077817a4a3cb24378157c0e1b163c`; PASS.

Independent checkpoint `/private/tmp/sec-stage4-plan5-independent-th0wqyvh/checkpoint`: 28,873 tracked paths compared byte-for-byte to every blob in commit `b788b44a84d077817a4a3cb24378157c0e1b163c`; 0 mismatches. This is a complete exported tracked-tree comparison, not a planning-worktree verification.

The original stopped checkout remains absent under the existing owner-approved independent checkpoint/recovery disposition. Its preserved stopped branch/archive ref remain exact. The ignored-recovery receipt SHA-256 remains `a1ccf73e2032ed2dd18f9f441c96f365d08f8f94496010d34f4c6c2f306a3597`; all 1,556 root records match, including the receipt and 1,555 payload records. The disposition permits the 433 original unmatched runtime/bytecode artifacts to be regenerated offline; this audit makes no restoration claim.

The approved Plan 5 source/snapshot, Stage 4 spec/source/snapshot, original roadmap snapshot, Plan 4 source/snapshot and original owner receipt all match in execution and independent checkpoint (16 checks). Fresh Plan 5 owner receipt SHA-256 `8b7870434000331d6995520b1b85d240aeade8843b9b099a7dfed0e1b8ddc7ab` matches in both. Eight planning authority checks are unavailable because that checkout is absent.

## Material gap and full failures

`/Users/lowell/.codex/worktrees/sec-edgar-stage-4-replan/sec-edgar` is absent. Read-only `git worktree list --porcelain` lists primary and current execution only. Its branch still preserves the expected commit. Its final working tree/status/index cannot be verified; no complete planning ignored-file inventory or original planning-index hash was supplied. The independent export and retained inputs are preserved, but only an explicit owner disposition can resolve the missing-checkout gate.

The first complete eight-root inventory run then exited 1 on `FileNotFoundError` while attempting the missing planning index. Its exact executable, stdout and full traceback are retained. The robust second run also exits 1 and retains every missing-planning Git/authority failure in `audit.json.errors`; these are not suppressed or presented as passes. No evidence attributes the timing or cause of the disappearance.

## Methods and limitations

The executable audit uses stdlib `os.walk(followlinks=False)`, compares exact path membership, regular byte sizes/SHA-256 and literal `os.readlink` targets to the retained preflight inventories, and writes complete after inventories. Entries named `.git` are excluded consistently with the supplied baseline inventory; explicit primary HEAD/index/status and preserved-ref checks supplement them. Read-only Git calls use `--no-optional-locks` and `GIT_OPTIONAL_LOCKS=0`.

No initial preflight audit driver was present in the provided preflight root. The retained inventory record schema is reproduced explicitly; the script and baseline SHA-256 references make that method reviewable. The independent export comparison reads each preserved commit blob via `git cat-file blob` and compares exact checkpoint bytes. The supplement compares the original 30,007-record inventory against the fresh primary-after inventory and records exact worktree-list output and approval receipt hashes.

Directory modes, mtime, permissions, empty-directory membership and other volatile Git metadata are not audited. Record coverage claims include complete regular/symlink membership only. All observations are point-in-time. No implementation or Task 11 acceptance claim is made. `audit.json.passed=false` remains accurate until the absent planning-checkout disposition is resolved externally.

Evidence: `audit.json`, `supplement.json`, all eight `*-after.json` inventories, both executable audit versions, complete first/rerun stdout/stderr, supplement executable, and `evidence-sha256.json`.
