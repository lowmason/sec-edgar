# Task 7 repair round 1 — timeout ownership and evidence retention

Status: **DONE_WITH_CONCERNS**. Base `4b6e54c18b886e02ff75643d6f5b399e0ededf3b`.
The complete two-item review list is addressed in Task 7's proof code/tests only.
No production source, pins, identity/parser policy, approval or later-stage work
changed. Parent controller owns fresh reviews and its controller-verification
paths; this repair changed none of them. No agents or reviewers were spawned.
`all22_stage7_checks: reserved`; retained-source acceptance remains blocked.

## Important finding: clean up every owned child before raising on timeout

`join_children` now records deadline/join/termination failures while visiting every
supplied owned process, waits a bounded interval after terminate, falls back to
kill if still alive, waits again and verifies termination. It raises the aggregate
failure only after all children receive cleanup. The default normal join remains
60 seconds; `TERMINATE_SECONDS` is 10 for each terminate/kill wait. Optional
`timeout` supports immediate cleanup for partial startup. A race whose second
start fails cleans all children with an actual PID, preserves the original start
exception and adds cleanup details as an exception note. No global/unowned child
is targeted. These are helper changes, not a new publication algorithm.

Real spawned regression children wait on a controlled target after installing
the offline guard. The first deliberately ignores SIGTERM; the sibling remains
alive until cleanup. Corrected red observed PIDs 26258/26259 both still alive after
the old helper raised; its independent emergency-reap path safely killed and
joined them, so the red suite could not hang. Corrected partial-start red observed
PID 26266 alive after injected second start failure. The parent-side proxy injects
startup failure without replacing the real child's pickled start method.

Green observed PIDs 26439/26440 already dead with exits -9/-15 before emergency
cleanup, and partial-start PID 26445 dead with exit -15 while the second PID remained
null. Full-check regression independently observed PIDs 27520/27521 dead with
-9/-15 and partial-start PID 27528 dead with -15. Thus bounded kill fallback,
sibling cleanup and partial-start cleanup are proved with real processes.

## Minor finding: retain subprocess output when a command times out

`run_logged(..., *, timeout=300)` preserves its 300-second default and permits a
short regression timeout. It catches real `TimeoutExpired`, saves argv/cwd,
actual runtime, native dependency/platform metadata and safe environment flags,
sets `outcome: timeout`, **exit:null**, retains partial stdout/stderr, then reraises.
When the exception carries bytes, separate `.stdout.bin`/`.stderr.bin` files and
actual size/SHA preserve those bytes exactly; display text uses UTF-8 with
backslash replacement. No observed exit is invented. Successful commands keep
stdout/stderr and now explicitly record `outcome: completed` plus timeout metadata.

The real offline subprocess installs the guard before imports, writes invalid
UTF-8 on both streams and then waits. Corrected red shows that the old helper lost
its command record after the actual timeout. Green uses a 1-second injected
helper timeout (the test separately asserts default 300) and verifies exact raw
bytes. Full check retained actual timeout runtime 1.0064515001140535 seconds,
exit:null; stdout 23 bytes SHA256
`ccc40a1819606591ee2ad8cacb91d4f756ec3f68e5074179ad1dc2644cb060a6`, stderr 23 bytes SHA256
`5d64ffd774a95ef8629131a26c12f7cda6908946871c090a306eacfc567422c5`.

## Retained red, green and final verification

- `red/`: six tests in 15.479s, exit 1, two meaningful failures and one test-setup
  PicklingError; full output preserved. The test-only setup was corrected before
  implementing either helper fix.
- `red-corrected/`: six tests in 15.495s, exit 1, exactly three meaningful failures:
  both owned children left alive, first child leaked on partial startup, missing
  timeout command/output record. Full logs, actual PID observations and emergency
  reap receipt retained.
- `green/`: six tests in 5.644s, exit 0. The final signature/default assertion and
  direct-file test-main placement were covered by the following full check.
- `scripts/check-sec-edgar-ingest.sh`: **442 tests in 160.172s, exit 0**; wrapper
  160.85067750001326 seconds. Build wheel/sdist,
  four-command help, module version 0.1.0, compileall and then-unstaged whitespace
  check passed. New implementation justified this new complete check. Its complete
  command/logs, actual ordinary process proofs and timeout regressions are in
  `verification/final-check/`.
- Prescribed `etl_proof.py sequence --output …/verification/sequence`: **exit 0**,
  wrapper 5.818909999914467 seconds; actual
  raw-only command/replay/gate/reader and spawned CAS/death proofs retained.
- Prescribed `etl_proof.py installed --output …/verification/installed`: **exit 0**,
  wrapper 9.546294999774545 seconds. Exact full-check
  wheel installed with frozen cached lock pins, no PYTHONPATH, cwd outside checkout,
  before-import guards and actual site-packages byte checks. Full raw/process proof
  repeated using the repaired helper. No fetch/interpreter fallback.
- `audit-command/`: exit 0, all 6634 prior payload records and 1657 selected proof
  inventory records verified, final wheel, 28 source files and README checked, real
  child/timeout observations inspected. Complete command arrays/stdout/stderr and
  native metadata accompany every retained run. Every new helper test safely reaps
  its own process even against the intentionally buggy pre-fix implementation.

Final wheel remains `sec_edgar_ingest-0.1.0-py3-none-any.whl`, 110438bytes,
SHA256 `7d370cbe94d82254ae2095e8bcb8993ebef939651fc788181fc6b90906d1cfdc`. All 28 production Python source bytes and
README match source tree, wheel and installed package; no production edit means
the deterministic wheel content is unchanged. Native Python 3.14.0/macOS arm64 proves
no Linux amd64/Python 3.14.8 capacity. All 22 integrated checks remain reserved.

## Preservation and scope

Original final-check/sequence/installed directories and command records moved
byte-for-byte to `verification/prior-task7-before-fix1/`; its `relocation.json`
explicitly maps original prefixes. The **original 6634-record root inventory bytes**
are preserved there and in repair originals. All 6634 original payloads were checked
against their exact mapped paths before changes to authoritative metadata.
Original implementation/test files, verification prose and the full prior task
report are retained in repair `originals/`. Previous history/failure/whitespace
logs and controller material were not normalized, removed or rewritten.

No specimen parse was repeated: unchanged original report exit 1, all 970622 rows
and 51 conflicting observations stay authoritative. Its exact report/inventory hashes
and the unchanged reader/repair receipt binding are in `unchanged-evidence.json`.
That binding checks saved capture/manifest/file hashes against the exact prior
sequence store. Reader/repair behavior was not affected or rerun.

Only `etl_proof.py`, `test_etl_processes.py`, necessary verification prose and owned
repair evidence/report/ledger changed. `owned-code.diff` is the scoped review
material against the exact repair base. Clean-code scope was confined to the
requested failure paths: aggregate cleanup ownership (G30/T5), named bounded
termination wait (G25), explicit timeout outcome/raw evidence (N1/T6). No adjacent
production cleanup was performed.

The original full-history whitespace limitation remains disclosed. The full check
passes before newly retained historical text is staged; an additional staged
full-diff receipt and implementation/docs-only check are retained separately.
No unqualified claim of a whitespace-clean historical evidence diff is made.
Status remains DONE_WITH_CONCERNS pending owner source-policy reconciliation and
controller re-review; no COMPLETE/roadmap/retirement/integration/cleanup.


### Final staging checks

The repair's full staged evidence diff check exited **2**. Its complete retained
output identifies only `verification/fix1/owned-code.diff`: the exact scoped
unified diff has space-only context lines. Those bytes were preserved, not
normalized. `staged-history-whitespace/` retains the actual argv, duration, full
stdout/stderr, exit and affected-path list. The staged implementation/prose check
exited **0**, recorded in `staged-owned-whitespace/`. This is separate from the
older full-history whitespace findings, which also remain preserved.
