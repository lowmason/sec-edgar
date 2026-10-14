# Azure deployment and orchestration

Stage 6 defines the Azure deployment; nothing here has run against Azure. Every command below is for Stage 7 or later, under that stage's own authorization. All 22 Stage 7 integrated checks remain reserved/not_run, and Stage 7 verifies each command before relying on it.

The definitions live in `infra/azure/sec-edgar-ingest/`:

- `main.bicep` and `modules/` define everything.
- `main.json` is the committed compile, built with Bicep 0.38.33. Deploy that file.
- `roles.json` is the role matrix.
- `pipelines/*.json` are the ADF pipelines, rendered by `pipelines/render.py`.
- `alerts/*.kql` are the alert queries.
- `config/` holds the Azure config template.

## What a deployment creates

| Resource | Name | Notes |
|---|---|---|
| Resource group | `rg-sec-edgar-dev-eastus` | |
| Custom roles | `SecEdgar Job Controller`, `SecEdgar Job Async Observer`, `SecEdgar Blob Reader`, `SecEdgar Blob Writer`, `SecEdgar Entity Reader`, `SecEdgar Entity Writer` | Subscription-assignable; the grants are in `roles.json` |
| Identities | `id-sec-edgar-dev-worker`, `id-sec-edgar-dev-pull` | The worker reaches storage; the pull identity reaches only the registry |
| Registry | `secedgardevb8617` | Basic; admin user, anonymous pull and keys off |
| Storage | `secedgardevb8617` | HNS, ZRS, Entra only; 8 containers, 4 tables |
| Workspace and action group | `law-sec-edgar-dev`, `ag-sec-edgar-dev` | 90-day retention; email to the operator |
| Container Apps | `cae-sec-edgar-dev-eastus`, `job-sec-edgar-dev` | Manual job, no schedule, no volumes |
| Data Factory | `adf-sec-edgar-dev` | Four pipelines and two triggers; the triggers deploy stopped |
| Alerts | `alert-sec-edgar-*` | Ten; the two staleness alerts deploy disabled |

## Deploy (Stage 7)

1. Render the config for the release digest that S7-05 published:

   ```bash
   uv run --offline --frozen --package sec-edgar-ingest python -m sec_edgar_ingest.deployment --template infra/azure/sec-edgar-ingest/config/sec-edgar-ingest.azure.template.json --image-digest sha256:<release digest> --provenance <S7-05 build reference> --out-dir /tmp/sec-edgar-release
   ```

2. Rebuild the template and check it matches the committed compile:

   ```bash
   ~/.azure/bin/bicep build infra/azure/sec-edgar-ingest/main.bicep --outfile /tmp/sec-edgar-release/main.json
   cmp /tmp/sec-edgar-release/main.json infra/azure/sec-edgar-ingest/main.json
   ```

3. Confirm that no execution is in flight. A config or digest change redeploys the job, and an attempt begun under the old pair fails on replay with `Conflict`. Both checks must list nothing:
   - executions of `job-sec-edgar-dev` in `Running` or `Processing`;
   - `pl-sec-edgar-*` pipeline runs `InProgress`.

4. Validate, run what-if, then deploy at subscription scope. Use the same parameters for all three:

   ```bash
   az deployment sub what-if --location eastus --template-file infra/azure/sec-edgar-ingest/main.json --parameters @/tmp/sec-edgar-release/main.parameters.json operatorPrincipalId=<operator object ID> dailyStartTime=<yyyy-MM-ddTHH:mm:ss> reconcileStartTime=<yyyy-MM-ddTHH:mm:ss>
   ```

   The two start times are Eastern local times without `Z`; the template rejects any other length.

Bootstrap authority (D-04) is a Stage 7 prerequisite, outside the template.

## Triggers and staleness alerts (Stage 8)

Triggers deploy stopped and nothing in the template starts them. Stage 8 starts `tr-sec-edgar-daily` and `tr-sec-edgar-reconcile`. With each trigger it enables the matching staleness alert: `alert-sec-edgar-daily-staleness` and `alert-sec-edgar-reconcile-staleness`. Record each step.

ADF rejects an update to a started trigger. Any redeploy after Stage 8 therefore:

1. stops both triggers;
2. deploys;
3. starts both triggers again.

Record all three steps.

`pl-sec-edgar-backfill` has no trigger. Run it by hand as a bounded campaign.

## Pipeline outcomes

Each `pl-sec-edgar-<command>` pipeline runs `pl-sec-edgar-run-worker`. Every launch is attempt `launch-<n>` of the calling pipeline's run ID. The worker writes `results/runs/sec/<run ID>/<command>/launch-<n>/result.json`. Only `success` ends a pipeline Succeeded. Every other outcome ends in the `Fail run` activity, whose error code is the outcome:

| Error code | Meaning | First response |
|---|---|---|
| `success` | The execution succeeded and its matching result has an exit-0 outcome | None |
| `awaiting_approval` | The run is gated on a withdrawal | Review it with `candidates`; see the reconciliation and approval runbook |
| `execution_unknown` | No execution name could be resolved, the state was unknown, or the 4,200 s observation deadline passed. Nothing was relaunched | Recover by hand (below) |
| `execution_stopped` | The execution was stopped | Find who stopped it; the next run is a new attempt |
| `execution_mismatch` | The execution ran an image other than the pinned digest | Compare the job image with the rendered config |
| `result_missing` | The execution ended with no readable result | Read the execution's console log |
| `result_mismatch` | The result does not match the launch, or an exit-0 outcome came from a `Failed` execution | Compare the result's context with the launch |
| `stale` | An approval or rollback was stale (exit 11) | Re-run `candidates` or `history` |
| `pending` | The second launch was still pending | The next scheduled run continues |
| Any other `EXIT_CODES` name | The worker's own outcome | See the acquisition and publication runbooks |

**Recovering `execution_unknown`.** Read `results/runs/sec/<run ID>/<command>/launch-<n>/result.json` first. If it exists, its `context.execution_id` names the execution. Otherwise, the only valid evidence is a job execution whose arguments carry that exact `--run-id` and `--attempt-id`. Never infer the execution from the newest one or from timing. While such an execution is running, wait. Never start a launch by hand under the same run ID. The next scheduled run uses a new run ID.

## Alerts

All alerts mail `ag-sec-edgar-dev`. Per-run alerts run every 15 minutes over a 30-minute window, so one event can mail twice and an event ingested up to 15 minutes late still mails.

| Alert | Fires on | First response |
|---|---|---|
| `alert-sec-edgar-failed-job` | A run-worker Fail other than `awaiting_approval` and `execution_unknown` | The pipeline outcomes table above |
| `alert-sec-edgar-ambiguous-start` | `execution_unknown` | Recover by hand (above) |
| `alert-sec-edgar-lease-failure` | `ownership_lost` | Check for a second worker; see the acquisition runbook |
| `alert-sec-edgar-access-block` | `access_blocked` | Stop the triggers; review SEC access before resuming |
| `alert-sec-edgar-retry-exhausted` | `member_outcomes.retry_exhausted` above 0 | The next run revisits the member; repeated alerts need review |
| `alert-sec-edgar-quarantine` | Quarantined members or outcome | See the acquisition runbook's quarantine section |
| `alert-sec-edgar-publication-conflict` | `publication_conflict` | See the publication runbook |
| `alert-sec-edgar-pending-approval` | `pending_approvals` above 0, on every run | Review `candidates` |
| `alert-sec-edgar-reconcile-staleness` | The latest summary shows no successful reconciliation in 8 days | Disabled until Stage 8. Check the reconcile trigger and the last reconcile outcome |
| `alert-sec-edgar-daily-staleness` | No daily summary with complete discovery in 30 h | Disabled until Stage 8. Check the daily trigger and the last daily outcome |

## Reported, not alerted

The three figures below are separate from the alerts. A weekend with no new files is `no_new_sources`, not stale ingestion. Read each from the latest daily `workflow_summary`:

```kusto
ContainerAppConsoleLogs
| where JobName == "job-sec-edgar-dev"
| extend entry = parse_json(Log)
| where tostring(entry.event) == "workflow_summary" and tostring(entry.context.command) == "daily"
| summarize arg_max(TimeGenerated, entry)
| project TimeGenerated, discovery_complete = entry.fields.discovery_complete, boundary_after = entry.fields.boundary_after, oldest_unresolved_period = entry.fields.oldest_unresolved_period, last_successful_reconcile_at = entry.fields.last_successful_reconcile_at
```

- Discovery age is the age of `boundary_after`.
- The oldest listed-but-unpublished source is `oldest_unresolved_period`.
- The last successful reconciliation is `last_successful_reconcile_at`.
