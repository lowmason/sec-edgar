# Eastern schedule contract

Accepted parent §4.8 defaults remain daily 05:00 Eastern and Sunday 06:00 Eastern reconciliation of all supported quarters. Selected ADF resource API: Microsoft.DataFactory/factories/triggers `2018-06-01`, ScheduleTrigger. This task creates no trigger definition and activates none; production triggers must remain stopped in later deployment until readiness/activation authority is separately granted.

| Schedule | Exact recurrence expectation |
|---|---|
| Daily | frequency `Day`, interval `1`, timeZone `Eastern Standard Time`, schedule hours `[5]`, minutes `[0]` |
| Reconciliation | frequency `Week`, interval `1`, timeZone `Eastern Standard Time`, schedule weekDays `["Sunday"]`, hours `[6]`, minutes `[0]` |

For this Windows zone, serialize local `startTime` and optional `endTime` as `yyyy-MM-ddTHH:mm:ss` **without Z**; concrete initial start date/end date are deployment-time inputs, not guessed here. A Z suffix denotes UTC and renders the timeZone ineffective. Monitoring/query request timestamps use UTC. Always set explicit hours/minutes/weekDays rather than inheriting from the start date. The template reference gives the exact plural field names; overview examples using singular hour/minute do not override them. Microsoft lists `Eastern Standard Time` as DST-observing even though its name says Standard. [ADF schedule guidance](https://learn.microsoft.com/en-us/azure/data-factory/how-to-create-schedule-trigger), [selected trigger schema](https://learn.microsoft.com/en-us/azure/templates/microsoft.datafactory/2018-06-01/factories/triggers). Retained claim passages: `provider/task5-contracts/fields.web-extract.txt` and `async-schema.web-extract.txt`.

## Local conversion observation

Command: `python3 specs/evidence/sec-filing-index-ingestion/stage-1/provider/task5-contracts/offline_checks.py`. Python 3.14.7 on the local host, `zoneinfo.ZoneInfo('America/New_York')`, system zone data `2026c-rearguard`; zone file SHA-256 `e9ed07d7bee0c76a9d442d091ef1f01668fee7c4f26014c0a868b19fe6c18a95`. Full path/version/result receipts are retained in `provider/task5-contracts/dst-observation.json` and `offline-verification.json`. This is a local conversion observation, not the Python 3.14.8 Linux runtime proof from Task 4 and not proof ADF's Windows-zone trigger executes correctly.

| Local date / offset at scheduled hour | Daily 05:00 UTC | 06:00 UTC offset expectation | Sunday reconciliation due? |
|---|---|---|---|
| 2026-03-01 / -05:00 | 10:00 | 11:00 | Yes, Sunday before spring transition |
| 2026-03-07 / -05:00 | 10:00 | 11:00 | No, Saturday offset check |
| 2026-03-08 / -04:00 | 09:00 | 10:00 | Yes, spring transition Sunday |
| 2026-03-15 / -04:00 | 09:00 | 10:00 | Yes, Sunday after spring transition |
| 2026-10-25 / -04:00 | 09:00 | 10:00 | Yes, Sunday before fall transition |
| 2026-10-31 / -04:00 | 09:00 | 10:00 | No, Saturday offset check |
| 2026-11-01 / -05:00 | 10:00 | 11:00 | Yes, fall transition Sunday |
| 2026-11-08 / -05:00 | 10:00 | 11:00 | Yes, Sunday after fall transition |

All 16 UTC-hour assertions passed on the initial corrected verification run. Evaluation year is 2026, matching the requested transition year; no additional evaluation-year transitions are needed. Scheduled local hours are outside repeated/skipped early-morning DST hours, but this alone does not prove once-only ADF dispatch. Stage 7 must retain actual trigger definitions/state, time zone serialization, query UTC run timestamps, daily/reconciliation associations and before/after DST evidence. A missing/delayed run requires alert/recovery evidence; docs and zoneinfo do not discharge those obligations.

The local evidence helper's first integrity run failed because it treated mixed `URL; artifact` index references as a single local path. This was an offline verification-helper issue, not source hash corruption. It was isolated to reference parsing, corrected to use the retained artifact component, then all 180 pre-Task-5 hashes passed. Final verification is retained separately after adding Task 5 index entries.
