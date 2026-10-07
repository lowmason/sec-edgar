Plan: /Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/plans/3-sec-filing-index-ingestion-stage-3-spec.md

Primary: /Users/lowell/Projects/sec-edgar
Worktree: /Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar
Branch: codex/sec-edgar-stage-3
Original inspected base: 5f90a2116eab21525e88a02d0988567e71d95967
Execution-documents commit: 8bb17c1277544ee46a1d351982d9e3e9c6e0d122
Preservation preflight: preservation-preflight/receipt.json; all hashes/absences match, 19088 inventory records.
Live-access authorizations: closed. All Stage 7 integrated checks: reserved.
Preflight plan conflict scan: no contradictions requiring owner adjudication identified.
Model-runtime deviation: Claude tier aliases are unavailable in this Codex runtime; standard maps to gpt-6.1-sol and capable to gpt-6-astra. Explicit supported models will be recorded per dispatch.
Task 1: pending.
Task 2: pending.
Task 3: pending.
Task 4: pending.
Task 5: pending.
Task 6: pending.
Task 7: pending.

Baseline: complete; 302 guarded tests, exit 0, 113.853s test runtime; full stdout/stderr/command in baseline/.
Task 1 BASE: 8bb17c1277544ee46a1d351982d9e3e9c6e0d122. Implementer capable tier: gpt-6-astra.

Task 1 offline dependency gate: inspected 01-red (exit 1: missing ETL/blob_address), 02-lock/03-sync/04-import/05-signatures (all exit 0); PyArrow 25.0.1. Actual uv Python 3.14.0 macOS arm64, runner Python metadata 3.14.7 distinguished.
Parallel read-only lookup complete: retained-evidence-locations.md; cheap tier gpt-6-luna.

Cross-task clarification: ObservationRef.quarter_counts counts retained observation rows by filing-date quarter; sum equals source_row_count, distinct_key_count separately counts keys. Task 1 adds identical-duplicate regression; downstream transform/readback must preserve this meaning.
Task 1 in-progress spec correction: closed daily-only GenerationManifest may have membership_source=None, per Stage 3 §6/Task 4; it cannot infer withdrawals. Worker notified before commit/review.

Task 1: complete (commits 8bb17c1..966bd9e, review clean). Exact public signatures match interfaces.md; 80 covering guarded tests exit 0, retained 16-final-covering-green. Review: task-1-review.md. No open findings.
Task 1 reviewer runtime deviation: named task-reviewer unavailable; default read-only agent with full template, gpt-6-astra capable tier.
Task 1 cannot-verify resolution: fingerprints/identity/adoption/no-op -> Tasks 3–5; CAS orchestration/index ordering -> Task 5; offline full/process proof -> Task 7; deployed Linux resource/integrated checks -> later roadmap Stage 7 reserved.
Task 2 BASE: 966bd9e6bc8d5ce3803c0db7e95a4011e94e2ee9. Implementer standard tier: gpt-6.1-sol.

Task 2: complete (commits 966bd9e..3b2c03a, review clean). Exact parser signatures match interfaces.md; 19 covering guarded tests exit 0, including committed 17-committed-green. Review: task-2-review.md. No open findings.
Task 2 cannot-verify resolution: source/envelope/quarantine/duplicate integration -> Task 3; before-adapter refusal -> Task 6; canonical/replay/CAS -> Tasks 3–6; full ten parsed receipts/installed/process -> Task 7. Explicit independent golden literals verified; authoring provenance retained in report/red sequence.
Task 3 BASE: 3b2c03a4f129d88d1bb4cd7f9ada314fb895ad85. Implementer capable tier: gpt-6-astra.

Task 3: complete (commits 3b2c03a..1f6726d, review clean). Exact production signatures match interfaces.md; 28 guarded covering tests exit 0 and retained independent restart proof exit 0. Review: task-3-review.md. All 5 artifact-hashes payload lengths/SHA256 independently matched actual files. No open findings.
Deviation Task 3: etl/state.py unchanged because checked Task 1 accept_transform already implements required create/adopt semantics; no redundant change needed.
Downstream contract: observation Parquet uses Parquet 2.6/snappy/dictionary disabled/use_compliant_nested_type=False to preserve original_fields item schema; no run/time/image data in row bytes. Canonical observation manifest envelope keys are format_version/observation/image_digest, format sec-observation-v1.
Task 3 cannot-verify resolution: partial/empty publish -> Tasks 5–6; gates/rebuild/pointer -> Tasks 4–5; full retained/installed/process/check -> Task 7; deployed Linux/all22 -> roadmap Stage 7 reserved.
Task 4 BASE: 1f6726d66f7cd13af377c2cd8f9e3d52c741e99b. Implementer capable tier: gpt-6-astra.

Task 4 implementation clarification: preserve approved GenerationManifest fields; immutable candidate-prefix retained-base.json records exact supplied prior GenerationCapture when retained rows require it. Strict canonical capture/hash/length/quarter/generation and explicit prior files must validate, no mutable latest. Supporting artifact deviation, not public contract extension.

Independent read-only parser preflight dispatched while Task 4 writer runs: retained_parser_preflight standard tier gpt-6.1-sol. Evidence-only ownership retained-parser-preflight/, actual parser/all ten retained receipts under existing network guard, no source changes or substitute for Task 7 final driver. Primary inventory recheck: all 19088 records unchanged during Task 4.

Task 4 implementation DONE: HEAD 9f47166ca318b0a9f8e8cf6bb428e49bfb8e4486; final 26 guarded tests exit 0, no warnings/skips. Root inspected full green-final.json and matched all 20 artifact-ledger payloads (19 objects + proof). Fresh capable Task 4 reviewer active; not yet complete.

Retained receipt blocker discovered independently: all 10 original hashes/counts/date bounds/selected rows and parser scans match, total 970622 rows. Three quarterly sources SEC-0141/0142/0143 have 21/24/6 conflicting duplicate observations (51 total), whole-source acceptance refused under approved duplicate rule. Guarded offline preflight exit 1, 125.769s; exact rows/reasons in retained-parser-preflight/report.json. No syntax/family failures, no source edits. Spec §8: invalid retained rows are blockers and cannot be bypassed to stamp completion. Continue unaffected implementation/review/proofs, preserve refusal, no COMPLETE/retirement/roadmap tick pending owner reconciliation at completion.

Task 4 initial review FAILED: Important I1 exact-base delta validation gap permits suppressed withdrawal changes with gate clear and consistent hashes/counts. No Critical/Minor. Fix round 1 returns to original implementer; exact base capture needed every noninitial candidate and adversarial full-delta covering tests. Task 4 remains incomplete. Retained preflight prose correction: SEC-0142 earliest actual conflict 87808 (not 1240); report bytes unchanged.

Retained blocker concrete production proof: actual transform_member on SEC-0141/0142/0143 quarantines at lines 6580/87808/40292, reason conflicting duplicate logical key. No accepted Processing/ObservationRef/pointer, raw bytes preserved. Guarded follow-up assertion proof exit 0, 18.056s, stderr empty; retained-parser-preflight/transform-refusal/report.json SHA256 6f16618b2a2a3ee6888bd288284764e032c19acf5881655425b38c666f02d900. Original full scan remains exit 1 and untouched.

Task 4 fix round 1 DONE: e460df72b72f090762f382136cbb9e7689635d21. Root verified full frozen/offline guarded covering output, 31 tests exit 0 and all 21 fresh artifact records; original20 unchanged. Scoped re-review active, Task 4 not yet complete. Actual sidecar contract deviation supersedes earlier scope: every noninitial generation requires candidate-prefix retained-base.json with exact base GenerationCapture, even retained_from_generation=None; public retained field retains absent-key meaning. SQLite validates all exact-base changes/counts/provenance before gate/adoption.

Task 4: complete (commits 1f6726d..9f47166..e460df7, initial Important I1 resolved in fix round 1, scoped review Approved/no new findings). Exact public signatures unchanged. Final 31 frozen/offline guarded tests exit0; fresh21 artifact payloads independently matched; original20 unchanged. Review task-4-review.md + task-4-re-review-1.md. Supporting artifact deviation retained-base.json for every noninitial exact base; no state.py/support_etl.py changes needed. Cannot-verify resolution earlier guards/quarantine/pins -> reviewed Tasks1–3 + Task7 full check; pointers/CAS/read/repair -> Task5; all22 deployment checks -> later Stage7 reserved.
Task 5 BASE: e460df72b72f090762f382136cbb9e7689635d21. Implementer capable tier gpt-6-astra.

Retained blocker classification from exact full scan (no rerun): 45 conflicts differ only in form_type, 6 only in company_name; same normalized CIK/path/date/accession. conflict-classification.json binds unchanged report SHA. Observed differences, not authorization to revise identity or accept sources. Concrete owner policy reconciliation remains pending after unaffected implementation/proofs.

Task 5 outcome clarification/deviation: publication_conflict may carry last attempted uncommitted candidate manifest_ref, with generation_id=None and clear candidate_ref=None; before any candidate both remain None. Shape/signature unchanged. Illustrative null-return loop does not itself carry required latest-candidate/race command-gap evidence. Task6 strict result validation/Error.details must distinguish conflict artifact refs from committed captures; no publication claim. Published/unchanged fields retain current semantics. Worker must retain covering tests of exhaustion and deadline-after-loss.

Task 5 implementation DONE: HEAD 1d14c9ceee330affd5ab961974932f2f09782f1e; final green-final-covering.json full argv/stdout/stderr inspected, 66 tests/exit0/no warning or failure diagnostic. Root independently matched three capture manifest hashes/lengths plus six explicit data/change files (9 payloads) and checked old/current rows and partial/full repair values. Fresh capable task5_review active; not yet complete. Actual helper seed_observation(objects,state,context,settings,*,period=2026Q4,kind=quarterly,rows=None,seconds=0) uses actual transform. Processing.value published absent means false; added only in repair, true iff every output quarter has receipt-backed membership; public state signatures unchanged.

Task 5 initial review PASS/Approved, no Critical/Important; Minor M1 second reader-spool failure coverage. Controller chooses to resolve now (library fail-closed pre-yield guarantee, focused test only, no speculative production patch), original implementer fix round1; Task5 remains incomplete until scoped review. Cannot-verify disposition Task4 exact validation -> clean prior review, pins/timeouts/codec -> prior gates + Task7full, conflict ref semantics -> Task6, all22 Linux -> laterStage7 reserved.

Task 5: complete (e460df7..1d14c9c..1ec404a, review Approved + Minor M1 resolved). Final core66 tests/exit0, then test-only M1 publication24/exit0; all full output inspected, no warnings. Review task-5-review.md + task-5-re-review-1.md, no open findings. Source signatures unchanged; conflict manifest_ref/Processing.published/helper deviations documented above and report.
Task 6 BASE: 1ec404a29f945448c735efe712526edc41efaacc. Implementer capable tier gpt-6-astra.

Task 6 implementation DONE_WITH_CONCERNS: HEAD 9c12b5738f8969380a0a5aad4f33295356abf239; exact seven assigned files committed, clean tree. Root inspected final green-final-retained.json full output: 57 tests/exit0/66.703s, no warnings. Independently matched all485 final ledger payloads (26 ledgers, 3,094,552 bytes, 40 results,43 intents,8 checkpoints) and all64 actual-summary refs including actual result equality; summary SHA d37cd6b6f8e0056cf601dd5f122cca7f11b3e664d9c336e1f554e2b174b83a86. Fresh capable task6_review active; Task6 not yet complete.
Task6 actual refinements: write_etl_result adds backward-compatible keyword-only observer=None for named boundaries; EtlResult Record uses canonical_json(to_mapping()) rather than nonexistent to_json; immutable command.json envelope freezes exact context plus intent {command,today,workset,force}. Public run signatures unchanged, acquisition bytes unchanged. Downstream Task7 consumes actual refinements.
Controller scope correction to Task6 report: Task7 performs native proof/reconciliation and records all22_stage7_checks reserved; it does not execute those22 deployed integrated checks. They remain later roadmap Stage7, as global constraints require. Native3.14.0/macOSarm64 limits and retained duplicate source blocker remain recorded; no completion stamp.

Task6 initial review FAILED: Important I1 plan-mandated canonical snapshot bytes not enforced (normalized payload identity alone accepts reordered/whitespace JSON). Critical/Minor none. Controller verified exact code path/approved Step2; no plan contradiction. Fixround1 original implementer, owned command boundary+CLI tests, preserve acquisition decoder; Task6 incomplete. Cannot-verify broader build/process/wheel->Task7; exact-base fidelity->clean Task4; historical compatibility->57 acquisition regression +Task7full; all22/Linux->later roadmapStage7 reserved (review prose attribution corrected).

Task6: complete (1ec404a..9c12b57..63c3273, initial Important I1 resolved in fixround1, scoped review ADDRESSED/no new findings). Main57 tests/exit0 then isolatedfix28/exit0/3.767s, full logs inspected; all511 fix payload hashes matched, actual malformed-input no Processing/output/pointer verified. Review task-6-review.md +task-6-re-review-1.md. Public signatures actual optional writer observer/context envelope documented; acquisition decoder and bytes unchanged. No open review findings. Cross-task full/process/build/wheel->Task7, exact-base->Task4clean, all22/Linux->laterroadmapStage7reserved. Retained51conflict source acceptance gate still blocks COMPLETE/retirement/roadmap.
Task7 BASE: 63c327390f76d466e04fb8285f7c95f39e4f4937. Implementer capable tier gpt-6-astra. Additional actual-interface/blocker/durable-evidence notes: task-7-execution-notes.md.
