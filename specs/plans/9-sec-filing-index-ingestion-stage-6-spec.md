# SEC filing-index ingestion — Stage 6 worker image and operator surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the worker and operator commands everything Azure needs: the worker identity, a read-only operator open with principal attribution and activation records, `history`, config and execution ID from the environment, alerting telemetry, the rendered Azure config, and a locally built Linux amd64 image proven to run every command.

**Architecture:** This is the first of the two Stage 6 plans (roadmap `specs/sec-filing-index-ingestion-roadmap.md`, Stage 6). It changes the `sec_edgar_ingest` package and adds `infra/azure/sec-edgar-ingest/{config,image}`. Plan 10 builds the Bicep, ADF and alert definitions against what this plan ships. **This plan does not tick Stage 6; Plan 10 carries the stage stamp.** Credentials are selected per command class. Operator opens verify the binding registry and never write it. Every new Azure behaviour is exercised through pinned-SDK mocked transports, and the local backend stays in step.

**Tech Stack:** Python ≥3.14, unittest under `tests/network_guard.py`, azure-identity 1.26.0 (`ManagedIdentityCredential`, `AzureCliCredential`), azure-storage-blob 12.31.0, uv 0.12.15 (offline, frozen), Docker Engine with buildx on Colima (Rosetta amd64 emulation).

**Spec:** `specs/sec-filing-index-ingestion-stage-6-spec.md` (APPROVED 2026-10-12). Sections §3–§6, §7.1 (execution ID), §7.3 (content type), §8 (worker telemetry), §11 and §12 rows marked 9.

## Global Constraints

Copied verbatim from spec §2:

- The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.
- Use managed identities for ADF management calls and worker access to Azure resources.
- Pin and review permissions; do not place storage keys in worksets or source URLs.
- Production deployment pins the image digest and configuration revision.
- All commands emit structured logs with run, execution, attempt, source and generation identifiers.
- Report discovery age, oldest listed-but-unpublished source and last successful reconciliation separately.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.
- **Python and SDKs:** Python **>=3.14**, Requests **2.34.2**, Identity **1.26.0**, Blob **12.31.0** / **2026-04-06**, Tables **12.7.0** / **2020-12-06**, PyArrow **25.0.1**, and the existing `uv.lock`. No dependency is added; `AzureCliCredential` ships in Identity 1.26.0.
- **F1 §4 runtime:** base `python:3.14.8-slim-bookworm`, Linux amd64 child `sha256:d1e795fbdab8a4744432467f32f348c6baa99f07abc05ffde710913f65c8261d`; lock SHA-256 `523b2da36079ce4a7c6b11ac06feb0a7992a8c3aef757c32909850685023b5c2`.
- **Tools:** CLI **2.90.0**, Bicep **0.38.33**, uv **0.12.15**.
- Existing config, workset and binding-registry bytes are never rewritten. All 22 Stage 7 integrated checks remain reserved/not_run.

From spec §1, §3 and §14:

- The work is offline: no SEC, Azure management or data-plane, credential, deployment or trigger activity. D1 authorizes local tool installs only.
- `FROM --platform` is never used. The platform is a `docker buildx` CLI flag, never a Dockerfile line.
- The local image digest is never recorded as a release digest.
- Lean process: red/green TDD and a review per task, a final whole-branch review, and at plan exit the full offline suite, a wheel build and a CLI smoke test.

Leave alone: `specs/evidence/**` (read-only; Task 10 copies one file *from* it), the accepted F1 bytes, `specs/sec-filing-index-ingestion-stage-4-spec.md`, `specs/plans/4-…`, `specs/plans/5-…`, everything under `specs/plans/completed/`, the historical roadmap sections, and deferred items not bound to Stage 6.

**Conventions used below.** Run every command from the repository root `/Users/lowell/Projects/sec-edgar`. One test module runs with:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py <module> -v
```

`tests/network_guard.py` blocks sockets and makes every `azure.identity` credential constructor and `get_token` raise. Tests must therefore patch the credential names in `sec_edgar_ingest.storage.azure` (as `tests/test_azure_contracts.py` already does), never build a real credential. Every commit message ends with:

```text
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## Decisions

- **D1** (owner, brief, 2026-10-12): "Local build, Stage 6 only. Install a local container runtime with buildx (amd64 emulation) and Bicep 0.38.33. These are tool installs only, with no Azure or SEC calls. The local image proves the commands run; the release image is still built by ACR quick task in Stage 7 (S7-05), so its digest will differ." Applied in: Task 10, Task 11 (Bicep goes to Plan 10). Home: spec §14.
- **D2** (owner, brief, 2026-10-12): a short Stage 6 spec with an owner-decisions section before the plan. Applied in: the spec (approved 2026-10-12). Home: spec §14.
- **D3** (owner, spec review, 2026-10-12): "Approved — write both plans". This approves the spec, Q1–Q4 and its twelve defaults, including two plans at the §13 seam (this plan has no `Roadmap:` line), the §1 deferred-item scope, and Plan 10's offline checks. Applied in: all tasks; Global Constraints.

Settled for the owner's review at plan approval:

1. **Two plans** (brief default 1): this plan is the worker and operator half; Plan 10 carries the stage stamp.
2. **Deferred-item scope** (brief default 2): `history` (Task 5), attribution and re-activation (Tasks 3–4) and the mistyped path (Tasks 2–3). Completing this plan ticks those three items in `specs/deferred_items.md`.
3. **Offline checks** (brief default 3): Plan 10's subject; this plan supplies the contracts those checks read.
4. **Network during the image build (reading of D1).** `docker buildx build` pulls the pinned base image by digest from Docker Hub, and pip fetches the 21 hash-pinned wheels from PyPI. Neither is an Azure or SEC call. Nothing else touches the network, and the smoke runs with `--network none`.
5. **Base reference (spec amendment, Task 9).** The Dockerfile uses `FROM docker.io/library/python@sha256:d1e795fb…`, the exact reference F1's successful quick task used, not `python:3.14.8-slim-bookworm@sha256:…`. F1 asserted no wider scanner grammar.

---

## File map

| File | Responsibility | Task |
|---|---|---|
| `src/sec_edgar_ingest/storage/identity.py` (new) | Environment names, worker client ID, operator token principal | 1 |
| `src/sec_edgar_ingest/storage/azure.py` | `worker_credential`, `operator_credential`, JSON content type, operator open | 1, 2 |
| `src/sec_edgar_ingest/storage/contracts.py` | `StoreMissing`, `ApprovalActivation` routing | 2, 4 |
| `src/sec_edgar_ingest/storage/local.py` | `create=False` verify-only constructors | 2 |
| `src/sec_edgar_ingest/storage/__init__.py` | `open_stores(..., access, credential)` | 2 |
| `src/sec_edgar_ingest/cli.py` | client-ID gate, operator identity, `history`, `--config-env`, execution ID, summary hook | 1, 3, 5, 6, 7 |
| `src/sec_edgar_ingest/etl/contracts.py`, `etl/state.py`, `etl/approval.py` | Activation record, index and write-ahead store | 4 |
| `src/sec_edgar_ingest/config.py` | `parse_config`, `load_config_env` | 6 |
| `src/sec_edgar_ingest/workflows/summary.py` (new) | `workflow_summary` fields and the reconcile milestone | 7 |
| `src/sec_edgar_ingest/deployment.py` (new) | Azure config renderer and ARM parameters | 8 |
| `infra/azure/sec-edgar-ingest/config/*` (new) | Azure config template, golden binding | 8 |
| `infra/azure/sec-edgar-ingest/image/*` (new) | Dockerfile, `requirements.lock` | 10 |
| `scripts/build-image-context.sh` (new) | Build context assembly | 10 |
| `tests/image_smoke.py` (new) | Container smoke of every command | 11 |
| `tests/support_azure.py`, `tests/support_scenario.py` (new) | Azure settings, JWT and credential fakes; scenario packs | 1, 7 |
| `docs/runbooks/sec-edgar-reconciliation-approval.md`, `packages/sec-edgar-ingest/README.md` | Operator docs | 4, 5, 6 |
| `scripts/check-sec-edgar-ingest.sh` | Help for every command | 12 |

Test paths below are under `packages/sec-edgar-ingest/tests/`; source paths under `packages/sec-edgar-ingest/src/sec_edgar_ingest/`.

---

### Task 1: Worker identity, operator credential and the JSON content type

**Files:**
- Create: `src/sec_edgar_ingest/storage/identity.py`
- Create: `tests/support_azure.py`
- Create: `tests/test_azure_identity.py`
- Modify: `src/sec_edgar_ingest/storage/azure.py` (imports; `_upload` at lines 248–258; `open_azure_stores` at 509–530)
- Modify: `src/sec_edgar_ingest/cli.py` (imports; `_validate` Azure branch at lines 133–136)
- Modify: `tests/test_azure_contracts.py` (`test_factory_conditions_fixed_registry_before_authority_clients`, lines 339–375)

**Interfaces:**
- Produces:
  - `storage.identity`: `WORKER_CLIENT_ID_ENV = 'SEC_EDGAR_INGEST_WORKER_CLIENT_ID'`, `EXECUTION_NAME_ENV = 'CONTAINER_APP_JOB_EXECUTION_NAME'`, `OPERATOR_TOKEN_SCOPE = 'https://storage.azure.com/.default'`, `worker_client_id(environ: Mapping[str, str]) -> str` and `principal_from_token(token: str) -> str`. Both raise `ValueError`.
  - `storage.azure`: `worker_credential()`, `operator_credential()`, and `open_azure_stores(settings, *, observer=None, credential=None)`.
  - Test support `support_azure`: `TENANT_ID`, `OBJECT_ID`, `WORKER_CLIENT_ID`, `AZURE_STORAGE`, `azure_settings(**overrides) -> Settings`, `write_azure_config(path) -> Path`, `jwt(**claims) -> str`, `FakeCredential(token)`, `FailingCredential()`.

- [ ] **Step 1: Write the test support module**

`tests/support_azure.py`:

```python
"""Azure settings, operator tokens and credential fakes for offline identity tests."""
import base64
import json
from pathlib import Path

from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError

from support import fixture_settings

BLOB_ENDPOINT = "https://secedgardevb8617.blob.core.windows.net"
TABLE_ENDPOINT = "https://secedgardevb8617.table.core.windows.net"
TENANT_ID = "11111111-1111-4111-8111-111111111111"
OBJECT_ID = "22222222-2222-4222-8222-222222222222"
WORKER_CLIENT_ID = "33333333-3333-4333-8333-333333333333"
AZURE_STORAGE = {"backend": "azure", "root": None, "account_name": "secedgardevb8617",
                 "blob_endpoint": BLOB_ENDPOINT, "table_endpoint": TABLE_ENDPOINT,
                 "raw_container": "raw", "workset_container": "worksets", "quarantine_container": "quarantine",
                 "lock_container": "locks", "lock_blob": "sec-owner-lowell-mason/sentinel.json",
                 "binding_registry_blob": "sec-owner-lowell-mason/binding.json"}


def azure_settings(**overrides):
    """A valid Azure configuration: the legal parser and a configured, non-fixture image."""
    return fixture_settings(storage=AZURE_STORAGE, etl={"parser_version": "sec-index-parser-v1"},
                            worker={"image_digest": "sha256:" + "1" * 64, "provenance": "configured-image"},
                            **overrides)


def write_azure_config(path: Path) -> Path:
    from sec_edgar_ingest.models import canonical_json, to_mapping_value
    path.write_bytes(canonical_json(to_mapping_value(azure_settings().to_mapping())))
    return path


def jwt(**claims) -> str:
    """An unsigned token with these claims; attribution decodes without verifying the signature."""
    def part(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()
    return part({"alg": "RS256", "typ": "JWT"}) + "." + part(claims) + ".offline-signature"


class FakeCredential:
    """Stands in for AzureCliCredential; records the scopes each token was requested for."""

    def __init__(self, token: str):
        self.token, self.scopes = token, []

    def get_token(self, *scopes, **kwargs):
        self.scopes.append(scopes)
        return AccessToken(self.token, 4102444800)


class FailingCredential:
    def get_token(self, *scopes, **kwargs):
        raise ClientAuthenticationError("Please run 'az login' to set up an account")
```

- [ ] **Step 2: Write the failing tests**

`tests/test_azure_identity.py`:

```python
"""Worker identity selection, operator token attribution and the Azure JSON content type."""
from network_guard import install
install()

import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from azure.storage.blob import BlobServiceClient

from support_azure import OBJECT_ID, TENANT_ID, WORKER_CLIENT_ID, jwt, write_azure_config
from test_azure_contracts import BLOB_ENDPOINT, RETRY, ScriptedTransport, response
from sec_edgar_ingest.cli import main
from sec_edgar_ingest.storage.contracts import Conflict
from sec_edgar_ingest.storage.identity import WORKER_CLIENT_ID_ENV, principal_from_token, worker_client_id

PRINCIPAL = f"entra:{TENANT_ID}/{OBJECT_ID}"


class WorkerClientIdTests(unittest.TestCase):
    def test_requires_one_exact_guid(self):
        self.assertEqual(worker_client_id({WORKER_CLIENT_ID_ENV: WORKER_CLIENT_ID}), WORKER_CLIENT_ID)
        for value in (None, "", " ", WORKER_CLIENT_ID + " ", "not-a-guid", WORKER_CLIENT_ID + "\n"):
            environ = {} if value is None else {WORKER_CLIENT_ID_ENV: value}
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, WORKER_CLIENT_ID_ENV):
                worker_client_id(environ)


class PrincipalTests(unittest.TestCase):
    def test_records_tenant_object_and_user_name(self):
        self.assertEqual(principal_from_token(jwt(tid=TENANT_ID, oid=OBJECT_ID, upn="lowell@example.com")),
                         PRINCIPAL + " lowell@example.com")
        self.assertEqual(principal_from_token(jwt(tid=TENANT_ID, oid=OBJECT_ID, preferred_username="lm@example.com")),
                         PRINCIPAL + " lm@example.com")
        self.assertEqual(principal_from_token(jwt(tid=TENANT_ID, oid=OBJECT_ID)), PRINCIPAL)

    def test_drops_a_name_that_is_not_one_bounded_printable_line(self):
        for name in ("two\nlines", " padded", "x" * 300, "", 7):
            with self.subTest(name=name):
                self.assertEqual(principal_from_token(jwt(tid=TENANT_ID, oid=OBJECT_ID, upn=name)), PRINCIPAL)

    def test_refuses_a_token_without_tenant_and_object_ids(self):
        for token in ("not-a-jwt", "a.b", "a.!!!.c", jwt(tid=TENANT_ID), jwt(oid=OBJECT_ID),
                      jwt(tid="tenant", oid=OBJECT_ID)):
            with self.subTest(token=token), self.assertRaises(ValueError):
                principal_from_token(token)


class AzureCredentialTests(unittest.TestCase):
    def setUp(self):
        from sec_edgar_ingest.storage import azure
        self.azure = azure

    def test_worker_credential_selects_the_worker_identity_by_client_id(self):
        with patch.object(self.azure, "ManagedIdentityCredential") as credential, \
                patch.dict(os.environ, {WORKER_CLIENT_ID_ENV: WORKER_CLIENT_ID}):
            self.assertIs(self.azure.worker_credential(), credential.return_value)
        credential.assert_called_once_with(client_id=WORKER_CLIENT_ID)

    def test_worker_credential_refuses_a_missing_client_id_before_construction(self):
        with patch.object(self.azure, "ManagedIdentityCredential") as credential, patch.dict(os.environ):
            os.environ.pop(WORKER_CLIENT_ID_ENV, None)
            with self.assertRaisesRegex(ValueError, WORKER_CLIENT_ID_ENV):
                self.azure.worker_credential()
        credential.assert_not_called()

    def test_operator_credential_is_the_azure_cli_sign_in(self):
        with patch.object(self.azure, "AzureCliCredential") as credential:
            self.assertIs(self.azure.operator_credential(), credential.return_value)
        credential.assert_called_once_with()

    def test_json_objects_upload_with_the_json_content_type(self):
        transport = ScriptedTransport([response(201), response(201)])
        service = BlobServiceClient(BLOB_ENDPOINT, api_version="2026-04-06", transport=transport, **RETRY)
        self.addCleanup(service.close)
        objects = self.azure.AzureObjectStore(service)
        objects.put_once("runs/sec/r/backfill/a/result.json", b"{}")
        objects.put_once("runs/sec/r/backfill/a/notes.txt", b"x")
        self.assertEqual(transport.requests[0].headers.get("x-ms-blob-content-type"), "application/json")
        self.assertNotEqual(transport.requests[1].headers.get("x-ms-blob-content-type"), "application/json")


class WorkerGateCliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.config = write_azure_config(Path(temp.name) / "azure.json")
        deadline = (datetime.now(timezone.utc) + timedelta(seconds=1800)).isoformat()
        self.argv = ["discover", "--config", str(self.config), "--run-id", "r", "--execution-id", "e",
                     "--attempt-id", "a", "--deadline", deadline, "--mode", "quarterly", "--discovery-id", "d"]

    def invoke(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(self.argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_azure_stage_commands_require_the_worker_client_id_before_any_io(self):
        with patch.dict(os.environ), \
                patch("sec_edgar_ingest.cli.open_stores", side_effect=AssertionError("opened stores")):
            os.environ.pop(WORKER_CLIENT_ID_ENV, None)
            code, stdout, stderr = self.invoke()
        self.assertEqual((code, stdout), (2, ""))
        self.assertEqual(json.loads(stderr.splitlines()[-1])["outcome"], "configuration")

    def test_azure_stage_commands_keep_their_execution_id(self):
        # Workflow children pass --execution-id in process on Azure; only workflow commands refuse it (Task 6).
        with patch.dict(os.environ, {WORKER_CLIENT_ID_ENV: WORKER_CLIENT_ID}), \
                patch("sec_edgar_ingest.cli.open_stores", side_effect=Conflict("validation passed")) as opened:
            code, stdout, _ = self.invoke()
        self.assertEqual((code, json.loads(stdout)["outcome"]), (9, "state_conflict"))
        opened.assert_called_once()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_identity -v`
Expected: ERROR at import with `ModuleNotFoundError: No module named 'sec_edgar_ingest.storage.identity'`.

- [ ] **Step 4: Implement `storage/identity.py`**

```python
"""Azure identity inputs and operator attribution, without constructing SDK clients."""
from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping

WORKER_CLIENT_ID_ENV = "SEC_EDGAR_INGEST_WORKER_CLIENT_ID"
EXECUTION_NAME_ENV = "CONTAINER_APP_JOB_EXECUTION_NAME"
OPERATOR_TOKEN_SCOPE = "https://storage.azure.com/.default"
MAX_PRINCIPAL_CHARS = 256
GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z")


def worker_client_id(environ: Mapping[str, str]) -> str:
    """The worker UAMI's client ID, which Bicep sets on the job container; required on Azure."""
    value = environ.get(WORKER_CLIENT_ID_ENV, "")
    if GUID.fullmatch(value) is None:
        raise ValueError(f"{WORKER_CLIENT_ID_ENV} must hold the worker managed identity client ID")
    return value


def principal_from_token(token: str) -> str:
    """`entra:<tid>/<oid>`, plus the token's user name when it is one bounded printable line.

    The token is decoded without signature verification: Entra has just issued it to this
    process. Attribution is evidence; RBAC still authorizes every write.
    """
    try:
        _, payload, _ = token.split(".")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("operator token is not a decodable JWT") from error
    if not isinstance(claims, dict):
        raise ValueError("operator token claims must be an object")
    tid, oid = claims.get("tid"), claims.get("oid")
    if not all(isinstance(value, str) and GUID.fullmatch(value) for value in (tid, oid)):
        raise ValueError("operator token lacks tenant and object identifiers")
    principal = f"entra:{tid}/{oid}"
    name = claims.get("upn") or claims.get("preferred_username")
    if (isinstance(name, str) and name == name.strip() and name.isprintable()
            and len(principal) + 1 + len(name) <= MAX_PRINCIPAL_CHARS):
        principal += " " + name
    return principal
```

- [ ] **Step 5: Implement the Azure adapter changes**

In `storage/azure.py`:
- Add `import os`.
- Replace `from azure.identity import ManagedIdentityCredential` with `from azure.identity import AzureCliCredential, ManagedIdentityCredential`.
- Replace `from azure.storage.blob import BlobLeaseClient, BlobServiceClient` with `from azure.storage.blob import BlobLeaseClient, BlobServiceClient, ContentSettings`.
- Add `from .identity import worker_client_id` after the `.contracts` import.

Replace `_upload` with:

```python
    def _upload(self, path: str, stream, sha256: str, byte_count: int) -> str:
        blob = self._blob(path)
        # ADF reads JSON results as parsed output only when the blob is typed JSON (S7-09).
        options = {"content_settings": ContentSettings(content_type="application/json")} if path.endswith(".json") else {}
        observe(self.observer, "object.before_upload")
        try:
            blob.upload_blob(stream, length=byte_count, overwrite=False, match_condition=MatchConditions.IfMissing,
                             **options)
        except (ResourceExistsError, ResourceModifiedError) as error:
            if error.status_code not in (409, 412):
                raise
            self.verify(path, sha256, byte_count)
        observe(self.observer, "object.after_upload")
        return path
```

Insert before `open_azure_stores`:

```python
def worker_credential() -> ManagedIdentityCredential:
    """The job's user-assigned worker identity, selected by client ID; never the system identity."""
    return ManagedIdentityCredential(client_id=worker_client_id(os.environ))


def operator_credential() -> AzureCliCredential:
    """The operator's own `az login`; operator commands never fall back through a credential chain."""
    return AzureCliCredential()
```

In `open_azure_stores`, change the signature to `def open_azure_stores(settings: Settings, *, observer: BoundaryObserver | None = None, credential=None):` and replace `credential = ManagedIdentityCredential()` with `credential = credential if credential is not None else worker_credential()`.

- [ ] **Step 6: Gate Azure stage commands on the client ID**

In `cli.py` add `import os` and `from .storage.identity import worker_client_id`. In `_validate`, replace:

```python
    if settings.storage.backend == 'azure':
        if getattr(args, 'fixture_pack', None) or args.state_dir or args.today:
            raise ValueError('fixture pack, state directory and date override are fixture-only')
        pack = None
```

with:

```python
    if settings.storage.backend == 'azure':
        if getattr(args, 'fixture_pack', None) or args.state_dir or args.today:
            raise ValueError('fixture pack, state directory and date override are fixture-only')
        worker_client_id(os.environ)
        pack = None
```

- [ ] **Step 7: Update the pinned factory test**

In `tests/test_azure_contracts.py`, add `import os` to the imports and `from support_azure import WORKER_CLIENT_ID` after the `support` import, and add `from sec_edgar_ingest.storage.identity import WORKER_CLIENT_ID_ENV` inside the test. In `test_factory_conditions_fixed_registry_before_authority_clients`:
- Wrap both `with patch.object(self.azure, "ManagedIdentityCredential") …` blocks in `with patch.dict(os.environ, {WORKER_CLIENT_ID_ENV: WORKER_CLIENT_ID}):`.
- Replace `credential.assert_called_once_with()` with `credential.assert_called_once_with(client_id=WORKER_CLIENT_ID)`.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_identity test_azure_contracts -v`
Expected: PASS, all tests.

- [ ] **Step 9: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/identity.py packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/support_azure.py packages/sec-edgar-ingest/tests/test_azure_identity.py packages/sec-edgar-ingest/tests/test_azure_contracts.py
git commit -m "feat(ingest): select the worker identity by client ID and type JSON objects

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Verify-only operator store open on both backends

**Files:**
- Modify: `src/sec_edgar_ingest/storage/contracts.py` (add `StoreMissing` after `ClockUncertain`)
- Modify: `src/sec_edgar_ingest/storage/local.py` (`LocalObjectStore.__init__` lines 30–38; `LocalStateStore.__init__` lines 153–177)
- Modify: `src/sec_edgar_ingest/storage/azure.py` (`open_azure_stores`)
- Modify: `src/sec_edgar_ingest/storage/__init__.py`
- Modify: `tests/support_approval.py` (add `tree_snapshot`)
- Create: `tests/test_operator_open.py`

**Interfaces:**
- Consumes: `open_azure_stores(settings, *, observer=None, credential=None)` and `worker_credential()` from Task 1.
- Produces:
  - `storage.contracts.StoreMissing(LookupError)`.
  - `open_stores(settings, *, base_path=None, observer=None, access='worker', credential=None)`. With `access='operator'` it returns `(state, objects, None)`: it never creates a root, schema, registry or lease. A missing store raises `StoreMissing`; a different registry raises `Conflict`.
  - `open_azure_stores(..., access='worker', credential=None)`.
  - `LocalObjectStore(root, *, observer=None, binding=None, create=True)` and `LocalStateStore(root, *, page_size=128, observer=None, binding=None, create=True)`.
  - `support_approval.tree_snapshot(root) -> dict[str, str]`.

- [ ] **Step 1: Add the snapshot helper**

Append to `tests/support_approval.py` (add `import hashlib` to its imports):

```python
def tree_snapshot(root: Path) -> dict[str, str]:
    """Every directory and file under root, files by content hash. SQLite's transient WAL files are
    excluded: a reader creates and removes them without changing stored state."""
    entries = {}
    for path in sorted(Path(root).rglob('*')):
        if path.name.endswith(('-wal', '-shm')):
            continue
        entries[str(path.relative_to(root))] = 'dir' if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest()
    return entries
```

- [ ] **Step 2: Write the failing tests**

`tests/test_operator_open.py`:

```python
"""Operator stores open verify-only: never a new root, schema, registry, container, table or lease."""
from network_guard import install
install()

import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from azure.storage.blob import BlobServiceClient

from support import fixture_settings
from support_approval import tree_snapshot
from support_azure import azure_settings
from test_azure_contracts import BLOB_ENDPOINT, RETRY, TABLE_ENDPOINT, ScriptedTransport, blob_error, response
from sec_edgar_ingest.storage import open_stores
from sec_edgar_ingest.storage.contracts import (REGISTRY_PATH, Conflict, StoreMissing, deployment_binding,
                                                payload_bytes)


class LocalOperatorOpenTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.settings = fixture_settings()
        self.root = self.base / self.settings.storage.root

    def worker_open(self):
        for resource in reversed(open_stores(self.settings, base_path=self.base)):
            resource.close()

    def operator_open(self, base=None):
        return open_stores(self.settings, base_path=base or self.base, access='operator')

    def test_a_missing_store_is_refused_and_nothing_is_created(self):
        for base in (self.base / 'typo', self.base):
            with self.subTest(base=base), self.assertRaises(StoreMissing):
                self.operator_open(base)
        self.assertEqual(list(self.base.iterdir()), [])

    def test_a_store_without_its_registry_or_database_is_refused_unchanged(self):
        for missing in (self.root / 'objects' / REGISTRY_PATH, self.root / 'state.sqlite3'):
            with self.subTest(missing=missing.name):
                self.worker_open()
                missing.unlink()
                before = tree_snapshot(self.base)
                with self.assertRaises(StoreMissing):
                    self.operator_open()
                self.assertEqual(tree_snapshot(self.base), before)

    def test_a_different_binding_is_a_conflict(self):
        self.worker_open()
        (self.root / 'objects' / REGISTRY_PATH).write_bytes(b'{"namespace":"other"}')
        with self.assertRaises(Conflict):
            self.operator_open()

    def test_an_existing_store_opens_without_writes_or_a_lease(self):
        self.worker_open()
        before = tree_snapshot(self.base)
        state, objects, leases = self.operator_open()
        self.assertIsNone(leases)
        self.assertIsNone(state.get('Candidate', 'a' * 64))
        self.assertEqual(objects.read(REGISTRY_PATH),
                         payload_bytes(deployment_binding(self.settings, root=self.root)))
        state.close()
        self.assertEqual(tree_snapshot(self.base), before)

    def test_access_must_be_worker_or_operator(self):
        with self.assertRaisesRegex(ValueError, 'worker or operator'):
            open_stores(self.settings, base_path=self.base, access='admin')


class AzureOperatorOpenTests(unittest.TestCase):
    def setUp(self):
        from sec_edgar_ingest.storage import azure
        self.azure = azure
        self.settings = azure_settings()
        self.binding = payload_bytes(deployment_binding(self.settings))

    @contextlib.contextmanager
    def factories(self, responses):
        transport = ScriptedTransport(responses)
        service = BlobServiceClient(BLOB_ENDPOINT, api_version='2026-04-06', transport=transport, **RETRY)
        self.addCleanup(service.close)
        with patch.object(self.azure, 'BlobServiceClient', return_value=service) as blobs, \
                patch.object(self.azure, 'TableServiceClient') as tables, \
                patch.object(self.azure, 'ManagedIdentityCredential', side_effect=AssertionError('worker identity')):
            tables.return_value.get_table_client.side_effect = lambda name: Mock(url=TABLE_ENDPOINT, table_name=name)
            yield transport, blobs, tables

    def test_operator_open_reads_the_registry_and_never_writes(self):
        credential = object()
        with self.factories([response(body=self.binding)]) as (transport, blobs, tables):
            state, objects, leases = self.azure.open_azure_stores(self.settings, access='operator',
                                                                  credential=credential)
        self.assertIsNone(leases)
        self.assertEqual([request.method for request in transport.requests], ['GET'])
        self.assertIs(blobs.call_args.kwargs['credential'], credential)
        self.assertIs(tables.call_args.kwargs['credential'], credential)
        self.assertEqual(state.approval_client.table_name, 'Approvals')

    def test_a_missing_registry_is_store_missing_before_any_table_client(self):
        with self.factories([blob_error(404, 'BlobNotFound')]) as (_, _, tables):
            with self.assertRaises(StoreMissing):
                self.azure.open_azure_stores(self.settings, access='operator', credential=object())
        tables.assert_not_called()

    def test_a_different_registry_is_a_conflict(self):
        with self.factories([response(body=b'{"namespace":"other"}')]) as (_, _, tables):
            with self.assertRaises(Conflict):
                self.azure.open_azure_stores(self.settings, access='operator', credential=object())
        tables.assert_not_called()

    def test_open_stores_passes_access_and_credential_to_azure(self):
        credential = object()
        with patch.object(self.azure, 'open_azure_stores', return_value=('s', 'o', None)) as opened:
            self.assertEqual(open_stores(self.settings, access='operator', credential=credential), ('s', 'o', None))
        self.assertEqual(opened.call_args.kwargs, {'observer': None, 'access': 'operator', 'credential': credential})


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_operator_open -v`
Expected: ERROR at import with `ImportError: cannot import name 'StoreMissing'`.

- [ ] **Step 4: Add `StoreMissing`**

In `storage/contracts.py`, after `class ClockUncertain`:

```python
class StoreMissing(LookupError):
    """An operator open found no store at the configured binding; nothing was created."""
```

- [ ] **Step 5: Add verify-only local constructors**

In `storage/local.py`, import `StoreMissing` from `.contracts`, and replace `LocalObjectStore.__init__` with:

```python
    def __init__(self, root: Path, *, observer: BoundaryObserver | None = None, binding=None, create: bool = True):
        self.root = Path(root).resolve()
        self.directory = self.root / "objects"
        self.observer = observer
        expected = payload_bytes(binding or deployment_binding(root=self.root))
        if not create:
            # Operator opens never mkdir or write: a write-once probe would still leave a temp file behind.
            if not self.directory.is_dir() or self.directory.is_symlink():
                raise StoreMissing(f"no local store exists at {self.root}")
            try:
                registry = self.read(REGISTRY_PATH)
            except FileNotFoundError as error:
                raise StoreMissing(f"local store at {self.root} has no deployment binding") from error
            if registry != expected:
                raise Conflict("local store binding differs from this deployment")
            return
        self.root.mkdir(parents=True, exist_ok=True)
        self.directory.mkdir(exist_ok=True)
        if self.directory.is_symlink():
            raise ValueError("object root must not be a symlink")
        self._write_once(REGISTRY_PATH, io.BytesIO(expected), notify=False)
```

In `LocalStateStore.__init__`, change the signature to `def __init__(self, root: Path, *, page_size: int = 128, observer: BoundaryObserver | None = None, binding=None, create: bool = True):`, change `LocalObjectStore(self.root, binding=binding)` to `LocalObjectStore(self.root, binding=binding, create=create)`, and insert immediately before `for attempt in range(SQLITE_INIT_ATTEMPTS):`:

```python
        if not create:
            if not self.database.is_file():
                raise StoreMissing(f"local store at {self.root} has no state database")
            return
```

- [ ] **Step 6: Add operator access to the Azure factory**

Replace `open_azure_stores` in `storage/azure.py` with:

```python
def open_azure_stores(settings: Settings, *, observer: BoundaryObserver | None = None, access: str = "worker",
                      credential=None):
    """Worker access writes the binding registry once; operator access only verifies it and takes no lease."""
    if access not in ("worker", "operator"):
        raise ValueError("store access must be worker or operator")
    validated = Settings.from_mapping(settings.to_mapping())
    if validated.storage.backend != "azure":
        raise ValueError("Azure factory requires validated Azure settings")
    if not validated.coordination.lease_seconds.is_integer():
        raise ValueError("Azure finite lease duration must use whole seconds")
    credential = credential if credential is not None else worker_credential()
    storage = validated.storage
    options = {**RETRY_OPTIONS, "connection_timeout": STORAGE_CONNECTION_TIMEOUT_SECONDS,
               "read_timeout": STORAGE_READ_TIMEOUT_SECONDS}
    blob_service = BlobServiceClient(account_url=storage.blob_endpoint, credential=credential,
                                    api_version=storage.blob_api_version, **options)
    objects = AzureObjectStore(blob_service, observer=observer)
    binding = payload_bytes(deployment_binding(validated))
    if access == "worker":
        objects.put_once(REGISTRY_PATH, binding)
    else:
        try:
            registry = objects.read(REGISTRY_PATH)
        except FileNotFoundError as error:
            raise StoreMissing("the configured Azure store has no deployment binding registry") from error
        if registry != binding:
            raise Conflict("the Azure deployment binding registry differs from this configuration")
    tables = TableServiceClient(endpoint=storage.table_endpoint, credential=credential,
                               api_version=storage.table_api_version, **options)
    state = AzureStateStore(tables.get_table_client(storage.source_table), tables.get_table_client(storage.attempt_table),
                            objects=objects, observer=observer, active_client=tables.get_table_client("ActivePointers"),
                            approval_client=tables.get_table_client("Approvals"))
    if access == "operator":
        return state, objects, None
    leases = AzureLeaseStore(blob_service, lease_seconds=int(validated.coordination.lease_seconds),
                             uncertainty_seconds=validated.coordination.clock_uncertainty_seconds, observer=observer)
    return state, objects, leases
```

Add `StoreMissing` to the `.contracts` import list in `storage/azure.py`.

- [ ] **Step 7: Route access through `open_stores`**

Replace `storage/__init__.py` with:

```python
"""Open one validated deployment's durable state, immutable objects and fixed lease."""
from pathlib import Path

from ..config import Settings
from .contracts import (AlreadyExists, ClockUncertain, Conflict, LeaseHandle, LeaseStore,
                        ObjectStore, OwnershipLost, StateStore, StoreMissing, BoundaryObserver, deployment_binding)


def open_stores(settings: Settings, *, base_path: Path | None = None, observer: BoundaryObserver | None = None,
                access: str = 'worker', credential=None) -> tuple[StateStore, ObjectStore, LeaseStore | None]:
    """Worker access creates and binds the store; operator access verifies an existing one and takes no lease."""
    if access not in ('worker', 'operator'):
        raise ValueError('store access must be worker or operator')
    validated = Settings.from_mapping(settings.to_mapping())
    if validated.storage.backend == "local-fixture":
        from .local import LocalLeaseStore, LocalObjectStore, LocalStateStore
        root = (base_path if base_path is not None else Path.cwd()) / validated.storage.root
        binding = deployment_binding(validated, root=root)
        if access == 'operator':
            state = LocalStateStore(root, observer=observer, binding=binding, create=False)
            return state, LocalObjectStore(root, observer=observer, binding=binding, create=False), None
        objects = LocalObjectStore(root, observer=observer, binding=binding)
        state = LocalStateStore(root, observer=observer, binding=binding)
        leases = LocalLeaseStore(root, observer=observer, binding=binding)
        return state, objects, leases
    from .azure import open_azure_stores
    return open_azure_stores(validated, observer=observer, access=access, credential=credential)
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_operator_open test_azure_contracts test_storage -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/storage packages/sec-edgar-ingest/tests/support_approval.py packages/sec-edgar-ingest/tests/test_operator_open.py
git commit -m "feat(ingest): open operator stores verify-only on both backends

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Operator identity and attribution in the CLI

**Files:**
- Modify: `src/sec_edgar_ingest/cli.py` (`_parser` approve/rollback at lines 91–101; `_operator_main` 459–484; `_approve_main`, `_candidates_main`, `_rollback_main` 487–512)
- Create: `tests/test_operator_identity.py`

**Interfaces:**
- Consumes: `operator_credential()`, `principal_from_token`, `OPERATOR_TOKEN_SCOPE` (Task 1); `open_stores(..., access, credential)` and `StoreMissing` (Task 2); test support `FakeCredential`, `FailingCredential`, `jwt`, `write_azure_config` and `tree_snapshot`.
- Produces:
  - `cli._operator_identity(settings, supplied, flag) -> tuple[credential | None, str | None]`.
  - `cli._operator_main(args, event, empty, run, actor=None)`, where `run(objects, state, actor)` takes three arguments.
  - `approve --approver` and `rollback --operator` become optional: local requires them; Azure refuses them.

- [ ] **Step 1: Write the failing tests**

`tests/test_operator_identity.py`:

```python
"""Azure operators are their signed-in principal; local operators name themselves; reads write nothing."""
from network_guard import install
install()

import contextlib
import json
import unittest
from unittest.mock import patch

from support_approval import GateFixture, operator_cli, tree_snapshot
from support_azure import OBJECT_ID, TENANT_ID, FailingCredential, FakeCredential, jwt, write_azure_config
from sec_edgar_ingest.storage import open_stores

PRINCIPAL = f'entra:{TENANT_ID}/{OBJECT_ID} lowell@example.com'


class OperatorIdentityTests(GateFixture):
    def setUp(self):
        super().setUp()
        self.base, self.revised, self.candidate = self.gated()
        self.local_config = self.write_config()
        self.azure_config = write_azure_config(self.root / 'azure.json')
        self.credential = FakeCredential(jwt(tid=TENANT_ID, oid=OBJECT_ID, upn='lowell@example.com'))

    def approve_argv(self, config, *extra):
        return ('approve', '--config', str(config), '--quarter', '2026Q4',
                '--generation', self.candidate.manifest.generation_id,
                '--quarterly-sha256', self.revised.snapshot.sha256, *extra)

    def rollback_argv(self, config, *extra):
        return ('rollback', '--config', str(config), '--quarter', '2026Q4',
                '--from-generation', self.candidate.manifest.generation_id,
                '--to-generation', self.base.generation_id, '--reason', 'bad correction', *extra)

    @contextlib.contextmanager
    def azure(self, credential=None):
        """Azure configuration and sign-in, with this fixture's local stores standing in for Azure's."""
        def local(*args, **kwargs):
            return open_stores(self.settings, base_path=self.root, access='operator')
        with patch('sec_edgar_ingest.storage.azure.operator_credential',
                   return_value=credential or self.credential), \
                patch('sec_edgar_ingest.cli.open_stores', side_effect=local) as opened:
            yield opened

    def assert_configuration(self, result):
        code, message, events = result
        self.assertEqual((code, message), (2, None))
        self.assertEqual(json.loads(events.splitlines()[-1])['outcome'], 'configuration')

    def test_local_actors_are_required_free_text(self):
        self.assert_configuration(operator_cli(*self.approve_argv(self.local_config, '--state-dir', str(self.root))))
        self.assertIsNone(self.state.approval(self.candidate.manifest.generation_id))
        self.assert_configuration(operator_cli(*self.rollback_argv(self.local_config, '--state-dir', str(self.root))))

    def test_azure_approve_and_rollback_record_the_signed_in_principal(self):
        with self.azure() as opened:
            code, message, _ = operator_cli(*self.approve_argv(self.azure_config))
            self.assertEqual((code, message['outcome'], message['approval']['approver']), (0, 'success', PRINCIPAL))
            code, message, _ = operator_cli(*self.rollback_argv(self.azure_config))
            self.assertEqual((code, message['outcome'], message['rollback']['operator']), (0, 'success', PRINCIPAL))
        self.assertEqual(opened.call_args.kwargs, {'base_path': None, 'access': 'operator',
                                                   'credential': self.credential})
        self.assertEqual(self.credential.scopes, [('https://storage.azure.com/.default',)] * 2)

    def test_azure_refuses_free_text_and_unusable_sign_ins_before_opening_stores(self):
        cases = {'free text': (self.credential, ('--approver', 'Lowell Mason')),
                 'no object id': (FakeCredential(jwt(tid=TENANT_ID)), ()),
                 'not signed in': (FailingCredential(), ())}
        for label, (credential, extra) in cases.items():
            with self.subTest(label), \
                    patch('sec_edgar_ingest.storage.azure.operator_credential', return_value=credential), \
                    patch('sec_edgar_ingest.cli.open_stores', side_effect=AssertionError('opened stores')):
                self.assert_configuration(operator_cli(*self.approve_argv(self.azure_config, *extra)))

    def test_azure_candidates_need_no_actor(self):
        with self.azure():
            code, message, _ = operator_cli('candidates', '--config', str(self.azure_config))
        self.assertEqual((code, [entry['status'] for entry in message['candidates']]), (0, ['pending']))

    def test_a_mistyped_state_dir_creates_nothing(self):
        typo = self.root / 'typo'
        self.assert_configuration(operator_cli('candidates', '--config', str(self.local_config),
                                               '--state-dir', str(typo)))
        self.assertFalse(typo.exists())

    def test_operator_reads_leave_the_store_unchanged(self):
        before = tree_snapshot(self.root)
        code, _, _ = operator_cli('candidates', '--config', str(self.local_config), '--state-dir', str(self.root))
        self.assertEqual(code, 0)
        self.assertEqual(tree_snapshot(self.root), before)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_operator_identity -v`
Expected: FAIL. Without `--approver`, argparse still exits (`SystemExit: 2`). On Azure, `open_stores` is called without `access`. The mistyped `--state-dir` is created.

- [ ] **Step 3: Make the actor flags optional**

In `cli._parser`, replace the approve and rollback blocks with:

```python
    sub = commands.add_parser('approve')
    for name in ('config', 'quarter', 'generation', 'quarterly-sha256'):
        sub.add_argument('--' + name, required=True)
    sub.add_argument('--approver', help='local-fixture only; Azure records the signed-in principal')
    sub.add_argument('--state-dir')
    sub = commands.add_parser('candidates')
    sub.add_argument('--config', required=True)
    sub.add_argument('--state-dir')
    sub = commands.add_parser('rollback')
    for name in ('config', 'quarter', 'from-generation', 'to-generation', 'reason'):
        sub.add_argument('--' + name, required=True)
    sub.add_argument('--operator', help='local-fixture only; Azure records the signed-in principal')
    sub.add_argument('--state-dir')
```

- [ ] **Step 4: Resolve the operator identity before any store opens**

In `cli.py`, extend the `storage.contracts` import with `StoreMissing`, and change the identity import to `from .storage.identity import OPERATOR_TOKEN_SCOPE, principal_from_token, worker_client_id`. Replace `_operator_main`, `_approve_main`, `_candidates_main` and `_rollback_main` with:

```python
def _configuration_error(error: Exception) -> int:
    sys.stderr.write(canonical_json({'outcome': 'configuration', 'error': str(error)}).decode() + '\n')
    return 2


def _operator_identity(settings: Settings, supplied: str | None, flag: str | None):
    """(credential, actor). Azure uses the operator's `az login` and records its principal, refusing free
    text; the local-fixture backend requires the free-text flag of a command that records an actor."""
    if settings.storage.backend != 'azure':
        if flag is not None and supplied is None:
            raise ValueError(f'--{flag} is required on the local-fixture backend')
        return None, supplied
    if supplied is not None:
        raise ValueError(f'--{flag} is refused on Azure; the signed-in principal is recorded')
    from azure.core.exceptions import ClientAuthenticationError
    from .storage.azure import operator_credential
    credential = operator_credential()
    try:
        token = credential.get_token(OPERATOR_TOKEN_SCOPE)
    except ClientAuthenticationError as error:
        raise ValueError('operator sign-in is unavailable: ' + error_text(error)) from error
    return credential, principal_from_token(token.token)


def _operator_main(args, event: str | None, empty: dict[str, object], run, actor: str | None = None) -> int:
    """Run one operator command on verify-only stores and print its canonical result.

    `actor` names the flag (`approver` or `operator`) of a command that records who acted.
    """
    try:
        settings = _operator_settings(args)
        credential, principal = _operator_identity(settings, None if actor is None else getattr(args, actor), actor)
    except (ValueError, OSError, TypeError) as error:
        return _configuration_error(error)
    opened = ()
    try:
        opened = open_stores(settings, base_path=Path(args.state_dir) if args.state_dir else None,
                             access='operator', credential=credential)
        store, objects, _ = opened
        value = {**empty, **run(objects, EtlState(store), principal)}
    except StoreMissing as error:
        return _configuration_error(error)
    except Exception as exception:
        outcome = ('state_conflict' if isinstance(exception, (Conflict, ValueError, OSError, KeyError))
                   else 'internal_error')
        value = {**empty, 'outcome': outcome, 'error': Error(
            outcome, error_text(exception), False, None, {'type': type(exception).__name__}).to_mapping()}
    finally:
        for resource in reversed(opened):
            if hasattr(resource, 'close'):
                resource.close()
    body = to_mapping_value(value)
    if event is not None:
        sys.stderr.write(canonical_json({'event': event, 'fields': body}).decode() + '\n')
    sys.stdout.write(canonical_json(body).decode() + '\n')
    return exit_code(value['outcome'])


def _approve_main(args) -> int:
    def run(objects, state, actor):
        result = approve(args.quarter, args.generation, args.quarterly_sha256, actor, objects, state)
        ref = None if result.approval is None else approval_ref(result.approval.quarter, result.approval.generation_id)
        return {**result.to_mapping(), 'approval_ref': ref}
    return _operator_main(args, 'withdrawal_approval',
                          {'quarter': args.quarter, 'generation_id': args.generation, 'approval_ref': None,
                           'approval': None, 'publication': None, 'error': None}, run, actor='approver')


def _candidates_main(args) -> int:
    return _operator_main(args, None, {'candidates': None, 'error': None},
                          lambda objects, state, actor: {'outcome': 'success',
                                                         'candidates': list(withdrawal_candidates(objects, state))})


def _rollback_main(args) -> int:
    def run(objects, state, actor):
        result = rollback(args.quarter, args.from_generation, args.to_generation, actor, args.reason,
                          objects, state)
        return {**result.to_mapping(),
                'rollback_ref': None if result.rollback is None else rollback_ref(result.rollback)}
    return _operator_main(args, 'quarter_rollback',
                          {'quarter': args.quarter, 'from_generation_id': args.from_generation,
                           'to_generation_id': args.to_generation, 'rollback_ref': None, 'active': None,
                           'rollback': None, 'error': None}, run, actor='operator')
```

- [ ] **Step 5: Run the new and the existing operator tests**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_operator_identity test_etl_approval test_etl_rollback test_etl_history test_etl_cli test_reconcile_acceptance -v`
Expected: PASS. The existing tests always open stores before their operator calls, so the verify-only open finds them.

- [ ] **Step 6: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/test_operator_identity.py
git commit -m "feat(ingest): attribute Azure operator commands to the signed-in principal

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Activation records for every attempted approve move

**Files:**
- Modify: `src/sec_edgar_ingest/etl/contracts.py` (add `ACTIVATION_FORMAT` beside `ROLLBACK_FORMAT`; add `ApprovalActivation` after `QuarterRollback`)
- Modify: `src/sec_edgar_ingest/storage/contracts.py:16` (`APPROVAL_KINDS`)
- Modify: `src/sec_edgar_ingest/etl/state.py` (import; `record_activation`, `activations` after `rollbacks`)
- Modify: `src/sec_edgar_ingest/etl/approval.py` (`ApprovalOutcome`, `_committed`, new `activation_ref` and `_store_activation`, `approve`)
- Modify: `src/sec_edgar_ingest/cli.py` (`_approve_main`)
- Modify: `tests/test_etl_approval.py:225-226` (exact CLI key set)
- Modify: `docs/runbooks/sec-edgar-reconciliation-approval.md` (Approve section, Roll back closing paragraph, Not provided)
- Create: `tests/test_approval_activation.py`

**Interfaces:**
- Consumes: `rollback(...)` and `EtlState._immutable` (existing).
- Produces:
  - `etl.contracts.ApprovalActivation(quarter, generation_id, base_generation_id, from_pointer_version, approval_ref, approval_sha256, actor, activated_at, format_version='sec-approval-activation-v1')`, with property `activation_id`.
  - `etl.approval.activation_ref(record) -> str` and `etl.approval._store_activation(record, objects) -> ApprovalActivation`.
  - `EtlState.record_activation(record)` and `EtlState.activations(quarter) -> tuple[ApprovalActivation, ...]`, ordered by `(activated_at, activation_id)`.
  - `ApprovalOutcome.activation`, which is non-null exactly on `success`.
  - The `approve` CLI keys gain `activation` and `activation_ref`.

- [ ] **Step 1: Write the failing tests**

`tests/test_approval_activation.py`:

```python
"""Write-ahead activation records of approve's pointer moves."""
from network_guard import install
install()

import hashlib
import unittest
from dataclasses import replace

from support import Faults
from support_approval import GateFixture, operator_cli, row
from sec_edgar_ingest.etl.approval import _store_activation, activation_ref, approve
from sec_edgar_ingest.etl.contracts import ApprovalActivation
from sec_edgar_ingest.etl.manifest import approval_ref
from sec_edgar_ingest.etl.rollback import rollback
from sec_edgar_ingest.models import canonical_json
from sec_edgar_ingest.storage.contracts import table_for


class ActivationTests(GateFixture):
    def approve(self, candidate, quarterly_sha256, approver='Lowell Mason', **kwargs):
        return approve('2026Q4', candidate.manifest.generation_id, quarterly_sha256, approver,
                       self.objects, self.state, **kwargs)

    def activation_objects(self):
        return sorted(self.objects.directory.rglob('activation.json'))

    def moved_base(self):
        return self.observation(rows=row('Updated') + row(number=2), seconds=2)

    def test_a_first_approval_writes_the_decision_and_one_activation(self):
        base, revised, candidate = self.gated()
        before = self.state.pointer('2026Q4')
        result = self.approve(candidate, revised.snapshot.sha256)
        activation = result.activation
        generation = candidate.manifest.generation_id
        self.assertEqual(result.outcome, 'success')
        self.assertEqual((activation.quarter, activation.generation_id, activation.base_generation_id,
                          activation.from_pointer_version, activation.actor),
                         ('2026Q4', generation, base.generation_id, before.version, 'Lowell Mason'))
        approval_body = self.objects.read(approval_ref('2026Q4', generation))
        self.assertEqual((activation.approval_ref, activation.approval_sha256),
                         (approval_ref('2026Q4', generation), hashlib.sha256(approval_body).hexdigest()))
        self.assertEqual(activation.activation_id,
                         hashlib.sha256(canonical_json(['2026Q4', generation, before.version])).hexdigest())
        self.assertEqual(activation_ref(activation),
                         f'approvals/sec/filing_index/year=2026/quarter=4/generation={generation}'
                         f'/activation={activation.activation_id}/activation.json')
        self.assertEqual(self.objects.read(activation_ref(activation)), canonical_json(activation.to_mapping()))
        self.assertEqual(self.state.activations('2026Q4'), (activation,))

    def test_refused_and_unchanged_approvals_write_no_activation(self):
        _, revised, candidate = self.gated()
        self.assertEqual(self.approve(candidate, '0' * 64).outcome, 'approval_refused')
        self.assertEqual(self.activation_objects(), [])
        self.assertEqual(self.approve(candidate, revised.snapshot.sha256).outcome, 'success')
        again = self.approve(candidate, revised.snapshot.sha256, 'Someone Else')
        self.assertEqual((again.outcome, again.activation), ('unchanged', None))
        self.assertEqual(len(self.state.activations('2026Q4')), 1)

    def test_a_stale_candidate_writes_no_activation(self):
        _, revised, candidate = self.gated()
        self.assertEqual(self.publish(self.moved_base()).outcome, 'published')
        self.assertEqual(self.approve(candidate, revised.snapshot.sha256).outcome, 'approval_stale')
        self.assertEqual((self.activation_objects(), self.state.activations('2026Q4')), ([], ()))

    def test_a_lost_race_keeps_its_activation_as_evidence(self):
        _, revised, candidate = self.gated()
        moved = self.moved_base()
        faults = Faults()
        faults.at('approval.before_pointer', lambda: self.assertEqual(self.publish(moved).outcome, 'published'))
        result = self.approve(candidate, revised.snapshot.sha256, 'Racing Approver', observer=faults)
        self.assertEqual(result.outcome, 'approval_stale')
        attempt, = self.state.activations('2026Q4')
        self.assertEqual(attempt.actor, 'Racing Approver')
        self.assertNotEqual(self.capture().generation_id, attempt.generation_id)

    def test_the_first_record_of_an_attempted_move_wins_and_is_revalidated(self):
        _, revised, candidate = self.gated()
        first = self.approve(candidate, revised.snapshot.sha256).activation
        self.assertEqual(_store_activation(replace(first, actor='Retry Actor'), self.objects), first)
        with self.assertRaisesRegex(ValueError, 'exact pointer move'):
            _store_activation(replace(first, approval_sha256='f' * 64), self.objects)

    def test_reactivation_after_rollback_records_only_its_own_activation(self):
        base, revised, candidate = self.gated()
        self.assertEqual(self.approve(candidate, revised.snapshot.sha256, 'First Approver').outcome, 'success')
        self.assertEqual(rollback('2026Q4', candidate.manifest.generation_id, base.generation_id, 'Lowell Mason',
                                  'reconsider', self.objects, self.state).outcome, 'success')
        again = self.approve(candidate, revised.snapshot.sha256, 'Second Approver')
        self.assertEqual((again.outcome, again.approval.approver, again.activation.actor),
                         ('success', 'First Approver', 'Second Approver'))
        self.assertEqual([record.actor for record in self.state.activations('2026Q4')],
                         ['First Approver', 'Second Approver'])
        self.assertEqual(len(list(self.objects.directory.rglob('approval.json'))), 1)

    def test_approve_cli_prints_the_activation_reference(self):
        _, revised, candidate = self.gated()
        command = ('approve', '--config', str(self.write_config()), '--state-dir', str(self.root),
                   '--quarter', '2026Q4', '--generation', candidate.manifest.generation_id,
                   '--quarterly-sha256', revised.snapshot.sha256, '--approver', 'Lowell Mason')
        code, message, _ = operator_cli(*command)
        self.assertEqual((code, message['outcome']), (0, 'success'))
        self.assertEqual(message['activation_ref'],
                         activation_ref(ApprovalActivation.from_mapping(message['activation'])))
        code, message, _ = operator_cli(*command)
        self.assertEqual((code, message['outcome'], message['activation'], message['activation_ref']),
                         (0, 'unchanged', None, None))

    def test_activation_rows_route_to_the_approvals_table(self):
        from azure.core.credentials import AzureSasCredential
        from azure.data.tables import TableServiceClient
        from sec_edgar_ingest.storage.azure import AzureStateStore
        from test_azure_contracts import RETRY, TABLE_ENDPOINT, ScriptedTransport, table_response
        self.assertEqual(table_for('ApprovalActivation'), 'Approvals')
        transport = ScriptedTransport([table_response(201, etag='W/"activation"')])
        service = TableServiceClient(TABLE_ENDPOINT, credential=AzureSasCredential('sv=offline&sig=synthetic'),
                                     api_version='2020-12-06', transport=transport, **RETRY)
        self.addCleanup(service.close)
        tables = service.get_table_client
        store = AzureStateStore(tables('SourceState'), tables('Attempts'), active_client=tables('ActivePointers'),
                                approval_client=tables('Approvals'))
        self.assertEqual(store.insert('ApprovalActivation', 'c' * 64, {'actor': 'Lowell Mason'}).version,
                         'W/"activation"')
        self.assertIn('/Approvals', transport.requests[0].url)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_approval_activation -v`
Expected: ERROR at import with `ImportError: cannot import name '_store_activation'`.

- [ ] **Step 3: Add the record and its routing**

In `etl/contracts.py`, add `ACTIVATION_FORMAT = 'sec-approval-activation-v1'` after `ROLLBACK_FORMAT`, and after the `QuarterRollback` class:

```python
@dataclass(frozen=True, slots=True)
class ApprovalActivation(Record):
    """Immutable, write-ahead record of one attempted approve move; the pointer decides what took effect."""
    quarter: str
    generation_id: str
    base_generation_id: str
    from_pointer_version: str
    approval_ref: str
    approval_sha256: str
    actor: str
    activated_at: datetime
    format_version: str = ACTIVATION_FORMAT

    def __post_init__(self):
        _record(self)
        if self.format_version != ACTIVATION_FORMAT:
            raise ValueError('unsupported activation format')
        require_hash(self.base_generation_id, 'base_generation_id')
        if self.base_generation_id == self.generation_id:
            raise ValueError('activation must change the active generation')
        require_text(self.from_pointer_version, 'from_pointer_version')
        require_line(self.actor, 'actor', MAX_OPERATOR_CHARS)
        require_utc(self.activated_at, 'activated_at')

    @property
    def activation_id(self) -> str:
        """One identity per attempted move of the quarter from an exact pointer version to this generation."""
        return hashlib.sha256(canonical_json([self.quarter, self.generation_id, self.from_pointer_version])).hexdigest()
```

In `storage/contracts.py`, replace line 16 with:

```python
APPROVAL_KINDS = frozenset({"WithdrawalApproval", "QuarterRollback", "ApprovalActivation"})
```

In `etl/state.py`, add `ApprovalActivation` to the `.contracts` import, and after `rollbacks`:

```python
    def record_activation(self, record: ApprovalActivation) -> None:
        self._immutable('ApprovalActivation', record.activation_id, record.to_mapping())

    def activations(self, quarter: str) -> tuple[ApprovalActivation, ...]:
        """Every write-ahead approve activation of one quarter; the pointer decides which took effect."""
        quarter_value(quarter)
        records = (ApprovalActivation.from_mapping(row.to_mapping()['value'])
                   for row in self.store.scan('ApprovalActivation', {'quarter': quarter}))
        return tuple(sorted(records, key=lambda record: (record.activated_at, record.activation_id)))
```

- [ ] **Step 4: Write the activation ahead of the swap**

In `etl/approval.py`:
- Change the models import to `from ..models import Error, Record, canonical_json, parse_json, quarter_value, require_hash, validate_record_fields`.
- Add `ApprovalActivation` to the `.contracts` import.

Replace `ApprovalOutcome` and `_committed` with:

```python
@dataclass(frozen=True, slots=True)
class ApprovalOutcome(Record):
    outcome: str
    publication: PublicationResult | None
    approval: WithdrawalApproval | None
    error: Error | None
    activation: ApprovalActivation | None = None

    def __post_init__(self):
        validate_record_fields(self)
        if self.outcome not in APPROVAL_OUTCOMES:
            raise ValueError('unsupported approval outcome')
        committed = self.outcome in ('success', 'unchanged')
        if committed != (self.publication is not None and self.approval is not None and self.error is None):
            raise ValueError('approval outcome evidence differs from its outcome')
        if not committed and (self.error is None or self.error.code != self.outcome):
            raise ValueError('refused or stale approval requires its matching error')
        if (self.activation is not None) != (self.outcome == 'success'):
            raise ValueError('exactly a successful approval carries the activation that moved the pointer')
```

```python
def _committed(outcome: str, candidate: Candidate, approval: WithdrawalApproval, conflicts: int,
               activation: ApprovalActivation | None = None) -> ApprovalOutcome:
    publication = PublicationResult(candidate.manifest.quarter, 'published' if outcome == 'success' else 'unchanged',
                                    candidate.manifest.generation_id, candidate.manifest_ref, None, conflicts)
    return ApprovalOutcome(outcome, publication, approval, None, activation)
```

After `_store_approval`, add:

```python
def activation_ref(record: ApprovalActivation) -> str:
    year, ordinal = quarter_value(record.quarter)
    return (f'approvals/sec/filing_index/year={year}/quarter={ordinal}/generation={record.generation_id}'
            f'/activation={record.activation_id}/activation.json')


def _store_activation(record: ApprovalActivation, objects: ObjectStore) -> ApprovalActivation:
    ref = activation_ref(record)
    try:
        objects.put_once(ref, canonical_json(record.to_mapping()))
    except Conflict:
        pass  # The first record of this exact attempted move wins; it is re-validated below.
    body = objects.read(ref)
    stored = ApprovalActivation.from_mapping(parse_json(body))
    if canonical_json(stored.to_mapping()) != body or activation_ref(stored) != ref or (
            stored.base_generation_id, stored.approval_ref, stored.approval_sha256) != (
            record.base_generation_id, record.approval_ref, record.approval_sha256):
        raise ValueError('stored activation differs from this exact pointer move')
    return stored
```

In `approve`, replace the block from `stored = _store_approval(pending, candidate, objects)` through `return _committed('success', candidate, stored, conflicts)` with:

```python
        stored = _store_approval(pending, candidate, objects)
        state.record_approval(stored)
        activation = _store_activation(ApprovalActivation(
            quarter, generation_id, candidate.manifest.base_generation_id, current.version,
            approval_ref(quarter, generation_id), hashlib.sha256(canonical_json(stored.to_mapping())).hexdigest(),
            approver, _now()), objects)
        state.record_activation(activation)
        observe(observer, 'approval.before_pointer')
        try:
            state.commit_pointer(quarter, pointer_value(candidate), current)
        except (AlreadyExists, Conflict):
            observe(observer, 'approval.cas_lost')
            continue
        observe(observer, 'approval.after_pointer')
        return _committed('success', candidate, stored, conflicts, activation)
```

`current` is never `None` here: the candidate's base is a required hash, and the loop reaches this line only when the active generation equals that base.

- [ ] **Step 5: Print `activation_ref` from the CLI**

In `cli.py`, change the approval import to `from .etl.approval import activation_ref, approve`, and replace `_approve_main` with:

```python
def _approve_main(args) -> int:
    def run(objects, state, actor):
        result = approve(args.quarter, args.generation, args.quarterly_sha256, actor, objects, state)
        ref = None if result.approval is None else approval_ref(result.approval.quarter, result.approval.generation_id)
        return {**result.to_mapping(), 'approval_ref': ref,
                'activation_ref': None if result.activation is None else activation_ref(result.activation)}
    return _operator_main(args, 'withdrawal_approval',
                          {'quarter': args.quarter, 'generation_id': args.generation, 'approval_ref': None,
                           'approval': None, 'publication': None, 'activation': None, 'activation_ref': None,
                           'error': None}, run, actor='approver')
```

In `tests/test_etl_approval.py`, replace the exact key set in `test_a_corrupt_approval_object_reports_state_conflict_through_the_cli` with:

```python
        self.assertEqual(set(message), {'outcome', 'quarter', 'generation_id', 'approval_ref', 'approval',
                                        'publication', 'activation', 'activation_ref', 'error'})
```

- [ ] **Step 6: Update the approval runbook**

In `docs/runbooks/sec-edgar-reconciliation-approval.md`:
- Replace the approve usage line `  --quarterly-sha256 HASH --approver TEXT [--state-dir PATH]` with `  --quarterly-sha256 HASH [--approver TEXT] [--state-dir PATH]`.
- Insert this paragraph directly after the usage block:

  > `--approver` is required on the local-fixture backend and refused on Azure. On Azure, `approve` signs in with the operator's `az login` and records `entra:<tenant-id>/<object-id>` followed by the account's user name. The same holds for `rollback --operator`.

- Replace the sentence `` `approve` writes the approval object, the `Approvals` index and the conditional pointer replace. `` with:

  > `approve` writes the approval object (the decision), then an activation record (the move), then the conditional pointer replace. The record is at `approvals/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/activation=<activation-id>/activation.json`, format `sec-approval-activation-v1`, and both are indexed in `Approvals`. `unchanged`, `approval_stale` and refusals write no activation. stdout names it in `activation_ref`.

- Replace `; the later operator's name is not recorded.` with `; that re-activation writes only an activation record, attributed to its own actor.`
- Replace ``From `pending`, `approve` re-activates it under the original stored approval, and the new `--approver` is not recorded.`` with ``From `pending`, `approve` re-activates it under the original stored approval and records the re-activating actor in a new activation record.``
- In "Not provided", replace `- Approver and rollback-operator identity mapping, alerts for pending approvals, and schedules belong to Stage 6.` with `- Alerts for pending approvals and schedules are Stage 6's Azure definitions (Plan 10).`

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_approval_activation test_etl_approval test_etl_rollback test_etl_history test_etl_storage test_reconcile_acceptance -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest packages/sec-edgar-ingest/tests/test_approval_activation.py packages/sec-edgar-ingest/tests/test_etl_approval.py docs/runbooks/sec-edgar-reconciliation-approval.md
git commit -m "feat(ingest): record every attempted approve move as a write-ahead activation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The read-only `history` command

**Files:**
- Modify: `src/sec_edgar_ingest/cli.py` (`_parser`, `_operator_settings`, new `_history_main`, `main`)
- Modify: `docs/runbooks/sec-edgar-reconciliation-approval.md` (the `quarter_history` references and the History section)
- Modify: `packages/sec-edgar-ingest/README.md` (operator commands paragraph)
- Create: `tests/test_history_cli.py`

**Interfaces:**
- Consumes: `quarter_history` (existing), `EtlState.rollbacks`, `EtlState.activations` (Task 4), `_operator_main(..., actor=None)` (Task 3).
- Produces: `sec-edgar-ingest history --config PATH --quarter YYYYQn [--state-dir PATH]`, which prints canonical `{outcome, quarter, lineage, rollbacks, activations, error}`. Exits: `success` 0, `configuration` 2 (empty stdout), `state_conflict` or `internal_error` 9.

- [ ] **Step 1: Write the failing tests**

`tests/test_history_cli.py`:

```python
"""`history` prints a quarter's lineage, rollback records and activation records, read-only."""
from network_guard import install
install()

import json
import unittest
from unittest.mock import patch

from support_approval import GateFixture, operator_cli, tree_snapshot
from sec_edgar_ingest.etl.approval import approve
from sec_edgar_ingest.etl.rollback import rollback
from sec_edgar_ingest.models import canonical_json, to_mapping_value
from sec_edgar_ingest.storage.contracts import Conflict

KEYS = {'outcome', 'quarter', 'lineage', 'rollbacks', 'activations', 'error'}


class HistoryCliTests(GateFixture):
    def history(self, quarter='2026Q4', state_dir=None):
        return operator_cli('history', '--config', str(self.write_config()),
                            '--state-dir', str(state_dir or self.root), '--quarter', quarter)

    def test_a_quarter_without_a_pointer_has_empty_history(self):
        self.gated()
        code, message, _ = self.history('2026Q3')
        self.assertEqual((code, message), (0, {'outcome': 'success', 'quarter': '2026Q3', 'lineage': [],
                                                'rollbacks': [], 'activations': [], 'error': None}))

    def test_history_lists_lineage_rollbacks_and_activations(self):
        base, revised, candidate = self.gated()
        approved = approve('2026Q4', candidate.manifest.generation_id, revised.snapshot.sha256, 'Lowell Mason',
                           self.objects, self.state)
        code, message, _ = self.history()
        self.assertEqual((code, set(message)), (0, KEYS))
        self.assertEqual([entry['generation_id'] for entry in message['lineage']],
                         [candidate.manifest.generation_id, base.generation_id])
        self.assertEqual(message['activations'],
                         [json.loads(canonical_json(to_mapping_value(approved.activation.to_mapping())))])
        self.assertEqual(rollback('2026Q4', candidate.manifest.generation_id, base.generation_id, 'Lowell Mason',
                                  'reconsider', self.objects, self.state).outcome, 'success')
        code, message, _ = self.history()
        self.assertEqual([entry['generation_id'] for entry in message['lineage']], [base.generation_id])
        record, = message['rollbacks']
        self.assertEqual((record['from_generation_id'], record['to_generation_id']),
                         (candidate.manifest.generation_id, base.generation_id))
        self.assertEqual(len(message['activations']), 1)

    def test_an_invalid_quarter_or_missing_store_is_a_configuration_error(self):
        self.gated()
        for result in (self.history('2026Q5'), self.history(state_dir=self.root / 'typo')):
            code, message, events = result
            self.assertEqual((code, message), (2, None))
            self.assertEqual(json.loads(events.splitlines()[-1])['outcome'], 'configuration')
        self.assertFalse((self.root / 'typo').exists())

    def test_a_failed_read_reports_state_conflict(self):
        self.gated()
        with patch('sec_edgar_ingest.cli.quarter_history', side_effect=Conflict('lineage drifted')):
            code, message, _ = self.history()
        self.assertEqual((code, message['outcome'], set(message), message['error']['code']),
                         (9, 'state_conflict', KEYS, 'state_conflict'))

    def test_history_and_candidates_leave_the_store_unchanged(self):
        self.gated()
        self.write_config()
        before = tree_snapshot(self.root)
        self.assertEqual(self.history()[0], 0)
        self.assertEqual(operator_cli('candidates', '--config', str(self.write_config()),
                                      '--state-dir', str(self.root))[0], 0)
        self.assertEqual(tree_snapshot(self.root), before)


if __name__ == '__main__':
    unittest.main()
```

`write_config` writes `config.json` beside `.fixture-state` inside the snapshotted directory. The test therefore writes it before taking the snapshot. Rewriting the same bytes later leaves its content hash unchanged.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_history_cli -v`
Expected: FAIL. argparse rejects the `history` subcommand with `SystemExit: 2`.

- [ ] **Step 3: Implement the command**

In `cli.py`:
- Change the history import to `from .etl.history import quarter_history, withdrawal_candidates`.
- Add `quarter_value` to the `.models` import.
- In `_parser`, after the `candidates` block, add:

```python
    sub = commands.add_parser('history')
    sub.add_argument('--config', required=True)
    sub.add_argument('--quarter', required=True)
    sub.add_argument('--state-dir')
```

Replace `_operator_settings` with:

```python
def _operator_settings(args) -> Settings:
    if args.command == 'history':
        quarter_value(args.quarter)
    settings = load_config(Path(args.config))
    if settings.storage.backend == 'azure' and args.state_dir:
        raise ValueError('state directory is fixture-only')
    return settings
```

After `_candidates_main`, add:

```python
def _history_main(args) -> int:
    def run(objects, state, actor):
        return {'outcome': 'success', 'lineage': list(quarter_history(args.quarter, objects, state)),
                'rollbacks': [record.to_mapping() for record in state.rollbacks(args.quarter)],
                'activations': [record.to_mapping() for record in state.activations(args.quarter)]}
    return _operator_main(args, None, {'quarter': args.quarter, 'lineage': None, 'rollbacks': None,
                                       'activations': None, 'error': None}, run)
```

In `main`, after the `candidates` branch, add:

```python
    if args.command == 'history':
        return _history_main(args)
```

- [ ] **Step 4: Point the runbook and README at the command**

In `docs/runbooks/sec-edgar-reconciliation-approval.md`:
- Replace ``; `quarter_history` lists each generation's membership hash.`` with ``; `sec-edgar-ingest history` lists each generation's membership hash.``
- Replace ``The pointer, `quarter_history` and `EtlState.rollbacks` show what took effect.`` with ``The pointer and `sec-edgar-ingest history` show what took effect.``
- Replace ``take both from `quarter_history`.`` with ``take both from `sec-edgar-ingest history`.``
- Replace ``Re-read `quarter_history` and decide again.`` with ``Re-run `sec-edgar-ingest history` and decide again.``
- Replace the History section's paragraph with:

````markdown
```text
sec-edgar-ingest history --config PATH --quarter YYYYQn [--state-dir PATH]
```

Read-only. It prints `{"activations": [...], "error": null, "lineage": [...], "outcome": "success", "quarter": ..., "rollbacks": [...]}`:

- `lineage` is the active generation's lineage, newest first, through each exact `retained-base.json`. Each entry carries the counts, gate, mode, membership hash and change file, plus the approval of each approved gated generation. A quarter with no pointer has an empty lineage.
- `rollbacks` are the quarter's rollback records. After a rollback, they name the generations the lineage no longer shows.
- `activations` are the quarter's approve activation records, attempted moves included. The pointer decides which took effect.

Exit 0 is success. Exit 2 with empty stdout is a configuration error: an invalid quarter, or no store at the configured binding (a mistyped `--state-dir` creates nothing). Exit 9 is `state_conflict` or `internal_error`.

Every operator command (`approve`, `rollback`, `candidates`, `history`) opens an existing store verify-only. It never creates a directory, database, container, table or binding registry.
````

In `packages/sec-edgar-ingest/README.md`, append:

```markdown
Operator commands are `candidates`, `approve`, `rollback` and the read-only `history --quarter YYYYQn`; see
`docs/runbooks/sec-edgar-reconciliation-approval.md`. They open an existing store verify-only and never create
one: a missing store is a configuration error (exit 2, empty stdout). On Azure they authenticate with the
operator's `az login`, and `approve`/`rollback` record that principal instead of `--approver`/`--operator`.
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_history_cli test_etl_history test_operator_identity -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/test_history_cli.py docs/runbooks/sec-edgar-reconciliation-approval.md packages/sec-edgar-ingest/README.md
git commit -m "feat(ingest): add the read-only history operator command

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Workflow config and execution ID from the environment

**Files:**
- Modify: `src/sec_edgar_ingest/config.py` (`load_config` at lines 254–259; new `parse_config`, `load_config_env`)
- Modify: `src/sec_edgar_ingest/cli.py` (`_parser` lines 75–90; `_validate_workflow` lines 303–330)
- Modify: `packages/sec-edgar-ingest/README.md`
- Create: `tests/test_workflow_config_env.py`

**Interfaces:**
- Consumes: `worker_client_id`, `EXECUTION_NAME_ENV`, `WORKER_CLIENT_ID_ENV` (Task 1); `azure_settings` and `WORKER_CLIENT_ID` (test support).
- Produces:
  - `config.parse_config(text: str) -> Settings` and `config.load_config_env(name: str, environ: Mapping[str, str]) -> Settings`.
  - Workflow commands take exactly one of `--config PATH` / `--config-env NAME` (argparse exit 2 otherwise).
  - `--execution-id` is optional for workflow commands. On Azure it is refused, and the value comes from `CONTAINER_APP_JOB_EXECUTION_NAME`. Local-fixture requires it. Stage commands are unchanged.

- [ ] **Step 1: Write the failing tests**

`tests/test_workflow_config_env.py`:

```python
"""Workflow commands read their config from an environment variable and, on Azure, their execution ID."""
from network_guard import install
install()

import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from support_azure import WORKER_CLIENT_ID, azure_settings
from support_workflows import CommandHarness, simple_pack
from sec_edgar_ingest.cli import main
from sec_edgar_ingest.models import canonical_json, to_mapping_value
from sec_edgar_ingest.storage.contracts import Conflict
from sec_edgar_ingest.storage.identity import EXECUTION_NAME_ENV, WORKER_CLIENT_ID_ENV

CONFIG_ENV = 'SEC_EDGAR_INGEST_CONFIG'


def run(argv, environ=None, remove=()):
    stdout, stderr = io.StringIO(), io.StringIO()
    with patch.dict(os.environ, environ or {}):
        for name in remove:
            os.environ.pop(name, None)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
    return code, (json.loads(stdout.getvalue()) if stdout.getvalue() else None), stderr.getvalue()


class LocalConfigEnvTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.h = CommandHarness(self.root, simple_pack(self.root / 'pack'))
        self.addCleanup(self.h.close)

    def argv(self, *source, execution=('--execution-id', 'manual')):
        return ['backfill', *source, '--run-id', 'env', *execution, '--attempt-id', 'a',
                '--deadline', self.h.deadline.isoformat(), '--state-dir', str(self.root), '--today', '2026-10-07',
                '--fixture-pack', str(self.h.pack)]

    def test_config_env_runs_the_same_settings_through_every_child(self):
        code, message, _ = run(self.argv('--config-env', CONFIG_ENV), {CONFIG_ENV: self.h.config.read_text()})
        self.assertEqual((code, message['outcome']), (0, 'success'))
        results = [json.loads(path.read_bytes()) for path in (self.h.objects.directory / 'runs').rglob('result.json')]
        self.assertGreater(len(results), 1)
        self.assertEqual({result['context']['config_sha256'] for result in results}, {self.h.settings.config_sha256})

    def test_exactly_one_config_source_is_accepted(self):
        for source in (('--config', str(self.h.config), '--config-env', CONFIG_ENV), ()):
            with self.subTest(source=source), self.assertRaises(SystemExit) as caught, \
                    contextlib.redirect_stderr(io.StringIO()):
                main(self.argv(*source))
            self.assertEqual(caught.exception.code, 2)

    def test_an_unusable_config_env_is_a_configuration_error_before_stores(self):
        cases = {'unset': (CONFIG_ENV, None), 'empty': (CONFIG_ENV, ''), 'not json': (CONFIG_ENV, '{'),
                 'bad name': ('lower-case', self.h.config.read_text())}
        for label, (name, value) in cases.items():
            environ = {} if value is None else {name: value}
            with self.subTest(label), \
                    patch('sec_edgar_ingest.cli.open_stores', side_effect=AssertionError('opened stores')):
                code, message, _ = run(self.argv('--config-env', name), environ, remove=(CONFIG_ENV,) if value is None else ())
                self.assertEqual((code, message), (2, None))

    def test_local_workflows_still_require_an_execution_id(self):
        with patch('sec_edgar_ingest.cli.open_stores', side_effect=AssertionError('opened stores')):
            code, message, events = run(self.argv('--config', str(self.h.config), execution=()))
        self.assertEqual((code, message), (2, None))
        self.assertIn('--execution-id', json.loads(events.splitlines()[-1])['error'])


class AzureWorkflowIdentityTests(unittest.TestCase):
    def setUp(self):
        deadline = (datetime.now(timezone.utc) + timedelta(seconds=1800)).isoformat()
        self.argv = ['daily', '--config-env', CONFIG_ENV, '--run-id', 'pipeline-run', '--attempt-id', 'launch-1',
                     '--deadline', deadline]
        self.environ = {CONFIG_ENV: canonical_json(to_mapping_value(azure_settings().to_mapping())).decode(),
                        WORKER_CLIENT_ID_ENV: WORKER_CLIENT_ID, EXECUTION_NAME_ENV: 'sec-edgar-ingest-job-abc123'}

    def test_the_execution_id_comes_from_the_job_execution(self):
        frozen = []

        def freeze(context, intent, store, objects):
            frozen.append(context)
            raise Conflict('stop once the context is built')
        objects, store = Mock(), Mock()
        objects.read.side_effect = FileNotFoundError
        store.get.return_value = None
        with patch('sec_edgar_ingest.cli.open_stores', return_value=(store, objects, Mock())), \
                patch('sec_edgar_ingest.cli.freeze_workflow', side_effect=freeze):
            code, message, _ = run(self.argv, self.environ)
        self.assertEqual((code, message['outcome']), (9, 'state_conflict'))
        self.assertEqual((frozen[0].execution_id, frozen[0].attempt_id, frozen[0].config_sha256),
                         ('sec-edgar-ingest-job-abc123', 'launch-1', azure_settings().config_sha256))

    def test_azure_refuses_a_supplied_execution_id_and_missing_job_variables(self):
        cases = {'supplied execution id': (('--execution-id', 'manual'), ()),
                 'no execution name': ((), (EXECUTION_NAME_ENV,)),
                 'no worker client id': ((), (WORKER_CLIENT_ID_ENV,))}
        for label, (extra, remove) in cases.items():
            with self.subTest(label), \
                    patch('sec_edgar_ingest.cli.open_stores', side_effect=AssertionError('opened stores')):
                code, message, events = run([*self.argv, *extra], self.environ, remove)
                self.assertEqual((code, message), (2, None))
                self.assertEqual(json.loads(events.splitlines()[-1])['outcome'], 'configuration')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_workflow_config_env -v`
Expected: FAIL or ERROR, with argparse reporting `unrecognized arguments: --config-env`.

- [ ] **Step 3: Add `parse_config` and `load_config_env`**

In `config.py`, add `from collections.abc import Mapping` to the imports, and replace `load_config` with:

```python
def parse_config(text: str) -> Settings:
    try:
        value = parse_json(text)
    except ValueError as error:
        raise ValueError("configuration requires strict JSON syntax (YAML 1.2 subset)") from error
    return Settings.from_mapping(value)


def load_config(path: Path) -> Settings:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("configuration requires strict JSON syntax (YAML 1.2 subset)") from error
    return parse_config(text)


def load_config_env(name: str, environ: Mapping[str, str]) -> Settings:
    """The same strict configuration, carried by one environment variable (the Azure job secret)."""
    if not isinstance(name, str) or re.fullmatch(r"[A-Z][A-Z0-9_]*", name) is None:
        raise ValueError("--config-env must name an upper-case environment variable")
    text = environ.get(name)
    if not text:
        raise ValueError(f"configuration environment variable {name} is unset or empty")
    return parse_config(text)
```

- [ ] **Step 4: Accept `--config-env` and resolve the execution ID**

In `cli.py`:
- Change the config import to `from .config import Settings, load_config, load_config_env, pin_context`.
- Change the identity import to `from .storage.identity import EXECUTION_NAME_ENV, OPERATOR_TOKEN_SCOPE, principal_from_token, worker_client_id`.

Replace the first loop of `_parser` (through the `transform` `--force` line) with:

```python
    for command in ('discover', 'collect', 'transform', 'publish', *WORKFLOW_COMMANDS):
        sub = commands.add_parser(command)
        workflow = command in WORKFLOW_COMMANDS
        if workflow:
            source = sub.add_mutually_exclusive_group(required=True)
            source.add_argument('--config')
            source.add_argument('--config-env', metavar='NAME',
                                help='read the configuration JSON from this environment variable')
            sub.add_argument('--execution-id', help='local-fixture only; Azure uses ' + EXECUTION_NAME_ENV)
        for name in ('config', 'run-id', 'execution-id', 'attempt-id', 'deadline'):
            if not (workflow and name in ('config', 'execution-id')):
                sub.add_argument('--' + name, required=True)
        for name in ('state-dir', 'today'):
            sub.add_argument('--' + name)
        if command in ('discover', 'collect', *WORKFLOW_COMMANDS):
            sub.add_argument('--fixture-pack')
        if command == 'discover':
            sub.add_argument('--mode', required=True, choices=('quarterly', 'daily'))
            sub.add_argument('--discovery-id', required=True)
            sub.add_argument('--refresh', action='store_true')
        elif command in ('collect', 'transform', 'publish'):
            sub.add_argument('--workset', required=True)
        if command == 'transform':
            sub.add_argument('--force', action='store_true')
```

Replace the head of `_validate_workflow`, from `def _validate_workflow(args):` through `settings = load_config(Path(args.config))` (the `_segment` loop and the config load), with:

```python
def _validate_workflow(args):
    for name in ('run_id', 'attempt_id'):
        _segment(getattr(args, name), name)
    settings = (load_config_env(args.config_env, os.environ) if args.config_env is not None
                else load_config(Path(args.config)))
    if settings.storage.backend == 'azure':
        if args.execution_id is not None:
            raise ValueError('--execution-id is refused on Azure; the job execution name is used')
        # The workflow path reads the resolved execution ID from args from here on.
        args.execution_id = os.environ.get(EXECUTION_NAME_ENV, '')
        if not args.execution_id:
            raise ValueError(f'{EXECUTION_NAME_ENV} must name the job execution on Azure')
    elif args.execution_id is None:
        raise ValueError('local-fixture workflow commands require --execution-id')
    _segment(args.execution_id, 'execution_id')
```

and in the same function replace its Azure branch:

```python
    if settings.storage.backend == 'azure':
        if args.fixture_pack or args.state_dir or args.today:
            raise ValueError('fixture pack, state directory and date override are fixture-only')
        pack = None
```

with:

```python
    if settings.storage.backend == 'azure':
        if args.fixture_pack or args.state_dir or args.today:
            raise ValueError('fixture pack, state directory and date override are fixture-only')
        worker_client_id(os.environ)
        pack = None
```

The rest of `_validate_workflow` stays as it is.

- [ ] **Step 5: Document the Azure invocation**

Append to `packages/sec-edgar-ingest/README.md`:

```markdown
Workflow commands (`backfill`, `daily`, `reconcile`) take exactly one of `--config PATH` or
`--config-env NAME`; the latter reads the same strict JSON from that environment variable. On Azure, the job
sets `SEC_EDGAR_INGEST_CONFIG` from its `ingest-config` secret and `SEC_EDGAR_INGEST_WORKER_CLIENT_ID` to the
worker identity, and Container Apps sets `CONTAINER_APP_JOB_EXECUTION_NAME`. A workflow command there takes
its execution ID from that variable and refuses `--execution-id`, so its result names the real execution.
Stage commands keep `--config` and `--execution-id`.
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_workflow_config_env test_workflow_cli test_azure_identity test_config -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/config.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/test_workflow_config_env.py packages/sec-edgar-ingest/README.md
git commit -m "feat(ingest): read workflow config and execution ID from the job environment

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: `workflow_summary` telemetry and the reconcile milestone

**Files:**
- Create: `src/sec_edgar_ingest/workflows/summary.py`
- Modify: `src/sec_edgar_ingest/cli.py` (`_workflow_main`, after the `command_finished` log at lines 425–427)
- Create: `tests/support_scenario.py`
- Create: `tests/test_workflow_summary.py`

**Interfaces:**
- Consumes: `withdrawal_candidates` (existing), `WorkflowResult`, `member_status`, `log_event`, `exit_code`.
- Produces:
  - `workflows.summary`: `MILESTONE_KIND = 'WorkflowMilestone'`, `RECONCILE_MILESTONE = 'reconcile'`, `SUMMARY_FIELDS` (frozenset), `describe(result) -> dict`, `record_reconcile_success(result, reference, store) -> None`, `last_successful_reconcile(store) -> str | None` and `emit_summary(result, reference, objects, store) -> None`.
  - A `workflow_summary` stderr event after `command_finished` on every fresh workflow result.
  - Test support `support_scenario`: `TODAY`, `BASE_Q3`, `GATED_Q3`, `scenario_settings()` and `scenario_pack(root, name, q3) -> Path` (the manifest path).

- [ ] **Step 1: Write the scenario support module**

`tests/support_scenario.py`:

```python
"""Backfill, daily and a gated reconcile on fixture packs: shared by the summary tests and the image smoke."""
from pathlib import Path

from support import fixture_settings
from support_reconcile import A, B, X, Y, Q3_URL, Q4_URL, quarterly
from support_workflows import quarter_pack, replace_pack_body

TODAY = '2026-10-07'
BASE_Q3 = (A, B)
GATED_Q3 = (A,)


def scenario_settings():
    return fixture_settings(backfill={'start_quarter': '2026Q3', 'end_quarter': 'open'},
                            daily={'start_date': '2026-10-01'}, etl={'parser_version': 'fixture-index-parser-v1'},
                            http={'retry_base_seconds': 0.001, 'retry_cap_seconds': 0.001},
                            fixture={'allow_clock_override': True, 'allow_deadline_override': False})


def scenario_pack(root: Path, name: str, q3: tuple) -> Path:
    """A pack whose 2026Q3 quarterly lists `q3` and whose 2026Q4 quarterly lists X and Y; returns its manifest."""
    pack = quarter_pack(Path(root) / name, ('2026Q3', '2026Q4'), empty_daily=True)
    replace_pack_body(pack, Q3_URL, quarterly(q3))
    replace_pack_body(pack, Q4_URL, quarterly((X, Y)))
    return pack
```

- [ ] **Step 2: Write the failing tests**

`tests/test_workflow_summary.py`:

```python
"""One `workflow_summary` per fresh workflow result; it never changes the result, stdout or exit code."""
from network_guard import install
install()

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from support_approval import operator_cli
from support_reconcile import sha
from support_scenario import BASE_Q3, GATED_Q3, scenario_pack, scenario_settings
from support_workflows import CommandHarness
from sec_edgar_ingest.workflows.summary import (MILESTONE_KIND, RECONCILE_MILESTONE, SUMMARY_FIELDS,
                                                last_successful_reconcile, record_reconcile_success)


class WorkflowSummaryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.h = CommandHarness(self.root, scenario_pack(self.root, 'pack-1', BASE_Q3), scenario_settings())
        self.addCleanup(self.h.close)

    def events(self):
        return [json.loads(line) for line in self.h.calls[-1]['stderr'].splitlines()]

    def summary(self):
        events = self.events()
        self.assertEqual([event['event'] for event in events[-2:]], ['command_finished', 'workflow_summary'])
        self.assertEqual(set(events[-1]['fields']), SUMMARY_FIELDS)
        return events[-1]['fields']

    def gate(self):
        self.assertEqual(self.h.invoke('backfill', run='base')[0], 0)
        self.assertEqual(self.h.invoke('daily', run='day')[0], 0)
        self.h.pack = scenario_pack(self.root, 'pack-2', GATED_Q3)
        self.assertEqual(self.h.invoke('reconcile', run='gate')[0], 10)

    def test_each_fresh_result_logs_one_summary_after_command_finished(self):
        self.assertEqual(self.h.invoke('backfill', run='base')[0], 0)
        fields = self.summary()
        self.assertEqual((fields['command'], fields['outcome'], fields['summary_error']), ('backfill', 'success', None))
        self.assertEqual(fields['counts'], self.h.calls[-1]['stdout']['counts'])
        self.assertEqual(fields['result_ref'], self.h.calls[-1]['stdout']['result_ref'])
        self.assertEqual(self.h.invoke('daily', run='day')[0], 0)
        fields = self.summary()
        self.assertEqual((fields['outcome'], fields['discovery_complete'], fields['pending_approvals'],
                          fields['last_successful_reconcile_at']), ('no_new_sources', True, 0, None))

    def test_a_gated_reconcile_reports_its_pending_approval_and_oldest_unresolved_source(self):
        self.gate()
        fields = self.summary()
        self.assertEqual((fields['outcome'], fields['pending_approvals'], fields['oldest_unresolved_period'],
                          fields['last_successful_reconcile_at']), ('awaiting_approval', 1, '2026Q3', None))
        self.assertGreaterEqual(fields['member_outcomes']['awaiting_approval'], 1)

    def test_a_successful_reconcile_advances_the_milestone_that_every_summary_reports(self):
        self.gate()
        listing = operator_cli('candidates', '--config', str(self.h.config), '--state-dir', str(self.root))[1]
        request, = listing['candidates']
        approved = operator_cli('approve', '--config', str(self.h.config), '--state-dir', str(self.root),
                                '--quarter', '2026Q3', '--generation', request['generation_id'],
                                '--quarterly-sha256', sha(GATED_Q3), '--approver', 'Lowell Mason')
        self.assertEqual(approved[0], 0)
        self.assertEqual(self.h.invoke('reconcile', run='after')[0], 0)
        reference = self.h.calls[-1]['stdout']['result_ref']
        ended_at = json.loads(self.h.objects.read(reference))['ended_at']
        self.assertEqual(self.summary()['last_successful_reconcile_at'], ended_at)
        self.assertEqual(dict(self.h.store.get(MILESTONE_KIND, RECONCILE_MILESTONE).value),
                         {'workflow': 'reconcile', 'ended_at': ended_at, 'result_ref': reference})
        self.assertEqual(self.h.invoke('daily', run='day2')[0], 0)
        self.assertEqual(self.summary()['last_successful_reconcile_at'], ended_at)

    def test_the_milestone_only_moves_forward_on_an_exit_zero_reconcile(self):
        now = datetime.now(timezone.utc)

        def result(command, outcome, at):
            return SimpleNamespace(context=SimpleNamespace(command=command), outcome=outcome, ended_at=at.isoformat())
        record_reconcile_success(result('reconcile', 'unchanged', now), 'runs/sec/a/reconcile/a/result.json',
                                 self.h.store)
        for ignored in (result('reconcile', 'unchanged', now - timedelta(days=1)),
                        result('reconcile', 'awaiting_approval', now + timedelta(days=1)),
                        result('daily', 'success', now + timedelta(days=1))):
            record_reconcile_success(ignored, 'runs/sec/b/reconcile/a/result.json', self.h.store)
        self.assertEqual(last_successful_reconcile(self.h.store), now.isoformat())
        later = now + timedelta(days=2)
        record_reconcile_success(result('reconcile', 'success', later), 'runs/sec/c/reconcile/a/result.json',
                                 self.h.store)
        self.assertEqual(last_successful_reconcile(self.h.store), later.isoformat())

    def test_a_failed_extra_is_reported_without_changing_the_outcome(self):
        with patch('sec_edgar_ingest.workflows.summary.withdrawal_candidates',
                   side_effect=RuntimeError('listing exploded')):
            code, message = self.h.invoke('backfill', run='base')
        self.assertEqual((code, message['outcome']), (0, 'success'))
        self.assertEqual(self.summary()['summary_error'], {'type': 'RuntimeError', 'message': 'listing exploded'})

    def test_a_replayed_result_logs_no_summary(self):
        self.assertEqual(self.h.invoke('backfill', run='base')[0], 0)
        self.assertEqual(self.h.invoke('backfill', run='base')[0], 0)
        self.assertEqual([event['event'] for event in self.events()][-1], 'result_replayed')
        self.assertNotIn('workflow_summary', [event['event'] for event in self.events()])

    def test_workflow_commands_write_no_approval_evidence(self):
        self.gate()
        with sqlite3.connect(self.root / '.fixture-state' / 'state.sqlite3') as database:
            rows = database.execute("SELECT COUNT(*) FROM records WHERE table_name='Approvals'").fetchone()[0]
        self.assertEqual(rows, 0)
        self.assertFalse((self.h.objects.directory / 'approvals').exists())


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_workflow_summary -v`
Expected: ERROR at import with `ModuleNotFoundError: No module named 'sec_edgar_ingest.workflows.summary'`.

- [ ] **Step 4: Implement `workflows/summary.py`**

```python
"""Alerting telemetry for one fresh workflow result. It never changes the result, stdout or exit code."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime

from ..etl.history import withdrawal_candidates
from ..etl.state import EtlState
from ..models import error_text, quarter_value
from ..results import exit_code, log_event
from ..storage.contracts import AlreadyExists, CAS_ATTEMPTS, Conflict, ObjectStore, StateStore
from .contracts import WorkflowResult, member_status

MILESTONE_KIND = 'WorkflowMilestone'
RECONCILE_MILESTONE = 'reconcile'
SUMMARY_FIELDS = frozenset({'result_ref', 'command', 'outcome', 'counts', 'member_outcomes', 'gap_codes',
                            'discovery_complete', 'boundary_after', 'oldest_unresolved_period',
                            'pending_approvals', 'last_successful_reconcile_at', 'summary_error'})


def _period_start(period: str) -> date:
    if 'Q' in period:
        year, ordinal = quarter_value(period)
        return date(year, 3 * ordinal - 2, 1)
    return date.fromisoformat(period)


def describe(result: WorkflowResult) -> dict[str, object]:
    """Counts by name and discovery facts, read from the result alone."""
    unresolved = [member.source.period for member in result.members if member_status(member.outcome) != 'complete']
    codes = Counter(gap.code for gap in result.gaps)
    codes.update(gap.code for member in result.members for gap in member.gaps)
    return {'member_outcomes': dict(sorted(Counter(member.outcome for member in result.members).items())),
            'gap_codes': dict(sorted(codes.items())),
            'discovery_complete': bool(result.directories) and all(
                directory['outcome'] != 'discovery_failed' for directory in result.directories),
            'oldest_unresolved_period': min(unresolved, key=_period_start, default=None)}


def last_successful_reconcile(store: StateStore) -> str | None:
    row = store.get(MILESTONE_KIND, RECONCILE_MILESTONE)
    return None if row is None else row.value['ended_at']


def record_reconcile_success(result: WorkflowResult, reference: str, store: StateStore) -> None:
    """Advance the reconcile milestone to an exit-0 reconcile result. It only moves forward and can be
    rebuilt from results."""
    if result.context.command != 'reconcile' or exit_code(result.outcome) != 0:
        return
    value = {'workflow': RECONCILE_MILESTONE, 'ended_at': result.ended_at, 'result_ref': reference}
    for _ in range(CAS_ATTEMPTS):
        current = store.get(MILESTONE_KIND, RECONCILE_MILESTONE)
        try:
            if current is None:
                store.insert(MILESTONE_KIND, RECONCILE_MILESTONE, value)
            elif datetime.fromisoformat(current.value['ended_at']) < datetime.fromisoformat(result.ended_at):
                store.replace(MILESTONE_KIND, RECONCILE_MILESTONE, value, current.version)
            return
        except (AlreadyExists, Conflict):
            continue
    raise Conflict('reconcile milestone exhausted conditional races')


def emit_summary(result: WorkflowResult, reference: str, objects: ObjectStore, store: StateStore) -> None:
    """Log one `workflow_summary`. A failure of any extra lands in `summary_error`, never in the outcome."""
    fields = {'result_ref': reference, 'command': result.context.command, 'outcome': result.outcome,
              'counts': dict(result.counts), 'member_outcomes': None, 'gap_codes': None,
              'discovery_complete': None, 'boundary_after': result.boundary_after,
              'oldest_unresolved_period': None, 'pending_approvals': None,
              'last_successful_reconcile_at': None, 'summary_error': None}
    try:
        fields.update(describe(result))
        record_reconcile_success(result, reference, store)
        fields['last_successful_reconcile_at'] = last_successful_reconcile(store)
        fields['pending_approvals'] = sum(entry['status'] == 'pending'
                                          for entry in withdrawal_candidates(objects, EtlState(store)))
    except Exception as error:
        fields['summary_error'] = {'type': type(error).__name__, 'message': error_text(error)}
    log_event(result.context, 'workflow_summary', fields)
```

- [ ] **Step 5: Call it after `command_finished`**

In `cli.py`, add `from .workflows.summary import emit_summary`, and in `_workflow_main` replace:

```python
        log_event(context, 'command_finished', {'outcome': result.outcome,
            'result_ref': reference, 'counters': result.to_mapping()['counts']})
        return _workflow_stdout(result, reference)
```

with:

```python
        log_event(context, 'command_finished', {'outcome': result.outcome,
            'result_ref': reference, 'counters': result.to_mapping()['counts']})
        emit_summary(result, reference, objects, store)
        return _workflow_stdout(result, reference)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_workflow_summary test_workflow_cli test_reconcile_workflow test_reconcile_acceptance -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/summary.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/support_scenario.py packages/sec-edgar-ingest/tests/test_workflow_summary.py
git commit -m "feat(ingest): log a workflow summary and advance the reconcile milestone

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Azure config template, renderer and golden binding

**Files:**
- Create: `infra/azure/sec-edgar-ingest/config/sec-edgar-ingest.azure.template.json`
- Create: `infra/azure/sec-edgar-ingest/config/deployment-binding.json`
- Create: `src/sec_edgar_ingest/deployment.py`
- Create: `tests/test_azure_config_template.py`

**Interfaces:**
- Consumes: `Settings`, `deployment_binding`, `payload_bytes`, `load_config_env` (Task 6).
- Produces:
  - `deployment.render_azure_config(template: bytes, image_digest: str, provenance: str) -> tuple[bytes, str]` (canonical bytes, `config_sha256`).
  - `deployment.arm_parameters(body: bytes, config_sha256: str) -> dict`.
  - `deployment.main(argv)`: `python -m sec_edgar_ingest.deployment --template PATH --image-digest sha256:… --provenance TEXT --out-dir DIR` writes `sec-edgar-ingest.azure.json` and `main.parameters.json`.
  - Plan 10 reads the template and golden paths above.

- [ ] **Step 1: Write the template**

`infra/azure/sec-edgar-ingest/config/sec-edgar-ingest.azure.template.json`. Every section except `storage`, `etl.parser_version` and the omitted `worker` equals `conf/sec-edgar-ingest.yaml`, the accepted §4.8 defaults:

```json
{
  "config_version": "sec-acquisition-v1",
  "backfill": {
    "start_quarter": "2015Q1",
    "end_quarter": "open"
  },
  "daily": {
    "start_date": "2026-10-01"
  },
  "sec": {
    "user_agent": "Lowell Mason sec-edgar-ingest mason.lowell@mac.com",
    "requests_per_second": 3,
    "max_active_collectors": 1
  },
  "http": {
    "max_attempts": 5,
    "retry_base_seconds": 2,
    "retry_cap_seconds": 120,
    "connect_timeout_seconds": 15,
    "read_timeout_seconds": 60,
    "exchange_deadline_seconds": 90,
    "max_received_bytes": 67108864,
    "max_expanded_bytes": 536870912
  },
  "coordination": {
    "lease_seconds": 60,
    "renew_every_seconds": 20,
    "namespace": "sec-owner-lowell-mason",
    "clock_uncertainty_seconds": 2
  },
  "storage": {
    "backend": "azure",
    "account_name": "secedgardevb8617",
    "blob_endpoint": "https://secedgardevb8617.blob.core.windows.net",
    "table_endpoint": "https://secedgardevb8617.table.core.windows.net",
    "raw_container": "raw",
    "workset_container": "worksets",
    "quarantine_container": "quarantine",
    "lock_container": "locks",
    "lock_blob": "sec-owner-lowell-mason/sentinel.json",
    "binding_registry_blob": "sec-owner-lowell-mason/binding.json",
    "source_table": "SourceState",
    "attempt_table": "Attempts",
    "blob_api_version": "2026-04-06",
    "table_api_version": "2020-12-06"
  },
  "etl": {
    "parser_version": "sec-index-parser-v1",
    "schema_version": "sec-index-v1"
  },
  "jobs": {
    "replica_retry_limit": 0
  },
  "orchestration": {
    "transient_replays": 1
  },
  "reconciliation": {
    "require_withdrawal_approval": true
  }
}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_azure_config_template.py`:

```python
"""The versioned Azure config template renders one canonical config whose binding is frozen."""
from network_guard import install
install()

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from sec_edgar_ingest.config import Settings, load_config_env
from sec_edgar_ingest.deployment import main as deployment_main, render_azure_config
from sec_edgar_ingest.models import canonical_json, to_mapping_value
from sec_edgar_ingest.storage.contracts import deployment_binding, payload_bytes

REPO = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO / 'infra/azure/sec-edgar-ingest/config'
TEMPLATE = CONFIG_DIR / 'sec-edgar-ingest.azure.template.json'
GOLDEN = CONFIG_DIR / 'deployment-binding.json'
SHIPPED = REPO / 'conf/sec-edgar-ingest.yaml'
DIGEST = 'sha256:' + '1' * 64


def render(template=None, digest=DIGEST, provenance='stage-6-offline-test'):
    return render_azure_config(TEMPLATE.read_bytes() if template is None else template, digest, provenance)


def binding(body: bytes) -> bytes:
    return payload_bytes(deployment_binding(Settings.from_mapping(json.loads(body))))


class AzureConfigTemplateTests(unittest.TestCase):
    def test_rendered_config_is_canonical_and_identifies_itself(self):
        body, digest = render()
        settings = Settings.from_mapping(json.loads(body))
        self.assertEqual(body, canonical_json(to_mapping_value(settings.to_mapping())))
        self.assertEqual((digest, hashlib.sha256(body).hexdigest()), (settings.config_sha256,) * 2)
        self.assertEqual((settings.storage.backend, settings.etl.parser_version, settings.worker.image_digest),
                         ('azure', 'sec-index-parser-v1', DIGEST))
        self.assertEqual(load_config_env('SEC_EDGAR_INGEST_CONFIG',
                                         {'SEC_EDGAR_INGEST_CONFIG': body.decode()}).config_sha256, digest)

    def test_every_value_outside_storage_and_parser_is_the_accepted_default(self):
        template, shipped = json.loads(TEMPLATE.read_text()), json.loads(SHIPPED.read_text())
        self.assertEqual(set(template), set(shipped) - {'worker'})
        for section in set(shipped) - {'storage', 'etl', 'worker'}:
            self.assertEqual(template[section], shipped[section], section)
        self.assertEqual(template['etl'], {**shipped['etl'], 'parser_version': 'sec-index-parser-v1'})
        self.assertEqual((template['backfill'], template['daily']),
                         ({'start_quarter': '2015Q1', 'end_quarter': 'open'}, {'start_date': '2026-10-01'}))

    def test_endpoints_are_spelled_without_a_trailing_slash(self):
        storage = json.loads(TEMPLATE.read_text())['storage']
        self.assertEqual((storage['blob_endpoint'], storage['table_endpoint']),
                         ('https://secedgardevb8617.blob.core.windows.net',
                          'https://secedgardevb8617.table.core.windows.net'))

    def test_the_golden_binding_freezes_every_bound_value(self):
        for digest in (DIGEST, 'sha256:' + '2' * 64):
            self.assertEqual(binding(render(digest=digest)[0]), GOLDEN.read_bytes())
        template = json.loads(TEMPLATE.read_text())
        template['storage']['blob_endpoint'] += '/'
        self.assertNotEqual(binding(render(json.dumps(template).encode())[0]), GOLDEN.read_bytes())

    def test_the_renderer_refuses_fixture_values_and_a_worker_section(self):
        template = json.loads(TEMPLATE.read_text())
        cases = {'worker section': {**template, 'worker': {'image_digest': DIGEST, 'provenance': 'x'}},
                 'local backend': {**template, 'storage': {**template['storage'], 'backend': 'local-fixture'}},
                 'fixture parser': {**template, 'etl': {**template['etl'], 'parser_version': 'fixture-index-parser-v1'}}}
        for label, value in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                render(json.dumps(value).encode())
        for digest, provenance in (('sha256:' + '0' * 64, 'release'), (DIGEST, 'synthetic-fixture'), ('latest', 'release')):
            with self.subTest(digest=digest, provenance=provenance), self.assertRaises(ValueError):
                render(digest=digest, provenance=provenance)

    def test_the_cli_writes_the_config_and_arm_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'rendered'
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = deployment_main(['--template', str(TEMPLATE), '--image-digest', DIGEST,
                                        '--provenance', 'stage-6-offline-test', '--out-dir', str(out)])
            self.assertEqual(code, 0)
            body = (out / 'sec-edgar-ingest.azure.json').read_bytes()
            digest = hashlib.sha256(body).hexdigest()
            parameters = json.loads((out / 'main.parameters.json').read_text())
            self.assertEqual(parameters['parameters'], {'configJson': {'value': body.decode()},
                                                        'configSha256': {'value': digest}})
            self.assertEqual(json.loads(stdout.getvalue())['config_sha256'], digest)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_config_template -v`
Expected: ERROR at import with `ModuleNotFoundError: No module named 'sec_edgar_ingest.deployment'`.

- [ ] **Step 4: Implement the renderer**

`src/sec_edgar_ingest/deployment.py`:

```python
"""Render the versioned Azure config template into deployment inputs. Offline: no Azure call."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .config import Settings
from .models import canonical_json, parse_json, to_mapping_value

ARM_PARAMETERS_SCHEMA = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#'


def render_azure_config(template: bytes, image_digest: str, provenance: str) -> tuple[bytes, str]:
    """The template plus the image digest and provenance, validated through Settings, as canonical bytes
    and their config_sha256."""
    value = parse_json(template)
    if not isinstance(value, dict) or 'worker' in value:
        raise ValueError('the Azure template must be an object without a worker section')
    settings = Settings.from_mapping({**value, 'worker': {'image_digest': image_digest, 'provenance': provenance}})
    if settings.storage.backend != 'azure':
        raise ValueError('the Azure template must select the azure backend')
    body = canonical_json(to_mapping_value(settings.to_mapping()))
    if hashlib.sha256(body).hexdigest() != settings.config_sha256:
        raise ValueError('rendered bytes differ from the configuration identity')
    return body, settings.config_sha256


def arm_parameters(body: bytes, config_sha256: str) -> dict[str, object]:
    return {'$schema': ARM_PARAMETERS_SCHEMA, 'contentVersion': '1.0.0.0',
            'parameters': {'configJson': {'value': body.decode('utf-8')},
                           'configSha256': {'value': config_sha256}}}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m sec_edgar_ingest.deployment')
    parser.add_argument('--template', required=True)
    parser.add_argument('--image-digest', required=True)
    parser.add_argument('--provenance', required=True)
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args(argv)
    try:
        body, config_sha256 = render_azure_config(Path(args.template).read_bytes(), args.image_digest,
                                                  args.provenance)
    except (ValueError, OSError, TypeError) as error:
        sys.stderr.write(json.dumps({'outcome': 'configuration', 'error': str(error)}) + '\n')
        return 2
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    config, parameters = out / 'sec-edgar-ingest.azure.json', out / 'main.parameters.json'
    config.write_bytes(body)
    parameters.write_text(json.dumps(arm_parameters(body, config_sha256), indent=2, sort_keys=True) + '\n')
    sys.stdout.write(json.dumps({'config_sha256': config_sha256, 'config': str(config),
                                 'parameters': str(parameters)}, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 5: Write the golden binding and check it against the planned bytes**

```bash
uv run --offline --frozen --package sec-edgar-ingest python - <<'EOF'
import json
from pathlib import Path
from sec_edgar_ingest.config import Settings
from sec_edgar_ingest.deployment import render_azure_config
from sec_edgar_ingest.storage.contracts import deployment_binding, payload_bytes
config = Path('infra/azure/sec-edgar-ingest/config')
body, _ = render_azure_config((config / 'sec-edgar-ingest.azure.template.json').read_bytes(), 'sha256:' + '1' * 64, 'golden')
(config / 'deployment-binding.json').write_bytes(payload_bytes(deployment_binding(Settings.from_mapping(json.loads(body)))))
EOF
cat infra/azure/sec-edgar-ingest/config/deployment-binding.json; echo
```

Expected: exactly these bytes, which were computed independently during planning (no trailing newline in the file):

```text
{"account":"secedgardevb8617","binding_version":"sec-owner-binding-v1","coordination":{"clock_uncertainty_seconds":2.0,"lease_seconds":60.0,"namespace":"sec-owner-lowell-mason","renew_every_seconds":20.0},"namespace":"sec-owner-lowell-mason","sec":{"max_active_collectors":1,"requests_per_second":3.0,"user_agent":"Lowell Mason sec-edgar-ingest mason.lowell@mac.com"},"storage":{"account_name":"secedgardevb8617","attempt_table":"Attempts","backend":"azure","binding_registry_blob":"sec-owner-lowell-mason/binding.json","blob_api_version":"2026-04-06","blob_endpoint":"https://secedgardevb8617.blob.core.windows.net","local_root":null,"lock_blob":"sec-owner-lowell-mason/sentinel.json","lock_container":"locks","quarantine_container":"quarantine","raw_container":"raw","source_table":"SourceState","table_api_version":"2020-12-06","table_endpoint":"https://secedgardevb8617.table.core.windows.net","workset_container":"worksets"}}
```

If the bytes differ, stop: the binding would differ from the one the first Azure open writes. Report it rather than editing the expectation.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_azure_config_template -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add infra/azure/sec-edgar-ingest/config packages/sec-edgar-ingest/src/sec_edgar_ingest/deployment.py packages/sec-edgar-ingest/tests/test_azure_config_template.py
git commit -m "feat(infra): add the Azure config template, renderer and golden binding

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Spec amendment — the base image reference

Applies only if the owner approves it at plan review (Decisions, item 5). If declined, drop this task. Task 10 then uses `FROM docker.io/library/python:3.14.8-slim-bookworm@sha256:d1e795fbdab8a4744432467f32f348c6baa99f07abc05ffde710913f65c8261d`, and its `BASE` constant changes to match.

**Files:**
- Modify: `specs/sec-filing-index-ingestion-stage-6-spec.md` (§3, the **Base** bullet; the status line is untouched)

- [ ] **Step 1: Apply the amendment**

Replace:

```text
- **Base:** `infra/azure/sec-edgar-ingest/image/Dockerfile` starts `FROM docker.io/library/python:3.14.8-slim-bookworm@sha256:d1e795fb…`. That is the amd64 child digest, so no platform selection is needed.
```

with:

```text
- **Base:** `infra/azure/sec-edgar-ingest/image/Dockerfile` starts `FROM docker.io/library/python@sha256:d1e795fb…`, the exact reference F1's successful quick task used. That is `python:3.14.8-slim-bookworm`'s Linux amd64 child digest, so no platform selection is needed. (owner, plan 9, 2026-10-12)
```

- [ ] **Step 2: Commit**

```bash
git add specs/sec-filing-index-ingestion-stage-6-spec.md
git commit -m "docs(specs): use F1's proven base image reference in the Stage 6 spec

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Worker image definition and build context

**Files:**
- Create: `infra/azure/sec-edgar-ingest/image/Dockerfile`
- Create: `infra/azure/sec-edgar-ingest/image/requirements.lock` (byte copy)
- Create: `scripts/build-image-context.sh`
- Create: `tests/test_image_definition.py`

**Interfaces:**
- Produces: `scripts/build-image-context.sh OUT_DIR`, which writes `Dockerfile`, `requirements.lock` and exactly one `sec_edgar_ingest-*.whl` into a new or empty `OUT_DIR`. The image runs as UID 1000, has `ENTRYPOINT ["sec-edgar-ingest"]` and `TMPDIR=/tmp/sec-edgar-ingest`. Task 11 and Plan 10 (the Stage 7 handoff) use it.

- [ ] **Step 1: Write the failing test**

`tests/test_image_definition.py`:

```python
"""The worker image definition: F1's base and lock, no platform selection, UID 1000, no configuration."""
from network_guard import install
install()

import hashlib
import os
import re
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
IMAGE = REPO / 'infra/azure/sec-edgar-ingest/image'
F1_LOCK = REPO / 'specs/evidence/sec-filing-index-ingestion/stage-1/runtime/requirements.lock'
BASE = 'docker.io/library/python@sha256:d1e795fbdab8a4744432467f32f348c6baa99f07abc05ffde710913f65c8261d'
LOCK_SHA256 = '523b2da36079ce4a7c6b11ac06feb0a7992a8c3aef757c32909850685023b5c2'


def normalize(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def instructions(text: str) -> list[str]:
    """Dockerfile instructions with line continuations joined and comments dropped."""
    joined = re.sub(r'\\\n\s*', ' ', text)
    return [line.strip() for line in joined.splitlines() if line.strip() and not line.lstrip().startswith('#')]


class ImageDefinitionTests(unittest.TestCase):
    def setUp(self):
        self.text = (IMAGE / 'Dockerfile').read_text()
        self.lines = instructions(self.text)

    def test_base_is_f1s_child_digest_on_the_first_line_without_platform_selection(self):
        self.assertEqual(self.text.splitlines()[0], 'FROM ' + BASE)
        self.assertEqual([line for line in self.lines if line.startswith('FROM ')], ['FROM ' + BASE])
        self.assertNotIn('--platform', self.text)

    def test_runtime_user_entrypoint_and_temporary_space(self):
        self.assertIn('USER 1000:1000', self.lines)
        self.assertEqual(self.lines[-1], 'ENTRYPOINT ["sec-edgar-ingest"]')
        self.assertIn('ENV TMPDIR=/tmp/sec-edgar-ingest', self.lines)
        run, = [line for line in self.lines if line.startswith('RUN ')]
        for fragment in ('pip install --require-hashes --no-deps --only-binary=:all: -r /build/requirements.lock',
                         'pip install --no-deps /build/sec_edgar_ingest-', 'pip check',
                         'chown 1000:1000 /home/worker /tmp/sec-edgar-ingest'):
            self.assertIn(fragment, run)
        self.assertFalse(any(line.startswith(('VOLUME', 'ADD ')) for line in self.lines))
        self.assertNotIn('SEC_EDGAR_INGEST_CONFIG', self.text)

    def test_lock_is_f1s_exact_bytes_and_matches_uv_lock(self):
        body = (IMAGE / 'requirements.lock').read_bytes()
        self.assertEqual(hashlib.sha256(body).hexdigest(), LOCK_SHA256)
        self.assertEqual(body, F1_LOCK.read_bytes())
        pins = {}
        for line in body.decode().splitlines():
            name, pinned = re.fullmatch(r'([A-Za-z0-9_.-]+)==(\S+) --hash=sha256:[0-9a-f]{64}', line).groups()
            pins[normalize(name)] = pinned
        resolved = {normalize(package['name']): package['version']
                    for package in tomllib.loads((REPO / 'uv.lock').read_text())['package']}
        self.assertEqual(len(pins), 21)
        self.assertEqual(pins, {name: resolved[name] for name in pins})

    def test_the_context_script_is_executable(self):
        self.assertTrue(os.access(REPO / 'scripts/build-image-context.sh', os.X_OK))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_image_definition -v`
Expected: ERROR with `FileNotFoundError` for `infra/azure/sec-edgar-ingest/image/Dockerfile`.

- [ ] **Step 3: Write the Dockerfile and copy the lock**

`infra/azure/sec-edgar-ingest/image/Dockerfile`. `FROM` stays the literal first line, as in F1's accepted quick-task context:

```dockerfile
FROM docker.io/library/python@sha256:d1e795fbdab8a4744432467f32f348c6baa99f07abc05ffde710913f65c8261d
# sec-edgar-ingest worker. Context: scripts/build-image-context.sh. Stage 6 builds it locally (D1);
# Stage 7 builds the release image with an ACR quick task (S7-05). The base is F1's Linux amd64 child
# digest, so the platform is never selected here. The image carries no configuration.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HOME=/home/worker
COPY requirements.lock /build/requirements.lock
COPY sec_edgar_ingest-*.whl /build/
RUN python -m pip install --require-hashes --no-deps --only-binary=:all: -r /build/requirements.lock \
 && python -m pip install --no-deps /build/sec_edgar_ingest-*.whl \
 && python -m pip check \
 && rm -rf /build \
 && mkdir -p /home/worker /tmp/sec-edgar-ingest \
 && chown 1000:1000 /home/worker /tmp/sec-edgar-ingest \
 && chmod 0700 /tmp/sec-edgar-ingest
ENV TMPDIR=/tmp/sec-edgar-ingest
USER 1000:1000
WORKDIR /home/worker
ENTRYPOINT ["sec-edgar-ingest"]
```

`TMPDIR` is set only after the `RUN`, because pip needs a temporary directory that already exists.

```bash
mkdir -p infra/azure/sec-edgar-ingest/image
cp specs/evidence/sec-filing-index-ingestion/stage-1/runtime/requirements.lock infra/azure/sec-edgar-ingest/image/requirements.lock
shasum -a 256 infra/azure/sec-edgar-ingest/image/requirements.lock
```

Expected: `523b2da36079ce4a7c6b11ac06feb0a7992a8c3aef757c32909850685023b5c2`.

- [ ] **Step 4: Write the build context script**

`scripts/build-image-context.sh`:

```sh
#!/bin/sh
# Assemble the worker image build context: Dockerfile, F1's hash-pinned lock and the offline-built wheel.
# The same context serves the Stage 6 local build and the Stage 7 ACR quick task.
set -eu
[ $# -eq 1 ] || { echo "usage: scripts/build-image-context.sh OUT_DIR" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$1"
out=$(CDPATH= cd -- "$1" && pwd)
if [ -n "$(ls -A "$out")" ]; then
  echo "context directory must be new or empty: $out" >&2
  exit 2
fi
cp "$root/infra/azure/sec-edgar-ingest/image/Dockerfile" "$root/infra/azure/sec-edgar-ingest/image/requirements.lock" "$out/"
(cd "$root" && uv build --offline --package sec-edgar-ingest --wheel --out-dir "$out" >&2)
count=$(find "$out" -maxdepth 1 -name 'sec_edgar_ingest-*.whl' | wc -l | tr -d ' ')
[ "$count" -eq 1 ] || { echo "expected exactly one wheel in $out, found $count" >&2; exit 1; }
ls -1 "$out"
```

```bash
chmod +x scripts/build-image-context.sh
scripts/build-image-context.sh /tmp/s6-image-context-check
```

Expected: stdout lists `Dockerfile`, `requirements.lock` and `sec_edgar_ingest-0.1.0-py3-none-any.whl`; uv may also leave a `.gitignore`. Re-running into the same directory exits 2 with `context directory must be new or empty`. Then `rm -r /tmp/s6-image-context-check`, which is this step's own scratch output.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py test_image_definition -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add infra/azure/sec-edgar-ingest/image scripts/build-image-context.sh packages/sec-edgar-ingest/tests/test_image_definition.py
git commit -m "feat(infra): define the worker image and its build context

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Local Linux amd64 build and the image smoke (D1)

This task installs local tools under D1 and builds and runs the image. Pulling the pinned base image by digest and the 21 hash-pinned wheels are the only network access (Decisions, item 4). There are no Azure or SEC calls, and the containers run with `--network none`.

**Files:**
- Create: `packages/sec-edgar-ingest/tests/image_smoke.py`

**Interfaces:**
- Consumes: `scripts/build-image-context.sh` (Task 10); `support_scenario` (Task 7); `sha` from `support_reconcile`; `history` and `activation_ref` (Tasks 4–5).
- Produces: `image_smoke.py IMAGE`, which exits 0 only when every check passes. Plan 10 reruns it at stage exit.

- [ ] **Step 1: Install the container tools (D1)**

```bash
brew install colima docker docker-buildx
mkdir -p ~/.docker/cli-plugins
ln -sfn "$(brew --prefix docker-buildx)/bin/docker-buildx" ~/.docker/cli-plugins/docker-buildx
colima start --vm-type vz --vz-rosetta --cpu 4 --memory 8
docker buildx version
docker info --format '{{.OSType}}/{{.Architecture}}'
```

Expected: buildx prints its version (Homebrew stable 0.38.0 at planning time), and `docker info` prints `linux/aarch64`. Rosetta was present at planning time (`arch -x86_64 /usr/bin/true` succeeded); do not install or accept a Rosetta license. If Rosetta is missing, stop and ask the owner.

- [ ] **Step 2: Write the smoke script**

`packages/sec-edgar-ingest/tests/image_smoke.py`:

```python
"""Run every sec-edgar-ingest command in the built Linux amd64 image, offline (Stage 6, D1).

Usage: image_smoke.py IMAGE

Fixture packs and the config are built on the host. Every command that touches state runs inside the
container, so the store's bound root is always the container path /work/.fixture-state.
"""
from network_guard import install
install()

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

from support_reconcile import sha
from support_scenario import BASE_Q3, GATED_Q3, TODAY, scenario_pack, scenario_settings
from sec_edgar_ingest.models import canonical_json, to_mapping_value

COMMANDS = ('discover', 'collect', 'transform', 'publish', 'backfill', 'daily', 'reconcile',
            'approve', 'candidates', 'rollback', 'history')
# Colima shares the home directory with its VM; /tmp is not shared.
SMOKE_ROOT = Path.home() / '.cache' / 'sec-edgar-ingest-smoke'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit('image smoke failed: ' + message)


class Smoke:
    def __init__(self, image: str, work: Path):
        self.image, self.work = image, work
        self.deadline = (datetime.now(timezone.utc) + timedelta(seconds=1800)).isoformat()

    def docker(self, *args: str, entrypoint: str | None = None) -> subprocess.CompletedProcess:
        command = ['docker', 'run', '--rm', '--network', 'none', '--platform', 'linux/amd64',
                   '-v', f'{self.work}:/work']
        if entrypoint is not None:
            command += ['--entrypoint', entrypoint]
        return subprocess.run([*command, self.image, *args], capture_output=True, text=True, timeout=900)

    def expect(self, label: str, completed: subprocess.CompletedProcess, code: int) -> subprocess.CompletedProcess:
        require(completed.returncode == code, f'{label}: exit {completed.returncode}, expected {code}\n'
                                              f'{completed.stdout}\n{completed.stderr}')
        print(f'ok {label}: exit {code}')
        return completed

    def command(self, label: str, code: int, outcome: str, *argv: str) -> dict:
        message = json.loads(self.expect(label, self.docker(*argv), code).stdout)
        require(message['outcome'] == outcome, f'{label}: outcome {message["outcome"]}, expected {outcome}')
        return message

    def workflow(self, command: str, code: int, outcome: str, run: str, pack: str) -> dict:
        return self.command(command, code, outcome, command, '--config', '/work/config.json', '--run-id', run,
                            '--execution-id', 'manual', '--attempt-id', 'a', '--deadline', self.deadline,
                            '--state-dir', '/work', '--today', TODAY, '--fixture-pack', f'/work/{pack}/manifest.json')


def main(image: str) -> None:
    SMOKE_ROOT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='run-', dir=SMOKE_ROOT))
    smoke = Smoke(image, work)
    probe = smoke.expect('platform', smoke.docker(
        '-c', 'import os, platform, tempfile; print(platform.system(), platform.machine(), '
              'platform.python_version(), os.getuid(), tempfile.gettempdir())', entrypoint='python'), 0)
    require(probe.stdout.split() == ['Linux', 'x86_64', '3.14.8', '1000', '/tmp/sec-edgar-ingest'], probe.stdout)
    natives = smoke.expect('native imports', smoke.docker(
        '-c', 'import pyarrow, requests, cryptography.hazmat.bindings._rust, azure.identity, '
              'azure.storage.blob, azure.data.tables; print(pyarrow.__version__, requests.__version__)',
        entrypoint='python'), 0)
    require(natives.stdout.split() == ['25.0.1', '2.34.2'], natives.stdout)
    reported = smoke.expect('--version', smoke.docker('--version'), 0).stdout.strip()
    require(reported == version('sec-edgar-ingest'), reported)
    require(smoke.expect('--help', smoke.docker('--help'), 0).stdout.startswith('usage: sec-edgar-ingest'), '--help')
    for command in COMMANDS:
        shown = smoke.expect(f'{command} --help', smoke.docker(command, '--help'), 0).stdout
        require(shown.startswith(f'usage: sec-edgar-ingest {command}'), shown)

    for name, q3 in (('pack-1', BASE_Q3), ('pack-2', GATED_Q3)):
        scenario_pack(work, name, q3)
    (work / 'config.json').write_bytes(canonical_json(to_mapping_value(scenario_settings().to_mapping())))
    for path in (work, *work.rglob('*')):
        path.chmod(0o777 if path.is_dir() else 0o644)
    smoke.workflow('backfill', 0, 'success', 'base', 'pack-1')
    smoke.workflow('daily', 0, 'no_new_sources', 'day', 'pack-1')
    smoke.workflow('reconcile', 10, 'awaiting_approval', 'gate', 'pack-2')
    operator = ('--config', '/work/config.json', '--state-dir', '/work')
    request, = smoke.command('candidates', 0, 'success', 'candidates', *operator)['candidates']
    require(request['status'] == 'pending', str(request['status']))
    approved = smoke.command('approve', 0, 'success', 'approve', *operator, '--quarter', '2026Q3',
                             '--generation', request['generation_id'], '--quarterly-sha256', sha(GATED_Q3),
                             '--approver', 'Image Smoke')
    require(approved['activation_ref'] is not None, 'approve printed no activation_ref')
    history = smoke.command('history', 0, 'success', 'history', *operator, '--quarter', '2026Q3')
    lineage = history['lineage']
    require([entry['gate'] for entry in lineage] == ['awaiting_approval', 'clear'], str(lineage))
    require(len(history['activations']) == 1, str(history['activations']))
    smoke.command('rollback', 0, 'success', 'rollback', *operator, '--quarter', '2026Q3',
                  '--from-generation', lineage[0]['generation_id'], '--to-generation', lineage[1]['generation_id'],
                  '--operator', 'Image Smoke', '--reason', 'image smoke')
    history = smoke.command('history after rollback', 0, 'success', 'history', *operator, '--quarter', '2026Q3')
    require(len(history['rollbacks']) == 1, str(history['rollbacks']))
    shutil.rmtree(work)
    print(f'image smoke passed: {image}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: image_smoke.py IMAGE')
    main(sys.argv[1])
```

The work directory is created by this script and removed only after a pass. On failure it stays under `~/.cache/sec-edgar-ingest-smoke/` for inspection.

- [ ] **Step 3: Build the image for Linux amd64**

```bash
rm -rf /tmp/s6-image-context
scripts/build-image-context.sh /tmp/s6-image-context
docker buildx build --platform linux/amd64 --load -t sec-edgar-ingest:stage6-local /tmp/s6-image-context
docker image inspect sec-edgar-ingest:stage6-local --format '{{.Os}}/{{.Architecture}} {{.Config.User}} {{json .Config.Entrypoint}}'
```

Expected: the build succeeds, and inspect prints `linux/amd64 1000:1000 ["sec-edgar-ingest"]`. This local image ID is not a release digest and is never written into any config, template or record.

- [ ] **Step 4: Run the smoke**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/image_smoke.py sec-edgar-ingest:stage6-local`
Expected:
- an `ok …` line for `platform`, `native imports`, `--version`, `--help`, all 11 `<command> --help` checks, `backfill`, `daily`, `reconcile`, `candidates`, `approve`, `history`, `rollback` and `history after rollback`;
- then `image smoke passed: sec-edgar-ingest:stage6-local`.

The workflows run `discover`, `collect`, `transform` and `publish` as in-process children, with PyArrow and cryptography loaded natively under amd64 emulation.

- [ ] **Step 5: Stop the VM and commit**

```bash
colima stop
git add packages/sec-edgar-ingest/tests/image_smoke.py
git commit -m "test(infra): smoke every command in the locally built amd64 image

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Plan exit

**Files:**
- Modify: `scripts/check-sec-edgar-ingest.sh`

- [ ] **Step 1: Check help for every command in the check script**

In `scripts/check-sec-edgar-ingest.sh`, replace the line:

```sh
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest --help
```

with:

```sh
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest --help
for command in discover collect transform publish backfill daily reconcile approve candidates rollback history; do
  uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest "$command" --help >/dev/null
done
```

- [ ] **Step 2: Run the full plan-exit checks**

Run: `scripts/check-sec-edgar-ingest.sh`
Expected: exit 0. The full offline suite passes (`OK`), the wheel and sdist build offline, help prints for every command, `--version` prints `0.1.0`, `compileall` is quiet, and `git diff --check` is clean.

- [ ] **Step 3: Confirm no forbidden activity or edits**

```bash
git diff --stat 9d7ea225..HEAD -- specs/evidence specs/plans/completed specs/plans/4-sec-filing-index-ingestion-stage-4-spec.md specs/plans/5-sec-filing-index-ingestion-stage-4-spec.md specs/sec-filing-index-ingestion-stage-4-spec.md conf
grep -rn "stage6-local\|sha256:[0-9a-f]\{64\}" infra/azure/sec-edgar-ingest/config
```

Expected: the first command prints nothing. The second prints nothing: no local image digest was recorded, and the template has no digest.

- [ ] **Step 4: Commit**

```bash
git add scripts/check-sec-edgar-ingest.sh
git commit -m "chore(ingest): check help for every command at plan exit

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Then the final whole-branch review (subagent-driven-development), followed by the Plan Completion Protocol. This plan's header has no `Roadmap:` line, so step 3a does not apply: Stage 6 stays unticked until Plan 10 completes. Its deferred-items pass ticks `history`, actor identification and re-activation attribution, and the mistyped path, each `→ done in plan 9`. Plan retirement must leave the spec in place, because Plan 10 still implements it.
