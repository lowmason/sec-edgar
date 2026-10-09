"""Read-only repository diagnostic: actual three-process fixture race and control."""
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from dataclasses import replace

REPO = Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-4/sec-edgar')
sys.path.insert(0, str(REPO / 'packages/sec-edgar-ingest/tests'))
from support import (CollectionHarness, CollectionRaceStore, fixture_source,
                     fixture_workset, real_context, valid_idx_response, block_external_network)
from sec_edgar_ingest.worksets import encode_workset, decode_source_workset


def child(root, index, mode, request, staged, binding, checkpoint, fetch_ready):
    import sec_edgar_ingest.collection as collection
    from sec_edgar_ingest.coordination import Clock
    from sec_edgar_ingest.results import write_result
    block_external_network()
    root = Path(root)
    def trace(event, **fields):
        with (root / f'child-{index}.jsonl').open('a') as stream:
            stream.write(json.dumps({'event': event, 'pid': os.getpid(),
                                    'monotonic_ns': time.monotonic_ns(),
                                    'utc': datetime.now(timezone.utc).isoformat(), **fields}) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
    h = None
    try:
        clock = Clock()
        h = CollectionHarness(root, [valid_idx_response('daily', company=f'process-{index}')], clock=clock)
        h.context = replace(real_context(clock, h.settings), execution_id=f'process-{index}',
                            attempt_id=f'process-{index}', deadline=clock.now() + timedelta(seconds=60))
        h.coordinator.observer = lambda event: trace('coordinator', value=event)
        h.source_state.store = CollectionRaceStore(h.store, binding, trace)
        def receipt_checkpoint():
            trace('receipt_checkpoint')
            checkpoint.set()
            staged.wait(timeout=20)
            trace('receipt_barrier_released')
        h.faults.at('after_receipt_checkpoint', receipt_checkpoint)
        original_recovery = collection.recover_promoted
        def recovery(*args):
            trace('recovery_enter')
            if index == 2:
                gate = checkpoint if mode == 'before-collect' else fetch_ready
                trace('delayed_recovery_wait', gate='receipt' if mode == 'before-collect' else 'fetch-entry')
                if not gate.wait(20):
                    raise TimeoutError('ordering event was not set')
                trace('delayed_recovery_released')
            snapshot = original_recovery(*args)
            trace('recovery_return', snapshot_sha256=None if snapshot is None else snapshot.sha256)
            return snapshot
        collection.recover_promoted = recovery
        original_fetch = h.client.fetch
        def fetch(*args, **kwargs):
            trace('client_fetch_enter')
            fetch_ready.set()
            if mode == 'fetch-entry':
                request.wait(timeout=20)
                trace('fetch_barrier_released')
            return original_fetch(*args, **kwargs)
        h.client.fetch = fetch
        workset = decode_source_workset((root / 'input-workset.json').read_bytes())
        if mode == 'before-collect':
            trace('request_barrier_ready')
            request.wait(timeout=20)
            trace('request_barrier_released')
        result = collection.collect(workset, h.context, h.settings, h.client, h.source_state, h.objects, h.faults)
        ref = write_result(result, h.objects, h.source_state)
        trace('result_written', result=result.to_mapping(), ref=ref)
    except BaseException:
        trace('exception', traceback=traceback.format_exc())
        raise
    finally:
        if h is not None:
            h.close()


def case(root, mode):
    root.mkdir()
    clock = None
    source = fixture_source('2026-10-01', 'daily')
    workset = fixture_workset((source,))
    h = CollectionHarness(root, [])
    h.objects.put_once(h.source_workset_path(workset), encode_workset(workset))
    (root / 'input-workset.json').write_bytes(encode_workset(workset))
    h.close()
    spawn = multiprocessing.get_context('spawn')
    request, staged, binding = [spawn.Barrier(3) for _ in range(3)]
    checkpoint, fetch_ready = spawn.Event(), spawn.Event()
    processes = [spawn.Process(target=child, args=(str(root), index, mode, request, staged, binding, checkpoint, fetch_ready)) for index in range(3)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(45)
        if process.is_alive():
            process.terminate()
            process.join(5)
    summary = {'mode': mode, 'processes': [{'pid': p.pid, 'exit': p.exitcode} for p in processes]}
    (root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary), flush=True)
    for index in range(3):
        events = [json.loads(line) for line in (root / f'child-{index}.jsonl').read_text().splitlines()]
        print(json.dumps({'child': index, 'events': [{k: v for k, v in event.items() if k in ('event', 'snapshot_sha256', 'gate', 'traceback')} for event in events if event['event'] != 'coordinator']}), flush=True)
    return summary


if __name__ == '__main__':
    root = Path('/private/tmp/sec-edgar-race-evidence-20261007T224919')
    root.mkdir()
    envelope = {'command': 'uv run --offline --frozen --package sec-edgar-ingest python /private/tmp/sec-edgar-race-diagnostic-20261007T224919.py',
                'cwd': str(REPO), 'baseline': 'fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd',
                'start_utc': datetime.now(timezone.utc).isoformat(), 'root': str(root)}
    (root / 'command-envelope.json').write_text(json.dumps(envelope, indent=2) + '\n')
    print(str(root), flush=True)
    with (root / 'output.txt').open('x') as output:
        class Tee:
            def write(self, value):
                output.write(value)
                sys.__stdout__.write(value)
            def flush(self):
                output.flush()
                sys.__stdout__.flush()
        sys.stdout = Tee()
        summaries = [case(root / mode, mode) for mode in ('before-collect', 'fetch-entry')]
        print(json.dumps({'completed_utc': datetime.now(timezone.utc).isoformat(), 'summaries': summaries}), flush=True)
