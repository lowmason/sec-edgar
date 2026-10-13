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
