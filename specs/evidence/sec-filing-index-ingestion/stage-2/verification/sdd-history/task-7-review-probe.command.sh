/usr/bin/python3 -B - <<'PY'
from pathlib import Path
import json
import os
import subprocess
import tempfile

script = r'''
from pathlib import Path
from dataclasses import replace
import gc
import hashlib
import json
import os
import sys
from sec_edgar_ingest.collection import collect
from sec_edgar_ingest.download import ResponseSpec
from sec_edgar_ingest.worksets import decode_source_workset, encode_workset
from support import collection_harness, fixture_context, fixture_source, fixture_workset, valid_idx_response
root = Path(sys.argv[1])
phase = sys.argv[2]
if phase == 'crash':
    source = fixture_source(kind='daily', period='2026-10-01')
    workset = fixture_workset((source,))
    (root/'input.json').write_bytes(encode_workset(workset))
    h = collection_harness(root, [ResponseSpec(200, b'retained retry prefix', {'X-Fixture': 'partial'}, 'read_timeout'), valid_idx_response('daily')])
    def terminate():
        gc.collect()
        context = h.source_state.active_context
        history = [row.to_mapping()['value'] for row in h.source_state.request_history(context, source.canonical_url)]
        first = history[0]
        path = f'quarantine/sec/{context.run_id}/{source.source_id}/{context.attempt_id}/{first["request_id"]}/body'
        (root/'before.json').write_text(json.dumps({'pid':os.getpid(), 'context':context.to_mapping(), 'history':history, 'prefix_body_hex':Path(first['receipt']['temporary_path']).read_bytes().hex(), 'quarantine_path':path, 'quarantine_exists':(h.objects.directory/path).exists(), 'staged_receipts':h.source_state.staged_receipt(workset.workset_id, source.source_id)}, sort_keys=True))
        os._exit(73)
    h.faults.at('after_receipt_checkpoint', terminate)
    h.collect(workset)
else:
    workset = decode_source_workset((root/'input.json').read_bytes())
    source = workset.members[0]
    h = collection_harness(root, [])
    h.context = replace(fixture_context(), run_id='successor-run', execution_id='successor-execution', attempt_id='successor-attempt')
    h.forbid_fetch = True
    result = collect(workset, h.context, h.settings, h.client, h.source_state, h.objects, h.faults)
    before = json.loads((root/'before.json').read_text())
    snapshot = h.snapshot_workset(result).snapshots[0]
    original_context = type(h.context).from_mapping(before['context'])
    after = {'pid':os.getpid(), 'result':result.to_mapping(), 'original_history':[row.to_mapping()['value'] for row in h.source_state.request_history(original_context, source.canonical_url)], 'successor_history_count':len(h.source_state.request_history(h.context, source.canonical_url)), 'quarantine_exists':(h.objects.directory/before['quarantine_path']).exists(), 'quarantine_body_count':len(list((h.objects.directory/'quarantine').rglob('body'))) if (h.objects.directory/'quarantine').exists() else 0, 'raw_sha256':hashlib.sha256(h.objects.read(snapshot.raw_path)).hexdigest(), 'raw_path':snapshot.raw_path, 'prefix_still_exists':Path(before['history'][0]['receipt']['temporary_path']).exists()}
    (root/'after.json').write_text(json.dumps(after, sort_keys=True))
    h.close()
'''
with tempfile.TemporaryDirectory(prefix='sec-task7-review-', dir='/private/tmp') as directory:
    root = Path(directory)
    (root/'spool').mkdir()
    environment = {**os.environ, 'UV_CACHE_DIR':str(root/'uv-cache'), 'TMPDIR':str(root/'spool'), 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONPATH':'packages/sec-edgar-ingest/tests'}
    environment.pop('SEC_EDGAR_TASK7_TRACE_DIR', None)
    processes = []
    for phase in ('crash','resume'):
        command = ['uv','run','--offline','--frozen','--no-sync','python','-B','-c',script,str(root),phase]
        result = subprocess.run(command, capture_output=True, text=True, timeout=45, env=environment)
        processes.append({'phase':phase,'argv':command[:8]+['<script above>',str(root),phase], 'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
    before = json.loads((root/'before.json').read_text())
    after = json.loads((root/'after.json').read_text())
    assert [process['exit_code'] for process in processes] == [73,0]
    assert before['pid'] != after['pid']
    assert len(before['history']) == 2 and [row['outcome'] for row in before['history']] == ['retry','received']
    assert before['prefix_body_hex'] == b'retained retry prefix'.hex()
    assert after['original_history'] == before['history'] and after['successor_history_count'] == 0
    assert after['result']['outcome'] == 'success'
    assert not before['quarantine_exists'] and not after['quarantine_exists'] and after['quarantine_body_count'] == 0
    print(json.dumps({'processes':processes, 'before':before, 'after':after}, indent=2, sort_keys=True))
PY
