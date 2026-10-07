# Whole-branch Minor M1 — separate ETL example configuration prepared

Status: **DONE_WITH_CONCERNS / prepared; actual documented sequence pending**.
Base: `3c868351ea8c417d2a5edf88c6091ef0b72d519a`.
Owned commit: `d3c46768321de9a973f1b82258f1e224506848e5`.

The runbook previously passed `conf/sec-edgar-ingest.yaml` to transform and publish.
Its actual parser `fixture-envelope-v1` is acquisition provenance and is rejected
by the existing ETL `supported_parser` boundary. The independent before receipt
records the actual ValueError; no compatibility alias was added.

Added `conf/sec-edgar-etl-fixture.yaml`, copied from the original configuration
with only `etl.parser_version` changed to `fixture-index-parser-v1`. All accepted
settings/pins and the actual storage binding remain equal. Both documented CLI
commands and the reader example now select that actual committed file. Replay
instructions explicitly start from this provided row-parser configuration before
changing a separate replay copy to `fixture-index-parser-v2`. Documentation
separates these fixture-only aliases from production `sec-index-parser-v1`.

The runbook now explicitly requires an existing raw snapshot workset and pins
from acquisition or an explicit offline seed, followed by transform of its exact
reference and publication of the returned transformed reference. It does not
imply that ETL collects missing input. Root and package README point to the same
separate configuration, preserving the acquisition/ETL distinction.

Only these four paths were committed, with explicit `git add` and `git commit
--only` paths:

- `conf/sec-edgar-etl-fixture.yaml`
- `docs/runbooks/sec-edgar-etl-publication.md`
- `README.md`
- `packages/sec-edgar-ingest/README.md`

No production, tests, proof harness, dependency/pin, frozen tracked verification,
controller evidence or other worker edits were changed or included. Insight
blocks were emitted before and after the scoped edits. Applied the existing
receiving-code-review and verification-before-completion guidance.

## Actual independent validation

The guarded native command
`uv run --offline --frozen --package sec-edgar-ingest python .sdd/3-sec-filing-index-ingestion-stage-3-spec/final-fix1-doc-evidence/validate.py`
exited **0**, with full stdout/stderr and exact command metadata retained. It used
actual `load_config`/`Settings`, `supported_parser` and `deployment_binding`,
without opening adapters or executing the changing pipeline.

- Actual new Settings row parser accepted for the local-fixture backend.
- Original acquisition parser still refused at ETL boundary.
- Fixture row parser refused when `fixture=False`; production parser accepted.
- Only parser_version differs in complete normalized settings.
- Actual deployment binding equal for the same local root.
- Both CLI examples and reader example select the new actual file.
- Original acquisition bytes equal both before receipt and read-only primary.

Acquisition before/after: **1,397 bytes**, SHA256
`dd50a930e09e840d38109e0953b4b9e0cc1ff3253845d8649d9242fc63192a3a`.
New ETL file: **1,401 bytes**, SHA256
`b96a00a21fdb58f851d26e82509f7967e70760d7b193d5aebe81ceec22a4f173`.
Normalized ETL settings SHA256:
`017bc4992404b2849e530e2c59939a0d719bae3db941e285e9c73bd7abe5ec7a`.
Scoped staged whitespace check exited **0**. Postcommit path-list and acquisition
byte checks passed. These are configuration/documentation checks, not a claim
that the documented pipeline sequence has passed.

## Pending mandatory sequence and combined proof

Wait for the code worker's green result and commit. Then seed a fresh explicit
local raw snapshot workset using real Source/Binding/snapshot workset codecs
(the existing `support_etl.seed_snapshot` fixture helper is suitable), with valid
selected-family original bytes and the unchanged acquisition provenance. Substitute
that actual base path, snapshot reference and a valid future UTC deadline into
the documented transform command using `conf/sec-edgar-etl-fixture.yaml`; pass its
actual transformed reference to the documented publish command with the same
configuration. This actual transform → publish sample is mandatory before M1 can
be called fully verified. No fixture-pack or live collection is needed for ETL.

Controller will dispatch the subsequent turn for that sample and one combined
full check, sequence and isolated installed-wheel proof. New tracked proof will
use `specs/evidence/sec-filing-index-ingestion/stage-3/final-review-fix1/` with its own
safe exact-coverage inventory. Existing frozen `verification/` and its 7,525-record
inventory remain byte-for-byte unchanged; its HEAD3c proof is historical. The
package README changed, so the later wheel build/proof must cover its current
metadata as well as the stabilized production code.

No broad/full check, installed proof, specimen rerun or pipeline sequence was run
in this preparation turn. The retained 51-conflict source-acceptance blocker
remains; all 22 Stage 7 integrated checks remain reserved. Live SEC, Azure,
authentication, compute, provisioning, deployment and image-build authorization
remain closed. No completion stamp, retirement, integration or cleanup.
