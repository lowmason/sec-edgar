"""Stage 2a1 diagnosis: time the pieces of `select_work` on a scratch copy of the store.

Run with a release's own interpreter and `-I`, against a fresh clone of the store:

    <release>/venv/bin/python -I profile_selection.py <store-copy> <phase> <out.json> [--n N] [--profile out.prof]

Phases (each re-creates the work that `runner.select_work` / `freeze_selection` does for one run):

- `before`: `bootstrap_legacy`, `WorkflowMembers.inventory`, then for each sampled retained member
  `WorkflowMembers.completed` and, when that returns None, `evaluate_member` (runner.py:189-207).
- `project`: for each sampled source of a discovery parent, `project_member` and `reuse_exact_binding`
  (runner.py:233-238). The parent is `--parent` (default: invocation 2's parent).
- `after`: for each sampled member, `evaluate_member` and `capture_member_provenance` (runner.py:261-283).
- `freeze`: `freeze_selection` on invocation 2's saved selection (results.py:371).

No dispatcher is built, so no discovery child runs and no SEC request is possible. The store copy is
written to (repair rows, `put_once`, `immutable`), so each run needs its own fresh copy.
"""
import argparse
import cProfile
import json
import time
from collections import Counter
from pathlib import Path

from sec_edgar_ingest.models import RunContext, parse_json
from sec_edgar_ingest.storage.contracts import REGISTRY_PATH
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.workflows import completion, provenance
from sec_edgar_ingest.workflows.completion import capture_member_provenance, evaluate_member
from sec_edgar_ingest.workflows.legacy import bootstrap_legacy
from sec_edgar_ingest.workflows.members import WorkflowMembers
from sec_edgar_ingest.workflows.results import freeze_selection
from sec_edgar_ingest.workflows.runner import reuse_exact_binding

RUN2 = 'runs/sec/bdefaa5d-856d-4bc4-a621-018e66b6ef1e/backfill/625ccd33-4701-4e4b-ac0c-a43c98d39e91'
PARENT2 = 'worksets/sec/source/sha256=bd4d52a98339aa13138c282626b01fe20a51529ae0dac38a735ec385e1a2680c/workset.json'


class Counters:
    """Count store scans (calls and rows), object reads (calls and bytes) and selected functions."""

    def __init__(self, store, objects):
        self.calls, self.rows, self.read_bytes = Counter(), Counter(), Counter()
        scan, read = store.scan, objects.read

        def counted_scan(kind, filters):
            self.calls['scan:' + kind] += 1
            for row in scan(kind, filters):
                self.rows['scan:' + kind] += 1
                yield row

        def counted_read(path):
            body = read(path)
            self.calls['objects.read'] += 1
            self.read_bytes['objects.read'] += len(body)
            return body

        store.scan, objects.read = counted_scan, counted_read
        for module, name in ((completion, '_publish_calls'), (completion, '_obligations'),
                             (provenance, 'read_parent'), (completion, 'read_parent')):
            if hasattr(module, name):
                setattr(module, name, self._wrap(name, getattr(module, name)))

    def _wrap(self, name, function):
        def counted(*args, **kwargs):
            self.calls['fn:' + name] += 1
            return function(*args, **kwargs)
        return counted

    def snapshot(self):
        return {'calls': dict(self.calls), 'rows': dict(self.rows), 'bytes': dict(self.read_bytes)}


def cache_type_hints():
    """Spike for the diagnosis only: one `get_type_hints` result per record type (models.py:238, :280)."""
    import sec_edgar_ingest.models as models
    original, cache = models.get_type_hints, {}

    def cached(obj, *args, **kwargs):
        if args or kwargs:
            return original(obj, *args, **kwargs)
        try:
            return cache[obj]
        except KeyError:
            value = cache[obj] = original(obj)
            return value

    models.get_type_hints = cached


def memoize_store_wide():
    """Spike for the diagnosis only: compute each store-wide step once in this process.

    `_publish_calls` once, `read_parent` once per parent ref, `WorkflowMembers.inventory` once. This is not safe
    across writes and is not a design: it bounds what removing the repetition (§1 items 1-3) could save.
    The per-member decode of each publish input inside `_obligations` stays, so the estimate is conservative.
    """
    import sys
    from sec_edgar_ingest.workflows import members
    publish_calls, parents, inventories = completion._publish_calls, {}, {}
    read_parent, inventory = provenance.read_parent, members.WorkflowMembers.inventory

    def memo_publish_calls(store, objects):
        if 'value' not in inventories:
            inventories['value'] = publish_calls(store, objects)
        return inventories['value']

    def memo_read_parent(ref, store, objects):
        if ref not in parents:
            parents[ref] = read_parent(ref, store, objects)
        return parents[ref]

    def memo_inventory(self):
        if 'registry' not in inventories:
            inventories['registry'] = inventory(self)
        return inventories['registry']

    completion._publish_calls = memo_publish_calls
    for module in list(sys.modules.values()):
        if getattr(module, '__name__', '').startswith('sec_edgar_ingest') and module.__dict__.get('read_parent') is read_parent:
            module.read_parent = memo_read_parent
    members.WorkflowMembers.inventory = memo_inventory


def sample(values, n):
    if n is None or n >= len(values):
        return list(values)
    step = len(values) / n
    return [values[int(i * step)] for i in range(n)]


def timed(fn, *args):
    start = time.perf_counter()
    result = fn(*args)
    return time.perf_counter() - start, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('phase', choices=('before', 'project', 'after', 'freeze'))
    parser.add_argument('out', type=Path)
    parser.add_argument('--n', type=int)
    parser.add_argument('--parent', default=PARENT2)
    parser.add_argument('--parser-version', default='sec-index-parser-v2')
    parser.add_argument('--schema-version', default='sec-index-v2')
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--cache-type-hints', action='store_true')
    parser.add_argument('--memoize-store-wide', action='store_true')
    args = parser.parse_args()
    if args.cache_type_hints:
        cache_type_hints()
    if args.memoize_store_wide:
        memoize_store_wide()
    binding = json.loads((args.root / 'objects' / REGISTRY_PATH).read_bytes())
    objects = LocalObjectStore(args.root, binding=binding, create=False)
    store = LocalStateStore(args.root, binding=binding, create=False)
    counters = Counters(store, objects)
    registry = WorkflowMembers(store, objects)
    pv, sv = args.parser_version, args.schema_version
    out = {'phase': args.phase, 'root': str(args.root), 'parser_version': pv, 'schema_version': sv,
           'n': args.n, 'items': [], 'once': {}, 'cache_type_hints': args.cache_type_hints,
           'memoize_store_wide': args.memoize_store_wide}
    profiler = cProfile.Profile() if args.profile else None
    if profiler:
        profiler.enable()
    wall = time.perf_counter()
    if args.phase == 'before':
        out['once']['bootstrap_legacy_s'], gaps = timed(bootstrap_legacy, store, objects)
        out['once']['bootstrap_gaps'] = len(gaps)
        out['once']['inventory_s'], (retained, rgaps) = timed(registry.inventory)
        out['once']['retained'] = len(retained)
        out['once']['after_once'] = counters.snapshot()
        for value in sample(retained, args.n):
            before = counters.snapshot()
            t_done, done = timed(registry.completed, value, pv, sv)
            item = {'member_id': value['member_id'], 'kind': value['source']['kind'],
                    'period': value['source']['period'], 'completed_s': t_done, 'completed': done is not None}
            if done is None:
                item['evaluate_s'], ev = timed(evaluate_member, value, pv, sv, store, objects)
                item['evaluate_complete'] = ev.complete
                item['gaps'] = sorted({g.code for g in ev.gaps})
            item['counters'] = _delta(before, counters.snapshot())
            out['items'].append(item)
    elif args.phase == 'project':
        parent = provenance.read_parent(args.parent, store, objects)
        out['once']['parent_members'] = len(parent.members)
        for source in sample(list(parent.members), args.n):
            before = counters.snapshot()
            t_proj, value = timed(provenance.project_member, args.parent, source.source_id, store, objects)
            t_reuse, gaps = timed(reuse_exact_binding, value, store, objects)
            out['items'].append({'member_id': value['member_id'], 'kind': source.kind, 'period': source.period,
                                 'project_s': t_proj, 'reuse_s': t_reuse, 'reuse_gaps': len(gaps),
                                 'counters': _delta(before, counters.snapshot())})
    elif args.phase == 'after':
        retained, _ = registry.inventory()
        for value in sample(retained, args.n):
            before = counters.snapshot()
            t_eval, ev = timed(evaluate_member, value, pv, sv, store, objects)
            t_prov, _ = timed(capture_member_provenance, value, store, objects)
            out['items'].append({'member_id': value['member_id'], 'kind': value['source']['kind'],
                                 'period': value['source']['period'], 'evaluate_s': t_eval,
                                 'provenance_s': t_prov, 'evaluate_complete': ev.complete,
                                 'counters': _delta(before, counters.snapshot())})
    elif args.phase == 'freeze':
        saved = parse_json(objects.read(RUN2 + '/selection.json'))
        context = RunContext.from_mapping(saved['context'])
        out['once']['members'] = len(saved['members'])
        out['once']['freeze_s'], _ = timed(freeze_selection, context, saved, store, objects)
    out['wall_s'] = time.perf_counter() - wall
    if profiler:
        profiler.disable()
        profiler.dump_stats(args.profile)
    out['totals'] = counters.snapshot()
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    per = [item for item in out['items']]
    keys = [k for k in ('completed_s', 'evaluate_s', 'project_s', 'reuse_s', 'provenance_s') if per and k in per[0]]
    summary = {k: round(sum(i.get(k, 0) for i in per) / len(per), 3) for k in keys} if per else {}
    print(json.dumps({'phase': args.phase, 'n': len(per), 'wall_s': round(out['wall_s'], 1),
                      'mean_per_item_s': summary, 'once': {k: v for k, v in out['once'].items() if k != 'after_once'}}))


def _delta(before, after):
    result = {}
    for group in ('calls', 'rows', 'bytes'):
        result[group] = {k: v - before[group].get(k, 0) for k, v in after[group].items() if v - before[group].get(k, 0)}
    return result


if __name__ == '__main__':
    main()
