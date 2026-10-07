## Global Constraints

The following are copied verbatim from Stage 3 spec §3; every task inherits them:

- The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.
- ETL reads those bytes from ADLS and makes no SEC requests.
- ETL never silently follows a mutable “latest”.
- Original bytes are retained.
- Downloaded, transformed and published are different states.
- Refuse malformed rows rather than silently dropping them; quarantine the source and report the line and reason.
- An unrecognized legacy format does not by itself invalidate a usable index row.
- Never deduplicate on company name and filing date alone.
- An identical input fingerprint and unchanged versions are a no-op.
- A forced replay may rebuild output, but cannot create a second logical filing.
- A gated candidate is `awaiting_approval`, not current.
- A conflict requires rereading the active generation and rebuilding; never overwrite a newer pointer with stale work.
- The pointer update is the publication boundary.
- There is no assumed transaction spanning Blob Storage and Table Storage.
- Per-source published flags are recoverable indexes, not a second commit authority.
- Atomicity is **per quarter**, not across the entire historical dataset.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.

Exact values: Python >=3.14; PyArrow 25.0.1; Requests 2.34.2; Identity 1.26.0; Blob 12.31.0/API 2026-04-06; Tables 12.7.0/API 2020-12-06; canonical schema `sec-index-v1`; received-byte guard 67,108,864; expanded-byte guard 536,870,912; exchange deadline 90 seconds; batches 8,192 rows; CAS_ATTEMPTS 5. Retain accepted settings and pins, one ingest package and indefinite development evidence retention. Stage 7 measures actual Linux amd64/Python 3.14.8 worker memory, runtime and scratch; native proofs establish no deployed capacity.

Live SEC, Azure, authentication, compute, provisioning and deployment authorizations remain closed. Use cached libraries and retained evidence only. No auto-fetch fallback, optional codec selection, approval bypass, image build, workflow/schedule activation or later-stage routing belongs to this plan.

---

### Task 6: Offline transform/publish commands and durable ETL results

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py`, `packages/sec-edgar-ingest/tests/test_etl_cli.py`. Modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`, `results.py`, `state.py` under the same source prefix, `packages/sec-edgar-ingest/tests/test_workspace.py` and `tests/test_cli.py` only for command/result regression expectations.

**Interfaces:** Consumes transform_workset/publish_quarter and existing Settings/RunContext/Attempt identity. Produces run_transform/run_publish/write_etl_result/read_etl_result. Existing CommandResult/old result bytes stay valid and unchanged; EtlResult has explicit sec-etl-result-v1 format, not silently added defaults on acquisition result codec. Allow result_path for four shared commands; read_result remains acquisition decoder, read_etl_result is separate strict decoder. AcquisitionState.finish_attempt accepts `CommandResult | EtlResult` by shared context/to_mapping/gaps/ended_at contract, preserving existing type/identity validation.

- [ ] **Step 1: Write command-boundary tests, capture red.** Add unittest assertions that help advertises transform/publish, transform accepts a retained snapshot workset without fixture-pack and publish accepts a complete transformed workset; require config/run/execution/attempt/deadline/workset. The no-acquisition assertion uses:

```python
from unittest.mock import patch

with patch('sec_edgar_ingest.cli.Coordinator', side_effect=AssertionError('ETL constructed SEC coordinator')), \
     patch('sec_edgar_ingest.cli.BoundedSender', side_effect=AssertionError('ETL constructed SEC sender')), \
     patch('sec_edgar_ingest.cli.RequestClient', side_effect=AssertionError('ETL constructed SEC request client')):
    code = main(argv)
self.assertEqual(code, 0)
```

Build argv from a real seeded snapshot_ref/config with synthetic provenance and future explicit deadline; use actual command invocation, not a fake EtlResult. Add missing/unsupported parser/schema/config/ref path failures before open_stores. Run test_etl_cli.py guarded; expect argparse missing-command failure.

- [ ] **Step 2: Implement the separate ETL CLI path and exact correlation.** Extend parser with transform/publish, shared correlation/config/deadline flags, `--workset`, fixture-only `--state-dir/--today`, and transform-only `--force`. ETL commands refuse `--fixture-pack`, since all input is stored. Validate parser/versions, IDs, relative immutable workset path shape, pin date and deadline before constructing adapters. Snapshot refs match `worksets/sec/snapshot/sha256=<64hex>/workset.json`; publish refs match transformed equivalent. Validate inside commands that path ID equals decoded payload ID and full canonical bytes.

Branch before acquisition transport creation; open selected stores, create EtlState/AcquisitionState, begin exact Attempt, persist create-only command.json intent, and invoke run_transform/run_publish. No Coordinator/Sender/RequestClient/fixture-pack/SEC HTTP construction in that branch. Azure runtime identity is for storage only; offline tests mock clients and forbid credentials. New command flags do not change Settings serialization or immutable origin config hash.

Current CLI _existing_context replays acquisition results; implement analogous ETL flow using read_etl_result. Preserve saved start/pinned date for exact same completed attempt, compare frozen config/image/parser/schema/deadline/input/force and reject mismatched reuse. A new attempt may have current versions/date and old snapshot acquisition origin. Expired completed result replay may repair Attempt from its frozen context; a new expired attempt refuses without work. A crash with a begun Attempt/intent but no result resumes frozen context rather than fabricating a new start.

- [ ] **Step 3: Implement aggregate results, outcome exits and result-first repair.** run_transform returns complete/partial processing counts/ref/gaps and run_publish iterates the union of incoming quarter_counts and prior affected source-quarter receipts so a changed filing date updates old/new quarter outcomes explicitly. Reject partial TransformedWorkset before any pointer changes. Each quarter may advance independently; continue unaffected quarters on a gated/failing quarter and report every outcome. Do not claim a multi-quarter source fully published until its complete per-quarter receipts exist.

Use exits: success/unchanged/no_new_sources 0; configuration 2; incomplete 3; quarantined/invalid_source 7; state_conflict/internal_error/publication_conflict 9; awaiting_approval 10. Preserve existing acquisition exit meanings. Any gate makes aggregate awaiting_approval unless a harder invalid/conflict/incomplete failure exists; include all gates in quarters/counters regardless of aggregate priority. A complete empty workset returns unchanged with zero quarter advances. Files produced are not publication success.

EtlResult-first commit core:

```python
def write_etl_result(result, objects, acquisition):
    row = acquisition.store.get('Attempt', attempt_key(result.context))
    if row is None or row.value['context'] != result.context.to_mapping():
        raise Conflict('ETL result requires exact begun Attempt')
    saved = row.value['result']
    if saved is not None and saved != result.to_mapping():
        raise Conflict('ETL result differs from completed Attempt')
    path = result_path(result.context)
    objects.put_once(path, result.to_json())
    acquisition.finish_attempt(result)
    return path
```

read_etl_result checks format/path/correlation/canonical bytes/outcome and counters. Add `etl_result.after_object` and `etl_result.after_attempt` observer points. A result-write crash after quarter commit yields recoverable pointer/manifest state; a replay repairs per-quarter flags and writes exact matching result rather than failing falsely or re-advancing pointer. Structured logs include run/execution/attempt, source/ref/raw hash and quarter/generation/candidate for each real transition.

- [ ] **Step 4: Cover CLI regression/replay matrix and green.** Guarded test_etl_cli.py, test_workspace.py and test_cli.py: transform/publish end-to-end, fixture no sender/provider construction, parser-version replay, same completed attempt/no extra writes, changed flags/workset/version/image/config rejection, expired new/completed attempts, crash result object before Attempt update, gated exit10 with active capture stable, persistent conflict9, partial source success/incomplete3, invalid source7, multi-quarter progress, no-op0 and empty0. Retain actual stdout/stderr/result.json/Attempt bytes and commands. Old discover/collect result JSON must decode identically and existing fixture-pack/coordination checks remain effective.

- [ ] **Step 5: Commit owned files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/src/sec_edgar_ingest/results.py packages/sec-edgar-ingest/src/sec_edgar_ingest/state.py packages/sec-edgar-ingest/tests/test_etl_cli.py packages/sec-edgar-ingest/tests/test_workspace.py packages/sec-edgar-ingest/tests/test_cli.py
git commit -m 'feat: expose raw-only transform and safe publication commands'
```
