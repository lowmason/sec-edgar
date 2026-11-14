"""Stage 2a1 diagnosis: profile one `_publish_calls` pass and the unbound-member reuse path.

    <release>/venv/bin/python -I profile_pieces.py <store-copy> publish-calls <out-prefix>
    <release>/venv/bin/python -I profile_pieces.py <store-copy> reuse <out-prefix> --member <member_id>

`publish-calls` runs `completion._publish_calls` once under cProfile and writes the top functions by
cumulative time, plus the call and verify counts. `reuse` deletes the `Binding` row of one member on the
scratch copy (the state that invocation 2's new members were in before `reuse_exact_binding` bound them),
then times `reuse_exact_binding` for that member. Each mode needs its own fresh copy of the store.
"""
import argparse
import cProfile
import io
import json
import pstats
import sqlite3
import time
from collections import Counter
from pathlib import Path

from sec_edgar_ingest.storage.contracts import REGISTRY_PATH
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.workflows import completion
from sec_edgar_ingest.workflows.runner import reuse_exact_binding


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('mode', choices=('publish-calls', 'reuse'))
    parser.add_argument('out', type=Path)
    parser.add_argument('--member')
    args = parser.parse_args()
    binding = json.loads((args.root / 'objects' / REGISTRY_PATH).read_bytes())
    objects = LocalObjectStore(args.root, binding=binding, create=False)
    store = LocalStateStore(args.root, binding=binding, create=False)
    counts, verified = Counter(), Counter()
    verify = objects.verify

    def counted_verify(path, sha256, byte_count):
        counts['objects.verify'] += 1
        verified['bytes'] += byte_count
        return verify(path, sha256, byte_count)

    objects.verify = counted_verify
    out = {'mode': args.mode}
    profiler = cProfile.Profile()
    if args.mode == 'publish-calls':
        start = time.perf_counter()
        profiler.enable()
        calls = completion._publish_calls(store, objects)
        profiler.disable()
        out['wall_s'] = time.perf_counter() - start
        out['publish_calls'] = len(calls)
        out['checked'] = sum(1 for c in calls if c.get('format_version') != completion.LEGACY_PUBLISH_FORMAT)
    else:
        value = next(r.to_mapping()['value'] for r in store.scan('WorkflowMember', {})
                     if r.to_mapping()['value']['member_id'] == args.member)
        connection = sqlite3.connect(args.root / 'state.sqlite3')
        deleted = connection.execute("DELETE FROM records WHERE partition LIKE '%:Binding' AND value LIKE ?",
                                     ('%' + args.member + '%',)).rowcount
        connection.commit()
        connection.close()
        out['member'] = args.member
        out['bindings_deleted'] = deleted
        start = time.perf_counter()
        profiler.enable()
        gaps = reuse_exact_binding(value, store, objects)
        profiler.disable()
        out['wall_s'] = time.perf_counter() - start
        out['gaps'] = [g.to_mapping() for g in gaps]
        from sec_edgar_ingest.state import AcquisitionState
        out['rebound'] = AcquisitionState(store).binding(args.member, value['source']['source_id']) is not None
    out['verify_calls'] = counts['objects.verify']
    out['verify_bytes'] = verified['bytes']
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).sort_stats('cumulative').print_stats(35)
    args.out.with_suffix('.json').write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + '\n')
    args.out.with_suffix('.prof.txt').write_text(stream.getvalue())
    print(json.dumps({k: v for k, v in out.items() if k != 'gaps'}, default=str))


if __name__ == '__main__':
    main()
