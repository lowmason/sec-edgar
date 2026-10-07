import sys
from pathlib import Path
root = Path.cwd()
sys.path.insert(0, str(root / 'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
import hashlib
import json
import subprocess
base = root / '.sdd/3-sec-filing-index-ingestion-stage-3-spec/task6-fix1-evidence'
proofs = {}
for name in ('test_noncanonical_snapshot_whitespace_refuses_before_transform_outputs', 'test_noncanonical_snapshot_property_order_refuses_before_transform_outputs'):
    path = base / 'green-etl-covering-proof' / name / 'files/canonical-refusal-proof.json'
    value = json.loads(path.read_bytes())
    assert value['exit'] == 9 and value['processing'] == [] and value['pointers'] == []
    assert value['before_objects'] == value['after_objects'] and value['output']['result_ref'] is None
    proofs[name] = {key: value[key] for key in ('snapshot_ref', 'canonical_sha256', 'noncanonical_sha256', 'exit')}
    proofs[name]['proof_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
(base / 'verified-proof-summary.json').write_text(json.dumps(proofs, indent=2) + '\n')
report = base.parent / 'task-6-report.md'
with report.open('a') as stream:
    stream.write('''
## Review fix round 1 — Important I1

Confirmed the review finding through the existing acquisition decoder: normalized content identity permits whitespace/property ordering differences. Added two failing tests using semantically identical noncanonical bytes at the **matching** immutable snapshot content-ID path. Both red tests returned exit0 and produced outputs before the fix. The fix is six production lines in the owned `etl/commands.py`: read/decode snapshot, verify decoded path identity, compare original body with existing `encode_workset`, refuse with Conflict before calling transform_workset or scanning Processing. No global/acquisition decoder or Task3 change.

Existing acquisition behavior is explicitly verified independently in both tests: `decode_snapshot_workset(noncanonical) == decode_snapshot_workset(canonical)` and existing `encode_workset(snapshot)` reproduces canonical bytes. Tests use actual local stored object bytes and the actual CLI; they retain pre/post state/object byte snapshots. Green refusal exits9, leaves Processing/pointers empty, retains no result object, and has identical complete non-run object maps before/after (no observation/transformed/quarantine/curated output). Command intent/error Attempt audit remain available.

Evidence is separate in `task6-fix1-evidence/`: `red-canonical-snapshot.json` retains both expected failures; `green-etl-covering.json` retains **28 tests passed, 3.767 seconds, exit0**. Full argv/cwd/environment/stdout/stderr/exits are retained. Guarded commands:

```sh
uv run --offline --frozen python packages/sec-edgar-ingest/tests/network_guard.py test_etl_cli.EtlCliTests.test_noncanonical_snapshot_whitespace_refuses_before_transform_outputs test_etl_cli.EtlCliTests.test_noncanonical_snapshot_property_order_refuses_before_transform_outputs -v
uv run --offline --frozen python packages/sec-edgar-ingest/tests/network_guard.py test_etl_cli -v
```

Cwd: `/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar`. `SEC_EDGAR_TASK6_PROOF_DIR` selects separate red/green retained roots; each malformed case has `files/canonical-refusal-proof.json`, before/after checkpoints and full ledgers. Verified actual identities:

''')
    for name, value in proofs.items():
        stream.write('- ' + name + ': snapshot `' + value['snapshot_ref'] + '`, canonical body SHA `' + value['canonical_sha256'] + '`, noncanonical body SHA `' + value['noncanonical_sha256'] + '`, refusal proof SHA `' + value['proof_sha256'] + '`.\n')
    stream.write('''
Self-review: inspected full two-file diff; `git diff --check` passed. Applied N1 explicit snapshot-body/decoded names, T5/T6 semantically equivalent byte variants and no-output assertions. No adjacent cleanup or additional source changes. Scoped ETL covering verification includes existing canonical real/empty/replay behavior. No full suite/acquisition/workspace rerun was needed for this isolated boundary fix.

Scope clarification superseding earlier report wording: **Task7 reports `all22_stage7_checks` as reserved. Execution of those22 integrated checks and Linux capacity measurement belong to the later roadmap Stage7.** Task7 still handles its authorized full suite/build/wheel/process evidence. Closed authorizations, exact dependency pins and historical duplicate refusal remain unchanged.
''')
def call(name, argv):
    result = subprocess.run(argv, cwd=root, capture_output=True, text=True)
    (base / (name + '.json')).write_text(json.dumps({'argv': argv, 'cwd': str(root), 'stdout': result.stdout, 'stderr': result.stderr, 'exit': result.returncode}, indent=2) + '\n')
    if result.returncode: raise RuntimeError(result.stderr)
    return result.stdout
owned = ['packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py', 'packages/sec-edgar-ingest/tests/test_etl_cli.py']
call('self-review-check', ['git', 'diff', '--check'])
call('stage', ['git', 'add', *owned])
assert set(call('staged-names', ['git', 'diff', '--cached', '--name-only']).splitlines()) == set(owned)
call('staged-check', ['git', 'diff', '--cached', '--check'])
(base / 'owned.diff').write_text(call('staged-diff', ['git', 'diff', '--cached']))
print(call('commit', ['git', 'commit', '-m', 'fix: require canonical snapshot bytes before transform']))
sha = call('commit-sha', ['git', 'rev-parse', 'HEAD']).strip()
status = call('post-commit-status', ['git', 'status', '--short'])
with report.open('a') as stream:
    stream.write('\nFix commit: `' + sha + '` — `fix: require canonical snapshot bytes before transform`. Exactly the two owned files committed; post-commit status ' + ('clean.\n' if not status.strip() else status + '\n'))
print(json.dumps(proofs, indent=2))
print(sha)
