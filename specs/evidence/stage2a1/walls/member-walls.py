"""Stage 2a1, plan 9 Task 7: member walls in true dispatch order, with the engine work that plan 8 left out.

A copy of plan 8's `specs/evidence/stage2b/scratch/order-timing.py` (P5). Run every subcommand with a release's own
interpreter and flags, against scratch clones only:

    <release>/venv/bin/python -I -B -X pycache_prefix=/dev/null member-walls.py walls \
        <root> <config> <results.jsonl> <convergence.json> [--validate-only] [--branch]
    ... member-walls.py origins <live-root> <origins.json>
    ... member-walls.py starts <scratch-config> <origins.json> <scratch-root> <starts.json>

`walls` keeps plan 8's targets, order and production calls (`run_transform` and `run_publish` in-process, on a
scratch copy of the plan 8 Task 3 backup opened with its stored binding, with a fresh pinned context per call). For
each step that is not a repeat it also times the member's engine work in-process, one result line per term:

- before the transform: `sibling_completion`, `read_member`, `WorkflowMembers.replay`, `evaluate_member`;
- the collect body of collection.py:192-200 (an unbound member verifies the step's chosen snapshot instead);
- after the publish: `evaluate_member`, then twice (process_member, then registry.record) `read_etl_result` of the
  transform and publish results and `validate_capture` of the member's capture, with `read_member` before the second.

The member is the registered member of the step's source with the lowest member_id that passes `read_member`. Each
member gets a fresh workflow context (command backfill, built by `new_context` and pinned). `--validate-only` checks
every target and member, prints the plan, the chosen members and the convergence of the untouched copy, and writes no
file (it writes to the store: `retain_manifest`, and `evaluate_member` in the convergence check). `--branch` replaces
`preflight_current` with the read-only `preflight` of the config's release, whose manifest is still retained: the
interpreter is not a release, so its times are a check, not evidence.

`origins` reads a fresh live clone: every registered member of each target source, its parent and the release in its
origin context's runtime, and one origin effective config per origin release. `starts` runs the P5 child-start probe
(import the CLI, `load_config`, `preflight_current`) five times per release, each a child process started with
`native_python_argv(<release python>)`: the new release with <scratch-config>, and each origin release with a config made
from its origin effective config and storage and logging roots under <scratch-root>.

The script imports only names that the 2a release has. It opens a store only by explicit path and its stored binding,
and creates no network client. Every path argument, and every store root, must not be or be below the live `data/` or
`backups/`, by resolved prefix or by file identity of the path or an existing parent. No subcommand overwrites a file.
Exit codes: 0 done; 1 failed (or an output exists); 2 anomaly, stop and ask; 5 a path is under data/ or backups/.
"""
import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
import traceback
import uuid
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sec_edgar_ingest import collection
from sec_edgar_ingest.config import Settings, load_config, pin_context
from sec_edgar_ingest.etl.commands import read_etl_result, run_publish, run_transform
from sec_edgar_ingest.etl.contracts import Candidate, processing_key
from sec_edgar_ingest.etl.reader import capture_quarter, checked_manifest
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.models import RunContext, canonical_json, to_mapping_value
from sec_edgar_ingest.results import result_path
from sec_edgar_ingest.runtime import (configured_descriptor, isolated_environment, native_python_argv, preflight,
                                      preflight_current, resolve_child, retain_manifest)
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.storage import local as storage_local
from sec_edgar_ingest.storage.contracts import REGISTRY_PATH, Conflict
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.worksets import decode_snapshot_workset, decode_source_workset
from sec_edgar_ingest.workflows import runner
from sec_edgar_ingest.workflows.completion import evaluate_member, validate_capture
from sec_edgar_ingest.workflows.contracts import COMPLETE
from sec_edgar_ingest.workflows.members import WorkflowMembers
from sec_edgar_ingest.workflows.provenance import read_member

SNAPSHOT_DIR = 'worksets/sec/snapshot'
BASE_QUARTER = '2024Q1'
# step -> (kind, period, source_id). Step 3's source is D, chosen from the 2024Q1 manifest.
FIXED = {
    1: ('quarterly', '2024Q1', 'b2d153963f7d7f903ea8c4d2fcb4b6cf58e8d12ffa633ddc82cb57de0131fd63'),
    2: ('daily', '2026-07-01', '924fd5f5b380e8a8603bab21b91edcd9408962b3a25fe812f067b25777063d58'),
    4: ('daily', '2026-10-01', '6cf7f339fd98f08d888586fbf41d907cb071d3a54259128e659f51e1f7caaa72'),
    5: ('quarterly', '2026Q1', 'f8f05c9fd9e634303de40171631df987c8977b784ebd5919c1896e4e13d2ed12'),
    6: ('quarterly', '2026Q3', '5005901a1e8132207ea0cf7a0d4bec1d7b9ca3a6f0371b9e45c9eb2863045086'),
    8: ('daily', '2026-09-24', 'd2c80002601d76fb076f7141eb07bb5c0c995f56ffe1f3dbed1a9bd427805dd2'),
    10: ('quarterly', '2026Q4', 'd64895140b037ef3df3e0c867437b555053c3a14c33d8c0c3526c9067354d0c7'),
}
REPEATS = {7: 6, 9: 8}  # publish again with the transformed workset of the step before

PROJECT_ROOT = Path('/Users/lowell/Projects/sec-edgar-local')
FORBIDDEN_ROOTS = (PROJECT_ROOT / 'data', PROJECT_ROOT / 'backups')
# F8: the releases retained in releases/ when plan 9 was written.
F8_RELEASES = ('49b7a2ed', '900952a8', '9fa189a0', 'aa8de1ac', 'c4de77b8', 'd718ae5f', 'e49d3ba8', 'fc68adef')
SIDECAR = 'member-walls-targets.json'
# What `WorkflowMembers.inventory()` reports and skips when a member's read raises (workflows/members.py).
MEMBER_READ_ERRORS = (ValueError, OSError, Conflict, KeyError, TypeError)
# Per member: 4 terms before the transform, the collect body, and 8 terms after the publish (P5).
ENGINE_TERMS_PER_MEMBER = 13
PROBE_RUNS = 5
PROBE_TIMEOUT_S = 600
# P5's fixed child-start probe: what a child does before its command (cli.py main: import, _validate, _verified_runtime).
PROBE = '''import json, sys, time
started = time.perf_counter()
import sec_edgar_ingest.cli
from pathlib import Path
from sec_edgar_ingest.config import load_config
from sec_edgar_ingest.runtime import preflight_current
imported = time.perf_counter()
settings = load_config(Path(sys.argv[1]))
loaded = time.perf_counter()
verified = preflight_current(Path(settings.runtime.release_manifest))
done = time.perf_counter()
print(json.dumps({"release_id": verified.release_id, "import_s": imported - started,
                  "load_config_s": loaded - imported, "preflight_current_s": done - loaded}))
'''
TARGETS_FORMAT = 'stage2a1-member-walls-targets-v1'
ORIGINS_FORMAT = 'stage2a1-member-walls-origins-v1'
STARTS_FORMAT = 'stage2a1-member-walls-starts-v1'
EXIT_OK, EXIT_FAILED, EXIT_STOP, EXIT_REFUSED = 0, 1, 2, 5


class Anomaly(Exception):
    """A target or the store differs from the plan: nothing has been timed yet."""


class Refused(Exception):
    """A path argument or a store root resolves under the live data/ or backups/."""


def new_context(settings, command: str) -> RunContext:
    started = datetime.now(timezone.utc)
    run_id = 'stage2b-scratch-' + uuid.uuid4().hex
    context = RunContext(run_id=run_id, execution_id=run_id, command=command, attempt_id=uuid.uuid4().hex,
                         runtime=configured_descriptor(settings), format_version='sec-local-run-context-v1',
                         parser_version=settings.etl.parser_version, schema_version=settings.etl.schema_version,
                         config_sha256=settings.config_sha256, started_at=started,
                         deadline=started + timedelta(seconds=settings.execution.max_run_seconds), priority='backfill')
    return pin_context(settings, context, started.date())[0]


def append(path: Path, record: dict) -> None:
    line = json.dumps({'at': datetime.now(timezone.utc).isoformat(), **record}, sort_keys=True, default=str)
    with path.open('a') as stream:
        stream.write(line + '\n')
        stream.flush()
    print(line, flush=True)


# ---------------------------------------------------------------------------------------------------------- guards

def refuse_forbidden(path, label: str) -> Path:
    """Refuse `path` when it is, or is below, the live data/ or backups/, in any spelling.

    The prefix check after `resolve()` misses spellings that name the same directory: the volume is
    case-insensitive and `resolve()` keeps the typed case, and the `/System/Volumes/Data` firmlink keeps its prefix.
    So the resolved path and each existing parent are also compared by file identity (`os.path.samefile`). That only
    stats; it opens no file. A path that does not exist yet is checked through its nearest existing parent.
    """
    resolved = Path(path).resolve()
    bases = [root.resolve() for root in FORBIDDEN_ROOTS]
    for base in bases:
        if resolved == base or resolved.is_relative_to(base):
            raise Refused(f'{label} {path} resolves to {resolved}, under {base}')
    for candidate in (resolved, *resolved.parents):
        for base in bases:
            try:
                same = os.path.samefile(candidate, base)
            except (FileNotFoundError, NotADirectoryError):
                continue  # this spelling does not exist (yet): its parents decide
            except OSError as error:
                raise Refused(f'{label} {path}: cannot compare {candidate} with {base}: {error}') from error
            if same:
                raise Refused(f'{label} {path} resolves to {resolved}, and {candidate} is the same directory as {base}')
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


def open_stores(root: Path):
    binding = json.loads((root / 'objects' / REGISTRY_PATH).read_bytes())
    objects = LocalObjectStore(root, binding=binding, create=False)
    store = LocalStateStore(root, binding=binding, create=False)
    return objects, store


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def file_digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_new(path: Path, value) -> None:
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=1, sort_keys=True, default=str) + '\n').encode())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def interpreter() -> dict:
    return {'executable': sys.executable, 'prefix': sys.prefix, 'version': sys.version.split()[0],
            'isolated': bool(sys.flags.isolated), 'dont_write_bytecode': sys.dont_write_bytecode,
            'pycache_prefix': sys.pycache_prefix}


def under(path, root: Path, label: str) -> Path:
    resolved = refuse_forbidden(path, label)
    if not resolved.is_relative_to(root):
        raise Anomaly(f'{label} {resolved} is not under {root}')
    return resolved


# ------------------------------------------------------------------------------------------------- plan 8's plan

def pick_d(objects, state) -> dict:
    """D: the daily source with the earliest period in the active 2024Q1 manifest."""
    capture = capture_quarter(BASE_QUARTER, objects, state)
    if capture is None:
        raise Anomaly(BASE_QUARTER + ' has no active generation')
    manifest = checked_manifest(capture, objects)
    dailies = sorted((ref.source.period, ref.source.source_id) for ref in manifest.sources if ref.source.kind == 'daily')
    if not dailies:
        raise Anomaly(BASE_QUARTER + ' manifest lists no daily source')
    return {'period': dailies[0][0], 'source_id': dailies[0][1], 'daily_sources_in_manifest': len(dailies),
            'generation_id': capture.generation_id, 'schema_version': manifest.schema_version}


def locate(root: Path, objects, wanted: set[str]) -> dict[str, list[dict]]:
    """Every snapshot workset that holds a wanted source, with its snapshot count and receipt time."""
    found = defaultdict(list)
    for directory in sorted((root / 'objects' / SNAPSHOT_DIR).iterdir()):
        ref = f'{SNAPSHOT_DIR}/{directory.name}/workset.json'
        try:
            workset = decode_snapshot_workset(objects.read(ref))
        except Exception as error:
            raise Anomaly(f'undecodable snapshot workset {ref}: {type(error).__name__}: {error}') from error
        for snapshot in workset.snapshots:
            if snapshot.source_id in wanted:
                found[snapshot.source_id].append({
                    'workset_ref': ref, 'workset_id': workset.workset_id, 'source_workset_id': workset.source_workset_id,
                    'snapshots': len(workset.snapshots), 'received_at': snapshot.received_at.isoformat(),
                    'raw_sha256': snapshot.sha256, 'period': snapshot.raw_path.split('/period=')[1].split('/')[0]})
    return found


def pick_member(step, target, store, objects) -> dict:
    """The registered member of the step's source with the lowest member_id that passes `read_member`.

    Jobs run in (period, source_id, member_id) order, so this is the first member of its source in the run loop.
    """
    values = []
    for row in store.scan('WorkflowMember', {}):
        value = row.to_mapping()['value']
        if (isinstance(value, dict) and isinstance(value.get('source'), dict)
                and value['source'].get('source_id') == target['source_id']):
            values.append(value)
    values.sort(key=lambda value: value['member_id'])
    refused = []
    for value in values:
        try:
            member = read_member(value, store, objects)
        except MEMBER_READ_ERRORS as error:
            refused.append({'member_id': value['member_id'], 'error': f'{type(error).__name__}: {error}'})
            continue
        if value['source']['period'] != target['period']:
            raise Anomaly(f'step {step}: member {value["member_id"]} names period {value["source"]["period"]}')
        binding = AcquisitionState(store).binding(value['member_id'], target['source_id'])
        pinned = None if binding is None else binding.snapshot_sha256
        return {'member_id': value['member_id'], 'value': dict(value),
                'registered': [other['member_id'] for other in values], 'refused_lower': refused,
                'unbound': binding is None, 'pinned_sha256': pinned,
                'pin_is_chosen': pinned == target['chosen']['raw_sha256'],
                'origin_release': member.context.to_mapping()['runtime'].get('release_sha256'),
                'origin_config_sha256': member.context.config_sha256}
    raise Anomaly(f'step {step}: no registered member of {target["source_id"]} passes read_member '
                  f'({len(values)} registered, refused: {refused})')


def plan(root: Path, objects, store) -> dict:
    state = EtlState(store)
    d = pick_d(objects, state)
    targets = {step: {'kind': kind, 'period': period, 'source_id': source_id} for step, (kind, period, source_id) in FIXED.items()}
    skipped = []
    if d['source_id'] == FIXED[2][2]:
        skipped.append(3)
    elif d['source_id'] in {FIXED[4][2], FIXED[8][2]}:
        raise Anomaly('D is the source of step 4 or 8, so a step would repeat: ' + d['source_id'])
    else:
        targets[3] = {'kind': 'daily', 'period': d['period'], 'source_id': d['source_id']}
    found = locate(root, objects, {target['source_id'] for target in targets.values()})
    for step, target in sorted(targets.items()):
        candidates = found.get(target['source_id'], [])
        # A member's snapshot workset holds exactly one snapshot (workflows/processing.py), so only those count.
        singles = [c for c in candidates if c['snapshots'] == 1]
        if not singles:
            raise Anomaly(f'step {step} {target["period"]}: no singleton snapshot workset ({len(candidates)} candidates)')
        if any(c['period'] != target['period'] for c in candidates):
            raise Anomaly(f'step {step}: a workset names another period than {target["period"]}')
        # Latest receipt wins. Identical bytes keep their first receipt time, so break ties by workset ref.
        chosen = max(singles, key=lambda c: (c['received_at'], c['workset_ref']))
        target.update(candidates=candidates, chosen=chosen)
    for step, target in sorted(targets.items()):  # Stage 2a1 (P5): each step that is not a repeat times a member
        target['member'] = pick_member(step, target, store, objects)
    first = [2, 3, 4] if 3 not in skipped else [2, 4]
    first.sort(key=lambda step: (targets[step]['period'], targets[step]['source_id']))
    order = [1, *first, 5, 6, 7, 8, 9, 10]  # F2: ascending period, steps 2-4 among themselves; 7 and 9 repeat a publish
    return {'d': d, 'targets': targets, 'skipped_steps': skipped, 'order': order,
            'expected_lines': 2 * len([s for s in order if s not in REPEATS]) + len([s for s in order if s in REPEATS])}


def describe_manifest(manifest) -> dict:
    return {'gate': manifest.gate, 'schema_version': manifest.schema_version, 'row_count': manifest.row_count,
            'quarter_mode': manifest.quarter_mode, 'base_generation_id': manifest.base_generation_id,
            **{name: getattr(manifest, name) for name in
               ('added', 'updated', 'withdrawn', 'unresolved_absence', 'provenance_refreshed')}}


def describe_quarter(result, objects, store) -> dict:
    """One PublicationResult, with its gate and change counts. Called after the timed region; never reads rows."""
    record = result.to_mapping()
    try:
        if result.outcome == 'awaiting_approval' and result.generation_id:
            candidate = Candidate.from_mapping(store.get('Candidate', result.generation_id).to_mapping()['value'])
            record['manifest'] = describe_manifest(candidate.manifest)
        elif result.outcome in ('published', 'unchanged'):
            capture = capture_quarter(result.quarter, objects, EtlState(store))
            if capture is not None:
                record['manifest'] = describe_manifest(checked_manifest(capture, objects))
    except Exception as error:
        record['manifest_error'] = f'{type(error).__name__}: {error}'
    return record


def transform_call(step, target, objects, store, settings, results: Path) -> str:
    chosen = target['chosen']
    context = new_context(settings, 'transform')
    reused = store.get('Processing', processing_key(
        target['source_id'], chosen['raw_sha256'], context.parser_version, context.schema_version)) is not None
    record = {'step': step, 'source_id': target['source_id'], 'kind': target['kind'], 'period': target['period'],
              'call': 'transform', 'workset_ref': chosen['workset_ref'], 'processing_existed_before': reused,
              'run_id': context.run_id}
    started = time.monotonic()
    try:
        result = run_transform(chosen['workset_ref'], context, settings, objects, store)
    except Exception as error:
        traceback.print_exc()
        append(results, {**record, 'wall_seconds': round(time.monotonic() - started, 3), 'outcome': 'error',
                         'error': f'{type(error).__name__}: {error}'})
        raise
    wall = time.monotonic() - started
    append(results, {**record, 'wall_seconds': round(wall, 3), 'outcome': result.outcome,
                     'transformed': result.transformed, 'unchanged': result.unchanged, 'failed': result.failed,
                     'quarantined': result.quarantined, 'gaps': [gap.to_mapping() for gap in result.gaps],
                     'transformed_workset_ref': result.transformed_workset_ref})
    if result.outcome not in ('success', 'unchanged'):
        raise Anomaly(f'step {step} transform ended {result.outcome}')
    return result.transformed_workset_ref


def publish_call(step, target, transformed_ref, objects, store, settings, results: Path) -> None:
    context = new_context(settings, 'publish')
    record = {'step': step, 'source_id': target['source_id'], 'kind': target['kind'], 'period': target['period'],
              'call': 'publish', 'input_ref': transformed_ref, 'run_id': context.run_id}
    started = time.monotonic()
    try:
        result = run_publish(transformed_ref, context, settings, objects, store)
    except Exception as error:
        traceback.print_exc()
        append(results, {**record, 'wall_seconds': round(time.monotonic() - started, 3), 'outcome': 'error',
                         'error': f'{type(error).__name__}: {error}', 'details': getattr(error, 'details', None)})
        raise
    wall = time.monotonic() - started
    quarters = [describe_quarter(quarter, objects, store) for quarter in result.quarters]
    append(results, {**record, 'wall_seconds': round(wall, 3), 'outcome': result.outcome, 'published': result.published,
                     'unchanged': result.unchanged, 'quarantined': result.quarantined,
                     'awaiting_approval': result.awaiting_approval, 'failed': result.failed,
                     'quarters': quarters, 'gaps': [gap.to_mapping() for gap in result.gaps]})
    if result.quarantined or any(quarter.outcome == 'quarantined' for quarter in result.quarters):
        raise Anomaly(f'step {step} publish quarantined a source')


def convergence(store, objects, settings, steps: dict[int, dict]) -> list[dict]:
    """Every registered member of each stepped source, evaluated under the config's versions."""
    inventory, _ = WorkflowMembers(store, objects).inventory()
    by_source = defaultdict(list)
    for member in inventory:
        by_source[member['source']['source_id']].append(member)
    rows, seen = [], {}
    for step, target in sorted(steps.items()):
        if target['source_id'] in seen:
            continue
        seen[target['source_id']] = step
        members = by_source.get(target['source_id'], [])
        if not members:
            rows.append({'step': step, 'source_id': target['source_id'], 'period': target['period'], 'member_id': None,
                         'complete': False, 'gaps': ['no_registered_member'], 'obligations': 0})
        for member in members:
            found = evaluate_member(member, settings.etl.parser_version, settings.etl.schema_version, store, objects)
            rows.append({'step': step, 'source_id': target['source_id'], 'period': target['period'],
                         'member_id': member['member_id'], 'complete': found.complete,
                         'gaps': sorted({gap.code for gap in found.gaps}), 'obligations': len(found.obligations)})
    return rows


# ---------------------------------------------------------------------------------------------------- engine terms

# The last result of each production call, for the read_etl_result terms. transform_call and publish_call look
# run_transform and run_publish up as module globals, so `keep_results` wraps those names and leaves both functions
# unchanged. The wrapper adds one call and one dict store inside the production call's timed region.
KEPT = {}


def keep_results() -> None:
    global run_transform, run_publish

    def keep(name, function):
        def wrapper(*args, **kwargs):
            result = function(*args, **kwargs)
            KEPT[name] = result
            return result
        return wrapper
    run_transform, run_publish = keep('transform', run_transform), keep('publish', run_publish)


def evaluation(found) -> dict:
    return {'complete': found.complete, 'gaps': sorted({gap.code for gap in found.gaps}),
            'obligations': len(found.obligations)}


class Member:
    """One step's member and its fresh workflow context; writes one result line per engine term."""

    def __init__(self, step, target, settings, store, objects, results: Path):
        self.step, self.target, self.store, self.objects, self.results = step, target, store, objects, results
        self.value = target['member']['value']
        self.context = new_context(settings, 'backfill')  # a fresh pinned workflow context for this member
        self.base = {'step': step, 'source_id': target['source_id'], 'kind': target['kind'], 'period': target['period'],
                     'call': 'engine', 'member_id': self.value['member_id'], 'workflow_run_id': self.context.run_id}
        self.anomalies = []

    def term(self, phase: str, term: str, function, *, occurrence: int = 1, describe=None, **fields):
        """Time `function()` alone with time.perf_counter(); the line is written after the timed region."""
        record = {**self.base, 'phase': phase, 'term': term, 'occurrence': occurrence, **fields}
        started = time.perf_counter()
        try:
            value = function()
        except Exception as error:
            wall = time.perf_counter() - started
            traceback.print_exc()
            append(self.results, {**record, 'wall_seconds': round(wall, 6), 'outcome': 'error',
                                  'error': f'{type(error).__name__}: {error}', 'loadavg': list(os.getloadavg())})
            raise
        wall = time.perf_counter() - started
        append(self.results, {**record, 'wall_seconds': round(wall, 6), 'outcome': 'ok',
                              'loadavg': list(os.getloadavg()), **(describe(value) if describe else {})})
        return value

    def not_run(self, phase: str, term: str, reason: str, *, occurrence: int = 1) -> None:
        append(self.results, {**self.base, 'phase': phase, 'term': term, 'occurrence': occurrence, 'wall_seconds': 0.0,
                              'outcome': 'not_run', 'reason': reason, 'loadavg': list(os.getloadavg())})

    def flag(self, message: str) -> dict:
        self.anomalies.append(f'step {self.step} member {self.value["member_id"]}: {message}')
        return {'anomaly': message}

    def before_transform(self) -> None:
        """The run loop's sibling check, then process_member's read, replay check and initial completion check.

        `sibling_completion` gets the run loop's arguments for the first job of its source: the previous result is
        another source's (`previous=None` gives the same refusal), and `completed_sources` is empty, because it is
        frozen at selection and no member of a target source is complete there (the untouched convergence of
        `--validate-only` shows it). So it returns at its first check, as in the run.
        """
        value, context, store, objects = self.value, self.context, self.store, self.objects

        def sibling(processed):
            if processed is not None:
                return {'returned': 'processed', **self.flag('sibling_completion completed the member before dispatch')}
            return {'returned': 'none'}
        self.term('before_transform', 'sibling_completion',
                  lambda: runner.sibling_completion(value, None, frozenset(), context, store, objects),
                  describe=sibling, previous='another source', completed_sources=[])
        self.term('before_transform', 'read_member', lambda: read_member(value, store, objects))

        def replayed(found):
            return {'returned': 'none'} if found is None else {'returned': 'receipt', **self.flag('replay found a receipt')}
        self.term('before_transform', 'WorkflowMembers.replay',
                  lambda: WorkflowMembers(store, objects).replay(value, context), describe=replayed)

        def initial(found):
            fields = evaluation(found)
            blocking = sorted({gap.code for gap in found.gaps if not gap.retryable})
            if blocking and not found.obligations:
                fields.update(self.flag(f'non-retryable gaps {blocking} would stop the member before dispatch'))
            elif found.obligations:
                fields.update(self.flag(f'{len(found.obligations)} repair obligations would dispatch repair publishes'))
            return fields
        self.term('before_transform', 'evaluate_member',
                  lambda: evaluate_member(value, context.parser_version, context.schema_version, store, objects),
                  describe=initial)

    def collect_body(self) -> None:
        """collection.py:192-200: a bound member verifies its pinned raw snapshot and recovers its staged receipts.

        An unbound member's collect would fetch or reuse, which cannot run offline: it verifies the step's chosen
        snapshot instead, and the line says `unbound: true`.
        """
        store, objects, chosen = self.store, self.objects, self.target['chosen']['raw_sha256']
        workset = decode_source_workset(objects.read(self.value['member_ref']))
        source = workset.members[0]
        if len(workset.members) != 1 or source.to_mapping() != self.value['source']:
            raise Anomaly(f'step {self.step}: member workset is not the singleton of its source')
        state = AcquisitionState(store)

        def body():
            pinned = state.binding(workset.workset_id, source.source_id)
            if pinned is None:
                accepted = collection._verify_snapshot(state.snapshot(source.source_id, chosen), source, objects)
                return {'unbound': True, 'snapshot_sha256': accepted.sha256, 'bytes': accepted.byte_count,
                        'staged_receipts': 0, 'recovered_receipts': 0}
            accepted = collection._verify_snapshot(state.snapshot(source.source_id, pinned.snapshot_sha256), source, objects)
            staged = state.staged_receipt(workset.workset_id, source.source_id)
            recovered = 0
            if staged is not None:
                for entry in staged['receipts']:
                    if entry['receipt']['sha256'] == accepted.sha256:
                        collection._recover_saved_receipt(workset, source, entry, state, objects)
                        recovered += 1
            return {'unbound': False, 'snapshot_sha256': accepted.sha256, 'bytes': accepted.byte_count,
                    'staged_receipts': 0 if staged is None else len(staged['receipts']), 'recovered_receipts': recovered}

        self.term('collect', 'collect_body', body,
                  describe=lambda found: {**found, 'pin_is_chosen': found['snapshot_sha256'] == chosen})

    def after_publish(self, transform_result, publish_result) -> None:
        """process_member's final completion check and evidence check, then registry.record's read and evidence check.

        Each evidence check reads the transform and publish results (`read_etl_result`) and, for a complete member,
        validates its capture. The results are stored first, outside the timed region, at the path the child writes.
        """
        value, context, store, objects = self.value, self.context, self.store, self.objects
        refs = {}
        for name, result in (('transform', transform_result), ('publish', publish_result)):
            refs[name] = result_path(result.context)
            objects.put_once(refs[name], canonical_json(result.to_mapping()))
        outcome = publish_result.outcome  # the member's outcome is its publish child's (processing.py)

        def final(found):
            fields = evaluation(found)
            if outcome in COMPLETE and not found.complete:
                fields.update(self.flag(f'publish ended {outcome} but the member is not complete: {fields["gaps"]}'))
            return fields
        found = self.term('after_publish', 'evaluate_member',
                          lambda: evaluate_member(value, context.parser_version, context.schema_version, store, objects),
                          occurrence=2, describe=final, member_outcome=outcome)
        capture = found.capture if outcome in COMPLETE and found.complete else None
        for occurrence in (1, 2):
            if occurrence == 2:
                self.term('after_publish', 'read_member', lambda: read_member(value, store, objects), occurrence=2)
            for name, result in (('transform', transform_result), ('publish', publish_result)):
                def read(found, result=result, name=name):
                    fields = {'result_outcome': found.outcome}
                    if canonical_json(found.to_mapping()) == canonical_json(result.to_mapping()):
                        return fields
                    return {**fields, **self.flag(f'{name} result reads back differently')}
                self.term('after_publish', 'read_etl_result', lambda ref=refs[name]: read_etl_result(ref, objects),
                          occurrence=occurrence, describe=read, command=name, result_ref=refs[name])
            if capture is not None:
                self.term('after_publish', 'validate_capture', lambda: validate_capture(capture, objects),
                          occurrence=occurrence)
            else:
                self.not_run('after_publish', 'validate_capture', f'member outcome {outcome} with complete '
                             f'{found.complete}: the evidence has no completion capture', occurrence=occurrence)


def time_step(step, target, objects, store, settings, results: Path) -> tuple[str, list[str]]:
    """One step that is not a repeat, in dispatch order: member work, collect body, production calls, member work."""
    member = Member(step, target, settings, store, objects, results)
    member.before_transform()
    member.collect_body()
    transformed = transform_call(step, target, objects, store, settings, results)
    transform_result = KEPT.pop('transform')
    publish_call(step, target, transformed, objects, store, settings, results)
    member.after_publish(transform_result, KEPT.pop('publish'))
    return transformed, member.anomalies


def chosen_members(found: dict) -> dict:
    return {str(step): {key: target['member'][key] for key in
                        ('member_id', 'unbound', 'pinned_sha256', 'pin_is_chosen', 'origin_release', 'registered',
                         'refused_lower')} | {'period': target['period'], 'chosen_raw_sha256': target['chosen']['raw_sha256']}
            for step, target in sorted(found['targets'].items())}


def summarize(results: Path) -> dict:
    """Each step's in-process sums from the result lines. The three child starts are in starts.json."""
    walls = defaultdict(lambda: {'transform_s': 0.0, 'publish_s': 0.0, 'engine_s': 0.0, 'engine_lines': 0})
    for line in results.read_text().splitlines():
        record = json.loads(line)
        entry = walls[record['step']]
        if record['call'] == 'engine':
            entry['engine_s'] += record['wall_seconds']
            entry['engine_lines'] += 1
        else:
            entry[record['call'] + '_s'] += record['wall_seconds']
    return {str(step): {**entry, 'in_process_s': round(entry['transform_s'] + entry['publish_s'] + entry['engine_s'], 6),
                        'engine_s': round(entry['engine_s'], 6)} for step, entry in sorted(walls.items())}


def command_walls(args) -> int:
    root = refuse_forbidden(args.root, '<root>')
    config = refuse_forbidden(args.config, '<config>')
    results = refuse_forbidden(args.results, '<results.jsonl>')
    convergence_path = refuse_forbidden(args.convergence, '<convergence.json>')
    sidecar = refuse_forbidden(results.with_name(SIDECAR), SIDECAR)
    if not args.validate_only:
        refuse_existing(results, sidecar, convergence_path)
    settings = load_config(config)
    if Path(settings.storage.root) != root:
        raise ValueError('config storage.root differs from <root>')
    refuse_forbidden(settings.logging.root, 'config logging.root')
    if args.branch:
        # The shadow venv is not a release: a check, not evidence. The config's release is still verified (read-only)
        # and retained, because the production calls validate their producer manifest in the store.
        verified, release = preflight(Path(settings.runtime.release_manifest)), 'branch'
    else:
        verified = preflight_current(Path(settings.runtime.release_manifest))
        release = verified.release_id
    objects, store = open_stores(root)
    try:
        retain_manifest(objects, verified.manifest)
        try:
            found = plan(root, objects, store)
        except Anomaly as error:
            print('ANOMALY before any production call: ' + str(error), file=sys.stderr)
            return EXIT_STOP
        steps = {step: found['targets'][step] for step in found['order'] if step in found['targets']}
        if args.validate_only:
            print(json.dumps({'plan': found, 'release': release, 'members': chosen_members(found),
                              'convergence_untouched': convergence(store, objects, settings, steps)},
                             indent=1, sort_keys=True, default=str))
            return EXIT_OK
        members = len([step for step in found['order'] if step not in REPEATS])
        write_new(sidecar, {**found, 'run': {
            'format': TARGETS_FORMAT, 'release': release, 'interpreter': interpreter(), 'root': str(root),
            'config': str(config), 'config_sha256': file_digest(config), 'started_at': utc_now(),
            'loadavg_start': list(os.getloadavg()), 'engine_terms_per_member': ENGINE_TERMS_PER_MEMBER,
            'expected_engine_lines': ENGINE_TERMS_PER_MEMBER * members,
            'expected_result_lines': found['expected_lines'] + ENGINE_TERMS_PER_MEMBER * members}})
        keep_results()
        transformed, anomalies = {}, []
        for step in found['order']:
            if step in REPEATS:
                publish_call(step, found['targets'][REPEATS[step]], transformed[REPEATS[step]], objects, store, settings, results)
                KEPT.pop('publish', None)
                continue
            transformed[step], flagged = time_step(step, found['targets'][step], objects, store, settings, results)
            anomalies.extend(flagged)
        write_new(convergence_path, convergence(store, objects, settings, steps))
        print(json.dumps({'release': release, 'walls_in_process': summarize(results), 'anomalies': anomalies,
                          'loadavg_end': list(os.getloadavg())}, indent=1, sort_keys=True))
        if anomalies:
            print('ANOMALY during the timed run: ' + '; '.join(anomalies), file=sys.stderr)
            return EXIT_STOP
        return EXIT_OK
    finally:
        store.close()


# --------------------------------------------------------------------------------------------------------- origins

def target_sources(objects, store) -> tuple[dict, dict[int, tuple[str, str, str]]]:
    """D and every target source, by step, as `plan` picks them (steps 7 and 9 repeat a publish)."""
    d = pick_d(objects, EtlState(store))
    targets = dict(FIXED)
    if d['source_id'] in {FIXED[4][2], FIXED[8][2]}:
        raise Anomaly('D is the source of step 4 or 8, so a step would repeat: ' + d['source_id'])
    if d['source_id'] != FIXED[2][2]:
        targets[3] = ('daily', d['period'], d['source_id'])
    return d, dict(sorted(targets.items()))


def object_inventory(root: Path) -> tuple[int, int]:
    count = size = 0
    for directory, _, files in os.walk(root / 'objects'):
        for name in files:
            count += 1
            size += (Path(directory) / name).lstat().st_size
    return count, size


def command_origins(args) -> int:
    root = refuse_forbidden(args.live_root, '<live-root>')
    out = refuse_forbidden(args.origins_json, '<origins.json>')
    refuse_existing(out)
    database = root / 'state.sqlite3'
    before = {'state_sha256': file_digest(database), 'objects': object_inventory(root)}
    objects, store = open_stores(root)
    try:
        d, steps = target_sources(objects, store)
        values = [row.to_mapping()['value'] for row in store.scan('WorkflowMember', {})]
        targets, releases = [], {}
        for step, (kind, period, source_id) in steps.items():
            mine = sorted((value for value in values if isinstance(value, dict) and isinstance(value.get('source'), dict)
                           and value['source'].get('source_id') == source_id), key=lambda value: value['member_id'])
            members = []
            for value in mine:
                entry = {'member_id': value['member_id'], 'parent_ref': value['parent_ref'], 'member_ref': value['member_ref']}
                try:
                    context = read_member(value, store, objects).context
                    entry['read_member'] = 'ok'
                except MEMBER_READ_ERRORS as error:
                    entry['read_member'] = f'{type(error).__name__}: {error}'
                    context = decode_source_workset(objects.read(value['member_ref'])).context
                origin = context.to_mapping()
                effective = json.loads(canonical_json(to_mapping_value(origin['effective_config'])))
                release = origin['runtime'].get('release_sha256')
                entry.update(release_id=release, runtime=origin['runtime'], command=origin['command'],
                             config_sha256=origin['config_sha256'],
                             effective_config_sha256=sha256(canonical_json(to_mapping_value(effective))))
                members.append(entry)
                kept = releases.setdefault(release, {'members': 0, 'sources': [], 'effective_config_sha256s': [],
                                                     'from_member_id': value['member_id'], 'effective_config': effective})
                kept['members'] += 1
                kept['sources'] = sorted({*kept['sources'], source_id})
                kept['effective_config_sha256s'] = sorted({*kept['effective_config_sha256s'], entry['effective_config_sha256']})
            lowest = next((entry['member_id'] for entry in members if entry['read_member'] == 'ok'), None)
            for entry in members:
                entry['lowest'] = entry['member_id'] == lowest
            targets.append({'step': step, 'kind': kind, 'period': period, 'source_id': source_id,
                            'registered': len(members), 'lowest_member_id': lowest, 'members': members,
                            'origin_releases': sorted({entry['release_id'] for entry in members}, key=str)})
    finally:
        store.close()
    after = {'state_sha256': file_digest(database), 'objects': object_inventory(root)}
    for release, kept in releases.items():
        kept['effective_config_sha256'] = sha256(canonical_json(to_mapping_value(kept['effective_config'])))
        kept['in_f8'] = isinstance(release, str) and release[:8] in F8_RELEASES
        kept['release_dir_exists'] = isinstance(release, str) and (PROJECT_ROOT / 'releases' / ('sha256=' + release)).is_dir()
    stops = []
    outside = sorted(str(release) for release, kept in releases.items() if not kept['in_f8'] or not kept['release_dir_exists'])
    if outside:
        stops.append(f'origin releases outside F8: {outside}')
    if before != after:
        stops.append(f'the live clone changed while it was read: {before} then {after}')
    for target in targets:
        if target['lowest_member_id'] is None:
            stops.append(f'step {target["step"]}: no registered member passes read_member')
    result = {'format': ORIGINS_FORMAT, 'created_at': utc_now(), 'live_root': str(root), 'interpreter': interpreter(),
              'clone_before': before, 'clone_after': after, 'd': d, 'f8_release_prefixes': list(F8_RELEASES),
              'targets': targets,
              'origin_releases': {str(release): kept for release, kept in sorted(releases.items(), key=lambda item: str(item[0]))},
              'outside_f8': outside, 'stops': stops, 'exit': EXIT_STOP if stops else EXIT_OK}
    write_new(out, result)
    print(json.dumps({'d': d['source_id'], 'targets': [{key: target[key] for key in
                      ('step', 'period', 'registered', 'lowest_member_id', 'origin_releases')} for target in targets],
                      'origin_releases': {str(release): {'members': kept['members'], 'sources': len(kept['sources']),
                                                         'distinct_effective_configs': len(kept['effective_config_sha256s'])}
                                          for release, kept in releases.items()}, 'stops': stops},
                     indent=1, sort_keys=True))
    if stops:
        print('STOP: ' + '; '.join(stops), file=sys.stderr)
    return result['exit']


# ---------------------------------------------------------------------------------------------------------- starts

def probe(python: Path, config: Path, cwd: Path, release_id: str) -> dict:
    """One child start: a child process that imports the CLI, loads the config and runs preflight_current."""
    argv = [*native_python_argv(python), '-c', PROBE, str(config)]
    loadavg = list(os.getloadavg())
    started = time.perf_counter()
    finished = subprocess.run(argv, env=isolated_environment(), stdin=subprocess.DEVNULL, capture_output=True,
                              cwd=cwd, timeout=PROBE_TIMEOUT_S)
    wall = time.perf_counter() - started
    record = {'wall_s': round(wall, 6), 'returncode': finished.returncode, 'loadavg': loadavg}
    try:
        record['child'] = json.loads(finished.stdout)
    except ValueError:
        record['child'] = None
    if finished.returncode != 0 or not record['child'] or record['child'].get('release_id') != release_id:
        record['stdout'] = finished.stdout.decode('utf-8', 'replace')[-4000:]
        record['stderr'] = finished.stderr.decode('utf-8', 'replace')[-4000:]
    return record


def time_release(role: str, settings: Settings, config: Path, cwd: Path) -> dict:
    """PROBE_RUNS probes on the release that `resolve_child` picks for `settings`, as the dispatcher picks a child's.

    `resolve_child` itself runs in the parent before each child (checked.py, Dispatcher.execute); its time is kept
    apart, because P5's start is the child process alone.
    """
    entry = {'role': role, 'config': str(config), 'config_sha256': file_digest(config),
             'storage_root': settings.storage.root, 'logging_root': settings.logging.root,
             'parser_version': settings.etl.parser_version, 'schema_version': settings.etl.schema_version,
             'resolve_child_s': [], 'runs': []}
    for _ in range(PROBE_RUNS):
        started = time.perf_counter()
        python, descriptor = resolve_child(settings)
        entry['resolve_child_s'].append(round(time.perf_counter() - started, 6))
        entry.update(release_id=descriptor['release_sha256'], python=str(python))
        entry['runs'].append(probe(python, config, cwd, descriptor['release_sha256']))
    failed = [run for run in entry['runs'] if 'stderr' in run]
    entry['median_s'] = round(statistics.median(run['wall_s'] for run in entry['runs']), 6)
    entry['resolve_child_median_s'] = round(statistics.median(entry['resolve_child_s']), 6)
    entry['refused'] = len(failed)
    return entry


def command_starts(args) -> int:
    config = refuse_forbidden(args.scratch_config, '<scratch-config>')
    origins_path = refuse_forbidden(args.origins_json, '<origins.json>')
    scratch = refuse_forbidden(args.scratch_root, '<scratch-root>')
    out = refuse_forbidden(args.starts_json, '<starts.json>')
    refuse_existing(out)
    if not scratch.is_dir():
        raise FileNotFoundError(f'<scratch-root> {scratch} is not a directory')
    origins_body = origins_path.read_bytes()
    origins = json.loads(origins_body)
    if origins.get('format') != ORIGINS_FORMAT or origins.get('exit') != EXIT_OK:
        raise Anomaly(f'{origins_path} is not a clean {ORIGINS_FORMAT}')
    settings = load_config(config)
    for label, value in (('<scratch-config> storage.root', settings.storage.root),
                         ('<scratch-config> logging.root', settings.logging.root)):
        under(value, scratch, label)
    configs = scratch / 'starts-configs'
    configs.mkdir()
    releases = [time_release('new', settings, config, scratch)]
    for release_id, kept in origins['origin_releases'].items():
        # As the dispatcher freezes a collect child's config (process_member, Dispatcher.execute): the origin settings
        # decoded with Settings.from_mapping, here with scratch roots. load_config would admit them as new work.
        origin = Settings.from_mapping(kept['effective_config'])
        made = replace(origin, storage=replace(origin.storage, root=str(scratch / 'data')),
                       logging=replace(origin.logging, root=str(scratch / 'logs')))
        path = under(configs / f'origin-{release_id}.json', scratch, 'origin config')
        with path.open('xb') as stream:
            stream.write(canonical_json(to_mapping_value(made.to_mapping())))
        entry = time_release('origin', made, path, scratch)
        if entry['release_id'] != release_id:
            raise Anomaly(f'origin config of {release_id} resolves to {entry["release_id"]}')
        entry['effective_config_sha256'] = kept['effective_config_sha256']
        releases.append(entry)
    new = releases[0]
    medians = {entry['release_id']: entry['median_s'] for entry in releases[1:]}
    targets = []
    for target in origins['targets']:
        candidates = sorted(((medians[release], release) for release in target['origin_releases']), reverse=True)
        targets.append({'step': target['step'], 'kind': target['kind'], 'period': target['period'],
                        'source_id': target['source_id'], 'origin_releases': target['origin_releases'],
                        'collect_medians_s': {release: median for median, release in candidates},
                        'collect': {'release_id': candidates[0][1], 'median_s': candidates[0][0]}})
    refused = [f'{entry["role"]} {entry["release_id"]}: {entry["refused"]} of {PROBE_RUNS}' for entry in releases if entry['refused']]
    result = {'format': STARTS_FORMAT, 'created_at': utc_now(), 'interpreter': interpreter(),
              'scratch_config': {'path': str(config), 'sha256': file_digest(config)},
              'origins': {'path': str(origins_path), 'sha256': sha256(origins_body)}, 'scratch_root': str(scratch),
              'probe': {'code': PROBE, 'code_sha256': sha256(PROBE.encode()), 'runs': PROBE_RUNS,
                        'argv': 'native_python_argv(<release python>) -c <code> <config>',
                        'environment': 'runtime.isolated_environment()'},
              'releases': releases,
              'commands': {'transform': {'release_id': new['release_id'], 'median_s': new['median_s']},
                           'publish': {'release_id': new['release_id'], 'median_s': new['median_s']}},
              'targets': targets, 'refused': refused, 'exit': EXIT_STOP if refused else EXIT_OK}
    write_new(out, result)
    print(json.dumps({'releases': [{key: entry[key] for key in ('role', 'release_id', 'median_s', 'resolve_child_median_s',
                                                                 'refused')} for entry in releases],
                      'targets': [{'step': t['step'], 'collect': t['collect']} for t in targets], 'refused': refused},
                     indent=1, sort_keys=True))
    if refused:
        print('STOP: a release refused its config: ' + '; '.join(refused), file=sys.stderr)
    return result['exit']


# ------------------------------------------------------------------------------------------------------------ main

def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(
        description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='exit codes: 0 done; 1 failed (or an output exists); 2 anomaly (stop and ask); '
               '5 a path is under data/ or backups/')
    commands = top.add_subparsers(dest='command', required=True)
    walls = commands.add_parser('walls', help='time each step\'s production calls and its member\'s engine work')
    walls.add_argument('root', type=Path)
    walls.add_argument('config', type=Path)
    walls.add_argument('results', type=Path)
    walls.add_argument('convergence', type=Path)
    walls.add_argument('--validate-only', action='store_true')
    walls.add_argument('--branch', action='store_true', help='skip preflight_current: the interpreter is not a release')
    origins = commands.add_parser('origins', help='record the origin release of every member of each target source')
    origins.add_argument('live_root', type=Path)
    origins.add_argument('origins_json', type=Path)
    starts = commands.add_parser('starts', help='time the child-start probe on the new release and each origin release')
    starts.add_argument('scratch_config', type=Path)
    starts.add_argument('origins_json', type=Path)
    starts.add_argument('scratch_root', type=Path)
    starts.add_argument('starts_json', type=Path)
    return top


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    guard_store_roots()
    command = {'walls': command_walls, 'origins': command_origins, 'starts': command_starts}[args.command]
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
