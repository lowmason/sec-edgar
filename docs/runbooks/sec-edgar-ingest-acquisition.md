# SEC filing-index acquisition recovery

Use the installed `sec-edgar-ingest` command or the workspace entry point. All
commands use an explicit validated config and a finite aware UTC deadline. Check
help first and run `scripts/check-sec-edgar-ingest.sh` for the offline validation,
wheel/sdist, entry point, compilation, and whitespace checks. Dependencies/build
requirements must already be cached; a missing cache does not authorize registry,
SEC, authentication, Azure, or compute activity.

The checked-in config is strict JSON syntax in a `.yaml` file. It selects local
fixture storage with synthetic provenance. To reproduce the bounded archived
quarter demonstration, prepare an explicitly labelled config:

```sh
python3 - <<'PY'
import json
from pathlib import Path
config = json.loads(Path('conf/sec-edgar-ingest.yaml').read_text())
config['backfill'] = {'start_quarter': '2015Q1', 'end_quarter': '2015Q1'}
config['fixture'] = {'allow_clock_override': True, 'allow_deadline_override': True}
Path('/tmp/sec-edgar-quarter-fixture.json').write_text(json.dumps(config))
PY
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest discover \
  --config /tmp/sec-edgar-quarter-fixture.json \
  --fixture-pack packages/sec-edgar-ingest/tests/fixtures/acquisition/manifest.json \
  --state-dir /tmp/sec-edgar-acquisition-proof --today 2026-10-06 \
  --deadline 2099-01-01T00:00:00Z --mode quarterly \
  --discovery-id fixture-quarter --run-id fixture-run \
  --execution-id fixture-discover --attempt-id discover-1
```

This generates only the synthetic 2015 Q1 subset. The actual root is
`/tmp/sec-edgar-acquisition-proof/.fixture-state` because `--state-dir` is the
fixture base directory and `storage.root` remains the validated relative value.
The resolved actual root is bound in the registry. Preserve that directory and
its original-to-retained path map when copying evidence. The distant deadline
and explicit pin date are fixture-only; they confer no production authorization.

Copy `source_workset_ref` from stdout into the next command:

```sh
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest collect \
  --config /tmp/sec-edgar-quarter-fixture.json \
  --fixture-pack packages/sec-edgar-ingest/tests/fixtures/acquisition/manifest.json \
  --state-dir /tmp/sec-edgar-acquisition-proof --today 2026-10-06 \
  --deadline 2099-01-01T00:00:00Z --workset SOURCE_WORKSET_REF \
  --run-id fixture-run --execution-id fixture-collect --attempt-id collect-1
```

The workset reference must be
`worksets/sec/source/sha256=<source-workset-id>/workset.json`. Source discovery
freezes source identities and gaps. Collection pins exact original body hashes
using write-once Bindings, then writes
`worksets/sec/snapshot/sha256=<snapshot-workset-id>/workset.json` only when every
member and directory is complete. New collection attempts use their current
run/execution/attempt context in the result; the snapshot workset retains its
immutable discovery origin. ETL inputs must name this exact snapshot workset.

For a terminal incomplete result, preserve the same source workset and use a
**new attempt ID** and explicit execution ID. Completed earlier members use their
existing pins, with no new request. A completed attempt ID replays its exact saved
result and original context. Changed config, image, versions, deadline, correlation,
mode, discovery ID, refresh policy, or workset are refused under the same attempt.
An incomplete discovery session can be retried with a new command attempt and
its same discovery ID; successful recovery emits a new immutable source workset
including repaired directories. The earlier gap-bearing workset/result remains.

The committed pack contains daily root/year/QTR3/QTR4 listings, the handoff source,
and a delayed source scripted as 404 then valid IDX. The response cursor is stored
under an explicitly fixture-only record keyed by manifest hash and URL. Changing
a manifest changes that script identity. This cursor is not production acquisition
state or live permission. A daily command needs a valid current-quarter endpoint;
closed `2015Q1` cannot contain October 2026 sources. The approved Step 4 text's
one-config collision remains an owner decision; the retained proposed two-config
sequence is reviewable and must not be represented as a passed gate until approved.

Every result contains counters and structured gaps. The stdout result reference is
`runs/sec/<run-id>/<command>/<attempt-id>/result.json`; stderr logs carry the full
pinned current context. Result bytes are written immutable before Attempt
completion. If a process dies after writing a result, replaying its exact inputs
checks that result, restores its original start/context, and repairs the matching
Attempt. A conflicting or corrupt result is refused. Unexpected command errors
retain an Attempt error and return 9 without inventing a completed result.

| Exit | Outcome | Operator meaning |
| --- | --- | --- |
| 0 | `success`, `no_new_sources` | Acquisition complete; a valid decoded empty listing is distinct from failure. |
| 2 | `configuration` | Invalid args/config/identity/fixture inputs; validation precedes backend construction. |
| 3 | `discovery_failed`, `incomplete` | Explicit directory gaps or multiple partially acquired members remain. |
| 4 | `pending` | A single listed source returned 404; keep it pending and revisit older work. |
| 5 | `retry_exhausted`, `deferred`, `throttled` | Inclusive attempt/deadline/server-delay policy stopped this command. |
| 6 | `access_blocked` | Durable access denial stops all further sends in this run. |
| 7 | `quarantined`, `invalid_source` | Invalid/truncated/guard-violating bytes were refused and evidence retained. |
| 8 | `ownership_lost` | New requests stop; preserve the unsafe in-flight ownership window. |
| 9 | `state_conflict`, `internal_error` | Immutable provenance/state conflict or unexpected failure needs investigation. |

A multi-source partial result retains every member error and pending/error counts;
a run-wide access/ownership/policy stop takes precedence. Downloaded counts new
accepted exchanges; unchanged counts verified pins or recovered originals; pending
counts unverified members. Quarantine counts nonempty failed receipt bodies
confirmed for the current command context, including retry prefixes. Older
quarantine evidence remains retained even when a successor reports zero new
quarantines. An HTTP failure, missing listing, open-quarter absence, or pending
source never approves withdrawal and never erases an earlier successful pin.

Never advance discovery past a failed directory read. Revisit pending/failed source
identities and failed directories irrespective of quarter. Daily discovery starts
at the approved handoff and replays overlap with the baseline. A successfully
decoded empty directory means no new source; invalid/truncated/denial bytes never
stand in for an empty directory.

Raw originals are promoted and verified before Snapshot state or Binding creation.
Quarterly locations end in `master.zip`; daily locations end in `master.idx` under
`raw/sec/indexes/kind=<kind>/period=<period>/sha256=<hash>/`. Keep the original
archive, receipt headers, staging/promotion checkpoints, quarantine body/sidecars,
worksets, results, and Attempt/transport audit. Recovery checks exact old context,
request ID, receipt hash and raw path. Existing Bindings win before latest/reuse
policy. Do not delete manifests or replace pins to force progress.

All pipelines in the deployment must share `sec-owner-lowell-mason`, its fixed
Blob sentinel/registry, storage binding and one no-burst 3 requests/second budget.
Discovery, download, retry and reconciliation each reserve from that budget.
Additional workers do not create request lanes. A lease loss or unconfirmed child
outcome stops the issuer. A successor waits through the persisted unsafe ownership
window plus bounded in-flight allowance, even after an old process disappears.
The fatal child timer and verified socket drain bound the selected local transport.

Local clean release can atomically finalize the sentinel and release its lease.
Azure cannot atomically acknowledge those two operations, so even a clean Azure
release retains the full conservative unsafe guard. Wait for its stored UTC guard;
do not break the lease or shorten the journal to improve throughput. Server UTC
bounds and current fencing are timing authority. Retained Permit/retry monotonic
values identify their originating host-domain evidence and confer no restart
scheduling authority.

SEC access denial halts the run durably. An unrepresentable valid `Retry-After`
retains its raw header/receipt and installs a durable **owner-wide policy block**;
this reports deferred/5. It has no reset/expiry API. A new run, process restart,
longer local deadline, or guessed delay cannot escape the block. Investigate the
retained reason and obtain an explicit policy resolution. Ordinary representable
server delays remain honored through the shared sentinel before issuer handoff.

Azure adapter tests use offline scripted transports. Actual local process tests
use bounded synthetic loopback bodies, shorter explicitly recorded test timers,
and independent clients/shared durable stores. Retained Stage 1 body hashes anchor
the selected representations. None of these proves live SEC availability, global
format coverage, a recovery horizon, Linux/default-90-second performance, live Azure
lease/CAS/HNS/network/auth behavior, worker sizing, or the 22 reserved S7 checks.
No production schedules, jobs, infrastructure, parser, publication, or withdrawal
approval are implemented here.

A completed attempt can replay its exact saved result after its original deadline. This returns the saved context and does not start another acquisition. An expired deadline cannot start unfinished work; supply a new attempt ID and a valid deadline for that recovery.
