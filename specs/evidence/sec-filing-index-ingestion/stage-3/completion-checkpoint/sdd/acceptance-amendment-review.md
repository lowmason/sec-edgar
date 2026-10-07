Spec Compliance: ✅ Compliant with the owner-authorized acceptance amendment and controller’s narrow runbook extension. The exact `3898502d7920d285f72f8f41057b706d8a85a64e` → `fee0f9659a2d6d7d0132c1ac5ddb111e362e3b1f` diff contains no missing, extra, or misunderstood task requirements.

### Strengths

- The amended acceptance language binds precisely SEC-0141, SEC-0142, and SEC-0143 by raw SHA256, byte length, quarter, row count, conflict count, and first conflicting line. It preserves whole-source refusal, other invalid-row/cache blockers, closed live authorization, and all 22 reserved Stage 7 checks. [Spec §8](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/sec-filing-index-ingestion-stage-3-spec.md:140).
- Current verification and the two authorized runbook paragraphs distinguish documentary acceptance from successful source acceptance. The original 970,622-row scan remains historical exit 1 with 51 conflicts; the fresh verifier result is separate. [Verification record](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/verification.md:3), [runbook](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/docs/runbooks/sec-edgar-etl-publication.md:8).
- Preservation is explicit and independently supported: the original verification bytes match the old delivery entry, and the unchanged delivery manifest hashes to `a2efc7405ed0050f71f9fb2df06783b8444ab5ab56fb8839155428ea1c1a770b`. Only `verification.md` is relocated in the historical resolution map. [Historical resolution](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/acceptance-amendment/historical-resolution.json:2).
- The verifier checks actual refusal artifacts rather than relying solely on receipt flags: stored raw hashes, quarantine errors, immutable SQLite records, and absence of curated output. Direct reviewer checks confirmed all three retained stores contain only Binding and Snapshot records; raw originals and stored copies match the authorized identities, and quarantine errors name the expected lines and canonical duplicate reason. [Source verification](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/acceptance-amendment/verify.py:136).
- Receipt validation enforces the exact allowlist and strict refusal contract; all 13 recorded negative mutations are rejected. Guard installation precedes package imports, and the retained command uses selected Python with `uv --offline --frozen`. [Receipt validation](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/acceptance-amendment/verify.py:91), [command receipt](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/acceptance-amendment/command.json:2).
- Fresh evidence is internally consistent: exit 0, Python 3.14.7/macOS arm64, exact pinned dependencies, verifier runtime 2.520775 seconds, wrapper runtime 2.700174 seconds, and empty stderr. Report and stdout both hash to `7acbc5289cbcdc268a48a5973bce405451cf3bde44a3b586b48f80b2f0765a25`. All 24 amendment payload identities and the complete file set match the new inventory; prior failed and passing attempts are retained. [Report](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/acceptance-amendment/report.json:1), [inventory](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/acceptance-amendment/sha256.json:1).

### Issues

- **Critical:** None.
- **Important:** None.
- **Minor:** None.

### Cannot verify items

- ⚠️ This task-scoped diff does not independently establish every unchanged Stage 3 production contract. The retained reviewed-implementation audit, 452-test/full-check result, installed-wheel result, and verifier’s unchanged-file/domain checks support their reuse; no suite or parser scan was rerun. [Implementation verification](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/acceptance-amendment/verify.py:196).
- ⚠️ Successful historical catalog/range coverage and deployed Linux worker capacity remain unestablished, as the amended documents explicitly require. Controller completion, retirement, final inventory, and later-stage authorization remain outside this task. [Spec §8](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/sec-filing-index-ingestion-stage-3-spec.md:148).

### Assessment

**Task Quality: Approved.**

The amendment changes the documentary gate within the authorized scope while preserving strict refusal and independently verifiable history. Retained results and direct artifact checks support the current acceptance claim without changing production behavior or asserting later-stage capacity.
