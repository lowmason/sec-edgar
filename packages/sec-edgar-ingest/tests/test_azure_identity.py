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
