# Task 2 implementation report

Status: implemented, awaiting fresh controller task review. Commit: `4780e1ffaa65f3d33bf1c68cf01256e868018b66` (owned five paths only; report/evidence unstaged).

## Scope and authority

Applied approved Plan5 Task2 in isolated worktree `/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar`, branch `codex/sec-edgar-stage4-plan5`, starting from accepted Task1 commit `133357cd140bc571ce72935989820fdc8bae5d7c`. Read the task brief including verbatim Global Constraints. Used clean-code, clean-coder, test-driven-development and verification-before-completion. No subagents; no controller ledger modification. Execution used approved escalation for isolated filesystem/cache access with offline frozen dependencies. No live access, provider/auth construction, network fetch, dependency/parser changes, stage7 checks, or retained runtime/config/binding/workset rewrites. All mutations in regressions target independent temporary fixtures.

## Changed files and APIs

- `packages/sec-edgar-ingest/src/sec_edgar_ingest/discovery.py`: public `reopen_listing` rename plus its one internal caller; body unchanged.
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/provenance.py`: exact approved immutable registry, canonical source reference, original discovery session/listing authority, pure recovered-parent reconstruction and validation, exact projection, checked member read and binding transfer functions.
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py`: exact approved inventory/all/register operations. Inventory exposes unresolved corrupt records while retaining valid siblings.
- `packages/sec-edgar-ingest/tests/support_workflows.py`: exact approved listing/IDX/ZIP/pack, CommandHarness and simple_pack builders, including repeated response entries.
- `packages/sec-edgar-ingest/tests/test_workflow_provenance.py`: all four supplied regressions retained, plus frozen metadata/ancestor/receipt/byte tampering, SQLite close/reopen durability, pure recovery, descriptor authority, actual valid-listing unauthorized-child, successful snapshot transfer and actual parser compatibility cases.

Boundary clarification confirmed by controller: header `.record(result, context, evidence)` is a forward interface; Task2 exact step implements registry only, and Task5 introduces checked receipt/record/completed authority. No completion stub or success invention. No API deviation. Production modules and support builders match approved snippets exactly; discovery differs only by the requested rename.

## Insight before / after

Before: discovery's private `_reopen_listing` already checked retained hashes and receipt context, but workflow members had no durable authority link back to original discovery.

After: `read_member` reopens the original parent and recomputes its exact singleton projection against the immutable registry. `transfer_binding` compares the returned bind_once winner to the requested snapshot and refuses divergence without altering the winner. Pure recovery checks complete ordered units and actual ancestor authorization before accepting a descriptor.

## TDD and actual command evidence

Evidence is create-only and unstaged under `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-2/`. Each `*-command.txt` contains actual argv and child exit; the paired log contains complete stdout/stderr.

Exact unchanged scoped runner:

```text
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_provenance.py -v
```

1. Four supplied regressions and support builders written before production; initial child fails missing `sec_edgar_ingest.workflows.provenance`. `red.log` retains actual child output. Initial zsh wrapper subsequently fails on read-only `status`; `wrapper-note.txt` records this separately.
2. Six further real-store/pure-recovery regression methods added before production. `red-all-command.txt` / `red-all.log`: actual child exit1, missing-module failure as required. No dependency/cache failure.
3. Exact production snippets created. `green-first-command.txt` / `green-first.log`: child exit1, 10 methods run, five subtest setup errors because new fixture mutations used literal DiscoverySession IDs rather than real SHA256 keys. No production patch.
4. Corrected only temporary test row keys; unchanged assertions. `green-corrected-setup-command.txt` / log: child exit0, 10 methods PASS.
5. Supplemental checks added after initial green without production changes. `supplemental-first` child exit1 due to test import using wrong module for parse_listing. Removed redundant root selection rewrite/import; selection already exact. Supplemental checks validate descriptor adoption, real valid unauthorized child and successful binding. This is additional verification of the supplied implementation, not a second feature implementation.
6. Required scoped verification with child envelopes: `workflow_provenance-final` exit0/13 PASS; `discovery-final` exit0/43 PASS; `worksets-final` exit0/20 PASS; `collection-final` exit0/35 PASS.
7. Investigated an apparent fixture escape defect. It was a mistaken reading of serialized tool output: approved/current Python literals already produce CRLF/LF. No literal or production correction. Added actual daily and quarterly parser compatibility test; `fixture-red-command.txt` has actual exit0/14 PASS and is a diagnostic attempt, NOT a red. Preserved its original label as evidence without misrepresenting the result.
8. Tightened pure-recovery failed-root fixture to correct Error source_id schema and exact ancestor Conflict assertion, avoiding a broad ValueError false-positive. `provenance-final-14-command.txt` / log: actual child exit0, 14 methods PASS, no warnings. All original supplied assertions retained; divergent Binding test now also proves complete row canonical bytes/version unchanged.
9. `git -c core.whitespace=cr-at-eol diff --check`: child exit0, empty output (`diff-check*`). Staged diff check also exit0, empty output (`staged-check*`); `staged-diff.log` retains exact five-file review diff. `commit-command.txt` / `commit.log` record actual commit argv/exit0/output.

Final relevant checks: provenance14 + discovery43 + worksets20 + collection35 =112 PASS. Full477 baseline belongs to controller; full suite deliberately not repeated because Task11 owns it.

## Self-review and Clean Code application

Fixed: exposed retained listing authority under public `reopen_listing` (N2/N4) at discovery.py:240 and its caller; same implementation/semantics.
Fixed: added independent real-store corruption/retention/durability boundaries (T1/T5/T6), test_workflow_provenance.py. Strengthened recovery refusal to an exact ancestor error and binding refusal to unchanged row bytes.
Applied: provenance verification/reconstruction/projection responsibilities follow existing domain boundaries (G6/G30/G34); no extraction solely for function length. Original API names/snippets kept as required. No adjacent cleanups or unrelated changes.

Checked exact body/canonical addresses, session revision authority, failed-unit preservation, listing receipt context/hash/size, actual root-year-quarter authorization including cached units, immutable source metadata, exact registered child recomputation, registry corruption isolation, restored/reopened source identity and original bytes, and bind_once winner equality. Every reused temporary tampering fixture restores retained bytes; one-use fixtures are discarded only by their TemporaryDirectory lifetime. Tests never rely on arbitrary fixture_workset listing hashes for provenance authority.

No implementation concern remains from scoped checks. Fresh independent review remains a controller checkpoint; this report does not self-accept Task2. All22 Stage7 integrated checks remain reserved/not_run.


## Round 1 independent-review corrections

Controller relayed two Important independent-review findings against initial commit `4780e1ffaa65f3d33bf1c68cf01256e868018b66` and confirmed both corrections are required by existing approved isolation/refusal boundaries. This section supersedes the initial statement of exact-snippet adoption for the two methods below; approved plan/spec bytes remain unchanged. Review identity and acceptance checkpoint are owned by the controller. Applied receiving-code-review alongside the existing code/TDD/verification skills: checked current code and reproduced both actual defects before fixes. No public API change, dependency/parser change, acceptance weakening, network access, controller ledger edit or unrelated edit.

Finding 1: `project_member` indexed `member_ref` on every registry row, so an unrelated missing-key row raised KeyError and prevented a valid sibling projection. Changed only the recursion scan to `row.value.get('member_ref')`. It still refuses an actual registered projection; malformed unrelated records remain untouched and visible through `inventory()` as legacy_member_unresolved.

Finding 2: `WorkflowMembers.register` called mutating project_member before comparing supplied member_ref, admitting a correct projection on a wrong-context canonical singleton refusal. It now uses read_parent and projection to compute the pure expected child, compares both the complete selected child and source_ref(expected) to supplied member_ref, and only then calls project_member. Refusals introduce no registry/object entries. Existing exact equality, original discovery/listing validation, durable idempotence and recursive-member constraints remain intact.

Changed owned files for this correction: workflows/provenance.py, workflows/members.py, tests/test_workflow_provenance.py only. The initial discovery rename and support builders are unchanged.

### Actual TDD evidence

Create-only unstaged evidence: `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-2/fix-1/`. Every command envelope includes actual argv and child exit; each paired log retains full stdout/stderr.

Added two real-store regressions before changing production:

- test_malformed_unrelated_registry_row_does_not_block_valid_projection: creates an unrelated missing-member_ref record, projects the valid discovered sibling, checks valid inventory plus retained unresolved gap and unchanged corrupt row bytes/version, then checks the registered-child recursion prohibition remains enforced.
- test_refused_wrong_context_registration_changes_no_registry_or_objects: constructs a canonical singleton with altered context, retains it, captures complete registry and retained object path/byte inventories, refuses registration, and asserts both inventories remain identical.

Exact covering command (unchanged red/green):

```text
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_provenance.py -v
```

`fix-1/red-command.txt` / red.log: child exit1,16 methods, one production KeyError from missing member_ref and one assertion FAIL showing a newly admitted WorkflowMember on refused wrong-context registration. Existing14 methods pass. These are genuine behavior reproductions on the initial committed implementation, not fixture setup errors.

After the two minimal corrections, workflow_provenance-green command/log: child exit0,16 PASS. Guarded regressions retain exact test filenames and same runner prefix: discovery-green exit0/43 PASS, worksets-green exit0/20 PASS, collection-green exit0/35 PASS. Final relevant total114 PASS, no warnings. Full suite remains reserved to Task11; all22 Stage7 integrated checks remain reserved/not_run.

Whitespace/scoped diff and correction commit envelopes are captured below in fix-1 evidence. The report and evidence remain unstaged for controller preservation/review.

### Self-review and adoption note

Fixed: added malformed unrelated registry and side-effect-free refusal boundary coverage (T1/T5/T6), test_workflow_provenance.py:381/403. Fixed: separated pure exact projection verification from admission inside register (G30/G34), members.py:31. No discretionary tidying or adjacent edit was bundled.

Insight before: the recursion scan trusted unrelated record shape; register performed admission before checking the caller's supplied singleton.
Insight after: unrelated malformed records no longer obstruct valid work, while wrong-context registration is rejected before object or registry writes. Neither correction permits recursive projections or weaker original-parent authority.

Task5 adoption must retain the corrected project_member scan, members.py provenance imports (projection/read_parent/source_ref), and pure-preflight register method while extending receipt/record/completed methods. Replacing the entire class from the earlier snippet would reintroduce Finding2. Public Task2 APIs and Task5 record/completed boundary are unchanged.

Correction commit: `17c2fbf8a99f0b54c89e6a579fea731fd2210614`. Actual commit child exit0; only the three named owned files committed. Both working/staged whitespace checks exit0 with empty output. Exact review diff: fix-1/staged-diff.log. Awaiting independent re-review; no self-acceptance.
