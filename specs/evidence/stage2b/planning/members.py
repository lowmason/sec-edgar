"""Plan 8 planning fact F1 (read-only, scratch copy): which registered members count as complete under v1 and v2.

Run on the 2a interpreter against a scratch copy of data/, never the live root:

    releases/sha256=<2A>/venv/bin/python -I -B -X pycache_prefix=/dev/null members.py <scratch>/data > members-v2.json

It opens the copy with its stored binding (the plan 2 Task 3e Step 4 method) and writes nothing.
"""
import json
import sys
from collections import Counter
from pathlib import Path

from sec_edgar_ingest.storage.contracts import REGISTRY_PATH
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.workflows.completion import evaluate_member
from sec_edgar_ingest.workflows.members import WorkflowMembers

root = Path(sys.argv[1])
binding = json.loads((root / 'objects' / REGISTRY_PATH).read_bytes())
objects = LocalObjectStore(root, binding=binding, create=False)
store = LocalStateStore(root, binding=binding, create=False)
registry = WorkflowMembers(store, objects)
inventory, inv_gaps = registry.inventory()
receipts = Counter((r['parser_version'], r['schema_version'])
                   for r in (row.to_mapping()['value'] for row in store.scan('WorkflowMemberResult', {})))
V1, V2 = ('sec-index-parser-v1', 'sec-index-v1'), ('sec-index-parser-v2', 'sec-index-v2')
rows = []
for member in inventory:
    row = {'period': member['source']['period'], 'kind': member['source']['kind'], 'member_id': member['member_id'][:12]}
    for tag, versions in (('v1', V1), ('v2', V2)):
        try:
            row['completed_' + tag] = registry.completed(member, *versions) is not None
        except Exception as error:
            row['completed_' + tag] = 'error: ' + type(error).__name__
        found = evaluate_member(member, *versions, store, objects)
        row['eval_' + tag] = {'complete': found.complete, 'obligations': len(found.obligations),
                              'gaps': sorted({(g.code, g.retryable) for g in found.gaps})}
    rows.append(row)
rows.sort(key=lambda r: (r['period'], r['member_id']))


def tally(tag):
    return {'completed_by_receipt': sum(r['completed_' + tag] is True for r in rows),
            'eval_complete': sum(r['eval_' + tag]['complete'] for r in rows),
            'gap_codes': dict(sorted(Counter(g[0] for r in rows for g in r['eval_' + tag]['gaps']).items())),
            'stop_before_dispatch': [r['period'] for r in rows if r['eval_' + tag]['obligations'] == 0
                                     and any(not g[1] for g in r['eval_' + tag]['gaps'])]}


print(json.dumps({'members': len(rows), 'inventory_gaps': len(inv_gaps),
                  'receipts_by_versions': {'/'.join(k): v for k, v in receipts.items()},
                  'kinds': dict(Counter(r['kind'] for r in rows)), 'v1': tally('v1'), 'v2': tally('v2'),
                  'dispatch_order': [(r['period'], r['kind'][0]) for r in rows]}, indent=1, default=str))
