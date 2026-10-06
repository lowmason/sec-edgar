"""Cite the categorized claims and preserve capture-time review boundaries."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-1'
TASK=BASE/'final-fix'
claims=json.loads((TASK/'claims.json').read_text())['records']
groups=json.loads((TASK/'claim-groups.json').read_text())
category_counts=__import__('collections').Counter(row['category'] for row in claims)
metadata={'boundary':'Controller-owned review/acceptance receipt, excluded from correction manifest; initial capture-time state only.',
 'whole_branch_review':'With fixes; P2 index classification/coverage and P3 S7-01 wording',
 'correction_scoped_review':'pending', 'final_candidate_freeze':'pending', 'owner_acceptance':'pending',
 'controller_obligation':'Retain exact scoped review, final candidate finding/manifest hashes and explicit owner revision/date/limitations acceptance; no automatic PASS or acceptance.'}
(TASK/'controller-boundary.json').write_text(json.dumps(metadata,indent=2)+'\n')
coverage=['# Final correction claim coverage','',
 'Every new record is an append to the exact original index prefix. Retention observations remain history. '+
 'Documentation asserts a retained primitive/schema, application handling is a design observation, selections use exact R3 receipts, '+
 'assumptions have impact/Lowell ownership/resolution, and all effective checks are reserved/not_run.', '',
 'Plan evidence design (lines45/66), Task5 contract/permission/schedule steps and Stage1 §§5.2–5.3, 7 and 8 require these distinctions. '+
 'Original Tasks1–4 observation/decision rows remain the source/runtime/accounting basis. '+
 'The classification correction obtains no new evidence and grants no later-stage authority.', '',
 '| Plan/spec/finding coverage | Independent claim IDs | Limit |','|---|---|---|']
for group,ids in groups.items():
 section='Finding §6; Stage1 §5.2' if group=='space' else 'Finding §8; parent §§4,6–7' if group=='reserved' else 'Finding §§2/5; Stage1 §5.3'
 coverage.append('| '+group+' — '+section+' | '+', '.join(ids)+' | documentation/selection/design/assumption boundary; effective behavior not_run |')
coverage += ['', 'All five exact categories occur in the current index. Newly appended category counts: '+str(dict(category_counts))+'.', '',
 '## Per-claim requirement and provenance route','',
 '| ID / category | Exact independently supportable claim | Source and receipt semantics |','|---|---|---|']
for row in claims:
 coverage.append('| '+row['evidence_id']+' / '+row['category']+' | '+row['claim'].replace('|',' / ')+' | '+
 row['url_or_artifact'].replace('|',' / ')+'; SHA256 '+row['sha256']+'; '+row['accessed_or_received_at_utc']+'; '+row['method']+' |')
coverage += ['', 'Full impact, responsible actor, resolution and required artifact fields remain in [claims.json](claims.json) and [claim-provenance.json](claim-provenance.json).',
 'Only [controller-boundary.json](controller-boundary.json) supplies current controller process status; its initial pending values make no future review prediction.']
(TASK/'coverage.md').write_text('\n'.join(coverage)+'\n')

finding_path=ROOT/'specs/sec-filing-index-ingestion-stage-1-findings.md'
finding=finding_path.read_text()
finding=finding.replace('**READY for the bounded Stage 1 source/runtime prerequisite conclusion, awaiting final review and exact-revision owner acceptance. Stage 1 is incomplete.**',
 '**The bounded source/runtime feasibility conclusion is supported; this corrected readiness candidate awaits scoped re-review, final freeze and exact-revision owner acceptance. Stage 1 is incomplete.**')
finding=finding.replace('The remaining completion gate is Lowell Mason\'s explicit acceptance of the reviewed finding revision, date and limitations;',
 'Final whole-branch review identified P2 claim-index coverage and P3 selection wording corrections; this batch addresses them and awaits scoped re-review. The subsequent completion gate is Lowell Mason\'s explicit acceptance of the reviewed finding revision, date and limitations;')
finding=finding.replace('The five categories remain distinct:',
 'The append-only correction supplies categorized claims and [claim/requirement coverage](evidence/sec-filing-index-ingestion/stage-1/final-fix/coverage.md); exact source artifacts, hashes and original receipt-time semantics are in [claim provenance](evidence/sec-filing-index-ingestion/stage-1/final-fix/claim-provenance.json). The five categories are now independently represented in the index:')
finding=finding.replace('Exact owner proposal revision 3 SHA-256',
 'E-FF-OWNER-BINDING, E-FF-OWNER-ACR, E-FF-OWNER-TOOLS and E-FF-OWNER-OBSERVER independently index the named selections against their exact original receipts. Exact owner proposal revision 3 SHA-256')

def citation_paragraph(group_names,claim_text):
 ids=[identifier for name in group_names for identifier in groups[name]]
 return claim_text+' Claim IDs: '+', '.join(ids)+'.\n\n'

provider_citations=citation_paragraph(['jobs','states','async'],
 'The selected Jobs operations/states, ADF Web constraints and ARM async guidance are documentation claims; causal tuple/result, unknown-state and turnOffAsync/retry handling are distinct application design records; D-18 is separately receipt-bound owner policy. ADF 202 output sufficiency is explicitly an assumption with operator-recovery impact.')
provider_citations+=citation_paragraph(['resources','auxiliary'],
 'Each of sixteen auxiliary resource schemas and its separate PUT/GET response contract is independently indexed with a direct official URL and exact retained-source byte/hash receipt. Optional fields and documented success/accepted responses never prove deployed readback.')
provider_citations+=citation_paragraph(['permissions','bootstrap','network','storage'],
 'Documented Actions/DataActions, namespace bootstrap strings, scopes/audiences, public network constraints, lease and actual ETag primitives are separately indexed. Application Blob-only lifecycle and network rules remain selections/design records; HNS/Table coexistence is separately an assumption requiring S7-14 proof. No role or identity grant is asserted effective.')
provider_citations+=citation_paragraph(['schedule','telemetry','tools','retry'],
 'Eastern/DST serialization, telemetry routes/table fields/retention bounds and published tool versions are documentation claims. Existing local conversions are observations. Log-alert selection and zero-retry maintenance trade-offs are application design; tool choices use R3 receipt records. Telemetry attribution remains an assumption with S7-17 resolution.')
finding=finding.replace('## 6. Resources, volume, temporary space and retry rationale',provider_citations+'## 6. Resources, volume, temporary space and retry rationale')
space_ids=[row['evidence_id'] for row in claims if row['category']=='Assumption' and row['evidence_id'] not in ('E-FF-ASSUME-HNS-TABLE','E-FF-ASSUME-ADF-202','E-FF-ASSUME-LOG-ATTRIBUTION')]
finding=finding.replace('Task5 supersedes Task3\'s numeric capacity phrasing:',
 'Assumption IDs '+', '.join(space_ids)+' explicitly separate listing scale, output scratch, generation scratch, reserve, sequential cleanup/model, unobserved tail and numeric Jobs allocation. Every row records impact, responsible owner Lowell Mason and a named later measurement/readback obligation. Task5 supersedes Task3\'s numeric capacity phrasing:')
finding=finding.replace('The [manifest](evidence/sec-filing-index-ingestion/stage-1/task6/evidence-manifest.json) is a bounded SHA256/byte inventory.',
 'The [historical Task6 manifest](evidence/sec-filing-index-ingestion/stage-1/task6/evidence-manifest.json) remains unchanged. Its mutable old-path references are verified against exact immutable old bytes using [historical-path-map.json](evidence/sec-filing-index-ingestion/stage-1/final-fix/historical-path-map.json), never against substituted new hashes. A separate correction-generation checker and manifest record the current claims/citations. The historical manifest is a bounded SHA256/byte inventory.')
finding=finding.replace('These checks require their own later implementation, permissions and authorization;',
 'Each entry has its own categorized claim with selected version, required passing artifact and responsible actor: '+', '.join(groups['reserved'])+'. These checks require their own later implementation, permissions and authorization;')
finding=finding.replace('Task6 scoped review and the controller\'s requested GPT-6.1 Max whole-branch review are pending for this draft.',
 'Capture-time history: Task6 scoped review passed its stated boundary; the subsequent GPT-6.1 Max whole-branch review returned With fixes (P2 index categorization/coverage and P3 S7-01 wording), retained [exactly](evidence/sec-filing-index-ingestion/stage-1/final-fix/before/final-whole-branch-review.md.'+
 next(r['sha256'] for r in json.loads((TASK/'historical-path-map.json').read_text())['records'] if r['source_path'].endswith('final-whole-branch-review.md'))+
 '). This correction candidate awaits scoped re-review at capture time. Current controller review/freeze/acceptance status is recorded only in [controller-boundary.json](evidence/sec-filing-index-ingestion/stage-1/final-fix/controller-boundary.json), an explicitly excluded post-capture process supplement; it can record completed review without changing these technical finding bytes. No completed scoped verdict or final acceptance is predicted.')
finding=finding.replace('The frozen draft references and capture boundary are supplied in task6/draft-freeze.json for review only; they are not an acceptance record.',
 'The original draft140f409493cc92c48b14dbe27d47ba5852b5b8c66db5de66d3ffd30c20f5c52c and TasK6 manifest e042f36446bfdd4e236e9286fb901e05c927585b1d7cb44491c93eea16154b10 remain retained historical referents. The correction generation manifest excludes itself, freeze receipts and later review/acceptance metadata to avoid circular hashes. Only the controller freezes the final post-review acceptance candidate. Neither historical draft nor correction capture is owner acceptance.')
finding_path.write_text(finding.replace('TasK6','Task6'))

checklist_path=BASE/'readiness-checklist.md'
checklist=checklist_path.read_text().replace('**Technical prerequisites READY; Stage 1 completion BLOCKED pending reviewed exact-revision finding acceptance.**',
 '**Bounded feasibility supported; correction candidate pending scoped re-review/final freeze; Stage 1 completion BLOCKED pending exact-revision finding acceptance.**')
checklist=checklist.replace('| 4a. API, async/execution and durable result |', '| 4a. API, async/execution and durable result | '+', '.join(groups['jobs']+groups['states']+groups['async'])+'. ')
checklist=checklist.replace('| 4b. Blob/HNS/Table/lease/CAS and trust |','| 4b. Blob/HNS/Table/lease/CAS and trust | '+', '.join(groups['storage'])+'. ')
checklist=checklist.replace('| 4c. Actor, audience, scope and network |','| 4c. Actor, audience, scope and network | '+', '.join(groups['permissions']+groups['network'])+'; every bootstrap Action in [coverage](final-fix/coverage.md). ')
checklist=checklist.replace('| 4d. Eastern/DST and observability |','| 4d. Eastern/DST and observability | '+', '.join(groups['schedule']+groups['telemetry'])+'. ')
checklist=checklist.replace('| 1b. Cloud, tenant, subscription, group, environment, names and operator |','| 1b. Cloud, tenant, subscription, group, environment, names and operator | E-FF-OWNER-BINDING. ')
checklist=checklist.replace('| 1d. Every accepted operating default |','| 1d. Every accepted operating default | E-FF-OWNER-OBSERVER / E-FF-POLICY-RETRY-POLICY / E-FF-DOC-MAINTENANCE. ')
checklist=checklist.replace('| 1e. Runtime, tools, APIs, permissions, registry/pull and rollback |','| 1e. Runtime, tools, APIs, permissions, registry/pull and rollback | E-FF-OWNER-ACR / E-FF-OWNER-TOOLS / E-FF-DOC-CLI-RELEASE / E-FF-DOC-BICEP-RELEASE; sixteen resource schemas and32 method-specific auxiliary claims in [coverage](final-fix/coverage.md). ')
checklist=checklist.replace('| 5. No blocking uncertainty; scope/contract revision explicit; deployment checks clearly reserved |','| 5. No blocking uncertainty; scope/contract revision explicit; deployment checks clearly reserved | Assumptions '+', '.join(row['evidence_id'] for row in claims if row['category']=='Assumption')+'. Reserved claims '+', '.join(groups['reserved'])+'. ')
checklist=checklist.replace('| PASS technical conclusion, subject to review |','| Correction candidate; scoped re-review pending |')
checklist=checklist.replace('READY names the bounded technical conclusion; the complete Stage1 exit remains blocked by line6. The controller-owned GPT-6.1 Max whole-branch review is unrun for this draft.',
 'The bounded feasibility conclusion remains supported. The complete Stage1 exit remains blocked by line6. Capture-time history: GPT-6.1 Max whole-branch review returned With fixes; this correction batch awaits scoped re-review, with no PASS prediction. Current process state comes from [controller-boundary.json](final-fix/controller-boundary.json).')
checklist += '\nClaim categorization/coverage correction: [coverage](final-fix/coverage.md), [source byte/hash and receipt semantics](final-fix/claim-provenance.json). All five categories occur; historical retention observations and verifier/results remain unchanged. Current correction checks are separate from historical Task6 PASS receipts.\n'
checklist_path.write_text(checklist)
print(json.dumps({'finding_sections':finding.count('\n## '),'claim_records':len(claims),'status':'scoped re-review and owner acceptance pending'},indent=2))
