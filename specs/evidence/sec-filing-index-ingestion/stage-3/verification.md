# Stage 3 offline capability verification — acceptance blocked

Task 7 delivers passing native capability proofs. **Stage 3 acceptance remains
blocked** by 51 conflicting duplicate observations in complete retained receipts
SEC-0141, SEC-0142 and SEC-0143. Their refusal follows the approved CIK/archive-path
logical key. No duplicate winner was selected and no original was edited. This
record does not stamp completion or retirement. `all22_stage7_checks: reserved`.

## Commands and actual results

All commands ran in the isolated `codex/sec-edgar-stage-3` managed worktree with
cached frozen dependencies and the selected Python 3.14.0/macOS arm64 runtime.
Live SEC, Azure, authentication, compute, provisioning, deployment and image
builds remained closed. Full argv/cwd/dependency/exit/runtime records and logs are
linked below; no Linux worker capacity is inferred.

| Proof | Actual result | Evidence |
| --- | --- | --- |
| `scripts/check-sec-edgar-ingest.sh` | Exit 0; 439 tests in 160.832s; wheel/sdist, four-command help, module version, compileall and whitespace pass | [command](verification/final-check/command.json), [full stderr](verification/final-check/stderr.txt), [full stdout](verification/final-check/stdout.txt), [real children](verification/final-check/processes/) |
| `etl_proof.py specimens --output …/verification/specimens` | Exit 1; all 970,622 rows scanned; three source acceptance failures | [report](verification/specimens/report.json), [hashes](verification/specimens/sha256.json) |
| `etl_proof.py sequence --output …/verification/sequence` | Exit 0; actual raw-only commands, replay/no-op, cross-quarter source, gates and process recovery | [command](verification/sequence-command/command.json), [report](verification/sequence/report.json), [hashes](verification/sequence/sha256.json) |
| `etl_proof.py installed --output …/verification/installed` | Exit 0; exact wheel and lock pins; isolated site-packages imports and source-byte equality; full raw/process sequence | [command](verification/installed-command/command.json), [report](verification/installed/report.json), [installed report](verification/installed/installed-sequence/report.json), [hashes](verification/installed/sha256.json) |
| Saved-capture reader and repair example | Exit 0; complete read and unchanged committed pointer | [command](verification/runbook-command/command.json), [proof](verification/runbook-proof.json) |
| Primary preservation | 19,088 records verified; four absences and exact roadmap bytes preserved | [receipt](verification/primary-preservation.json) |

After the full check, a documentation-only correction removed obsolete
acquisition-only installation instructions. The package README is wheel metadata,
so [the wheel was rebuilt](verification/readme-wheel-build/command.json) and its
installed proof rerun. The prior passing installed proof remains under
[installed-before-readme-correction](verification/installed-before-readme-correction/report.json).
There was no implementation change or unneeded repeated full suite.

The complete check passed before historical evidence was staged. The final
staged historical diff contains preserved whitespace and its exact postcommit
recheck exited **2**. The committed Task 7 implementation/documentation-only
whitespace check exited **0**. See the [staging addendum](verification/task-7-report-addendum.md),
[full failure output](verification/committed-history-whitespace/stdout.txt) and
[exact affected paths](verification/committed-history-whitespace/affected-paths.json).
Historical bytes were not normalized; there is no claim that the full final
evidence diff is whitespace-clean.

## Ten retained complete specimens

Each scan resolves the inspection's original path relative to the Stage 1 root,
checks both matrix/inspection hash and byte count and separately retained receipt
bytes, selects its actual family, runs the production parser, checks row counts,
date bounds and every selected inspected row, counts quarters and applies the
production duplicate-key policy. The root quarterly alias is parsed under its
matching 2026Q4 source context, explicitly recorded per receipt. Compact synthetic
legacy goldens remain separate from observed retained evidence.

| Receipt | Parsed rows | Identical duplicates | Conflicting observations | Source acceptance |
| --- | ---: | ---: | ---: | --- |
| SEC-0141 | 300,561 | 0 | 21 | blocked |
| SEC-0142 | 318,647 | 0 | 24 | blocked |
| SEC-0143 | 302,315 | 0 | 6 | blocked |
| SEC-0144 | 12,479 | 0 | 0 | accepted |
| SEC-0145 | 12,479 | 0 | 0 | accepted |
| SEC-0146 | 3,594 | 51 | 0 | accepted |
| SEC-0147 | 5,527 | 92 | 0 | accepted |
| SEC-0148 | 7,159 | 69 | 0 | accepted |
| SEC-0149 | 3,084 | 68 | 0 | accepted |
| SEC-0150 | 4,777 | 46 | 0 | accepted |

[Individual specimen JSON files](verification/specimens/) retain actual original
hashes, counts, dates, selected rows, quarter counts, first conflicting payloads,
physical lines and refusal reasons. Earliest conflicts occur at lines 6,580,
87,808 and 40,292 respectively. Archived
[complete-source transform refusal](verification/sdd-history/retained-parser-preflight/)
and controller history preserve earlier independent source-gate investigation;
this Task 7 scan performed its own complete parse. Seven passing receipts do not
establish history-wide range acceptance.

## Real process evidence

[Sequence process traces](verification/sequence/processes/) and the independent
full-suite children retain separate stdout/stderr, PIDs, candidate/manifest hashes,
exact bases and actual local CAS exceptions. The insert race used PIDs 20087 and
20088 on the same absent pointer; PID 20087 encountered `AlreadyExists` and rebuilt.
The replace race used PIDs 20094 and 20095 on version
`f67a448a83f54b0894500a49070e7957`; PID 20095 encountered `Conflict` and rebuilt from
the new version. The final logical keys equal the required union. The barrier is
used once, before first CAS, so the losing rebuild is not blocked.

The closed-quarter gate race used PIDs 20100 and 20101. The winner added a key
omitted by the loser's quarterly membership; the loser experienced a real insert
conflict and rebuilt to `awaiting_approval`. The winner remained current. Candidate
records and unreferenced losing candidate files remain retained.

Actual child exits 73 occurred at `candidate.after_data` (PID 20110),
`publication.before_pointer` (20116), `publication.after_pointer` (20120) and
`etl_result.after_object` (20123). Independent reopened stores exposed only the
complete old or new capture. Exact frozen CLI intent resumed successfully;
post-CAS recovery and repeated completed attempts did not add a pointer commit.
Children have finite joins; only a test's own hung child may be terminated.

## Installed boundary and retained history

The final installed proof uses the built wheel with its actual retained SHA,
exports exact lock hashes, installs cached PyArrow separately from the retained
Stage 2 wheel files, then installs that exact wheel without dependency resolution.
Every Python proof child installs the network/provider guard before package
imports. The site-packages check and source inventory reject checkout leakage;
cwd is outside the repository and PYTHONPATH is removed. Native dependencies and
runtime are recorded by the actual installed child as well as its invoking process.

[Archived SDD history](verification/sdd-history/) retains prior briefs, interfaces,
reports, reviews, ledger/progress, baseline/red/green, raw artifacts, preflight and
blocker evidence. [Task 7 intermediate evidence](verification/sdd-history/task7-evidence/)
includes the first missing-driver red, early process green, failed offline cache
combinations and installed spawn-main failure before fixes. Historical pending
statements and failures were not rewritten. The first archival verifier's absent
sentinel mistake is also retained. Early red/green wrapper elapsed time was not
captured; their records explicitly distinguish known unittest runtime from that
unavailable value. Later runs retain full wrapper timing and actual child traces.

[Owner approval](owner-approval.json), [planning reconciliation](planning-reconciliation.json)
and approved document versions were copied byte-for-byte from primary. Hash
inventories bind actual final files using safe relative paths, sizes and SHA256,
excluding only the inventory itself. Controller Task 7 and final whole-branch
review receipts are added later. The [runbook](../../../../docs/runbooks/sec-edgar-etl-publication.md)
explains exact-reference reads, replay, no-op, gates and safe repair.

All 22 integrated checks remain reserved for later roadmap Stage 7, including
actual Linux amd64/Python 3.14.8 worker memory/runtime/scratch, ADLS/HNS,
identity and real Azure ETag behavior. Mocked SDK and native local proofs do not
establish those capacities. Owner policy reconciliation of the retained-source
conflicts is required before any Stage 3 completion decision.
