"""Stage 2a1 diagnosis: where the daily 2026-07-01 member's 3,234 s publish goes, by phase.

    <2a release>/venv/bin/python -I profile_member.py <store-copy> <scratch-config> <out.json>

Same method as plan 8 Task 2 (specs/evidence/stage2b/scratch/order-timing.py, step 2): one `run_transform`
on the source's snapshot workset, then one `run_publish` on its transformed workset, each with a fresh
pinned context. No network client is created and nothing is approved. Timers wrap the publish steps
(`publish_quarter`, `build_candidate`, `transform_member`, the catalog load/resolve/write steps and the
candidate checks), so nested times overlap: read each name as the time spent inside it.
"""
import argparse
import json
import sys
import time
import typing
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sec_edgar_ingest.config import load_config, pin_context
from sec_edgar_ingest.etl.commands import run_publish, run_transform
from sec_edgar_ingest.models import RunContext
from sec_edgar_ingest.runtime import configured_descriptor, preflight_current, retain_manifest
from sec_edgar_ingest.storage.contracts import REGISTRY_PATH
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.worksets import decode_snapshot_workset

SOURCE = '924fd5f5b380e8a8603bab21b91edcd9408962b3a25fe812f067b25777063d58'  # daily 2026-07-01
TIMED = ('publish_quarter', 'build_candidate', 'transform_member', '_load_observations', '_load_active', '_resolve',
         '_write_parquet', '_identify_candidate', 'check_candidate_integrity', 'validate_candidate_content',
         '_incremental_candidate', '_affected_quarters', '_validate_raw', 'read_observations')
spent, calls, by_quarter = defaultdict(float), defaultdict(int), defaultdict(lambda: defaultdict(float))


def cached_type_hints(original):
    """Spike for the diagnosis only: one `get_type_hints` result per record type, as a per-type cache would give.

    Both call sites (models.py:238 and :280) pass one type and only read the returned dict.
    """
    cache = {}

    def cached(obj, *args, **kwargs):
        if args or kwargs:
            return original(obj, *args, **kwargs)
        try:
            return cache[obj]
        except KeyError:
            value = cache[obj] = original(obj)
            return value

    return cached


def instrument(cache_hints=False):
    """Wrap each timed function in every loaded sec_edgar_ingest module that names the same object."""
    originals = {}
    for module in list(sys.modules.values()):
        if module is None or not getattr(module, '__name__', '').startswith('sec_edgar_ingest'):
            continue
        for name in TIMED:
            function = module.__dict__.get(name)
            if callable(function) and getattr(function, '__module__', '').startswith('sec_edgar_ingest'):
                originals.setdefault(id(function), (name, function))
    wrappers = {}
    for key, (name, function) in originals.items():
        def wrapper(*args, __name=name, __function=function, **kwargs):
            quarter = args[0] if args and isinstance(args[0], str) and len(args[0]) == 6 else None
            start = time.perf_counter()
            try:
                return __function(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                spent[__name] += elapsed
                calls[__name] += 1
                if quarter and __name in ('publish_quarter', 'build_candidate'):
                    by_quarter[quarter][__name] += elapsed
        wrappers[key] = wrapper
    for module in list(sys.modules.values()):
        if module is None or not getattr(module, '__name__', '').startswith('sec_edgar_ingest'):
            continue
        for name in TIMED:
            function = module.__dict__.get(name)
            if callable(function) and id(function) in wrappers:
                setattr(module, name, wrappers[id(function)])
    hints = cached_type_hints(typing.get_type_hints) if cache_hints else typing.get_type_hints

    def counted_hints(*args, **kwargs):
        calls['typing.get_type_hints'] += 1
        return hints(*args, **kwargs)

    typing.get_type_hints = counted_hints
    import sec_edgar_ingest.models as models
    models.get_type_hints = counted_hints


def new_context(settings, command):
    started = datetime.now(timezone.utc)
    run_id = 'stage2a1-diag-' + uuid.uuid4().hex
    context = RunContext(run_id=run_id, execution_id=run_id, command=command, attempt_id=uuid.uuid4().hex,
                         runtime=configured_descriptor(settings), format_version='sec-local-run-context-v1',
                         parser_version=settings.etl.parser_version, schema_version=settings.etl.schema_version,
                         config_sha256=settings.config_sha256, started_at=started,
                         deadline=started + timedelta(seconds=settings.execution.max_run_seconds), priority='backfill')
    return pin_context(settings, context, started.date())[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('config', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--cache-type-hints', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    settings = load_config(args.config)
    if Path(settings.storage.root) != root:
        raise ValueError('config storage.root differs from <root>')
    verified = preflight_current(Path(settings.runtime.release_manifest))
    binding = json.loads((root / 'objects' / REGISTRY_PATH).read_bytes())
    objects = LocalObjectStore(root, binding=binding, create=False)
    store = LocalStateStore(root, binding=binding, create=False)
    retain_manifest(objects, verified.manifest)
    candidates = []
    for directory in sorted((root / 'objects/worksets/sec/snapshot').iterdir()):
        ref = f'worksets/sec/snapshot/{directory.name}/workset.json'
        workset = decode_snapshot_workset(objects.read(ref))
        for snapshot in workset.snapshots:
            if snapshot.source_id == SOURCE:
                candidates.append((snapshot.received_at, len(workset.snapshots), ref))
    # Plan 8 chose the newest single-snapshot workset of the source; take the same rule.
    received, size, workset_ref = sorted(c for c in candidates if c[1] == 1)[-1]
    instrument(args.cache_type_hints)
    out = {'source_id': SOURCE, 'workset_ref': workset_ref, 'received_at': received.isoformat(),
           'cache_type_hints': args.cache_type_hints}
    start = time.perf_counter()
    transformed = run_transform(workset_ref, new_context(settings, 'transform'), settings, objects, store)
    out['transform_s'] = time.perf_counter() - start
    out['transform_outcome'] = transformed.outcome
    spent.clear(); calls.clear()
    start = time.perf_counter()
    published = run_publish(transformed.transformed_workset_ref, new_context(settings, 'publish'), settings, objects, store)
    out['publish_s'] = time.perf_counter() - start
    out['publish_outcome'] = published.outcome
    out['quarters'] = [{'quarter': q.quarter, 'outcome': q.outcome} for q in published.quarters]
    out['spent_s'] = {k: round(v, 2) for k, v in sorted(spent.items(), key=lambda item: -item[1])}
    out['calls'] = dict(calls)
    out['by_quarter_s'] = {q: {k: round(v, 2) for k, v in d.items()} for q, d in sorted(by_quarter.items())}
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: out[k] for k in ('transform_s', 'publish_s', 'publish_outcome', 'spent_s')}))


if __name__ == '__main__':
    main()
