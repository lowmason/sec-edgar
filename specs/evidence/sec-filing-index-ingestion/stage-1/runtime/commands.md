# Task 4 exact isolated probe commands

The accepted ACR quick-task exception replaces local Docker execution. Inputs are copied into `/evidence`, root-owned with read-only file/directory modes; the probe runs as UID 1000 with an isolated writable virtual environment and `/out`. No host bind occurs. Input hashes are checked before and after successful execution. This is investigation evidence, not a worker/release build or publication.

Public metadata is retained from Docker Hub official `library/python` and PyPI; `public-metadata/receipts.json` records canonical URLs, status, response headers, sanitized final URLs, byte counts, timestamps and body hashes. Python 3.14.8 slim-bookworm index digest is `sha256:c8137f4c460908c8763f281c8f22c431eb5c538514ba9553fc3a89c06b7cfb88`; Linux amd64 child is `sha256:d1e795fbdab8a4744432467f32f348c6baa99f07abc05ffde710913f65c8261d`. Registry/config hashes and Linux/amd64 metadata were checked against raw bytes. Docker/buildx are unavailable, so registry protocol inspection under the accepted facility exception supplies immutable manifest evidence; no `imagetools` success is claimed.

The resolver context is generated with:

```sh
python3 specs/evidence/sec-filing-index-ingestion/stage-1/runtime/prepare_context.py resolve /private/tmp/sec-edgar-task4-resolve-02
```

Its upload allowlist is `results/sec-edgar-task4-resolve-02-allowlist.json`. The following proposed CLI argv was retained but rejected by Azure CLI 2.90.0 before upload/submission (exit 2; zero tasks). It is superseded by the reviewed SDK launcher below:

```sh
az acr build --subscription 3c92a216-8ed6-4897-b741-11ed287b8617 --registry secedgarstage1probe20261005b8617 --resource-group rg-sec-edgar-stage1-probe-20261005 --platform linux/amd64 --cpu 2 --timeout 1800 --no-cache --no-push --file Dockerfile /private/tmp/sec-edgar-task4-resolve-02
```

Expanded subprocess argv, start/end UTC, stdout/stderr and exit codes are written independently under `/out`. The launcher installs `pip==26.2.1` with its selected PyPI wheel SHA-256 from `installer.lock`; resolver dry-run and downloads require binary wheels. The resolver writes exact transitive `requirements.lock`, selected-wheel `dependency-matrix.csv`, pip JSON resolver report and each downloaded wheel's `WHEEL`/`METADATA` bytes. Downloaded wheels are individually SHA-256 verified against the lock. No source build is implied. Wheel bytes remain ephemeral; exact metadata/hashes/source URLs are retained.

Root retains complete ACR output/logs and terminal run status. The bounded `TASK4_BEGIN`/numbered `TASK4_CHUNK`/`TASK4_END` stdout frame exports `/out` as tar.gz/base64 with at most 4,096 base64 characters per chunk. The whole bundle SHA-256, size, complete numbered chunk set and end marker must verify. Extraction uses `extract_artifacts.py LOGFILE NEW_RESULT_DIRECTORY`, rejecting absolute/traversal/duplicate names, links, excessive expansion and hash mismatch. Failures are exported by the launcher as `failure.txt` and `overall.json`, with command output preserved where completed. An unknown submitted run must be reconciled before any retry; it consumes the shared four-run maximum.

After retaining and verifying the resolver artifacts, copy its lock/matrix to the runtime evidence directory and prepare a new validation context:

```sh
python3 specs/evidence/sec-filing-index-ingestion/stage-1/runtime/prepare_context.py validate /private/tmp/sec-edgar-task4-validate-01
```

Validation uses the same submission argv with the reviewed validation context path substituted. A second independently prepared `validate-02` context requires a second uncached submission and fresh venv. Neither validation reuses the resolver environment or downloaded wheel directory. Each contains the matrix and nine unique original specimen files corresponding to ten receipts. It runs hash-required install, pip check/inspect/debug, the unchanged brief core probe, separate offline Requests import, five per-receipt `python -m zipfile -t` commands, and bounded native decoding for every selected receipt with original/decoded hash, exact length, strict ASCII and newline verification. Each ZIP complete read checks CRC; plain IDX explicitly needs no archive decoder. Optional unselected codecs remain unsupported.

Execution is limited to four sequential submitted quick tasks including failures/cancellations; each uses Linux amd64, CPU 2, timeout 1800, no cache and no push. USD 5 is an operational budget, not an Azure enforcement control. Cleanup of the exact temporary registry/group is mandatory by 2026-10-06T23:50:30.922520+00:00 and immediately after retained-proof review. Root inventories before group deletion and stops if unexpected resources appear. No SEC access, credential use inside the probe, production publication, worker fit measurements or later-stage planning is authorized.

Prerun/final actual receipts and tool-version records will be linked in the Task 4 report. Planned argv here is not execution evidence.

## Observed submission failures and supported method

The CLI parse failure is retained under `results/acr-run-01-resolve-*`; it consumed zero tasks. Installed current task SDK serialization proves explicit `agent_configuration=AgentProperties(cpu=2)`, `no_cache=True`, `is_push_enabled=False`, `timeout=1800`, and `PlatformProperties(os=Linux, architecture=amd64)`. The standalone controller `submit_acr_probe.py` performs allowlist/hash verification, transient upload, one scheduling call with zero retries, and immediate selective run-ID receipt persistence. `sdk-method.json` distinguishes current installed publisher source from the accessible older official REST reference. No SAS/token or full returned model is printed.

Actual ordinal 1 (`ca1`) failed in the ACR dependency scanner before Docker execution because it rejected the first-line `FROM --platform=linux/amd64` form. Its original context, request/submission receipt, ordinary cloud log and terminal CPU/platform/status remain retained under `results/acr-sdk-resolve-01`. No resolver/install output was produced. The failure counts against the four actual-run limit.

Frozen `/private/tmp/sec-edgar-task4-resolve-03` differs from frozen `resolve-02` only by removing the FROM platform option. The exact Linux amd64 child digest remains in FROM and Linux amd64 is explicit in the SDK request. Its nine-file/13,943-byte allowlist records this precise correction; no general scanner grammar support is asserted. Root reviews this context before ordinal 2:

```sh
/opt/homebrew/Cellar/azure-cli/2.90.0/libexec/bin/python specs/evidence/sec-filing-index-ingestion/stage-1/runtime/submit_acr_probe.py --context /private/tmp/sec-edgar-task4-resolve-03 --allowlist specs/evidence/sec-filing-index-ingestion/stage-1/runtime/results/sec-edgar-task4-resolve-03-allowlist.json --receipt-dir specs/evidence/sec-filing-index-ingestion/stage-1/runtime/results/acr-sdk-resolve-02 --ordinal 2
```

After ordinal 2 succeeds, exactly ordinals 3 and 4 remain for the two separate fresh validation tasks. Any additional actual failure blocks successful completion within the accepted limit. Logs/status retrieval is root-only and uses selective metadata plus ordinary task log capture with sanitized exceptions. Every unknown schedule outcome must be reconciled before any replay.

Ordinal 2 (`ca2`) succeeded; its 60 exported artifacts, lock/matrix/downloaded-wheel metadata, pip26.2.1 and Python3.14.8/glibc2.36 observations are retained at `results/resolve-02-artifacts`. Exact lock SHA-256 is `523b2da36079ce4a7c6b11ac06feb0a7992a8c3aef757c32909850685023b5c2`. Resolver-only success is not installation proof.

Frozen validation contexts01/02 each have22files/13,463,797bytes and matching distinct allowlists. Both offline prepare-only serializations pass. Root reviews/submits sequentially:

```sh
/opt/homebrew/Cellar/azure-cli/2.90.0/libexec/bin/python specs/evidence/sec-filing-index-ingestion/stage-1/runtime/submit_acr_probe.py --context /private/tmp/sec-edgar-task4-validate-01 --allowlist specs/evidence/sec-filing-index-ingestion/stage-1/runtime/results/sec-edgar-task4-validate-01-allowlist.json --receipt-dir specs/evidence/sec-filing-index-ingestion/stage-1/runtime/results/acr-sdk-validate-01 --ordinal 3
```

Only after its terminal outcome is retained and verified, ordinal4 uses:

```sh
/opt/homebrew/Cellar/azure-cli/2.90.0/libexec/bin/python specs/evidence/sec-filing-index-ingestion/stage-1/runtime/submit_acr_probe.py --context /private/tmp/sec-edgar-task4-validate-02 --allowlist specs/evidence/sec-filing-index-ingestion/stage-1/runtime/results/sec-edgar-task4-validate-02-allowlist.json --receipt-dir specs/evidence/sec-filing-index-ingestion/stage-1/runtime/results/acr-sdk-validate-02 --ordinal 4
```

Both use the same immutable official base child digest/pip installer pin/hash lock and fresh isolated venvs; copied evidence remains read-only. Every locked distribution is version-checked and imported offline, including explicit cryptography Rust/cffi native bindings. The lock/matrix remain unchanged throughout inputs; final runtime matrix status may be updated only after both validations succeed, retaining resolver/context versions. No fifth actual task is permitted.

## Retained completion

Ordinals3/4 (`ca3`/`ca4`) both succeeded independently. All15 subprocess commands in each exit0. Exact versions/imports/pipcheck/pipinspect/pipdebug/syntheticParquet/per-receiptZIPtest/tenboundeddecodes and inputunchanged checks pass. `results/final-runtime-verification.command.json` exits0 against158exportedartifacthashes, the actual21-distribution lock/matrix and both fresh output sets. `results/root-native-output-verification.json` retains independent root verification. The complete four-task allowance is exhausted; no fifth task or replay is permitted. The final matrix names ca3/ca4 support; resolver/pre-validation matrix bytes remain retained separately. Root retains cleanup proof and shared evidence-register/reference checks. These compatibility outputs confer no production/service/performance authority.

Temporary cleanup is complete: registrydeleteexit0 at00:49:07.132523UTC, emptygroupdeleteexit0 at00:50:34.942599UTC, exactgroup/registryabsenceverified00:51:14.960875UTC. `probe-setup/cleanup-summary.json` and ten hash-verified receipts retain actual inventory/deletion/absence proof. Provider registration remains; actual billedcost was not queried. This evidence cannot authorize further tasks after the exhaustedfourrunallowance.
