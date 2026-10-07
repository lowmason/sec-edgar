import sys
from pathlib import Path
root = Path.cwd()
sys.path.insert(0, str(root / 'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
import hashlib
import importlib.metadata
import json
import platform
import subprocess
from sec_edgar_ingest.models import canonical_json
base = root / '.sdd/3-sec-filing-index-ingestion-stage-3-spec/task6-evidence'
proof = base / 'green-final-retained-proof'
summary = {'runtime': {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
           'dependencies': {name: importlib.metadata.version(name) for name in ('pyarrow', 'requests', 'azure-identity', 'azure-storage-blob', 'azure-data-tables')}}, 'cases': {}, 'recovery': {}}
for name in ('test_real_transform_and_publish_without_acquisition_construction', 'test_multiple_quarters_gate_continues_other_quarter_and_complete_receipts', 'test_harder_failure_dominates_gate_but_preserves_both_quarters', 'test_persistent_conflict_retains_attempted_manifest_and_exit_nine', 'test_partial_transform_retains_success_and_publish_changes_no_pointer', 'test_empty_complete_transform_and_publish_are_unchanged', 'test_new_attempt_replays_parser_with_original_acquisition_context'):
    case = proof / name
    records = json.loads((case / 'state-records.json').read_bytes())
    objects = case / 'files/.fixture-state/objects'
    artifacts = {}
    for path in objects.rglob('*.json'):
        body = path.read_bytes()
        value = json.loads(body)
        if path.name in ('result.json', 'command.json', 'workset.json'):
            artifacts[path.relative_to(objects).as_posix()] = {'sha256': hashlib.sha256(body).hexdigest(), 'byte_count': len(body)}
        if path.name == 'result.json':
            artifacts[path.relative_to(objects).as_posix()]['result'] = value
    summary['cases'][name] = {'state_counts': {kind: len(rows) for kind, rows in records.items()},
                             'artifacts': artifacts, 'state_records_sha256': hashlib.sha256((case / 'state-records.json').read_bytes()).hexdigest()}
for name in ('test_result_object_crash_repairs_attempt_exactly', 'test_publish_noop_and_result_crash_do_not_advance_twice', 'test_pointer_crash_resumes_without_another_advance_and_repairs_receipts'):
    snapshots = {}
    for path in (proof / name / 'files/checkpoints').glob('*.json'):
        body = path.read_bytes()
        value = json.loads(body)
        snapshots[path.name] = {'sha256': hashlib.sha256(body).hexdigest(),
                               'pointer_sha256': hashlib.sha256(canonical_json(value['state']['QuarterPublication'])).hexdigest(),
                               'attempt_results': [row['value']['result'] is not None for row in value['state']['Attempt']],
                               'receipt_count': len(value['state']['PublicationReceipt'])}
    summary['recovery'][name] = snapshots
(base / 'actual-summary.json').write_bytes(canonical_json(summary))
owned = ['packages/sec-edgar-ingest/src/sec_edgar_ingest/' + path for path in ('etl/commands.py', 'cli.py', 'results.py', 'state.py')] + ['packages/sec-edgar-ingest/tests/' + path for path in ('test_etl_cli.py', 'test_workspace.py', 'test_cli.py')]
checks = []
for argv in (['git', 'diff', '--check'], ['git', 'status', '--short'], ['git', 'diff', '--', *owned]):
    done = subprocess.run(argv, cwd=root, capture_output=True, text=True)
    checks.append({'argv': argv, 'cwd': str(root), 'stdout': done.stdout, 'stderr': done.stderr, 'exit': done.returncode})
(base / 'self-review.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps({'runtime': summary['runtime'], 'recovery': summary['recovery'], 'summary_sha256': hashlib.sha256((base / 'actual-summary.json').read_bytes()).hexdigest()}, indent=2))
