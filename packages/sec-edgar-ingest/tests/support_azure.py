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
