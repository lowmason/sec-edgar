# Retained-byte ETL and per-quarter publication

`transform` reads one exact immutable snapshot workset from the selected object
store. `publish` reads one exact transformed workset. Both bypass collection and
SEC transport. The native offline proof exercises these commands, actual local
CAS races, forced process exits and recovery from an installed wheel.

The owner amended Stage 3 acceptance on 2026-10-07 America/New_York to allow the
exact documented SEC-0141, SEC-0142 and SEC-0143 quarantines while retaining strict
whole-source refusal for their 21, 24 and 6 conflicting observations. The
[verification record](../../specs/evidence/sec-filing-index-ingestion/stage-3/verification.md)
binds the complete raw SHA256/lengths and the separate fresh acceptance result.
No source or duplicate winner is approved; other invalid retained rows and missing
offline dependencies remain blockers. No history-wide range or deployed capacity
is established; all 22 Stage 7 integrated checks remain reserved.

## Select the exact stored input

For an already populated local fixture store, use its acquisition snapshot
reference. `--state-dir` is the base under which `storage.root` is resolved.
The separate, committed [ETL fixture configuration](../../conf/sec-edgar-etl-fixture.yaml)
selects the supported row parser `fixture-index-parser-v1`. It keeps the same
local storage binding and accepted settings as `conf/sec-edgar-ingest.yaml`;
only `etl.parser_version` differs. Keep the acquisition configuration unchanged:
its `fixture-envelope-v1` value remains acquisition provenance and is rejected
at the ETL boundary. Both configuration files use JSON syntax, a YAML 1.2 subset.

The raw snapshot workset must already exist, with its original bytes and pins,
from acquisition or an explicit offline fixture seed. Start with the exact
snapshot reference returned by that preparation, then transform it and publish
the returned transformed reference. See the [acquisition runbook](sec-edgar-ingest-acquisition.md)
for the preceding fixture acquisition lifecycle. ETL does not require
`--fixture-pack` and does not collect missing inputs. These examples use the
selected native Python and cached frozen workspace; the same arguments apply to the installed
`sec-edgar-ingest` console. Set the deadline to an explicit future aware UTC time
within the configuration's bounds.

```sh
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest transform \
  --config conf/sec-edgar-etl-fixture.yaml --state-dir /absolute/existing-fixture-base \
  --run-id replay-001 --execution-id local-001 --attempt-id transform-v1 \
  --deadline '<future-UTC-ISO-timestamp>' \
  --workset 'worksets/sec/snapshot/sha256=<exact-snapshot-workset-id>/workset.json'

uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest publish \
  --config conf/sec-edgar-etl-fixture.yaml --state-dir /absolute/existing-fixture-base \
  --run-id replay-001 --execution-id local-001 --attempt-id publish-v1 \
  --deadline '<same-future-UTC-ISO-timestamp>' \
  --workset 'worksets/sec/transformed/sha256=<returned-transformed-id>/workset.json'
```

Copy the returned transformed reference exactly from transform's stdout. A
source workset is `worksets/sec/source/sha256=<id>/workset.json`; it is collection
input and is not accepted as transform input. Original receipt bytes remain at
`raw/sec/indexes/kind=<kind>/period=<period>/sha256=<hash>/master.<zip|idx>`.
Observation manifests and Parquet are immutable processing outputs referenced
by the transformed workset. Generation manifests live at
`curated/sec/filing_index/year=<year>/quarter=<quarter>/generation=<id>/manifest.json`.
Candidate descriptors use `worksets/sec/candidates/sha256=<id>/candidate.json`.

The snapshot workset retains its acquisition `origin_context`. A separate ETL
configuration freezes the current parser/schema, image and effective context.
For local fixture parser replay, copy `conf/sec-edgar-etl-fixture.yaml` to a
separate replay configuration file, then change `etl.parser_version` from its
provided `fixture-index-parser-v1` to the supported
`fixture-index-parser-v2`, use a new attempt ID and the **same** snapshot workset,
and add `--force` to transform. Publish its returned workset with that same new
configuration via `--config` for both commands. Production parser
`sec-index-parser-v1` accepts the selected
quarterly ISO-date ZIP family and daily compact-date IDX family; synthetic
fixture aliases and overrides are refused by Azure configuration.

Replay changes transformation provenance without recollecting raw bytes or
creating a second logical filing. The key is normalized CIK plus archive path.
CIKs are ten digits; accession is nullable for usable unrecognized legacy paths.
Filing date determines output quarter, including a daily source with rows for
multiple quarters. Company name and filing date alone never form the key.

## Capture and read a generation

This local example establishes the actual stores used by the reader. Opening an
Azure configuration would construct its clients; live Azure/authentication is
outside the authorization for this proof.

```python
from pathlib import Path
from sec_edgar_ingest.config import Settings
from sec_edgar_ingest.storage import open_stores
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState
import json

settings = Settings.from_mapping(json.loads(Path('conf/sec-edgar-etl-fixture.yaml').read_text()))
store, objects, leases = open_stores(settings, base_path=Path('/absolute/existing-fixture-base'))
try:
    capture = capture_quarter('2026Q4', objects, EtlState(store))
    if capture is None:
        raise RuntimeError('quarter has no published generation')
    Path('saved-capture.json').write_text(json.dumps(capture.to_mapping()))
    for row in read_quarter(capture, objects):
        print(row.cik, row.archive_path)
finally:
    leases.close()
    store.close()
```

For a later reproducible read, decode that mapping with
`GenerationCapture.from_mapping` from `sec_edgar_ingest.etl.contracts` and pass
it to `read_quarter`. The saved capture fixes manifest path, hash and byte count.
The reader verifies full manifest/file sizes, checksums, schema, row counts,
quarter membership and logical identity before exposing the first row. It never
follows a mutable latest pointer after capture. Retained manifests include exact
source receipts and files; noninitial candidates retain their prior capture in
`retained-base.json`.

## No-op, gate and repair

Unchanged fingerprint and versions are a no-op. Forced transform may rebuild
observations; it does not duplicate a logical filing. The generation fingerprint
tracks selected processing references, versions, quarter mode and retained key
basis. Attempt paths and worker image digest do not create new logical filings;
original producer-image provenance remains in reused immutable output.

The pointer CAS is the publication boundary, independently for each quarter.
Contending publishers reread the winner and rebuild after a conflict. A daily
addition survives that rebuild. Atomicity does not extend across quarters or
across object and table stores. A partial command result records each quarter's
actual outcome and error; inspect those results before retrying.

An open quarterly omission preserves the key and emits `unresolved_absence`.
A closed quarterly withdrawal becomes `awaiting_approval`, CLI exit **10**.
Inspect the candidate descriptor, its manifest/files and the exact source hash
against the frozen original. A gate reached after a CAS loss is reevaluated
against the winning generation. A gated candidate is never current. Stage 3
provides no approval mutation or pointer rollback command; those operations
remain reserved for later authorized work.

A command's durable envelope freezes `{context, intent}` at
`runs/sec/<run-id>/<command>/<attempt-id>/command.json`; its full result is adjacent
`result.json`. Resume the same exact arguments/configuration and unexpired
frozen intent after interruption. Completed exact attempts replay their saved
result. If the result object exists but its Attempt index is incomplete, the CLI
repairs the index from that object. After pointer CAS, publication repair rebuilds
receipt/processing indexes from the validated committed generation and does not
advance the pointer again. For an explicit application-level repair:

```python
from sec_edgar_ingest.etl.publication import repair_publication
repair_publication('2026Q4', objects, EtlState(store))
```

Run that while the selected stores above are open. Per-source published flags
are recoverable indexes and become true only when all receipt-backed output
quarters are covered. Unreferenced losing candidate objects remain retained.
Expired incomplete attempts need a new authorized attempt against the exact
workset; they cannot silently change the frozen deadline or intent.

## Repeat the offline proof

Use new output directories for every run; existing outputs are refused to keep
failures and intermediate evidence intact.

```sh
scripts/check-sec-edgar-ingest.sh
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py specimens --output /absolute/new/specimens
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py sequence --output /absolute/new/sequence
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py installed --output /absolute/new/installed
```

The original specimen acceptance result remains historical exit 1 for the
documented source conflicts; the owner amendment has a separate acceptance verifier. The sequence proof records actual CLI logs, saved contexts, unchanged
raw hashes, reader captures, process PIDs, CAS versions and forced-exit recovery.
The installed proof uses the exact built wheel, hash-bearing frozen lock export,
retained Stage 2 wheels and cached PyArrow, a temporary native Python venv, no
PYTHONPATH, cwd outside the checkout, and a site-packages/source-byte guard.
Every evidence inventory uses safe relative paths, sizes and SHA256, excluding
itself. Native Python 3.14.0/macOS arm64 evidence establishes no Linux
amd64/Python 3.14.8 runtime, memory or scratch capacity. All 22 integrated checks
remain reserved for roadmap Stage 7. Live SEC/Azure/authentication, provisioning,
compute, deployment and image builds remain closed.
