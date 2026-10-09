### Spec Compliance

- ❌ Issues found: the required failed-source subset for quarantine is not enforced by `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py:68`. A pending member can carry `quarantined=True`, yielding a durable report with a quarantined source but zero failed sources. This is inherited from the illustrative invariant and conflicts with the approved report semantics in `specs/sec-filing-index-ingestion-stage-4-spec.md:67`.
- ✅ File-by-file scope check: all three required files have their corresponding additions: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/__init__.py:1`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py:1`, and `packages/sec-edgar-ingest/tests/test_workflow_contracts.py:1`. No unrelated implementation, dependency, lockfile, retention, or live-access change appears in this diff.
- ✅ The F5 attribution structure is implemented at `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py:133`: exact code and marker, nonempty unique array, selected quarantined-source membership, and optional source attribution consistency. Fatal precedence is applied before the pure-quarantine exception at `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py:172`; independent gaps and mixed selected-member progress remain incomplete.
- ⚠️ Cannot verify from diff: stored-object authority for child receipts, listing/projection provenance, already-complete sources, exact affected-quarter publication, and attribution truth remains Tasks 2–4/6. In particular, `directories` is intentionally a JSON-compatible Mapping field, not a decoded DirectoryOutcome validator (`packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py:79`); later report readers must validate its provenance and schema against retained evidence. These checks cannot be claimed from a structural roundtrip.
- ⚠️ Cannot verify from diff: preservation of original retained bytes, checkpoint/retry behavior, boundary advancement under failed directory reads, malformed-row quarantine, publication repair, and deployed resource limits are unchanged or later-task responsibilities. All 22 Stage 7 checks remain reserved/not_run; this review supplies no integrated or whole-suite acceptance.

### Strengths

- ✅ `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py:46` checks member hashes, workset/child reference namespaces, processing versions, duplicate quarters, and complete-member publication captures; `:88` checks workflow identities, exact counters/outcome, UTC/end ordering, quarter ordering, and canonical boundary dates.
- ✅ `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py:148` groups statuses by source identity using the worst status while independently retaining download/transform/quarantine progress; quarter operations remain separately counted at `:166`.
- ✅ `packages/sec-edgar-ingest/tests/test_workflow_contracts.py:73` explicitly enumerates every registered EXIT_CODES outcome and compares registry membership. `:179` exercises nested Mapping/record roundtrips and changed-counter refusal; the subsequent immutability/type-refusal tests exercise the shared codec rather than mocks.
- ✅ `packages/sec-edgar-ingest/tests/test_workflow_contracts.py:253` checks retained attributed gaps, exit 7, exact failed/quarantined counts, and roundtrip; subsequent cases cover independent failures, malformed/foreign attribution, mixed progress, and fatal precedence.

### Issues

#### Critical (Must Fix)

- None found in Task 1 scope.

#### Important (Should Fix)

- **Plan-mandated invariant gap — quarantine need not be a failed-source subset.** `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py:68` rejects quarantined members only when transformed or complete. Consequently, `replace(member, outcome='pending', transformed=False, quarantined=True)` is accepted; the same holds for deferred, throttled, and awaiting_approval. With this as the sole member, `summarize` returns pending/awaiting_approval with `pending_sources=1`, `failed_sources=0`, and `quarantined_sources=1` (`:160`), and WorkflowResult accepts the matching counters. This contradicts the explicit `quarantine is a failed subset` contract and the meaning of terminal whole-source refusal. The F5 aggregate correctly refuses to call this pure quarantine, but does not repair the invalid member/report state. Require quarantined members to have a failed status as well as no accepted transform; add a focused rejection table for all PENDING outcomes and preserve terminal failed quarantine/F5 acceptance. This is a local structural consistency check, not stored-reference authority that can be deferred to later tasks.

#### Minor (Nice to Have)

- None beyond the regression coverage required with the Important fix.

### Assessment

**Task quality:** Needs fixes.

**Reasoning:** The implementation is cohesive, scoped, and closely follows the approved contracts and F5 correction. One missing cross-field invariant permits internally inconsistent durable coverage counts and should be fixed before Task 1 acceptance.

- Check performed: read the supplied diff as the change view; the initial combined tool output truncated the implementation portion, so reread the missing first portion of the diff package only. No changed source file was separately reopened, no Git command was run, and no subagent was dispatched.
- Scoped outside checks: inspected the existing Mapping decoder/freezer in `packages/sec-edgar-ingest/src/sec_edgar_ingest/models.py:115` and `:150` to establish that JSON arrays become tuples and that nested Mapping strictness does not itself enforce semantic member invariants; inspected the approved report/count requirements in `specs/sec-filing-index-ingestion-stage-4-spec.md:67` to resolve the concrete pending-quarantine contradiction. Read the supplied F5 interface/addendum as requirements.
- Verification evidence read: controller-confirmed RED was missing `sec_edgar_ingest.workflows`, exit 1; exact unchanged 23-test GREEN was exit 0 in 0.066s, with no warnings/errors; staged whitespace check was reported clean. These are supplied controller results, not reviewer executions.
- Focused check attempted solely for the pending-quarantine doubt: guarded offline `uv run --offline --frozen --package sec-edgar-ingest python -B -c ...` construction/roundtrip probe. It exited 2 before Python execution because the sandbox denied opening `/Users/lowell/.cache/uv/sdists-v9/.git`; therefore this report does not claim a runtime reproduction. No escalation or alternative execution was attempted. The finding follows directly from the visible constructor and reducer branches; controller can run the focused regression under its approved test environment.
