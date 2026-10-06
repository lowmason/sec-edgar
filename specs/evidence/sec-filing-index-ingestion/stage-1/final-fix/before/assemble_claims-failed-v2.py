"""Append claim-level records from retained inputs without acquiring new evidence."""
import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-1'
TASK = BASE / 'final-fix'
NOW = datetime.now(timezone.utc).isoformat()
FIELDS = 'evidence_id,claim,category,method,url_or_artifact,accessed_or_received_at_utc,versions,result,limitation,sha256,command,exit_code'.split(',')
CLAIMS = []
PROVENANCE = []
GROUPS = {}

def relative(path):
    return str(path.relative_to(ROOT))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def add(identifier, claim, category, artifact, time, semantics, version, result, limitation, group, url=None, receipt=None, extra=None):
    path = ROOT / artifact if str(artifact).startswith('specs/') else BASE / artifact
    row = dict(zip(FIELDS, [identifier, claim, category,
        'Offline claim reconciliation of retained evidence; '+semantics,
        (url+'; ' if url else '')+relative(path), time, version, result, limitation, sha(path), '', '']))
    assert identifier not in {r['evidence_id'] for r in CLAIMS}
    CLAIMS.append(row)
    GROUPS.setdefault(group, []).append(identifier)
    PROVENANCE.append({'evidence_id':identifier, 'category':category, 'source_artifact':relative(path),
        'source_bytes':path.stat().st_size, 'source_sha256':sha(path), 'source_url':url,
        'receipt_artifact':receipt, 'time_value':time, 'time_semantics':semantics,
        'scope':'Retained evidence only; no new access or effective deployment proof', **(extra or {})})

CONTRACTS = json.loads((BASE/'provider/task5-contracts/retrieval-metadata.json').read_text())['records']
FIX = json.loads((BASE/'provider/task5-fix1/retrieval-metadata.json').read_text())['records']

def doc(identifier, claim, metadata_id, version, group, limitation='Bounded rendered documentation; actual selected deployment/request/build behavior remains reserved/not_run.'):
    record = next(r for r in CONTRACTS if r['id']==metadata_id)
    assert record['outcome']!='failed retrieval'
    add(identifier, claim, 'Verified documentation', 'provider/task5-contracts/'+record['artifact'],
        record['retained_at_utc'], record['access_time_semantics'], version, 'Documented primitive/schema only',
        limitation+' '+record['limitation'], group, record['source_url'],
        relative(BASE/'provider/task5-contracts/retrieval-metadata.json'), {'section_ordinal':record['section_ordinal'], 'section_sha256':record['section_sha256']})

for identifier, claim, record, group in [
 ('JOBS-CREATE','Jobs 2026-07-01 PUT create/update documents 200 Job update and 201 Job create with Azure-AsyncOperation/Retry-After.','jobs-current.web-extract-1','jobs'),
 ('JOBS-START','Jobs 2026-07-01 POST start documents optional execution-template overrides, 200 JobExecutionBase id/name and 202 Location/Retry-After.','core-current.web-extract-1','jobs'),
 ('JOBS-GET','Jobs 2026-07-01 exact execution GET documents a JobExecution resource with status and start/end/template fields.','core-current.web-extract-2','jobs'),
 ('JOBS-LIST','Jobs 2026-07-01 execution list documents value collection, nextLink and optional filter; no documented latest-list causal identity guarantee.','core-current.web-extract-3','jobs'),
 ('JOBS-STATES','Exact execution GET enumerates Running, Processing, Stopped, Degraded, Failed, Unknown and Succeeded; meaning descriptions repeat labels.','core-current.web-extract-2','states'),
 ('ADF-ASYNC','ADF Web turnOffAsync controls 202 Location GET follow-up; default async follow-up can wait up to seven days.','fields.web-extract-1','async'),
 ('ADF-OUTPUT','ADF Web requires JSON object output limited to 4 MB; request timeout defaults to one minute and permits at most ten minutes.','fields.web-extract-2','async'),
 ('ARM-ASYNC','ARM async guidance prioritizes Azure-AsyncOperation over Location, provides Retry-After guidance and warns polling permission may require resource-group-or-broader scope.','sdk-and-async.web-extract-4','async'),
 ('SDK-BLOB','Tagged azure-storage-blob 12.31.0 serialize source lists supported 2026-04-06.','sdk-and-async.web-extract-3','storage'),
 ('SDK-BLOB-DEFAULT','Tagged azure-storage-blob 12.31.0 constants selects the last supported version by default; explicit api_version avoids the mutable default.','sdk-and-async.web-extract-1','storage'),
 ('SDK-TABLE','Tagged azure-data-tables 12.7.0 base client supports explicit 2020-12-06 and documents default 2019-02-02.','sdk-2.web-extract-2','storage'),
 ('STORAGE-VERSION','Storage versioning documentation distinguishes fully deployed 2026-04-06 from newer enabled versions.','sdk-2.web-extract-3','storage'),
 ('JOBS-TEMP','Selected Jobs schema exposes ephemeralStorage and EmptyDir/template volumes; this does not establish an 8 GiB selected Jobs allocation.','jobs-storage-schema.web-extract-1','space'),
 ('EASTERN','ADF guidance identifies Eastern Standard Time as DST-observing and requires non-UTC local start/end timestamps without Z.','fields.web-extract-3','schedule'),
 ('CLI-RELEASE','Official CLI release notes publish Azure CLI 2.90.0; release existence does not prove local execution or latest-version status.','fields.web-extract-5','tools'),
 ('BICEP-RELEASE','Official Azure Bicep release tag v0.38.33 exists; no local installation/build is established.','fields.web-extract-6','tools'),
 ('LOG-ENV','Container Apps documentation provides azure-monitor environment log routing and console/system diagnostic categories.','log-routes.web-extract-1','telemetry'),
 ('LOG-CONSOLE','ContainerAppConsoleLogs table reference documents job attribution fields including JobName.','log-tables.web-extract-1','telemetry'),
 ('LOG-SYSTEM','ContainerAppSystemLogs table reference documents job attribution fields including JobName.','log-tables.web-extract-2','telemetry'),
 ('LOG-ADF','ADF ActivityRuns/PipelineRuns/TriggerRuns diagnostic categories map to dedicated operational tables.','log-tables.web-extract-3','telemetry'),
 ('LOG-RETENTION','Analytics table retention range 4–730 days and total retention range 4–4383 days permit 90/90; table overrides require separate readback from workspace defaults.','log-retention.web-extract-1','telemetry'),
 ('MAINTENANCE','Microsoft Jobs guidance recommends at least one native retry for long-running replicas interrupted by maintenance.','jobs-storage-overview.web-extract-1','retry'),
]:
    doc('E-FF-DOC-'+identifier, claim, record, 'Version/tag in source URL; otherwise retained rolling page', group)

# Each resource schema is independent of the selected value or observed response.
resources = [
 ('ENV','contract-fields.web-extract-8','Microsoft.App/managedEnvironments 2026-07-01','Environment schema exposes workload profiles and appLogsConfiguration.'),
 ('FACTORY','resources-1.web-extract-1','Microsoft.DataFactory/factories 2018-06-01','Factory schema exposes SystemAssigned identity and publicNetworkAccess.'),
 ('PIPELINE','contract-fields.web-extract-1','Microsoft.DataFactory/factories/pipelines 2018-06-01','Pipeline schema exposes activities/parameters and activity policy fields.'),
 ('TRIGGER','contract-fields.web-extract-2','Microsoft.DataFactory/factories/triggers 2018-06-01','ScheduleTrigger schema exposes recurrence frequency/interval/timeZone/startTime/endTime and plural hours/minutes/weekDays.'),
 ('ACCOUNT','resources-1.web-extract-5','Microsoft.Storage/storageAccounts 2025-06-01','Storage account schema exposes kind/sku/isHnsEnabled/accessTier/allowBlobPublicAccess/publicNetworkAccess.'),
 ('CONTAINER','resources-1.web-extract-6','Microsoft.Storage/storageAccounts/blobServices/containers 2025-06-01','Blob container schema exposes publicAccess.'),
 ('TABLE','resources-1.web-extract-7','Microsoft.Storage/storageAccounts/tableServices/tables 2025-06-01','ARM table resource schema is distinct from application entity fields and ETag CAS.'),
 ('UAMI','resources-2.web-extract-1','Microsoft.ManagedIdentity/userAssignedIdentities 2024-11-30','User-assigned identity resource schema supports separate identity resources; actual IDs require readback.'),
 ('ASSIGNMENT','resources-2.web-extract-2','Microsoft.Authorization/roleAssignments 2022-04-01','Role assignment schema exposes principalId/principalType/roleDefinitionId/condition/version.'),
 ('DEFINITION','bootstrap-fields.web-extract-4','Microsoft.Authorization/roleDefinitions 2022-04-01','Custom role schema exposes assignableScopes and Actions/DataActions/NotActions/NotDataActions.'),
 ('REGISTRY','bootstrap-fields.web-extract-3','Microsoft.ContainerRegistry/registries 2025-11-01','Registry schema exposes SKU/publicNetworkAccess/adminUserEnabled/anonymousPullEnabled/roleAssignmentMode.'),
 ('WORKSPACE','contract-fields.web-extract-4','Microsoft.OperationalInsights/workspaces 2025-07-01','Workspace schema exposes SKU and retentionInDays.'),
 ('LOGTABLE','contract-fields.web-extract-5','Microsoft.OperationalInsights/workspaces/tables 2025-07-01','Log table schema exposes plan/retentionInDays/totalRetentionInDays.'),
 ('DIAGNOSTIC','contract-fields.web-extract-6','Microsoft.Insights/diagnosticSettings 2021-05-01-preview','Diagnostic settings schema exposes workspaceId/category logs/logAnalyticsDestinationType.'),
 ('ACTION','resources-2.web-extract-7','Microsoft.Insights/actionGroups 2023-01-01','Action group schema exposes enabled/groupShortName/emailReceivers/useCommonAlertSchema.'),
 ('ALERT','contract-fields.web-extract-7','Microsoft.Insights/scheduledQueryRules 2023-12-01','Scheduled query rule schema exposes LogAlert scopes/criteria/severity/evaluationFrequency/windowSize/actions.'),
]
for identifier, record, version, claim in resources:
    doc('E-FF-DOC-SCHEMA-'+identifier, claim, record, version, 'resources')

# Selected-version auxiliary responses are separate PUT and GET claims, sourced directly.
aux_text = (BASE/'provider/task5-fix1/auxiliary-response-contracts.md').read_text()
aux_lines = [line for line in aux_text.splitlines() if line.startswith('| ') and '[PUT]' in line or line.startswith('| ActionGroup') or line.startswith('| ScheduledQueryRule')]
assert len(aux_lines)==16, len(aux_lines)
for number,line in enumerate(aux_lines,1):
    cols = [p.strip() for p in line.strip('|').split('|')]
    label = cols[0].split(';')[0]
    urls = re.findall(r'\]\((https://[^)]+)\)', line)
    for method, text, url in [('PUT',cols[1],urls[0]),('GET',cols[2].split(' [PUT]')[0].split(' [Publisher')[0],urls[1] if len(urls)>1 else urls[0])]:
        # Strip citations from the response wording while preserving models/statuses.
        text = re.sub(r'\[[^]]*\]\([^)]*\)', '',text).rstrip(' ,')
        candidates = [r for r in FIX if url in r['source_urls']]
        if len(urls)==1:
            candidates = [r for r in candidates if 'monitor-raw' in r['artifact']]
        record = next(r for r in candidates if not any(s in r['artifact'] for s in ('failed','search')))
        add(f'E-FF-DOC-AUX-{number:02}-{method}',f'{label} documented {method} response: {text}',
            'Verified documentation', record['artifact'],record['retained_at_utc'],
            'Retained file time after retrieval batch; exact HTTP access timestamp unavailable.',label,
            'Documented response/model only','Tool-selected bounded excerpts; optional fields can be absent; actual PUT/GET completion/readback reserved/not_run.',
            'auxiliary',url,relative(BASE/'provider/task5-fix1/retrieval-metadata.json'))

permission_claims = [
 ('JOB','jobs-actions.json','Catalog lists Jobs read/start/execution read/list Actions and location job-operation result/status read Actions.','permissions'),
 ('START-TRUST','jobs-trust.json','Jobs start permits template overrides using attached identities/secrets; start authority requires worker-level trust.','permissions'),
 ('BLOB','blob-roles.json','Storage role documentation lists Blob read/write DataActions; a built-in Blob reader includes authority beyond the selected custom read role.','permissions'),
 ('TABLE','table-roles.json','Storage role documentation lists entity read/add/update DataActions; grants do not validate application row content.','permissions'),
 ('TABLE-SCOPE','table-scope.json','Table role assignment can be scoped to a table; it does not restrict individual rows/partitions.','permissions'),
 ('STORAGE-AUTH','storage-operation-mapping.json','Storage Entra authorization maps Blob and entity operations to Actions/DataActions.','permissions'),
 ('LEASE','lease.json','Blob lease permits 15–60 second finite or infinite duration and requires lease ID for guarded writes/deletes; it does not fence SEC traffic or Table writes.','storage'),
 ('CAS','table-cas.json','Table Update Entity with exact If-Match ETag returns 204 on success and 412 on mismatch; wildcard bypasses concurrency and omitted If-Match may upsert.','storage'),
 ('ACR-PULL','acr-roles.json','AcrPull grants registry-wide pull/read Action in classic RBAC registry mode.','permissions'),
 ('ACR-MODE','acr-modes.json','ACR classic registry permissions and repository ABAC modes have different built-in roles/scopes.','permissions'),
 ('ACR-AUDIENCE','acr-audiences.json','ACR supports configuration controlling acceptance of ARM authentication tokens.','network'),
 ('ACR-MI','image-pull-arm.json','Container Apps managed identity pull requires ARM token authentication enabled for ACR.','network'),
 ('CONTRIBUTOR','deployment-authority.json','Contributor has broad management Actions minus NotActions and empty DataActions; management powers cannot be represented as data isolation.','permissions'),
 ('RBAC','rbac-admin.json','RBAC Administrator covers role-assignment management but does not grant custom role-definition creation.','permissions'),
 ('UAMI','identity-assignment.json','Attaching a UAMI requires identity assignment authority in addition to target-resource write authority.','permissions'),
 ('DELEGATION','rbac-delegation.json','Role-assignment delegation conditions can restrict allowed role/principal assignments; effective grants require later proof.','permissions'),
]
for identifier, name, claim, group in permission_claims:
    path=BASE/'provider/task5-permissions'/name
    source=json.loads(path.read_text())
    add('E-FF-DOC-PERM-'+identifier,claim,'Verified documentation',relative(path),source['retrieved_at_utc'],
        'Original collection-batch time anchor, not exact individual HTTP request time.',source['source_version'],
        'Curated official documentation extract; no effective grant observed',source.get('limitations','Effective operations reserved/not_run.'),group,
        source['source_url'],relative(BASE/'provider/task5-permissions/sources-manifest.json'))
for name in ('supplement-compute.json','supplement-analytics.json','supplement-storage.json','supplement-identity.json','supplement-containers.json','supplement-monitor.json','supplement-governance.json'):
    path=BASE/'provider/task5-permissions'/name
    source=json.loads(path.read_text())
    # One row per independently listed permission Action, not one combined bootstrap assertion.
    actions=sorted(set(re.findall(r'[A-Za-z][A-Za-z.]+/[A-Za-z0-9*/.]+',source['extract'])))
    for n,action in enumerate(actions,1):
        add(f'E-FF-DOC-CATALOG-{name.split("-")[1].split(".")[0].upper()}-{n:02}',
            'Official permission catalog includes Action '+action,'Verified documentation',relative(path),source['retrieved_at_utc'],
            'Original collection-batch anchor, not exact per-request HTTP timestamp.',source['source_version'],
            'Documented Action string only','Not a complete executable deployment role, effective assignment or resource-specific authorization proof.',
            'bootstrap',source['source_url'],relative(BASE/'provider/task5-permissions/supplement-sources-manifest.json'))

storage_sources=json.loads((BASE/'provider/task5-storage/sources-v1.json').read_text())
for name in ('hns-known-issues','put-block-list','storage-account-create','storage-overview','table-zrs','storage-redundancy','networking'):
    source=next(r for r in storage_sources['sources'] if r['id']==name)
    claim=source['claim']
    if name=='storage-overview':
        claim='Storage account overview lists Blob and Table services/endpoints and a GPv2 analytics workload table; it does not explicitly prove HNS plus Table coexistence.'
    add('E-FF-DOC-STORAGE-'+name.upper(),claim,'Verified documentation','provider/task5-storage/sources-v1.json',
        storage_sources['checkpoint_utc'],'Historical checkpoint upper bound; exact web retrieval time unavailable; not a new retrieval date.',
        'Retained rolling documentation/search-result body','Bounded documented primitive only',
        'Retained curated search excerpts, not original full page or HTTP response; regional capability/coexistence and effective reachability reserved.',
        'network' if name=='networking' else 'storage',source['url'],relative(BASE/'provider/task5-storage/sources-v1.json'))

# Application handling is recorded as a design observation, separate from provider facts.
for identifier,claim,group in [
 ('CORRELATION','Current design requires causal exact execution/run/command/attempt/workset/hash/image-digest tuple and matching durable result; acceptance/async success alone cannot pass.','states'),
 ('UNKNOWN','Current design classifies lost start, missing correlation, unavailable GET, new enum or observation deadline as execution_unknown/operator recovery with no blind launch/replay.','states'),
 ('START-POLICY','Current design selects ADF turnOffAsync=true and activity retry=0; initial response exposure remains reserved.','async'),
 ('STORAGE-POLICY','Current design uses Blob-created-only immutable artifact lifecycle, actual ETag Table CAS and no cross-service transaction; no DFS dependency is selected.','storage'),
 ('NETWORK-POLICY','Current design requires public HTTPS ARM/Blob/Table/ACR/Entra/telemetry/SEC paths and approved ARM polling hosts/audiences; MI does not establish network reachability.','network'),
 ('TELEMETRY-POLICY','Current design selects azure-monitor/Dedicated operational logs, five Analytics tables with 90/90 days and email log alerts for failed/unknown/missing success; actual route/delivery reserved.','telemetry'),
 ('RETRY-POLICY','Current design retains zero native retries and max one confirmed-transient replay, exposing maintenance interruption risk and preserving durable worksets.','retry'),
]:
    add('E-FF-POLICY-'+identifier,claim,'Source/probe observation','azure-contracts.md',NOW,
        'Current correction-time local design read, not source retrieval or additional owner acceptance.',
        'Current application design under unchanged parent/R3 selections','Recorded design only',
        'Effective implementation, fault handling and integrated passing artifacts remain reserved/not_run.',group)

assumptions=[
 ('LISTING-SCALE','KB/MB/GB labels use binary 1024 scaling for planning, with rounding unverified.','Totals may over/underestimate received volume; 214702080 bytes is a planning estimate.','In a separately authorized acquisition, compare exact received sizes with retained listing labels; use measured bytes for worker sizing.','specimens/volume-assessment.json','space'),
 ('OUTPUT-SCRATCH','Observation/output scratch is one sample maximum expanded-source size, 28748322 bytes.','Actual parser/ETL/output buffers may exceed this allowance and disk/memory fit is unproved.','Worker tester must measure representative full-worker peak scratch/output before S7-18 acceptance.','specimens/volume-assessment.json','space'),
 ('GENERATION-SCRATCH','Candidate-generation scratch is twice the sample maximum expansion, 57496644 bytes.','Partition rewrite/merge and concurrent generations may need greater space.','Worker/publisher tester must measure complete generation lifecycle, concurrency and reclamation at S7-18.','specimens/volume-assessment.json','space'),
 ('RESERVE','Installer/runtime/log reserve is 1GiB (1073741824 bytes).','Install/cache/runtime/log use is unmeasured and may exhaust assumed available space.','Worker tester must measure peak reserve terms and logs/cache cleanup within actual selected allocation at S7-18.','specimens/volume-assessment.json','space'),
 ('ONE-SOURCE','One-source temporary model assumes sequential processing and prompt scratch release; 1192636112 bytes is modeled, not peak process measurement.','Worker concurrency or failed cleanup may exceed model; no capacity or freshness guarantee follows.','Worker tester must prove scheduling/cleanup and measured disk/memory/runtime peaks at S7-18.','specimens/volume-assessment.json','space'),
 ('TAIL','Retained sample expansion 6.26–7.95 and largest retained body do not bound all historical/current-quarter tails.','Unfetched larger/changed sources may alter decode/parse/storage/runtime requirements.','Worker/integration tester must measure representative larger inputs with separately authorized evidence before coverage/fit claims at S7-18/20.','specimens/volume-assessment.json','space'),
 ('JOBS-8GIB','General app guide above-1-vCPU 8GiB quota applies numerically to selected Jobs only as a candidate assumption.','No documented exact selected Jobs allocation/readback exists; usable capacity/fit cannot be claimed.','Deployment and worker testers must record exact selected Jobs allocation/usable space and full-worker peaks at S7-01/18.','azure-contracts.md','space'),
 ('HNS-TABLE','HNS-enabled GPv2 Hot/ZRS and Table coexistence is inferred from combined documentation tables, not an explicit deployed proof.','Selected Blob/Table lifecycle could require a binding/configuration revision if coexistence is unsupported.','Storage tester must verify actual account properties, exact Table HTTPS endpoint and Blob/Table operations at S7-14 before integrated acceptance.','azure-contracts.md','storage'),
 ('ADF-202','Selected ADF initial 202/header/output handling can expose sufficient causal start data only as an unproved integration assumption.','Missing causal reference blocks automatic continuation and requires operator recovery; no latest-list fallback.','Orchestration tester must retain actual 200/202/header/output and exact async-to-execution correlation at S7-06/07/10.','azure-contracts.md','async'),
 ('LOG-ATTRIBUTION','Selected environment/ADF telemetry fields and categories suffice for execution attribution and operational alert queries only as an unproved integrated assumption.','Ingestion delay, missing attribution or unsupported categories may prevent failed/unknown/missing-success alerting.','Observability tester and Lowell must retain actual category/table/job correlation, retention readback and email receipt at S7-17.','azure-contracts.md','telemetry'),
]
for identifier,claim,impact,resolution,artifact,group in assumptions:
    add('E-FF-ASSUME-'+identifier,claim,'Assumption',artifact,NOW,
        'Correction-time classification of an existing unverified proposition; no new measurement/owner decision.',
        'Bounded sample/current design; selected candidate only','Unverified; no effective PASS',
        'Impact: '+impact+' Responsible owner: Lowell Mason; designated tester as stated in resolution. Resolution obligation: '+resolution,
        group,extra={'impact':impact,'responsible_owner':'Lowell Mason','resolution_obligation':resolution})

# Owner selections are tied to the exact accepted proposal and original recording times.
owner_groups=[
 ('BINDING','D-01–D-04 accepted R3 cloud/tenant/subscription/RG/dev names/operator and distinct worker/pull/ADF identities.','owner-decision-response-r3-part1.json','binding'),
 ('ACR','D-05–D-07 accepted R3 dedicated Basic classic-RBAC registry, distinct pull UAMI/AcrPull and indefinite deployed-digest retention.','owner-decision-response-r3-pending.json','registry'),
 ('TOOLS','D-08 accepted R3 CLI2.90.0/Bicep0.38.33 prerequisite and future ACR quick-task Linux amd64 method.','owner-decision-response-r3-pending.json','tools'),
 ('OBSERVER','D-18 accepted R3 observer 30s base, longer server delay honored and absolute 4200s deadline; expiry is unknown, not termination.','owner-decision-response-r3-pending.json','async'),
]
for identifier,claim,name,group in owner_groups:
    receipt=json.loads((BASE/name).read_text())
    time=receipt.get('root_recorded_at_utc') or receipt.get('recorded_at_utc') or receipt.get('received_at_utc')
    if not time:
        # Existing index already records the exact receipt anchor without inventing owner time.
        existing=list(csv.DictReader((BASE/'index.csv').open()))
        time=next(r['accessed_or_received_at_utc'] for r in existing if r['evidence_id']==('E-T5-OWNER-PART1' if 'part1' in name else 'E-T5-OWNER-PENDING'))
    add('E-FF-OWNER-'+identifier,claim,'Owner decision',name,time,
        'Original root receipt/recording time; owner-authored timestamp unknown.',
        'Owner Lowell Mason; exact accepted R3 proposal SHA256 '+receipt['accepted_proposal_sha256'],
        'Accepted documentation selection only','No final finding acceptance, effective authorization, provisioning or later-stage action authority.',group,receipt=relative(BASE/name))

stage7=(BASE/'stage-7-checks.md').read_text().replace('Accepted-if-owner-confirms AzureCloud/tenant/subscription/RG',
    'Accepted R3 D-01–D-04 binding (E-FF-OWNER-BINDING; owner-decision-response-r3-part1.json): AzureCloud/tenant/subscription/RG')
assert 'Accepted-if-owner-confirms' not in stage7
(BASE/'stage-7-checks.md').write_text(stage7)
for line in stage7.splitlines():
    if not line.startswith('| S7-'):continue
    cols=[p.strip() for p in line.strip('|').split('|')]
    identifier=cols[0].split(' / ')[0]
    add('E-FF-'+identifier,'Reserved obligation '+cols[0]+': '+cols[2],'Reserved Stage 7 check','stage-7-checks.md',NOW,
        'Correction-time register reconciliation; no execution/request was run.',cols[1],
        'reserved/not_run; required passing artifact: '+cols[3],
        'Responsible actor: '+cols[4]+'. Requires later authorized implementation/effective evidence; current docs/selection/native probe cannot pass this duty.',
        'reserved',extra={'stage7_id':identifier,'responsible_actor':cols[4],'required_passing_artifact':cols[3],'status':'reserved/not_run'})

# Current index contains no mutable Stage7 reference; append preserves all old bytes exactly.
before_map=json.loads((TASK/'historical-path-map.json').read_text())
before_index=ROOT/next(r['immutable_path'] for r in before_map['records'] if r['source_path']==relative(BASE/'index.csv'))
assert (BASE/'index.csv').read_bytes()==before_index.read_bytes()
stream=io.StringIO(newline='')
writer=csv.DictWriter(stream,fieldnames=FIELDS,lineterminator='\r\n')
writer.writerows(CLAIMS)
(BASE/'index.csv').write_bytes(before_index.read_bytes()+stream.getvalue().encode())
(TASK/'claims.json').write_text(json.dumps({'created_at_utc':NOW,'semantics':'Appended classifications from existing retained evidence only.','records':CLAIMS},indent=2)+'\n')
(TASK/'claim-provenance.json').write_text(json.dumps({'created_at_utc':NOW,'records':PROVENANCE},indent=2)+'\n')
(TASK/'claim-groups.json').write_text(json.dumps(GROUPS,indent=2)+'\n')
print(json.dumps({'appended':len(CLAIMS),'categories':dict(__import__('collections').Counter(r['category'] for r in CLAIMS)),'groups':{k:len(v) for k,v in GROUPS.items()}},indent=2))
