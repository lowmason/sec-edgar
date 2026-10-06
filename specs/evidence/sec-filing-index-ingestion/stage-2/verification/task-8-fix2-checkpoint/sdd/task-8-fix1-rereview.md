# Task 8 fix round 1 scoped re-review — complete reviewer response

- **I2 — NOT ADDRESSED.** The suite, connection/resolution, exact loopback origin, and spawned transport protections are implemented in [the runner](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/scripts/check-sec-edgar-ingest.sh:3), [guard installation](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/tests/network_guard.py:114), and [fixture wiring](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/tests/support.py:637). Authentication denial remains incomplete: [the MSAL class predicate](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/tests/network_guard.py:37) selects only names ending in `Application`, so the pinned SDK’s public `msal.ManagedIdentityClient` constructor and `acquire_token_for_client` remain callable. A bounded recording-stub probe confirmed both routes reach their original stubs after guard installation. This leaves the adopted requirement to deny unapproved authentication construction/token activity unresolved at **Important** severity. Extend coverage to this client and add constructor and existing-instance token regressions using recording stubs.

- **I3 — ADDRESSED.** [Package README instructions](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/packages/sec-edgar-ingest/README.md:24) and [runbook instructions](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/docs/runbooks/sec-edgar-ingest-acquisition.md:11) now give explicit workspace setup, frozen lock export, hash-checked cached dependency installation, and wheel installation commands. They state Python/platform/cache prerequisites and treat missing cache as a prerequisite failure. All 11 retained fresh installation/import/help/fixture command receipts exit zero. I independently verified that the 20 wheels at the documented retained cache path are byte-identical to the cache used by that successful recipe.

**NEW findings:** Critical: none. Important: none separate from residual I2. Minor: none.

The independent I2 probe used this exact command from `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar`:

```sh
.venv/bin/python -B - <<'PY'
import json
import socket
import sys
network_calls = []
def forbidden_network(*args, **kwargs):
    network_calls.append('network')
    raise AssertionError('probe never permits a real network operation')
for name in ('connect', 'connect_ex', 'sendto', 'sendmsg'):
    if hasattr(socket.socket, name):
        setattr(socket.socket, name, forbidden_network)
for name in ('getaddrinfo', 'getnameinfo', 'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr'):
    setattr(socket, name, forbidden_network)
import azure.identity as identity
import msal
auth_calls = []
def record(label):
    def stub(*args, **kwargs):
        auth_calls.append(label)
    return stub
client = msal.ManagedIdentityClient
client.__init__ = record('ManagedIdentityClient.__init__')
client.acquire_token_for_client = record('ManagedIdentityClient.acquire_token_for_client')
existing_client = object.__new__(client)
sys.path.insert(0, 'packages/sec-edgar-ingest/tests')
import network_guard
network_guard.install()
def denied(operation):
    try:
        operation()
    except AssertionError:
        return True
    return False
proof = {
    'DefaultAzureCredential_constructor_denied': denied(lambda: identity.DefaultAzureCredential()),
    'PublicClientApplication_constructor_denied': denied(lambda: msal.PublicClientApplication('synthetic')),
    'ManagedIdentityClient_constructor_denied': denied(lambda: client({'fixture': True}, http_client=object())),
    'existing_ManagedIdentityClient_token_denied': denied(lambda: existing_client.acquire_token_for_client(resource='synthetic-resource')),
    'auth_recording_stub_calls': auth_calls,
    'network_recording_stub_calls': network_calls,
}
print(json.dumps(proof, sort_keys=True))
PY
```

Exit code: **0**. Exact stdout:

```json
{"DefaultAzureCredential_constructor_denied": true, "ManagedIdentityClient_constructor_denied": false, "PublicClientApplication_constructor_denied": true, "auth_recording_stub_calls": ["ManagedIdentityClient.__init__", "ManagedIdentityClient.acquire_token_for_client"], "existing_ManagedIdentityClient_token_denied": false, "network_recording_stub_calls": []}
```

The probe performed no real authentication or network operation and wrote no files. It demonstrates missing denial, not observed live authentication.

I inspected the retained RED/GREEN and intermediate failure receipts, and independently checked the complete current log: **288 passing records**, 313 lines, matching SHA/footer/non-test output, with check exit zero. I also verified all 16 candidate hashes, all 18 production Python files against BASE and the current wheel, and exclusion of the guard from the wheel. The controller’s independent receipt verifies the 4,813 original payload records, 4,661 fix payload records, and 4,577 retention-map entries. No suites were rerun; the original four unstaged deletions remain preserved.

Reviewer routing: **GPT-6.1 Max (`gpt-6.1-sol` / `max`)**, fresh default read-only reviewer role because the named `task-reviewer` role was unavailable. Frozen range: `a62c05c0a961fecc2f1ac854b9dac68be3add7ef..35b47692168677acbe0410a33fc758d6d569a7a4`. Scope: I2/I3, all eight authored paths, supporting proof metadata/maps/receipts, and fix-introduced defects. This is not a full Task 8 or whole-branch verdict. I1’s combined Step 4 sequence remains pending the owner endpoint choice; all S7 checks remain reserved, and no live-service or platform-performance claim follows.
