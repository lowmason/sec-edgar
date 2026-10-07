"""Retain actual per-process disposition for the unfixed offline collector fixture."""
import json
import multiprocessing
from pathlib import Path
import queue
import sys
import tempfile
sys.path.insert(0, str(Path.cwd() / 'packages/sec-edgar-ingest/tests'))
import network_guard
network_guard.install()
import support
from sec_edgar_ingest.worksets import encode_workset


def main():
    spawn = multiprocessing.get_context('spawn')
    with tempfile.TemporaryDirectory(prefix='sec-fix1-diagnostic-') as temporary:
        root = Path(temporary)
        workset = support.fixture_workset((support.fixture_source('2026-10-01', 'daily'),))
        harness = support.collection_harness(root, [])
        harness.objects.put_once(harness.source_workset_path(workset), encode_workset(workset))
        (root / 'input-workset.json').write_bytes(encode_workset(workset))
        harness.close()
        request, staged, binding = (spawn.Barrier(3) for _ in range(3))
        output = spawn.Queue()
        processes = [spawn.Process(target=support.acquisition_race_entry,
                     args=(str(root), str(index), request, staged, binding, output)) for index in range(3)]
        try:
            for process in processes:
                process.start()
            records = []
            error = None
            try:
                records = [output.get(timeout=25) for _ in processes]
            except queue.Empty as caught:
                error = type(caught).__name__
            for process in processes:
                process.join(5)
            harness = support.collection_harness(root, [])
            attempts = [row.to_mapping() for row in harness.store.scan('Attempt', {})]
            harness.close()
            proof = {'queue_error': error, 'records': records, 'attempt_rows': attempts,
                     'processes': [{'pid': process.pid, 'name': process.name, 'exit': process.exitcode,
                                    'alive_after_join': process.is_alive()} for process in processes],
                     'barriers': {name: {'parties': value.parties, 'waiting': value.n_waiting, 'broken': value.broken}
                                  for name, value in [('request', request), ('staged', staged), ('binding', binding)]}}
            path = Path('.sdd/2-sec-filing-index-ingestion-stage-2-spec/final-review-fix1-evidence/collector-process-disposition.json')
            assert not path.exists(), path
            path.write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
            print(json.dumps(proof))
            assert error == 'Empty' and not attempts
            assert all(process.exitcode == 1 and not process.is_alive() for process in processes)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join(2)
            output.close()
            output.join_thread()


if __name__ == '__main__':
    main()
