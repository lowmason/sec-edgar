from pathlib import Path
import hashlib,json,re,datetime,posixpath,subprocess
root=Path('/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar')
base=root/'specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution'
out=base/'completion';out.mkdir(exist_ok=False)
plan=root/'specs/plans/5-sec-filing-index-ingestion-stage-4-spec.md'
spec=root/'specs/sec-filing-index-ingestion-stage-4-spec.md'
road_source=Path('/Users/lowell/Projects/sec-edgar/specs/sec-filing-index-ingestion-roadmap.md')
expected={plan:'87f9108735a13a9699086e5f50f1d4ce082c740d7f58eb47d37fdd775da67b45',spec:'5b822a4113eaa18c53a18ae71f244d6b69d2abd9e533381a69644e4b88cd1b0a',road_source:'0101934eadf0ca3241b03a458c80ec300012430875c44522410836ab6c0ecc03'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in expected.items():assert sha(p)==h,(p,sha(p))
def write(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
receipt={'format_version':'sec-stage4-owner-closeout-v1','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owner_message':'Approved','approval_context':'Direct response to the final implementation/verification and two closeout decisions presented at execution HEAD 8dce35b4d1ec1e17b1533c602291c89bbe4f85ad. Accepted final offline coverage and the first presented preservation disposition.','accepted_runtime_commit':'6528a4e7596ed55078cbe31892f448b3075773b3','accepted_evidence_commit':'8dce35b4d1ec1e17b1533c602291c89bbe4f85ad','coverage':'620 unique guarded offline tests; fresh native and installed proofs; independent task, whole-branch, fix and final-evidence reviews accepted','planning_disposition':'Accept independently verified checkpoint and retained evidence as preserved planning input; absent planning checkout is not represented as restored and no complete ignored-tree restoration is claimed','integration_disposition':'Keep execution branch and managed worktree; integration and cleanup remain later owner decisions','authority':{str(p):h for p,h in expected.items()},'stage7_checks':'22 reserved/not_run'}
write(out/'owner-approval.json',json.dumps(receipt,indent=2)+'\n')
deviations={1:'No runtime deviation; candidate contracts were independently reassessed before acceptance.',2:'Malformed unrelated registry rows are inspected safely; pure projection/ref validation precedes registration mutation.',3:'Snapshot authority validates canonical source input before dispatch and historical replay.',4:'An immutable original-call repair-authority anchor freezes the exact obligation and affected quarters; corrupt begun inventory blocks completion.',5:'Immutable terminal captures bind actual unfinished attempts; canonical frozen values, quarantine normalization and object-first member replay preserve checked authority.',6:'Exact receipt/context and discovered-member coverage are checked. Original unfinished discovery now retains terminal authority; required discovery failures cannot disappear from reports.',7:'Frozen legacy units are validated before sorting so malformed units become isolated gaps without hiding valid siblings.',8:'Parent cardinality and frozen provenance govern historical selection; undispatched reports require the exact canonical pending shape, and frozen failures survive later original-child success.',9:'Fixture wall time advances with monotonic time; operator proof statements were updated only after actual verification.',10:'Fixture setup uses actual durable child context; fixed synthetic bytes and process evidence were explicitly owner-approved before Task 11.',11:'The final full suite/build/native/installed proofs were refreshed after whole-branch runtime fixes; original strict parser refusal evidence remains preserved and applicable.'}
lines=plan.read_text().splitlines(keepends=True);body=[];fenced=False;ticked=0
for line in lines:
 if line.lstrip().startswith('```'):fenced=not fenced
 if not fenced:
  if line.startswith('- [ ] '):line=line.replace('- [ ] ','- [x] ',1);ticked+=1
  m=re.match(r'### Task (\d+):',line)
  if m:
   body.append(line);body.append('\n> Deviation: '+deviations[int(m.group(1))]+'\n');continue
  def rebase(m):
   target=m.group(2)
   if re.match(r'^[a-zA-Z][\w+.-]*:',target) or target.startswith(('/', '#')):return m.group(0)
   part,sep,fragment=target.partition('#')
   adjusted=posixpath.relpath(posixpath.normpath(posixpath.join('specs/plans',part)),'specs/plans/completed')
   return '['+m.group(1)+']('+adjusted+(sep+fragment if sep else '')+')'
  line=re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)',rebase,line)
 body.append(line)
header='''**Status: COMPLETE (2026-10-08)** — executed via subagent-driven-development; nothing deferred.

> Executed retirement copy of the exact approved Plan 5. The original [approved source](../5-sec-filing-index-ingestion-stage-4-spec.md) and approval snapshot retain their original bytes and historical planning status. This completion header governs this executed copy; proposed code below is historical plan text, with actual deviations recorded at each task.
>
> Stage 4: COMPLETE (2026-10-08) — implemented by plan 5 (specs/plans/completed/5-sec-filing-index-ingestion-stage-4-spec.md). See the [completion record](../../evidence/sec-filing-index-ingestion/stage-4/plan5-execution/completion/completion-record.md) and owner receipt. Original Plan 4 is superseded for this execution. Stages 5–8 remain open; next-stage routing requires a separate owner request.
>
> Preservation deviation: retire this executed copy instead of modifying/moving the hash-bound approved source. Retain the shared Stage 4 specification and SDD workspace/evidence under the approved handoff; integration/cleanup is a later owner decision.

'''
completed=root/'specs/plans/completed/5-sec-filing-index-ingestion-stage-4-spec.md'
write(completed,header+''.join(body))
road=road_source.read_text();old='- [ ] Stage 4: Backfill and daily catch-up workflows';new='- [x] Stage 4: Backfill and daily catch-up workflows'
assert road.count(old)==1
append='''
## Stage 4 completion and later-stage consistency

Stage 4: COMPLETE (2026-10-08) — implemented by plan 5 ([retired executed plan](plans/completed/5-sec-filing-index-ingestion-stage-4-spec.md)). The [hash-bound completion record](evidence/sec-filing-index-ingestion/stage-4/plan5-execution/completion/completion-record.md) supplements the unchanged approved shared Stage 4 spec. The owner accepted final actual offline coverage and the verified checkpoint/retained-evidence planning disposition. Original Plan 4 is superseded for execution.

Only Stage 4 is ticked by this completion. Stage 5 remains responsible for reconciliation and withdrawal approval; the shipped workflow/report contracts are its inputs. Stage 6 remains responsible for the complete worker image, Azure deployment/orchestration, configuration and disabled triggers. Stage 7 remains responsible for integrated validation, live smoke and recovery evidence; all 22 integrated checks remain reserved/not_run. Stage 8 remains responsible for accepted production coverage, activation and observed schedules. None of those exits is established by Stage 4 synthetic fixture proof. Their existing objectives, contracts and routing remain unchanged. Resume requires a separate owner request.

This execution roadmap was derived from the preserved historical primary/approval roadmap. Those original bytes remain unchanged. The execution branch/worktree is kept for a later deliberate integration decision.
'''
roadout=root/'specs/sec-filing-index-ingestion-roadmap.md';write(roadout,road.replace(old,new)+append)
record='''# Stage 4 Plan 5 completion record

**Status: COMPLETE (2026-10-08)** — executed via subagent-driven-development; nothing deferred.

Stage 4: COMPLETE (2026-10-08) — implemented by plan 5 (specs/plans/completed/5-sec-filing-index-ingestion-stage-4-spec.md).

The owner’s direct “Approved” response accepted final actual offline coverage and acceptance of the independently verified checkpoint and retained evidence as preserved planning input. [The immutable receipt](owner-approval.json) binds the exact approval context and source hashes. The former planning checkout remains absent; no physical restoration or complete planning ignored-tree preservation is claimed. The earlier stopped-checkout baseline disposition remains separate.

All eleven tasks passed independent task review. Whole-branch review found two report authority defects; fixes at runtime commit `6528a4e7596ed55078cbe31892f448b3075773b3` passed independent scoped re-review. The refreshed full suite passed 620 unique tests in 883.125 seconds. Build/help/version/compile/whitespace, fresh native and isolated installed proofs passed. Twelve actual process deaths exited 91 with successful reopen; 39 production files matched reviewed source/wheel/installed bytes; the complete 21-dependency CPython and synthetic 19-dependency PyPy graphs and real transitive-version refusal passed. Independent final evidence review accepted the exact 1360-file bundle. [Verification](../final-verification-refresh/refresh-report.md), [independent proof review](../final-verification-refresh-review/report.md), and [fix review](../whole-branch-fix-1/review.md) retain the concrete evidence.

Primary plus seven retained roots matched 138438 exact records and 28873 independent checkpoint blobs. Approved source/snapshot bytes, primary HEAD/index/status/legacy absences and protected refs remain unchanged. [Preservation refresh](../final-preservation-refresh/report.md) retains the audit, including its historical failure solely for the then-unresolved planning disposition; this later receipt resolves the owner decision, not the physical absence.

The executed Plan 5 is retired as a completed copy. Its original hash-bound source and snapshots retain exact bytes at their established locations. Original Plan 4 is superseded by this record and is retained unchanged; the shared Stage 4 specification therefore remains in place with its approved historical text. This completion record is the supplemental authoritative Stage 4 stamp. The execution roadmap ticks only Stage 4 and revalidates unchanged Stage 5–8 boundaries. All 22 Stage 7 checks remain reserved/not_run. No historical production coverage, deployed resource fit or schedule activation is claimed.

No plan work or review findings remain deferred. No deferred backlog exists; the statistics command reports “nothing deferred.” The available local Python runs the read-only statistics helper to preserve offline operation. The SDD ledger/review workspace remains retained under the handoff’s preservation requirement rather than being deleted by generic cleanup.

Finishing decision: keep `codex/sec-edgar-stage4-plan5` and its managed worktree at `/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar`. Reviewed runtime/evidence commits are named above and in the receipt. Integration, push, merge and worktree cleanup remain later deliberate owner decisions. No next stage is started by completion.
'''
write(out/'completion-record.md',record)
write(out/'markup-summary.json',json.dumps({'completed_checkboxes':ticked,'task_deviation_notes':11,'approved_sources_preserved':True,'completed_plan':str(completed.relative_to(root)),'roadmap_changed_stage':4,'later_stages_unticked':[5,6,7,8]},indent=2)+'\n')
write(out/'closeout-method.py',Path('/private/tmp/sec-stage4-closeout.py').read_text())
for p,h in expected.items():assert sha(p)==h
assert roadout.read_text()==road.replace(old,new)+append
assert all('- [ ] Stage '+str(n)+':' in roadout.read_text() for n in (5,6,7,8))
assert '- [ ] ' not in '\n'.join(line for line in completed.read_text().splitlines() if line.startswith('- [ ] '))
assert not (root/'specs/deferred_items.md').exists()
print(json.dumps({'completed_checkboxes':ticked,'approved_hashes_unchanged':True,'later_stage_boundaries_unchanged':True,'completed_plan_sha256':sha(completed),'roadmap_sha256':sha(roadout)},indent=2))
