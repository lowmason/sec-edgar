## Cross-task schemas and interfaces

Task 2 defines these deeply immutable records and deterministic JSON codecs. Convert nested mappings to read-only mappings/immutable values, and make mapping serializers return detached copies; frozen dataclass attributes alone do not freeze a dict. UTC timestamps are timezone-aware ISO strings; SHA-256 is 64 lower-case hex; immutable IDs hash canonical UTF-8 JSON with sorted keys, compact separators and no NaN. Include versions and effective config hash in the digest. Sort members by source ID and directories by canonical URL; reject duplicates rather than hide conflicting members.

| Record | Fields used across tasks |
|---|---|
| `Source` | `source_id: str`, `canonical_url: str`, `kind: Literal['quarterly','daily']`, `period: str`, `representation: Literal['zip','idx']` |
| `RunContext` | `run_id, execution_id, command, attempt_id, image_digest, parser_version, schema_version, config_sha256: str`; `started_at, deadline: datetime`; `priority: Literal['daily','backfill','reconciliation']` |
| `DirectoryOutcome` | `url, period: str`; `outcome: Literal['available','no_new_sources','discovery_failed']`; `listing_sha256: str | None`; `source_ids: tuple[str,...]`; `error: Error | None` |
| `SourceWorkset` | `workset_id: str`, frozen `context: RunContext`, `pinned_end_quarter: str`, `discovery_id: str`, `members: tuple[Source,...]`, `directories: tuple[DirectoryOutcome,...]`, `discovery_complete: bool`, `overlap_from: date`, `acquisition_mode: Literal['reuse_accepted','refresh']` |
| `Snapshot` | `source_id, sha256, raw_path: str`; `byte_count: int`; `received_at: datetime`; `validators: Mapping[str,str]`; `representation, envelope_version: str` |
| `Binding` | `source_workset_id, source_id, snapshot_sha256: str` |
| `SnapshotWorkset` | `workset_id, source_workset_id: str`; `context: RunContext`; `snapshots: tuple[Snapshot,...]`; exact `pinned_end_quarter`, `directories`, `overlap_from`; no mutable latest references |
| `Error` | `code, message: str`; `retryable: bool`; `source_id: str | None`; `details: Mapping[str,object]` |
| `CommandResult` | `context: RunContext`; `outcome: str`; `source_workset_ref, snapshot_workset_ref: str | None`; counters `discovered,downloaded,unchanged,pending,failed,quarantined: int`; `gaps: tuple[Error,...]`; `started_at,ended_at: datetime` |
| `Versioned` | `value: dict[str,object]`; `version: str` (opaque actual Table ETag or local revision) |
| `QueueTicket` | `ticket_id, owner_id, priority: str`; `enqueued_at, expires_at: datetime` |
| `Permit` | `owner_id: str`, `epoch: int`, `request_id: str`; `must_start_before, must_end_by, takeover_after: datetime`; `start_before_mono, deadline_mono: float` |
| `BodyReceipt` | `url: str`, `status: int`, `headers: dict[str,str]`, `temporary_path: Path`, `received_at: datetime`, `byte_count: int`, `sha256: str`, `complete: bool`, `error: Error | None` |
| `ValidatedBody` | `receipt: BodyReceipt`; `representation, envelope_version: str`; `expanded_byte_count: int` |

`Attempt` durable rows include parent §4.5's run/execution/command/attempt/image tuple, start/end, outcome and structured error; transport-attempt child rows include request ID, ordinal 1–5, URL, status, bytes, ownership epoch and next-allowed time. Discovery status and acquisition status are separate; a later discovery/download failure never deletes `latest_downloaded_snapshot` or existing bindings. Stage 2 creates no processing identity claiming transformation/publication.

The generic state adapter stores `Source`, `Snapshot`, `Binding`, `DirectoryProgress`, `DiscoveryBoundary`, `Coordination` and `QueueTicket` rows in **SourceState**, and attempts in **Attempts**. Namespace/kind are partition keys; stable identities are row keys. This adds no unapproved table binding. Use paginated reads for pending work. Snapshots are keyed by `(source_id, sha256)`; bindings by `(source_workset_id, source_id)`. A snapshot is not an approval or active publication pointer.

All named helper methods in code examples below are defined by the producing task's Interfaces block. Type protocol bodies may use `...` because they define interfaces, not unimplemented production behavior. Examples show the critical executable core and assertions; implementers must finish the specified surrounding modules and named matrix cases through red/green cycles, without replacing the behavioral requirements with examples alone.

## Evidence and review procedure for every task

Use the `subagent-driven-development` task brief/report/diff-file handoff. Record BASE before dispatch; never substitute `HEAD~1`. Each task's loop is: write its first failing behavioral test, run and retain the observed failure, implement the minimum required behavior, run covering tests, refactor, run covering tests again, commit only its named files, dispatch a fresh task reviewer, fix/re-review until both **Spec PASS** and **Quality PASS**. Commit messages below describe task boundaries. The progress ledger carries actual interfaces/deviations, commands and outputs; clean task-review evidence does not imply Stage 7 acceptance.

The commands after Task 1 assume a working workspace, cwd at its execution root:

```bash
uv run --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
```

For a targeted module use `python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_NAME.py' -v` through the same `uv run --frozen --package sec-edgar-ingest` prefix. This plan uses stdlib unittest so no unverified development dependency version is invented. Test failures must assert contract violations, not mirror private implementation details. No wall-clock sleeps in unit tests: use deterministic injected clocks/barriers. A separate bounded process test verifies the actual hard sender cancellation against a loopback server.

