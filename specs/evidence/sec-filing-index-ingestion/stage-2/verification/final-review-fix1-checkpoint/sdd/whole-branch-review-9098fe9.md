**Ready to merge: With fixes. Whole-branch Spec: FAIL pending two Important fixes. Whole-branch Quality: FAIL pending those fixes.** I found no Critical issue. One Minor runbook correction also needs an explicit disposition.

Reviewed the frozen range `09c649aad9c7049b1a58f641bb843917b6b61aa8..9098fe9b664d9f44a663fdd8357e34030c37e932`, with the base independently confirmed as `merge-base(main, HEAD)`. Routing was `gpt-6.1-sol`, effort `max`, fresh context, using the default-role fallback for the unavailable named code-reviewer role. This was a read-only whole-branch review; I made no changes and dispatched no agents.

**Strengths**

The acquisition boundaries are substantially implemented and tested. The code retains original response bytes, validates the accepted quarterly ZIP and daily IDX envelopes, writes raw content before Snapshot and member Binding, and preserves immutable snapshot pins across retries. The checkpoint repair paths keep current command provenance separate from the retained discovery and response origins.

Coordination received careful implementation and proof. I checked owner-wide namespace binding, the leased sentinel and fenced journal, one request per turn, daily priority, durable ordinal accounting, cooldown and halt behavior, time uncertainty, cancellation, drain, and successor takeover. The accepted conservative Azure release behavior is represented honestly: separate journal and lease writes retain the full unsafe guard; the local backend can shorten it through its atomic operation. The unrepresentable Retry-After latch remains durable without an expiry or new-run escape.

The retained verification supports real process behavior. The current log records **289 tests in 107.544 seconds**, followed by successful build, CLI help/version, compilation and whitespace checks. The actual three-collector proof contains three insert attempts, two conflicts and one winner. The collection crash receipts cover all seven checkpoints, including their retry-prefix variants, and the four CLI crash receipts verify Result-before-Attempt-finish repair.

The evidence package is unusually thorough. I read the complete 81-path authored view in bounded passes, the plan/spec/design/ADR and accepted findings, all eight task reports, and the operative review receipts. The full 12,162-path range reconciles with the inventory. All 12,081 paths omitted from the authored view have verified payload or declared control coverage.

**Issues**

**Critical — none.**

**Important**

1. **[P2] A supported historical discovery cannot fit Azure’s single string payload.**

   File: [azure.py:68](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py:68). The affected state construction is [state.py:94](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/state.py:94).

   `_entity()` puts the entire canonical state value into one `Payload` string. `begin_discovery()` first registers every unresolved required directory in the single `DiscoveryBoundary/daily` row.

   With the accepted intended range **2010Q1 through the pinned open quarter 2026Q4**, the real inventory produces 86 directory units. Running that registration in memory and passing the resulting value through the actual Azure serializer produces a **41,167-character / 82,334-byte UTF-16LE string**. This exceeds Azure Table Storage’s 64 KiB string-property limit. It fails while registering discovery, before any SEC request can resolve the pending gaps.

   The initial development range, 2015Q1–2026Q4, produces 58,404 UTF-16LE bytes and fits. That explains why the retained small fixture and development-range checks do not expose the intended-history failure. This is an adapter representability defect in an accepted configuration; the reserved Stage 7 capacity proof does not make it acceptable.

   **Fix:** Give Azure state a representation that respects both property and entity limits while preserving the conditional update of the complete boundary. Add an offline adapter regression using the actual 2010Q1 inventory and registration value, covering encode/decode and conditional replacement. Retain the accepted historical range and the shared boundary semantics.

   This finding comes from a guarded in-memory size probe and source inspection. I did not construct an Azure client or claim an observed service rejection.

2. **[P2] Snapshot decoding omits the exact source-period validation performed by its producer.**

   File: [worksets.py:131](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/worksets.py:131). Compare the stronger producer check at [worksets.py:157](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/src/sec_edgar_ingest/worksets.py:157).

   `_validate_snapshot()` checks source membership and representation, but does not verify that a snapshot’s raw address belongs to that exact source period. `make_snapshot_workset()` does verify the exact address, period and envelope.

   Starting with a valid quarterly snapshot workset, I changed only `raw_path` from `period=2015Q1` to `period=2015Q2`, recomputed the workset’s canonical digest, and decoded it through `decode_snapshot_workset()`. The decoder accepted it while the directory still named **2015Q1** and the snapshot retained the **2015Q1 SourceID**.

   The producer currently prevents this combination during normal collection. The defect is at the strict persisted/public decoding boundary: a well-formed, correctly hashed workset can claim a different quarter’s raw object for its named source. A digest validates the supplied content, so it does not replace semantic source validation.

   **Fix:** Apply equivalent exact source-address and period validation during decoding, including agreement with directory membership and the SourceID. Share the semantic validation with the producer, or supply an explicitly validated source workset if that is necessary to establish the exact member. Add a rejection test for a wrong-period raw path with a valid recomputed workset digest.

**Minor**

1. **[P3] The current runbook still describes the approved two-config sequence as awaiting an owner decision.**

   File: [sec-edgar-ingest-acquisition.md:115](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/docs/runbooks/sec-edgar-ingest-acquisition.md:115).

   Lines 115–117 say the one-config collision remains an owner decision and that the two-config sequence must not be represented as a passed gate until approved. The supplied owner **Yes** receipt, completed I1 sequence and complete scoped verdict establish that approval and execution have occurred.

   **Fix:** Update this operative runbook paragraph to describe the approved separate quarterly `2015Q1` and daily `end_quarter=open` configs and link the retained approval and sequence evidence. Historical pending-status passages in earlier receipts can remain as history.

**Recommendations**

Resolve the two Important findings with focused regression tests, then refresh the affected verification and review scope. They concern Azure record encoding and workset decoding; neither requires live SEC/Azure access, infrastructure work, or Stage 3 implementation.

Correct or explicitly dispose of the Minor runbook finding before the completion stamp. Keep the remaining acceptance claims within their established proof limits.

**Assessment**

**Ready to merge: With fixes.** The implementation has strong recovery, coordination and verification work, but the Azure backend cannot represent the accepted intended-history registration, and the snapshot decoder does not enforce an exact source identity contract. These are concrete implementation gaps in the whole-branch Spec and Quality gates.

The intentionally pending completion stamp, task tick, scaffold retirement and integration decision were not treated as defects. Frozen HEAD and merge-base still matched at the end. The four existing scaffold deletions remained as supplied.

**Scope and evidence checked**

I inspected these acquisition contracts across implementation, tests and retained evidence:

- Immutable configuration, pinned endpoint/date, RunContext, SourceWorkset, SnapshotWorkset, result and receipt identities; canonical paths and exact replay.
- Durable local SQLite/content stores and Azure Blob/Table create-only/CAS behavior, response ETags, API pins and the absence of a cross-store transaction.
- Owner-wide coordination, daily priority, ordinal accounting, pacing, Retry-After/cooldown/halt, cancellation, drain and safe takeover.
- Strict directory discovery, failed versus empty listings, old unresolved members, contiguous daily boundary and generation-aware gap recovery.
- Original bytes, quarterly ZIP/daily IDX envelope validation, exchange/received/expanded guards, quarantine and retained retry prefixes.
- Raw → receipt → Snapshot → Binding → SnapshotWorkset recovery; immutable Result → Attempt completion recovery.
- CLI validation, return codes, exact completed replay, installed entry points/imports, network/authentication denial, packaging, documentation and declared scope.

The supplied package identities independently matched:

| Review input | Bytes | SHA-256 |
|---|---:|---|
| Full standard diff | 40,666,489 | `27f6eec0f09c4a8b9e5555483c9ff7a01df77b575828e3f240e5580d382b2f21` |
| Complete authored view | 1,026,299 | `2b543aa72720530a3763c8bed77198da9fe92c262bd11639fb02889fa7d19a06` |
| Changed-path inventory | 4,962,927 | `9af6efdfc222175c3bbea9fea90abb69baab3b38899b868539fa38070bda7977` |
| Package receipt | 17,693 | `6d72e1ce471334462119c2c054d6fcd18a969d0760fc5a58b764f81f6ed9a483` |

All six retained manifests were checked against physical byte lengths and hashes: **12,150 manifest records**, including the declared 79-record reused installed proof. Retention mappings, compressed-original comparisons and current mapped SDD files matched. The newest acceptance checkpoint matched **16 payload records / 18 physical files / 174,917 bytes**, including the supplied manifest and map hashes.

The installed proof comparisons passed:

- All 11 retained command argv/exit receipts match.
- Current `dist` artifacts equal the retained wheel and sdist. All **19 package source/typing files** match current frozen source; package README and original pyproject also match.
- The installed environment has exactly the **20 locked runtime dependencies plus `sec-edgar-ingest==0.1.0`**, with fresh `site-packages` imports.
- All **27 SDK inspection source hashes** match the inspected installed source.
- The retained proof is **macOS arm64 / Python 3.14.0**. It does not establish execution on the accepted Linux amd64 / Python 3.14.8 container.

The approved combined sequence comparisons passed:

- All **11 actual command receipts** match: two refusal exits `2`, two incomplete/replay exits `3`, and seven success exits `0`.
- Read-only SQLite contents equal the retained dump: **7 Attempts, 3 Bindings, 10 fixture cursors and 11 TransportAttempts**.
- Only the delayed October 2 URL has cursor `2`; the other nine cursors are `1`. Completed quarterly collection and final daily reuse add no transport rows.
- All four retained worksets decode and match their addressed IDs; all three original raw objects match their path hashes.
- Its inner manifest verifies **96 payload records / 97 physical files / 502,536 physical bytes**.

The decisive retained process assertions passed:

```text
14 collection crash/prefix receipts: exit trio 73 / 0 / 0.
7 retry-prefix bodies retained exactly; old temporary paths absent.

Three collectors: 3 distinct PIDs, all exit 0.
Binding inserts: 3 attempts / 2 conflicts / 1 winner.
Winner raw hash == snapshot workset hash.
Replay: downloaded=0, unchanged=1.

Integrated takeover:
parent exit=-15
old socket closed       2763620.28299425
unsafe_until            2763622.31246675
successor first start   2763622.6734415
84 observations with zero successor requests through the guard.
Priority order: daily, daily, daily, backfill.
Child alarm disposition: default-fatal.

Independent child deadline: actual child exit=-14.
Incomplete 91-byte body and receipt hashes agree.

Stale dispatch: zero server events, zero body bytes, incomplete receipt.

4 CLI Result/Attempt crashes: crash=74 / replay=0.
Repaired successful Attempt contains the retained Result.
Pre-existing Result bytes preserved exactly.
```

The seven network/authentication guard receipts also agree with their assertions: denied operations never reached provider or network stubs; only the explicitly selected fixture-origin operations reached their designated stubs.

I did not rerun suites, builds, installation or the approved sequence. I did not use live networking, authentication or provider construction. The existing proof does not establish production default-90-second timing behavior, Linux child lifecycle, real SEC/Azure integration, worker/container behavior, a recovery horizon, expanded format coverage or Stage 7 capacity. All 22 reserved Stage 7 claims remain reserved.

**Exact bounded behavior probes**

Both commands below ran from `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar` and exited `0`. They install the existing network guard before importing the implementation and use only in-memory state and pure serialization. No provider client or credential was constructed and no files were written.

Probe 1, Azure registration payload size and strict snapshot decoding:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/sec-edgar-ingest/tests:packages/sec-edgar-ingest/src .venv/bin/python - <<'PY'
import network_guard
network_guard.install()
import json
from datetime import date
from dataclasses import replace
from support import fixture_settings, fixture_context, fixture_source, fixture_snapshot, fixture_workset
from sec_edgar_ingest.models import Versioned, RunContext, canonical_json
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.discovery import _inventory
from sec_edgar_ingest.storage.azure import AzureStateStore
from sec_edgar_ingest.storage.contracts import AlreadyExists, Conflict
from sec_edgar_ingest.config import pin_context
from sec_edgar_ingest.worksets import make_snapshot_workset, encode_workset, decode_snapshot_workset, workset_digest

class MemoryState:
    def __init__(self):
        self.rows = {}
    def get(self, kind, key):
        return self.rows.get((kind, key))
    def insert(self, kind, key, value):
        if (kind, key) in self.rows:
            raise AlreadyExists('exists')
        row = Versioned(value, '1')
        self.rows[(kind, key)] = row
        return row
    def replace(self, kind, key, value, version):
        old = self.rows[(kind, key)]
        if old.version != version:
            raise Conflict('version')
        row = Versioned(value, str(int(version) + 1))
        self.rows[(kind, key)] = row
        return row
    def scan(self, kind, filters):
        return iter(
            row for (k, _), row in self.rows.items()
            if k == kind and all(
                row.value.get(name) == value
                for name, value in filters.items()
            )
        )

serializer = object.__new__(AzureStateStore)
for start in ('2015Q1', '2010Q1'):
    settings = fixture_settings(
        backfill={'start_quarter': start, 'end_quarter': 'open'}
    )
    context = replace(
        fixture_context(command='discover'),
        config_sha256=settings.config_sha256,
        effective_config={}
    )
    context, end = pin_context(settings, context, date(2026, 10, 6))
    memory = MemoryState()
    state = AcquisitionState(memory)
    units, overlap = _inventory(
        settings, state, 'quarterly', date(2026, 10, 6), end
    )
    frozen = {
        'context': context.to_mapping(),
        'mode': 'quarterly',
        'acquisition_mode': 'reuse_accepted',
        'units': list(units),
        'today': '2026-10-06',
        'overlap_from': overlap.isoformat()
    }
    state.begin_discovery(
        'probe-' + start, frozen, context, 'quarterly', 'reuse_accepted'
    )
    print(json.dumps({
        'probe': 'ordinary-quarter-discovery-azure-payload',
        'start_quarter': start,
        'end_quarter': end,
        'unit_count': len(units),
        'rows': [{
            'kind': kind,
            'key': key,
            'payload_characters': len(
                serializer._entity(
                    kind, key, row.to_mapping()['value']
                )['Payload']
            ),
            'payload_utf16le_bytes': len(
                serializer._entity(
                    kind, key, row.to_mapping()['value']
                )['Payload'].encode('utf-16-le')
            )
        } for (kind, key), row in memory.rows.items()]
    }))

source = fixture_source()
original = make_snapshot_workset(
    fixture_workset((source,)),
    (fixture_snapshot(source, b'original-quarter-bytes'),)
)
payload = json.loads(encode_workset(original))
payload['snapshots'][0]['raw_path'] = (
    payload['snapshots'][0]['raw_path']
    .replace('period=2015Q1', 'period=2015Q2')
)
payload['workset_id'] = workset_digest({
    key: value for key, value in payload.items()
    if key != 'workset_id'
})
try:
    decoded = decode_snapshot_workset(canonical_json(payload))
    print(json.dumps({
        'probe': 'strict-snapshot-decoder-mutated-period',
        'accepted': True,
        'directory_period': decoded.directories[0].period,
        'source_id': decoded.snapshots[0].source_id,
        'raw_path': decoded.snapshots[0].raw_path
    }))
except ValueError as error:
    print(json.dumps({
        'probe': 'strict-snapshot-decoder-mutated-period',
        'accepted': False,
        'error': str(error)
    }))
print(json.dumps({
    'guard_installed': True,
    'provider_client_or_credential_constructed': False,
    'network_used': False,
    'writes': False
}))
PY
```

Decisive output:

```json
{"probe": "ordinary-quarter-discovery-azure-payload", "start_quarter": "2015Q1", "end_quarter": "2026Q4", "unit_count": 61, "rows": [{"kind": "DiscoverySession", "key": "b61c2ca6683e6012cb5eb333c9a162e7a6064e696fe2f28373bf3ba273f5364b", "payload_characters": 8926, "payload_utf16le_bytes": 17852}, {"kind": "DiscoveryBoundary", "key": "daily", "payload_characters": 29202, "payload_utf16le_bytes": 58404}]}
{"probe": "ordinary-quarter-discovery-azure-payload", "start_quarter": "2010Q1", "end_quarter": "2026Q4", "unit_count": 86, "rows": [{"kind": "DiscoverySession", "key": "0c1078ce136255e296328ab3135221d83eb2615c691b33585a960a9cade61045", "payload_characters": 11676, "payload_utf16le_bytes": 23352}, {"kind": "DiscoveryBoundary", "key": "daily", "payload_characters": 41167, "payload_utf16le_bytes": 82334}]}
{"probe": "strict-snapshot-decoder-mutated-period", "accepted": true, "directory_period": "2015Q1", "source_id": "f06d1de08e84905a6381309ab6406ca12d99de5ce7d28d09a4f7456fc82ef998", "raw_path": "raw/sec/indexes/kind=quarterly/period=2015Q2/sha256=e46ed89df660c74bf9a4102dad91f7ff538f1f78091e71cebeaaa2b5051155cf/master.zip"}
{"guard_installed": true, "provider_client_or_credential_constructed": false, "network_used": false, "writes": false}
```

Probe 2 bounded the Azure finding rather than extending it to ordinary daily-quarter progress:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/sec-edgar-ingest/tests:packages/sec-edgar-ingest/src .venv/bin/python - <<'PY'
import network_guard
network_guard.install()
import json
from datetime import date, timedelta
from support import fixture_source
from sec_edgar_ingest.models import Versioned, DirectoryOutcome
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.storage.azure import AzureStateStore

class MemoryState:
    def __init__(self):
        self.rows = {}
    def get(self, kind, key):
        return self.rows.get((kind, key))
    def insert(self, kind, key, value):
        row = Versioned(value, '1')
        self.rows[(kind, key)] = row
        return row
    def replace(self, kind, key, value, version):
        row = Versioned(value, '2')
        self.rows[(kind, key)] = row
        return row

memory = MemoryState()
state = AcquisitionState(memory)
days = [
    date(2026, 7, 1) + timedelta(days=n)
    for n in range(92)
]
members = tuple(sorted(
    (
        fixture_source(day.isoformat(), 'daily')
        for day in days if day.weekday() < 5
    ),
    key=lambda member: member.source_id
))
outcome = DirectoryOutcome(
    'https://www.sec.gov/Archives/edgar/daily-index/2026/QTR3/index.json',
    '2026Q3', 'available', 'a' * 64,
    tuple(member.source_id for member in members), None
)
state.record_directory(
    'probe-ordinary-daily-quarter',
    outcome, members,
    evidence={'sha256': 'a' * 64}
)
serializer = object.__new__(AzureStateStore)
for (kind, key), row in memory.rows.items():
    payload = serializer._entity(
        kind, key, row.to_mapping()['value']
    )['Payload']
    print(json.dumps({
        'kind': kind,
        'key': key,
        'daily_member_count': len(members),
        'payload_characters': len(payload),
        'payload_utf16le_bytes': len(payload.encode('utf-16-le')),
        'evidence': 'minimal sha256 only; real receipt may be larger'
    }))
print(json.dumps({
    'guard_installed': True,
    'provider_client_or_credential_constructed': False,
    'network_used': False,
    'writes': False
}))
PY
```

Output:

```json
{"kind": "DirectoryProgress", "key": "e36c3be6e3a29be4f9921cb8165c7acc52e88103f1a131307b99308a38c8debf", "daily_member_count": 66, "payload_characters": 20439, "payload_utf16le_bytes": 40878, "evidence": "minimal sha256 only; real receipt may be larger"}
{"kind": "DiscoveryBoundary", "key": "daily", "daily_member_count": 66, "payload_characters": 22, "payload_utf16le_bytes": 44, "evidence": "minimal sha256 only; real receipt may be larger"}
{"guard_installed": true, "provider_client_or_credential_constructed": false, "network_used": false, "writes": false}
```

This second probe does **not** establish that every daily progress entity fits; its receipt evidence was deliberately minimal. It establishes that a normal 66-weekday member list by itself is not the demonstrated failure.

**Corrected inspection assumptions**

These were inspector corrections, not failures of the implementation or retained proof:

- The full proof-bearing diff contains non-UTF-8 bytes. Its complete path reconciliation was performed using bytes, rather than treating the full package as UTF-8 text.
- Installed command receipts are indexed by `commands.json`; the combined sequence uses `calls.json`.
- Runtime pin comparison excludes the virtual workspace root `sec-edgar`. The corrected comparison matched all 20 runtime dependencies and the installed package.
- SQLite partitions include the namespace prefix, for example `sec-owner-lowell-mason:Attempt`. The corrected read-only queries matched the retained state dump.
- Result counters are top-level fields, and the combined SHA manifest is a list of records. The corrected structured inspection completed successfully.
- The final primary-preservation receipt is `task-8-i1-primary-preservation.json`, and SDK signatures are under `specs/evidence/sec-filing-index-ingestion/stage-2/`. Their actual retained paths were inspected; earlier candidate-name misses were not treated as missing evidence.
