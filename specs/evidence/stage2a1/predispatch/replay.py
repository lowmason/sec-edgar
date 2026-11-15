"""Stage 2a1, plan 9 Task 6: replay plan 8's selection on a scratch clone, with a dispatcher that sends nothing.

Run every subcommand with a release's own interpreter and flags, against scratch clones only:

    <release>/venv/bin/python -I -B -X pycache_prefix=/dev/null replay.py diff <live-root> <backup-root> <diff.json>
    ... replay.py cut <root> <diff.json> {1,2} <saved-rows.json>
    ... replay.py run <root> <saved-rows.json> {1,2} <out.json> [--branch]
    ... replay.py project <new-1.json> <new-2.json> <2a-2.json> <projection.json>

`diff` reads a live clone and a backup clone (`state.sqlite3` with a `mode=ro` URI, object files by path). It lists
each added, changed, version-only and removed row by (partition, key), with value SHA-256s and never a value, and
assigns each added row to plan 8's invocation 1 or 2. `cut` restores one invocation's starting state on a fresh live
clone: it saves and deletes the rows that its discovery child and dispatcher wrote, deletes its projected members and
bindings for good, and removes its frozen selection and result. `run` loads that invocation's own context and
intent, and calls `run_workflow` with a dispatcher whose one `discover` call puts the saved rows back and returns
the recorded child. An observer stops the run at `workflow.after_selection`, before the first member dispatch.
`project` fits the P4 model to three `run` outputs.

The script imports only names that the 2a release has. It looks up the new code's names (`WorkflowMembers.of_source`,
`runner.SelectionChecks`) with getattr. It opens a store only by explicit path and its stored binding. Every path
argument, and every store root, must not resolve under the live `data/` or `backups/`.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import statistics
import sys
import time
import traceback
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from sec_edgar_ingest.config import Settings
from sec_edgar_ingest.models import RunContext, canonical_json, parse_json, to_mapping_value
from sec_edgar_ingest.runtime import preflight_current
from sec_edgar_ingest.storage import local as storage_local
from sec_edgar_ingest.storage.contracts import REGISTRY_PATH, identity, payload_bytes, table_for
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.workflows import runner
from sec_edgar_ingest.workflows.checked import CheckedChild, call_ref, read_child
from sec_edgar_ingest.workflows.contracts import workflow_path
from sec_edgar_ingest.workflows.members import WorkflowMembers
from sec_edgar_ingest.workflows.results import workflow_key
from sec_edgar_ingest.worksets import decode_source_workset

PROJECT_ROOT = Path('/Users/lowell/Projects/sec-edgar-local')
FORBIDDEN_ROOTS = (PROJECT_ROOT / 'data', PROJECT_ROOT / 'backups')
# F1: plan 8's two v2 invocations, (run_id, attempt_id), in start order.
INVOCATIONS = {1: ('0746b217-d4ca-4f1d-9b05-d0c447b734ce', '6efe8c93-e50a-434f-b209-4128936e09e7'),
               2: ('bdefaa5d-856d-4bc4-a621-018e66b6ef1e', '625ccd33-4701-4e4b-ac0c-a43c98d39e91')}
# F7: invocation 2's recorded discovery call.
F7_CALL_REF = ('runs/sec/bdefaa5d-856d-4bc4-a621-018e66b6ef1e/backfill/625ccd33-4701-4e4b-ac0c-a43c98d39e91'
               '/children/wf-9d6e24b5586f3b747981db4ba6d1db6ae62fd34e/call.json')
CHANGEABLE_KINDS = frozenset({'Source', '_Lease', 'QueueTicket', 'TransportAttempt'})
# Rows that an invocation's discovery child and dispatcher wrote: saved, deleted, and put back at `discover`.
DISCOVERY_KINDS = frozenset({'DiscoverySession', 'DirectoryProgress', 'Attempt', 'WorkflowChildCall',
                             'WorkflowChildExecution', 'QueueTicket', 'TransportAttempt', 'Source', 'Failure'})
# Rows that the invocation's projection wrote: deleted for good, because the replay writes them again.
PROJECTION_KINDS = frozenset({'WorkflowMember', 'Binding'})
RUN_ID_KINDS = frozenset({'Attempt', 'WorkflowAttempt', 'WorkflowChildCall', 'TransportAttempt', 'Failure'})
ASSIGNMENT_RULES = {
    'Attempt': 'context.run_id',
    'WorkflowAttempt': 'context.run_id; the two rows are numbered by context.started_at and must equal F1',
    'WorkflowChildCall': 'context.run_id',
    'TransportAttempt': 'context.run_id',
    'Failure': 'context.run_id, and discovery_id must equal that invocation\'s discovery_id (not in the brief\'s list)',
    'WorkflowChildExecution': 'call_ref equals checked.call_ref() of an added WorkflowChildCall row',
    'QueueTicket': 'owner_id is execution_id:attempt_id:uuid; the first two parts match the context of an added '
                   'Attempt or TransportAttempt row',
    'DiscoverySession': 'discovery_id equals workflow-<command>-<run_id>',
    'DirectoryProgress': 'discovery_id equals workflow-<command>-<run_id>',
    'WorkflowMember': 'parent_ref equals the parent workset of the invocation\'s DiscoverySession',
    'Binding': 'source_workset_id is the member_id of an added WorkflowMember row',
    'Source': 'the earliest invocation whose parent workset lists source.source_id',
}
REGISTERED_AFTER_CUT = {1: 127, 2: 155}
PROJECTED_ROW_COUNTS = {1: {'WorkflowMember': 28, 'Binding': 28}, 2: {'WorkflowMember': 53, 'Binding': 48}}  # F4
PHASES = ('before_discovery', 'discovery_replayed', 'projection', 'after_discovery', 'freeze')
# The calls that make up one member's cost in each phase. Freeze has no per-member call among the timed ones.
PER_MEMBER_FUNCTIONS = {'before_discovery': ('WorkflowMembers.completed', 'evaluate_member'),
                        'projection': ('project_member', 'reuse_exact_binding'),
                        'after_discovery': ('evaluate_member', 'capture_member_provenance'),
                        'freeze': ()}
LAUNCHER_S = 1.0  # invocation 2: started_at 18:31:08.26Z to intent.json at 18:31:08Z (F1, diagnosis §3)
DISCOVERY_S = 29.0  # invocation 2's discovery child (diagnosis §3)
CUTOFF_S, TARGET_S = 1500.0, 600.0
# P4: each fitted phase, the run field it is fitted against, and that field's value at the growth allowance.
FITS = (('before_discovery', 'registered_at_start', 450),
        ('projection', 'members_reaching_registry_check', 55),
        ('after_discovery', 'registered_after_projection', 505),
        ('freeze', 'registered_after_projection', 505))
EXIT_OK, EXIT_FAILED, EXIT_STOP, EXIT_SELECTION_DIFFERS, EXIT_SLOPE, EXIT_REFUSED = 0, 1, 2, 3, 4, 5
DIFF_FORMAT = 'stage2a1-predispatch-diff-v1'
ROWS_FORMAT = 'stage2a1-predispatch-saved-rows-v1'
RUN_FORMAT = 'stage2a1-predispatch-run-v1'
PROJECTION_FORMAT = 'stage2a1-predispatch-projection-v1'


class Refused(Exception):
    """A path argument or a store root resolves under the live data/ or backups/."""


class Anomaly(Exception):
    """The store or a file differs from what the task expects: stop and ask."""


class Stop(Exception):
    """Raised by the observer at workflow.after_selection, before the first member dispatch."""


class UnexpectedCall(RuntimeError):
    """The replay dispatcher accepts exactly one discover call."""


# ---------------------------------------------------------------------------------------------------------- helpers

def refuse_forbidden(path, label: str) -> Path:
    resolved = Path(path).resolve()
    for root in FORBIDDEN_ROOTS:
        base = root.resolve()
        if resolved == base or resolved.is_relative_to(base):
            raise Refused(f'{label} {path} resolves to {resolved}, under {base}')
    return resolved


def guard_store_roots() -> None:
    """Make every local store constructor refuse a root under data/ or backups/, whoever builds it."""
    for cls in (storage_local.LocalObjectStore, storage_local.LocalStateStore, storage_local.LocalLeaseStore):
        def guarded(self, root, *args, _original=cls.__init__, _name=cls.__name__, **kwargs):
            refuse_forbidden(root, _name + ' root')
            _original(self, root, *args, **kwargs)
        cls.__init__ = guarded


def refuse_existing(*paths: Path) -> None:
    for path in paths:
        if path.exists() or path.is_symlink():
            raise FileExistsError(f'refusing to overwrite {path}')


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dump(value) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True) + '\n').encode()


def write_new(path: Path, value) -> None:
    with path.open('xb') as stream:
        stream.write(dump(value))


def replace_file(path: Path, value) -> None:
    temporary = path.with_name(path.name + '.pending')
    with temporary.open('xb') as stream:
        stream.write(dump(value))
    os.replace(temporary, path)


def kind_of(partition: str) -> str:
    return partition.split(':', 1)[1]


def open_stores(root: Path):
    binding = json.loads((root / 'objects' / REGISTRY_PATH).read_bytes())
    objects = LocalObjectStore(root, binding=binding, create=False)
    store = LocalStateStore(root, binding=binding, create=False)
    return objects, store


def read_records(database: Path):
    """Every `records` row and every `sentinel_journal` row, read through a mode=ro URI."""
    connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    try:
        rows = {}
        for table, partition, key, value, version in connection.execute(
                'SELECT table_name, partition, key, value, version FROM records'):
            if (partition, key) in rows:
                raise Anomaly(f'two tables hold one (partition, key): {partition} {key}')
            rows[partition, key] = (table, value, version)
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        journal = ({name: (value, version) for name, value, version in
                    connection.execute('SELECT identity, value, version FROM sentinel_journal')}
                   if 'sentinel_journal' in tables else {})
    finally:
        connection.close()
    return rows, journal


def registered_members(root: Path) -> list[str]:
    """The member IDs of every WorkflowMember row, by a raw mode=ro read that decodes nothing else."""
    partition, _ = identity('WorkflowMember', 'scan')
    connection = sqlite3.connect((root / 'state.sqlite3').as_uri() + '?mode=ro', uri=True)
    try:
        bodies = [row[0] for row in connection.execute(
            'SELECT value FROM records WHERE table_name=? AND partition=?', (table_for('WorkflowMember'), partition))]
    finally:
        connection.close()
    return sorted(json.loads(body)['member_id'] for body in bodies)


def object_files(root: Path) -> dict[str, tuple[str, int]]:
    base = root / 'objects'
    found = {}
    for directory, folders, files in os.walk(base):
        folders.sort()
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink():
                raise Anomaly(f'object is a symlink: {path}')
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            found[path.relative_to(base).as_posix()] = (digest, path.stat().st_size)
    return found


def descriptor(ref: str, body: bytes) -> dict:
    return {'ref': ref, 'sha256': sha256(body), 'bytes': len(body)}


def member_id(value):
    return value.get('member_id') if isinstance(value, Mapping) else None


def file_digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


# ------------------------------------------------------------------------------------------------------------- diff

def command_diff(args) -> int:
    live_root = refuse_forbidden(args.live_root, '<live-root>')
    backup_root = refuse_forbidden(args.backup_root, '<backup-root>')
    out = refuse_forbidden(args.diff_json, '<diff.json>')
    refuse_existing(out)
    live, live_journal = read_records(live_root / 'state.sqlite3')
    backup, backup_journal = read_records(backup_root / 'state.sqlite3')
    stops = []
    namespaces = sorted({partition.split(':', 1)[0] for partition, _ in (*live, *backup)})
    for (partition, key), (table, _, _) in (*live.items(), *backup.items()):
        if identity(kind_of(partition), key)[0] != partition or table_for(kind_of(partition)) != table:
            stops.append(f'row {partition} {key} has a partition or table that its kind does not give')
    added_keys = sorted(live.keys() - backup.keys())
    removed_keys = sorted(backup.keys() - live.keys())
    common = sorted(live.keys() & backup.keys())
    changed_keys = [key for key in common if live[key][1] != backup[key][1]]
    version_keys = [key for key in common if live[key][1] == backup[key][1] and live[key][2] != backup[key][2]]
    values = {key: parse_json(live[key][1]) for key in added_keys}
    by_kind = defaultdict(list)
    for key in added_keys:
        by_kind[kind_of(key[0])].append(key)

    # Number the invocations from their WorkflowAttempt rows and check them against F1.
    begun = sorted((datetime.fromisoformat(values[key]['context']['started_at']), key)
                   for key in by_kind['WorkflowAttempt'])
    found = [(values[key]['context']['run_id'], values[key]['context']['attempt_id']) for _, key in begun]
    if found != [INVOCATIONS[1], INVOCATIONS[2]]:
        raise Anomaly(f'added WorkflowAttempt rows {found} differ from F1 {list(INVOCATIONS.values())}')
    invocations = {}
    for number, (_, key) in enumerate(begun, 1):
        context = RunContext.from_mapping(values[key]['context'])
        if workflow_key(context) != key[1]:
            raise Anomaly(f'invocation {number} WorkflowAttempt key differs from workflow_key(context)')
        base = workflow_path(context).rsplit('/', 1)[0]
        invocations[number] = {'run_id': context.run_id, 'attempt_id': context.attempt_id,
                               'execution_id': context.execution_id, 'command': context.command,
                               'started_at': context.started_at.isoformat(), 'workflow_attempt_key': key[1],
                               'intent_ref': base + '/intent.json',
                               'discovery_id': 'workflow-' + context.command + '-' + context.run_id}
        for name in ('selection', 'result'):
            ref = f'{base}/{name}.json'
            invocations[number][name] = descriptor(ref, (live_root / 'objects' / ref).read_bytes())
    by_run = {value['run_id']: number for number, value in invocations.items()}
    by_discovery = {value['discovery_id']: number for number, value in invocations.items()}
    for key in by_kind['DiscoverySession']:
        number = by_discovery.get(values[key].get('discovery_id'))
        if number is not None:
            invocations[number]['parent_ref'] = (
                f'worksets/sec/source/sha256={values[key]["workset_id"]}/workset.json')
    listed = {}
    for number, value in invocations.items():
        if 'parent_ref' not in value:
            raise Anomaly(f'invocation {number} has no added DiscoverySession row')
        parent = decode_source_workset((live_root / 'objects' / value['parent_ref']).read_bytes())
        listed[number] = {source.source_id for source in parent.members}
        value['parent_sources'] = len(listed[number])
    by_parent = {value['parent_ref']: number for number, value in invocations.items()}

    assigned = {}
    for kind in RUN_ID_KINDS:
        for key in by_kind[kind]:
            context = values[key].get('context')
            number = by_run.get(context.get('run_id')) if isinstance(context, dict) else None
            if kind == 'Failure' and number is not None and (
                    values[key].get('discovery_id') != invocations[number]['discovery_id']):
                number = None
            assigned[key] = number
    contexts, call_refs = {}, {}
    for kind in ('Attempt', 'TransportAttempt'):
        for key in by_kind[kind]:
            if assigned[key] is None:
                continue
            context = values[key]['context']
            pair = (context['execution_id'], context['attempt_id'])
            if contexts.setdefault(pair, assigned[key]) != assigned[key]:
                raise Anomaly(f'execution and attempt {pair} belong to both invocations')
    for key in by_kind['WorkflowChildCall']:
        if assigned[key] is not None:
            call_refs[call_ref(values[key])] = assigned[key]
            invocations[assigned[key]].setdefault('discovery_call_refs', []).append(call_ref(values[key]))
    for key in by_kind['WorkflowChildExecution']:
        assigned[key] = call_refs.get(values[key].get('call_ref'))
    for key in by_kind['QueueTicket']:
        parts = str(values[key].get('owner_id')).split(':')
        assigned[key] = contexts.get((parts[0], parts[1])) if len(parts) == 3 else None
    for kind in ('DiscoverySession', 'DirectoryProgress'):
        for key in by_kind[kind]:
            assigned[key] = by_discovery.get(values[key].get('discovery_id'))
    members = {}
    for key in by_kind['WorkflowMember']:
        assigned[key] = by_parent.get(values[key].get('parent_ref'))
        if assigned[key] is not None:
            members[values[key]['member_id']] = assigned[key]
    for key in by_kind['Binding']:
        assigned[key] = members.get(values[key].get('source_workset_id'))
    for key in by_kind['Source']:
        source = values[key].get('source')
        source_id = source.get('source_id') if isinstance(source, dict) else None
        assigned[key] = next((number for number in (1, 2) if source_id in listed[number]), None)

    added = []
    for key in added_keys:
        table, body, _ = live[key]
        kind = kind_of(key[0])
        added.append({'partition': key[0], 'table_name': table, 'kind': kind, 'key': key[1],
                      'value_sha256': sha256(body.encode()), 'invocation': assigned.get(key)})
    unassigned = [entry for entry in added if entry['invocation'] is None]
    changed = [{'partition': key[0], 'table_name': live[key][0], 'kind': kind_of(key[0]), 'key': key[1],
                'backup_value_sha256': sha256(backup[key][1].encode()), 'live_value_sha256': sha256(live[key][1].encode())}
               for key in changed_keys]
    refused_changes = [entry for entry in changed if entry['kind'] not in CHANGEABLE_KINDS]
    version_only = [{'partition': key[0], 'table_name': live[key][0], 'kind': kind_of(key[0]), 'key': key[1],
                     'value_sha256': sha256(live[key][1].encode())} for key in version_keys]
    removed = [{'partition': key[0], 'table_name': backup[key][0], 'kind': kind_of(key[0]), 'key': key[1],
                'value_sha256': sha256(backup[key][1].encode())} for key in removed_keys]
    for number, value in invocations.items():
        mine = [entry for entry in added if entry['invocation'] == number]
        value['added_rows'] = dict(sorted(Counter(entry['kind'] for entry in mine).items()))
        value['discover_attempts'] = sum(1 for key in by_kind['Attempt']
                                         if assigned[key] == number and values[key]['context']['command'] == 'discover')
    if unassigned:
        stops.append(f'{len(unassigned)} added rows are unassigned')
    if refused_changes:
        stops.append(f'{len(refused_changes)} changed rows have a kind outside {sorted(CHANGEABLE_KINDS)}')
    if removed:
        stops.append(f'{len(removed)} backup rows are absent from the live clone')

    live_objects, backup_objects = object_files(live_root), object_files(backup_root)
    journal_names = sorted(live_journal.keys() | backup_journal.keys())
    result = {
        'format': DIFF_FORMAT, 'created_at': utc_now(), 'live_root': str(live_root), 'backup_root': str(backup_root),
        'state_sha256': {'live': file_digest(live_root / 'state.sqlite3'),
                         'backup': file_digest(backup_root / 'state.sqlite3')},
        'namespaces': namespaces, 'assignment_rules': ASSIGNMENT_RULES,
        'changeable_kinds': sorted(CHANGEABLE_KINDS),
        'invocations': {str(number): value for number, value in invocations.items()},
        'row_counts': {'live': len(live), 'backup': len(backup), 'added': len(added), 'changed': len(changed),
                       'version_only': len(version_only), 'removed': len(removed), 'unassigned': len(unassigned)},
        'rows': {'added': added, 'changed': changed, 'version_only': version_only, 'removed': removed},
        'sentinel_journal': [{'identity': name,
                              'backup_value_sha256': sha256(backup_journal[name][0].encode()) if name in backup_journal else None,
                              'live_value_sha256': sha256(live_journal[name][0].encode()) if name in live_journal else None,
                              'version_changed': live_journal.get(name, (None, None))[1] != backup_journal.get(name, (None, None))[1]}
                             for name in journal_names],
        'objects': {'live': len(live_objects), 'backup': len(backup_objects),
                    'added': [{'path': path, 'sha256': live_objects[path][0], 'bytes': live_objects[path][1]}
                              for path in sorted(live_objects.keys() - backup_objects.keys())],
                    'changed': [{'path': path, 'backup_sha256': backup_objects[path][0], 'live_sha256': live_objects[path][0]}
                                for path in sorted(live_objects.keys() & backup_objects.keys())
                                if live_objects[path] != backup_objects[path]],
                    'removed': sorted(backup_objects.keys() - live_objects.keys())},
        'stops': stops, 'exit': EXIT_STOP if stops else EXIT_OK,
    }
    write_new(out, result)
    summary = {'row_counts': result['row_counts'],
               'invocations': {number: {'added_rows': value['added_rows'], 'discover_attempts': value['discover_attempts']}
                               for number, value in invocations.items()},
               'changed': dict(Counter(entry['kind'] for entry in changed)),
               'version_only': dict(Counter(entry['kind'] for entry in version_only)),
               'objects_added': len(result['objects']['added']), 'stops': stops}
    print(json.dumps(summary, indent=1, sort_keys=True))
    return result['exit']


# -------------------------------------------------------------------------------------------------------------- cut

def command_cut(args) -> int:
    root = refuse_forbidden(args.root, '<root>')
    diff_path = refuse_forbidden(args.diff_json, '<diff.json>')
    rows_path = refuse_forbidden(args.saved_rows, '<saved-rows.json>')
    number = args.invocation
    selection_copy = rows_path.parent / f'saved-selection-{number}.json'
    refuse_existing(rows_path, selection_copy, rows_path.with_name(rows_path.name + '.pending'))
    diff_body = diff_path.read_bytes()
    diff = json.loads(diff_body)
    if diff.get('format') != DIFF_FORMAT or diff.get('exit') != EXIT_OK:
        raise Anomaly('the diff is not a clean ' + DIFF_FORMAT)
    invocation = diff['invocations'][str(number)]
    live, _ = read_records(root / 'state.sqlite3')
    # A fresh live clone holds every added row and every changed row exactly as the diff saw them.
    for entry in diff['rows']['added']:
        row = live.get((entry['partition'], entry['key']))
        if row is None or row[0] != entry['table_name'] or sha256(row[1].encode()) != entry['value_sha256']:
            raise Anomaly(f'{root} is not a fresh live clone: added row {entry["kind"]} {entry["key"]} differs')
    for entry in diff['rows']['changed']:
        row = live.get((entry['partition'], entry['key']))
        if row is None or sha256(row[1].encode()) != entry['live_value_sha256']:
            raise Anomaly(f'{root} is not a fresh live clone: changed row {entry["kind"]} {entry["key"]} differs')
    saved, forever, attempt = [], [], None
    for entry in diff['rows']['added']:
        if entry['invocation'] == number:
            if entry['kind'] in DISCOVERY_KINDS:
                saved.append(entry)
            elif entry['kind'] in PROJECTION_KINDS:
                forever.append(entry)
            elif entry['kind'] == 'WorkflowAttempt':
                attempt = entry
            else:
                raise Anomaly(f'invocation {number} row of kind {entry["kind"]} has no cut rule')
    projected = dict(Counter(entry['kind'] for entry in forever))
    if projected != PROJECTED_ROW_COUNTS[number]:
        raise Anomaly(f'invocation {number} projection rows {projected} differ from F4 {PROJECTED_ROW_COUNTS[number]}')
    if number == 1:
        forever.extend(entry for entry in diff['rows']['added']
                       if entry['invocation'] == 2 and entry['kind'] != 'WorkflowAttempt')
    if attempt is None or attempt['key'] != invocation['workflow_attempt_key']:
        raise Anomaly(f'invocation {number} WorkflowAttempt row differs from the diff')
    saved_rows = []
    for entry in sorted(saved, key=lambda e: (e['kind'], e['key'])):
        table, body, version = live[entry['partition'], entry['key']]
        if payload_bytes(parse_json(body)).decode('utf-8') != body:
            raise Anomaly(f'saved row {entry["kind"]} {entry["key"]} is not canonical, so insert would change it')
        if entry['kind'] in ('Attempt', 'WorkflowChildCall') and parse_json(body)['context']['command'] != 'discover':
            raise Anomaly(f'invocation {number} {entry["kind"]} {entry["key"]} is not its discover child')
        saved_rows.append({'table_name': table, 'partition': entry['partition'], 'kind': entry['kind'],
                           'key': entry['key'], 'value': body, 'version': version,
                           'value_sha256': entry['value_sha256']})
    calls = [row for row in saved_rows if row['kind'] == 'WorkflowChildCall']
    if len(calls) != 1:
        raise Anomaly(f'invocation {number} has {len(calls)} WorkflowChildCall rows, not one')
    call = parse_json(calls[0]['value'])
    discovery_call_ref = call_ref(call)
    if number == 2 and discovery_call_ref != F7_CALL_REF:
        raise Anomaly(f'invocation 2 discovery call {discovery_call_ref} differs from F7')
    objects, store = open_stores(root)
    try:
        if objects.read(discovery_call_ref) != canonical_json(to_mapping_value(call)):
            raise Anomaly('the recorded call.json differs from its WorkflowChildCall row')
        row = store.get('WorkflowAttempt', attempt['key'])
        value = row.to_mapping()['value']
        context = RunContext.from_mapping(value['context'])
        if (context.run_id, context.attempt_id) != INVOCATIONS[number] or workflow_key(context) != attempt['key']:
            raise Anomaly(f'invocation {number} WorkflowAttempt row has another context')
        selection_ref = invocation['selection']['ref']
        result_ref = invocation['result']['ref']
        if (value['selection_ref'] is None or value['result_ref'] is None
                or value['selection_ref']['ref'] != selection_ref or value['result_ref']['ref'] != result_ref):
            raise Anomaly(f'invocation {number} WorkflowAttempt refs are not the saved ones: not a fresh clone')
        selection_body = objects.read(selection_ref)
        if descriptor(selection_ref, selection_body) != invocation['selection'] or (
                value['selection_ref']['sha256'] != invocation['selection']['sha256']):
            raise Anomaly(f'invocation {number} selection.json differs from the diff')
        result_body = objects.read(result_ref)
        if descriptor(result_ref, result_body) != invocation['result']:
            raise Anomaly(f'invocation {number} result.json differs from the diff')
        with selection_copy.open('xb') as stream:
            stream.write(selection_body)
        record = {'format': ROWS_FORMAT, 'state': 'saved', 'created_at': utc_now(), 'invocation': number,
                  'root': str(root), 'diff': str(diff_path), 'diff_sha256': sha256(diff_body),
                  'run_id': context.run_id, 'attempt_id': context.attempt_id, 'command': context.command,
                  'intent_ref': invocation['intent_ref'], 'discovery_call_ref': discovery_call_ref,
                  'workflow_attempt_key': attempt['key'],
                  'saved_selection': {'file': selection_copy.name, **invocation['selection']},
                  'deleted_objects': [invocation['selection'], invocation['result']],
                  'saved_rows': saved_rows,
                  'saved_row_counts': dict(sorted(Counter(row['kind'] for row in saved_rows).items())),
                  'deleted_for_good': [{'kind': entry['kind'], 'key': entry['key'], 'invocation': entry['invocation'],
                                        'value_sha256': entry['value_sha256']} for entry in forever],
                  'deleted_for_good_counts': {str(n): dict(sorted(Counter(e['kind'] for e in forever
                                                                          if e['invocation'] == n).items()))
                                              for n in sorted({e['invocation'] for e in forever})},
                  'registered_expected': REGISTERED_AFTER_CUT[number], 'registered_after_cut': None}
        write_new(rows_path, record)
        # F4: the state database has no delete call, so rows are deleted with raw SQLite on the clone.
        connection = sqlite3.connect(root / 'state.sqlite3', timeout=5)
        try:
            connection.execute('BEGIN IMMEDIATE')
            for entry in (*saved_rows, *forever):
                count = connection.execute('DELETE FROM records WHERE table_name=? AND partition=? AND key=?',
                                           (entry['table_name'], entry['partition'], entry['key'])).rowcount
                if count != 1:
                    connection.rollback()
                    raise Anomaly(f'delete of {entry["kind"]} {entry["key"]} removed {count} rows')
            connection.commit()
        finally:
            connection.close()
        value['selection_ref'] = value['result_ref'] = None
        store.replace('WorkflowAttempt', attempt['key'], value, row.version)
    finally:
        store.close()
    for ref in (selection_ref, result_ref):
        (root / 'objects' / ref).unlink()
    registered = len(registered_members(root))
    record.update(state='cut' if registered == REGISTERED_AFTER_CUT[number] else 'count_differs',
                  registered_after_cut=registered)
    replace_file(rows_path, record)
    print(json.dumps({'invocation': number, 'saved_row_counts': record['saved_row_counts'],
                      'deleted_for_good_counts': record['deleted_for_good_counts'],
                      'registered_after_cut': registered, 'registered_expected': REGISTERED_AFTER_CUT[number],
                      'saved_selection': record['saved_selection']}, indent=1, sort_keys=True))
    if registered != REGISTERED_AFTER_CUT[number]:
        print(f'STOP: registered count {registered} differs from {REGISTERED_AFTER_CUT[number]}', file=sys.stderr)
        return EXIT_STOP
    return EXIT_OK


# -------------------------------------------------------------------------------------------------------------- run

class Recorder:
    """Phase marks and call times, all from time.perf_counter()."""

    def __init__(self):
        self.marks, self.marks_utc, self.calls = {}, {}, []
        self.in_reuse = False
        self.reuse_reached = False
        self.events = []

    def mark(self, name: str, *, last: bool = False) -> None:
        now = time.perf_counter()
        if last or name not in self.marks:
            self.marks[name] = now
            self.marks_utc[name] = utc_now()

    def observer(self, point: str) -> None:
        self.events.append(point)
        if point == 'workflow.after_selection':
            self.mark('after_selection')
            raise Stop(point)
        raise Anomaly('observer event before workflow.after_selection: ' + point)

    def timed(self, label: str, function, member_of):
        def wrapper(*args, **kwargs):
            start, result = time.perf_counter(), None
            try:
                result = function(*args, **kwargs)
                return result
            finally:
                self.calls.append({'function': label, 'start': start, 'end': time.perf_counter(),
                                   'member_id': member_of(args, result)})
        return wrapper

    def reuse(self, function):
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            self.in_reuse, self.reuse_reached = True, False
            try:
                return function(*args, **kwargs)
            finally:
                end = time.perf_counter()
                self.calls.append({'function': 'reuse_exact_binding', 'start': start, 'end': end,
                                   'member_id': member_id(args[0]) if args else None,
                                   'registry_check': self.reuse_reached})
                self.in_reuse = False
                self.mark('last_reuse_return', last=True)
        return wrapper

    def registry(self, label: str, function):
        def wrapper(*args, **kwargs):
            start, inside = time.perf_counter(), self.in_reuse
            if inside:
                self.reuse_reached = True
            try:
                return function(*args, **kwargs)
            finally:
                self.calls.append({'function': label, 'start': start, 'end': time.perf_counter(),
                                   'member_id': None, 'in_reuse': inside})
        return wrapper

    def freeze(self, function):
        def wrapper(*args, **kwargs):
            self.mark('freeze_entry')
            try:
                return function(*args, **kwargs)
            finally:
                self.mark('freeze_return')
        return wrapper


def instrument(recorder: Recorder) -> dict:
    """Wrap the names where `select_work` and `run_workflow` look them up: runner's module attributes, and the class."""
    has_of_source = getattr(WorkflowMembers, 'of_source', None) is not None
    has_selection_checks = getattr(runner, 'SelectionChecks', None) is not None

    def first_argument(args, result):
        return member_id(args[0]) if args else None

    def returned(args, result):
        return member_id(result)

    def method_argument(args, result):  # args[0] is the WorkflowMembers instance
        return member_id(args[1]) if len(args) > 1 else None

    def no_member(args, result):
        return None

    for name, member_of in (('evaluate_member', first_argument), ('capture_member_provenance', first_argument),
                            ('project_member', returned), ('bootstrap_legacy', no_member)):
        setattr(runner, name, recorder.timed(name, getattr(runner, name), member_of))
    runner.reuse_exact_binding = recorder.reuse(runner.reuse_exact_binding)
    runner.freeze_selection = recorder.freeze(runner.freeze_selection)
    WorkflowMembers.completed = recorder.timed('WorkflowMembers.completed', WorkflowMembers.completed, method_argument)
    WorkflowMembers.inventory = recorder.registry('WorkflowMembers.inventory', WorkflowMembers.inventory)
    if has_of_source:
        WorkflowMembers.of_source = recorder.registry('WorkflowMembers.of_source', getattr(WorkflowMembers, 'of_source'))
    return {'runner_file': runner.__file__, 'has_of_source': has_of_source,
            'has_selection_checks': has_selection_checks,
            'registry_check_function': 'WorkflowMembers.of_source' if has_of_source else 'WorkflowMembers.inventory'}


class ReplayDispatcher:
    """Accepts exactly one call: execute('discover', 'discover', settings, flags) with the recorded flags."""

    def __init__(self, call, rows, settings, store, objects, recorder):
        intent = call['intent']
        self.flags = ('--mode', intent['mode'], '--discovery-id', intent['discovery_id'],
                      *(('--refresh',) if intent['refresh'] else ()))
        self.call, self.rows, self.store, self.objects, self.recorder = call, rows, store, objects, recorder
        self.settings_body = canonical_json(to_mapping_value(settings.to_mapping()))
        self.calls = 0

    def execute(self, command, step_id, settings, flags):
        self.recorder.mark('discover_entry')
        self.calls += 1
        if (self.calls != 1 or (command, step_id) != ('discover', 'discover') or flags != self.flags
                or canonical_json(to_mapping_value(settings.to_mapping())) != self.settings_body):
            raise UnexpectedCall(f'replay dispatcher refuses call {self.calls}: {command} {step_id} {flags}')
        for row in self.rows:
            self.store.insert(row['kind'], row['key'], parse_json(row['value']))
            stored = self.store.get(row['kind'], row['key'])
            if payload_bytes(stored.to_mapping()['value']).decode('utf-8') != row['value']:
                raise Anomaly(f'restored {row["kind"]} {row["key"]} differs from the saved value')
        child = CheckedChild(self.call, self.call['result_ref'], read_child(self.call, self.store, self.objects))
        self.recorder.mark('discover_return')
        return child


def phase_bounds(marks: dict) -> list[tuple[float, float, str]]:
    start, entry, returned = marks['run_start'], marks['discover_entry'], marks['discover_return']
    projected = marks.get('last_reuse_return', returned)
    frozen, stopped = marks['freeze_entry'], marks['after_selection']
    return [(start, entry, 'before_discovery'), (entry, returned, 'discovery_replayed'),
            (returned, projected, 'projection'), (projected, frozen, 'after_discovery'), (frozen, stopped, 'freeze')]


def phase_of(bounds, start: float) -> str:
    return next((name for low, high, name in bounds if low <= start < high), 'outside')


def per_member_times(calls: list[dict], phase: str, *, reaching_only: bool = False) -> list[float]:
    """Each member's summed call time in `phase`, over the phase's per-member functions."""
    functions = PER_MEMBER_FUNCTIONS[phase]
    reaching = {call['member_id'] for call in calls if call['function'] == 'reuse_exact_binding'
                and call['phase'] == phase and call.get('registry_check')}
    totals = defaultdict(float)
    for call in calls:
        if call['phase'] == phase and call['function'] in functions and call['member_id'] is not None:
            if not reaching_only or call['member_id'] in reaching:
                totals[call['member_id']] += call['seconds']
    return sorted(totals.values())


def describe_times(times: list[float]) -> dict:
    return {'members': len(times), 'median_s': round(statistics.median(times), 6) if times else None,
            'total_s': round(sum(times), 6), 'max_s': round(max(times), 6) if times else None}


def selection_fields_that_differ(body: bytes, saved: bytes) -> list[str]:
    ours, theirs = parse_json(body), parse_json(saved)
    return sorted(name for name in set(ours) | set(theirs) if ours.get(name, KeyError) != theirs.get(name, KeyError))


def command_run(args) -> int:
    root = refuse_forbidden(args.root, '<root>')
    rows_path = refuse_forbidden(args.saved_rows, '<saved-rows.json>')
    out = refuse_forbidden(args.out_json, '<out.json>')
    refuse_existing(out)
    number = args.invocation
    if args.branch:
        release = 'branch'  # The shadow venv is not a release, so preflight_current is skipped (a check, not evidence).
    else:
        release = preflight_current(Path(sys.prefix).parent / 'release.json').release_id
    rows_body = rows_path.read_bytes()
    saved = json.loads(rows_body)
    if (saved.get('format') != ROWS_FORMAT or saved.get('state') != 'cut' or saved.get('invocation') != number
            or Path(saved['root']) != root):
        raise Anomaly(f'{rows_path} is not a completed cut of invocation {number} on {root}')
    saved_selection = (rows_path.parent / saved['saved_selection']['file']).read_bytes()
    if sha256(saved_selection) != saved['saved_selection']['sha256']:
        raise Anomaly('the saved selection differs from its recorded SHA-256')
    objects, store = open_stores(root)
    result = {'format': RUN_FORMAT, 'invocation': number, 'release': release, 'root': str(root),
              'saved_rows': str(rows_path), 'saved_rows_sha256': sha256(rows_body),
              'interpreter': {'executable': sys.executable, 'prefix': sys.prefix, 'version': sys.version.split()[0],
                              'isolated': bool(sys.flags.isolated), 'dont_write_bytecode': sys.dont_write_bytecode,
                              'pycache_prefix': sys.pycache_prefix}}
    try:
        frozen = parse_json(objects.read(saved['intent_ref']))
        context = RunContext.from_mapping(frozen['context'])
        intent = frozen['intent']
        if (context.run_id, context.attempt_id) != INVOCATIONS[number]:
            raise Anomaly(f'intent.json context is not invocation {number}')
        settings = Settings.from_mapping(context.to_mapping()['effective_config'])
        selection_ref = workflow_path(context).rsplit('/', 1)[0] + '/selection.json'
        try:
            objects.read(selection_ref)
        except FileNotFoundError:
            pass
        else:
            raise Anomaly(f'{selection_ref} exists: each run needs a fresh cut')
        call = parse_json(objects.read(saved['discovery_call_ref']))
        recorder = Recorder()
        dispatcher = ReplayDispatcher(call, saved['saved_rows'], settings, store, objects, recorder)
        result['code'] = instrument(recorder)
        start_members = registered_members(root)
        result['started_at'] = utc_now()
        result['loadavg_start'] = list(os.getloadavg())
        recorder.mark('run_start')
        try:
            runner.run_workflow(context, settings, intent, dispatcher, store, objects, observer=recorder.observer)
        except Stop:
            pass
        else:
            raise Anomaly('run_workflow returned without the workflow.after_selection event')
        result['loadavg_end'] = list(os.getloadavg())
        result['ended_at'] = utc_now()
        if dispatcher.calls != 1 or recorder.events != ['workflow.after_selection']:
            raise Anomaly(f'discover ran {dispatcher.calls} times; observer events {recorder.events}')
        end_members = registered_members(root)
        body = objects.read(selection_ref)
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
        result['traceback'] = traceback.format_exc()
        result['exit'] = EXIT_FAILED
        write_new(out, result)
        raise
    finally:
        store.close()
    marks, bounds = recorder.marks, phase_bounds(recorder.marks)
    calls = []
    for call_ in sorted(recorder.calls, key=lambda c: c['start']):
        entry = {'function': call_['function'], 'phase': phase_of(bounds, call_['start']),
                 'member_id': call_['member_id'], 'start_s': round(call_['start'] - marks['run_start'], 6),
                 'seconds': round(call_['end'] - call_['start'], 6)}
        for name in ('registry_check', 'in_reuse'):
            if name in call_:
                entry[name] = call_[name]
        calls.append(entry)
    phases = {name: round(high - low, 6) for low, high, name in bounds}
    summary = defaultdict(dict)
    for (function, phase), times in sorted(_group(calls).items()):
        summary[function][phase] = {'count': len(times), 'total_s': round(sum(times), 6),
                                    'median_s': round(statistics.median(times), 6), 'max_s': round(max(times), 6)}
    per_member = {phase: {'functions': list(PER_MEMBER_FUNCTIONS[phase]), **describe_times(per_member_times(calls, phase))}
                  for phase in PHASES if phase != 'discovery_replayed'}
    per_member['projection']['reaching_registry_check'] = describe_times(
        per_member_times(calls, 'projection', reaching_only=True))
    check = result['code']['registry_check_function']
    in_reuse = [c for c in calls if c['function'] == check and c.get('in_reuse')]
    outside = [c for c in calls if c['function'] in ('WorkflowMembers.inventory', 'WorkflowMembers.of_source')
               and not c.get('in_reuse')]
    new_ids = sorted(set(end_members) - set(start_members))
    equal = body == saved_selection
    result.update({
        'registered_at_start': len(start_members), 'registered_after_projection': len(end_members),
        'new_members': len(new_ids), 'new_member_ids': new_ids,
        'projected_members': sum(1 for c in calls if c['function'] == 'project_member'),
        'members_reaching_registry_check': sum(1 for c in calls if c['function'] == 'reuse_exact_binding'
                                               and c.get('registry_check')),
        'registry_check': {'function': check, 'calls_in_reuse': len(in_reuse),
                           'seconds_in_reuse': round(sum(c['seconds'] for c in in_reuse), 6),
                           'calls_outside_reuse': len(outside),
                           'seconds_outside_reuse': round(sum(c['seconds'] for c in outside), 6)},
        'marks_s': {name: round(value - marks['run_start'], 6) for name, value in sorted(marks.items())},
        'marks_utc': dict(sorted(recorder.marks_utc.items())),
        'phases_s': phases,
        'first_dispatch_s': round(LAUNCHER_S + DISCOVERY_S + sum(v for k, v in phases.items() if k != 'discovery_replayed'), 6),
        'first_dispatch_model': {'launcher_s': LAUNCHER_S, 'discovery_s': DISCOVERY_S,
                                 'formula': 'launcher_s + before_discovery + discovery_s + projection + after_discovery + freeze'},
        'calls_outside_phases': sum(1 for c in calls if c['phase'] == 'outside'),
        'calls_summary': dict(summary), 'per_member': per_member,
        'selection': {**descriptor(selection_ref, body), 'saved_sha256': sha256(saved_selection),
                      'saved_bytes': len(saved_selection), 'equal': equal,
                      'differing_fields': [] if equal else selection_fields_that_differ(body, saved_selection)},
        'calls': calls,
    })
    result['exit'] = EXIT_SELECTION_DIFFERS if (not equal and number == 2) else EXIT_OK
    write_new(out, result)
    print(json.dumps({key: result[key] for key in ('invocation', 'release', 'registered_at_start',
                      'registered_after_projection', 'new_members', 'members_reaching_registry_check', 'phases_s',
                      'first_dispatch_s', 'loadavg_start', 'loadavg_end', 'exit')}
                     | {'selection': {k: v for k, v in result['selection'].items() if k != 'ref'}}, indent=1, sort_keys=True))
    if not equal:
        print(f'selection differs from the saved one in fields: {result["selection"]["differing_fields"]}', file=sys.stderr)
    return result['exit']


def _group(calls):
    grouped = defaultdict(list)
    for call in calls:
        grouped[call['function'], call['phase']].append(call['seconds'])
    return grouped


# ---------------------------------------------------------------------------------------------------------- project

def factor(slope: float, median: float) -> float:
    if slope == median:
        return 1.0
    low, high = sorted((slope, median))
    return float('inf') if low <= 0 else high / low


def command_project(args) -> int:
    paths = {'new_1': refuse_forbidden(args.new_1, '<new-1.json>'), 'new_2': refuse_forbidden(args.new_2, '<new-2.json>'),
             'release_2a_2': refuse_forbidden(args.release_2a_2, '<2a-2.json>')}
    out = refuse_forbidden(args.projection_json, '<projection.json>')
    refuse_existing(out)
    bodies = {name: path.read_bytes() for name, path in paths.items()}
    runs = {name: json.loads(body) for name, body in bodies.items()}
    for name, number in (('new_1', 1), ('new_2', 2), ('release_2a_2', 2)):
        if runs[name].get('format') != RUN_FORMAT or runs[name].get('invocation') != number or 'phases_s' not in runs[name]:
            raise Anomaly(f'{paths[name]} is not a completed run of invocation {number}')
    if runs['new_1']['release'] != runs['new_2']['release']:
        raise Anomaly('the two new-release runs come from different releases')
    new_1, new_2, old = runs['new_1'], runs['new_2'], runs['release_2a_2']
    phases, failed = {}, []
    for phase, field, allowance in FITS:
        (x1, y1), (x2, y2) = ((run[field], run['phases_s'][phase]) for run in (new_1, new_2))
        times = sorted(per_member_times(new_1['calls'], phase, reaching_only=phase == 'projection')
                       + per_member_times(new_2['calls'], phase, reaching_only=phase == 'projection'))
        entry = {'x_field': field, 'points': [[x1, y1], [x2, y2]], 'x_at_allowance': allowance,
                 'per_member_functions': list(PER_MEMBER_FUNCTIONS[phase]), 'per_member_count': len(times),
                 'median_per_member_s': round(statistics.median(times), 6) if times else None}
        if x1 == x2:
            entry.update(check='fail', reason='both runs have the same count, so there is no slope')
            failed.append(phase)
            phases[phase] = entry
            continue
        raw = (y2 - y1) / (x2 - x1)
        slope = max(0.0, raw)
        anchor_x, anchor_y = max((x1, y1), (x2, y2))
        entry.update(slope_raw=round(raw, 6), slope=round(slope, 6), clamped=raw < 0, anchor=[anchor_x, anchor_y],
                     at_allowance_s=round(anchor_y + slope * (allowance - anchor_x), 6))
        if not times:
            entry.update(check='not_applicable', reason='no per-member call is timed in this phase')
        else:
            ratio = factor(slope, statistics.median(times))
            entry.update(factor=None if ratio == float('inf') else round(ratio, 6),
                         check='pass' if ratio <= 2 else 'fail')
            if ratio > 2:
                failed.append(phase)
        phases[phase] = entry
    result = {'format': PROJECTION_FORMAT, 'created_at': utc_now(),
              'inputs': {name: {'path': str(paths[name]), 'sha256': sha256(bodies[name]), 'release': runs[name]['release'],
                                'invocation': runs[name]['invocation'], 'first_dispatch_s': runs[name]['first_dispatch_s'],
                                'selection_equal': runs[name]['selection']['equal']} for name in paths},
              'model': {'launcher_s': LAUNCHER_S, 'discovery_s': DISCOVERY_S,
                        'allowance': {field: allowance for _, field, allowance in FITS},
                        'fit': 'line through the two new-release runs, slope clamped at 0, anchored at the run with '
                               'the larger count; each slope must be within a factor of 2 of the median per-member '
                               'call time of its phase (pooled over both runs; projection: members that reached the '
                               'registry check)',
                        'ratio_scaled_2a': 'each 2a phase time times (allowance count / the 2a run\'s count of the '
                                           'same field), a phase with a zero count kept unscaled'},
              'cutoff_s': CUTOFF_S, 'target_s': TARGET_S, 'phases': phases, 'failed_checks': failed}
    if failed:
        result.update(new_release=None, release_2a=None, exit=EXIT_SLOPE)
        write_new(out, result)
        print(f'slope check failed for {failed}: nothing projected', file=sys.stderr)
        return EXIT_SLOPE
    new_total = LAUNCHER_S + DISCOVERY_S + sum(phases[phase]['at_allowance_s'] for phase, _, _ in FITS)
    scaled, unscaled = {}, []
    for phase, field, allowance in FITS:
        count = old[field]
        if count:
            scaled[phase] = round(old['phases_s'][phase] * allowance / count, 6)
        else:
            scaled[phase] = old['phases_s'][phase]
            unscaled.append(phase)
    old_scaled = LAUNCHER_S + DISCOVERY_S + sum(scaled.values())
    result.update({
        'new_release': {'release': new_1['release'], 'first_dispatch_at_allowance_s': round(new_total, 6),
                        'before_cutoff': new_total < CUTOFF_S, 'within_target': new_total <= TARGET_S},
        'release_2a': {'release': old['release'], 'measured_first_dispatch_s': old['first_dispatch_s'],
                       'measured_before_cutoff': old['first_dispatch_s'] < CUTOFF_S,
                       'ratio_scaled_phases_s': scaled, 'ratio_scaled_unscaled_phases': unscaled,
                       'ratio_scaled_first_dispatch_s': round(old_scaled, 6),
                       'ratio_scaled_before_cutoff': old_scaled < CUTOFF_S},
        'exit': EXIT_OK})
    write_new(out, result)
    print(json.dumps({'new_release': result['new_release'], 'release_2a': result['release_2a']}, indent=1, sort_keys=True))
    return EXIT_OK


# ------------------------------------------------------------------------------------------------------------- main

def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(
        description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='exit codes: 0 done; 1 failed; 2 diff or cut found an anomaly (stop and ask); 3 run: invocation 2\'s '
               'selection differs from the saved one; 4 project: a slope check failed; 5 a path is under data/ or backups/')
    commands = top.add_subparsers(dest='command', required=True)
    diff = commands.add_parser('diff', help='list and assign the rows that plan 8 added (read-only)')
    diff.add_argument('live_root', type=Path)
    diff.add_argument('backup_root', type=Path)
    diff.add_argument('diff_json', type=Path)
    cut = commands.add_parser('cut', help='restore one invocation\'s starting state on a fresh live clone')
    cut.add_argument('root', type=Path)
    cut.add_argument('diff_json', type=Path)
    cut.add_argument('invocation', type=int, choices=(1, 2))
    cut.add_argument('saved_rows', type=Path)
    run = commands.add_parser('run', help='replay the invocation\'s selection and time its phases')
    run.add_argument('root', type=Path)
    run.add_argument('saved_rows', type=Path)
    run.add_argument('invocation', type=int, choices=(1, 2))
    run.add_argument('out_json', type=Path)
    run.add_argument('--branch', action='store_true', help='skip preflight_current: the interpreter is not a release')
    project = commands.add_parser('project', help='fit the P4 model and project to the growth allowance')
    project.add_argument('new_1', type=Path)
    project.add_argument('new_2', type=Path)
    project.add_argument('release_2a_2', type=Path)
    project.add_argument('projection_json', type=Path)
    return top


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    guard_store_roots()
    command = {'diff': command_diff, 'cut': command_cut, 'run': command_run, 'project': command_project}[args.command]
    try:
        return command(args)
    except Refused as error:
        print('REFUSED: ' + str(error), file=sys.stderr)
        return EXIT_REFUSED
    except Anomaly as error:
        print('STOP: ' + str(error), file=sys.stderr)
        return EXIT_STOP
    except Exception as error:
        traceback.print_exc()
        print(f'FAILED: {type(error).__name__}: {error}', file=sys.stderr)
        return EXIT_FAILED


if __name__ == '__main__':
    sys.exit(main())
