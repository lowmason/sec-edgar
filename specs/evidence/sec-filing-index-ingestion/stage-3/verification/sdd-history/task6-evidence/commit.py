import sys
from pathlib import Path
root = Path.cwd()
sys.path.insert(0, str(root / 'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
import json
import subprocess
base = root / '.sdd/3-sec-filing-index-ingestion-stage-3-spec/task6-evidence'
owned = ['packages/sec-edgar-ingest/src/sec_edgar_ingest/' + path for path in ('etl/commands.py', 'cli.py', 'results.py', 'state.py')] + ['packages/sec-edgar-ingest/tests/' + path for path in ('test_etl_cli.py', 'test_workspace.py', 'test_cli.py')]
def call(name, argv):
    result = subprocess.run(argv, cwd=root, capture_output=True, text=True)
    (base / (name + '.json')).write_text(json.dumps({'argv': argv, 'cwd': str(root), 'stdout': result.stdout, 'stderr': result.stderr, 'exit': result.returncode}, indent=2) + '\n')
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout
assert call('branch', ['git', 'branch', '--show-current']).strip() == 'codex/sec-edgar-stage-3'
assert call('base', ['git', 'rev-parse', 'HEAD']).strip() == '1ec404a29f945448c735efe712526edc41efaacc'
call('stage', ['git', 'add', *owned])
assert set(call('staged-names', ['git', 'diff', '--cached', '--name-only']).splitlines()) == set(owned)
call('staged-check', ['git', 'diff', '--cached', '--check'])
diff = call('staged-diff', ['git', 'diff', '--cached'])
(base / 'owned.diff').write_text(diff)
print(call('commit', ['git', 'commit', '-m', 'feat: expose raw-only transform and safe publication commands']))
sha = call('commit-sha', ['git', 'rev-parse', 'HEAD']).strip()
status = call('post-commit-status', ['git', 'status', '--short'])
report = base.parent / 'task-6-report.md'
with report.open('a') as stream:
    stream.write('\n## Commit\n\n`' + sha + '` — `feat: expose raw-only transform and safe publication commands`. Exact branch/base/stage/names/diff/check/commit/status argv and results are retained under task6-evidence; `owned.diff` is the complete committed diff. Post-commit status was ' + ('clean.\n' if not status.strip() else '`' + status.strip() + '`.\n'))
print(sha)
print(status)
