import json, socket
from unittest.mock import patch
import azure.identity
original_connect = socket.socket.connect
import support
support_import_installs_guard = socket.socket.connect is not original_connect
calls = []
def recorded_connect(sock, address):
    calls.append({"method": "connect", "address": list(address)})
    return None
def recorded_connect_ex(sock, address):
    calls.append({"method": "connect_ex", "address": list(address)})
    return 0
credential_before = azure.identity.DefaultAzureCredential
with patch.object(socket.socket, "connect", recorded_connect), patch.object(socket.socket, "connect_ex", recorded_connect_ex):
    support.block_external_network()
    credential_unchanged = azure.identity.DefaultAzureCredential is credential_before
    with socket.socket() as sock:
        sock.connect(("127.0.0.1", 54321))
        try:
            sock.connect(("198.51.100.1", 443))
        except AssertionError:
            external_connect_blocked = True
        else:
            external_connect_blocked = False
        sock.connect_ex(("198.51.100.1", 443))
print(json.dumps({"provenance": "offline probe; both original connection methods are recording stubs; no connection or authentication was attempted", "support_import_installs_guard": support_import_installs_guard, "external_connect_blocked": external_connect_blocked, "recorded_calls": calls, "credential_constructor_unchanged": credential_unchanged}, indent=2))
