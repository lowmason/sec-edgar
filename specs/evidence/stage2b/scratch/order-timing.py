"""Plan 8, Task 2: time the largest members in true dispatch order, on a scratch copy of the store.

Run it on the 2a interpreter against a scratch copy, never the live root:

    releases/sha256=<2A>/venv/bin/python -I -B -X pycache_prefix=/dev/null order-timing.py \
        <root> <config> <results.jsonl> <convergence.json> [--validate-only]

It opens <root> with its stored binding (the retransform.py method), creates no network client and never
approves. Each production call is `run_transform` or `run_publish` on a snapshot or transformed workset, with
a fresh pinned context. Collect, child spawn and the completion check are not measured.

Before the first production call it checks every target (see `plan`) and exits 2 on any anomaly, so a bad
target costs a minute, not a run. `--validate-only` stops there, prints the plan and the convergence of the
untouched copy, and writes nothing.

<results.jsonl> gets exactly one line per production call. The targets, candidates and D go to a sidecar,
`order-timing-targets.json`, next to it. A re-run refuses to start when either file exists.
"""
import argparse
import json
import sys
import time
import traceback
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sec_edgar_ingest.config import load_config, pin_context
from sec_edgar_ingest.etl.commands import run_publish, run_transform
from sec_edgar_ingest.etl.contracts import Candidate, processing_key
from sec_edgar_ingest.etl.reader import capture_quarter, checked_manifest
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.models import RunContext
from sec_edgar_ingest.runtime import configured_descriptor, preflight_current, retain_manifest
from sec_edgar_ingest.storage.contracts import REGISTRY_PATH
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.worksets import decode_snapshot_workset
from sec_edgar_ingest.workflows.completion import evaluate_member
from sec_edgar_ingest.workflows.members import WorkflowMembers

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


class Anomaly(Exception):
    """A target or the store differs from the plan: nothing has been timed yet."""


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('root', type=Path)
    parser.add_argument('config', type=Path)
    parser.add_argument('results', type=Path)
    parser.add_argument('convergence', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args(argv)
    sidecar = args.results.with_name('order-timing-targets.json')
    if not args.validate_only and any(path.exists() for path in (args.results, sidecar, args.convergence)):
        print('refusing to start: an output file exists', file=sys.stderr)
        return 2
    root = args.root.resolve()
    settings = load_config(args.config)
    if Path(settings.storage.root) != root:
        raise ValueError('config storage.root differs from <root>')
    verified = preflight_current(Path(settings.runtime.release_manifest))
    binding = json.loads((root / 'objects' / REGISTRY_PATH).read_bytes())
    objects = LocalObjectStore(root, binding=binding, create=False)
    store = LocalStateStore(root, binding=binding, create=False)
    try:
        retain_manifest(objects, verified.manifest)
        try:
            found = plan(root, objects, store)
        except Anomaly as error:
            print('ANOMALY before any production call: ' + str(error), file=sys.stderr)
            return 2
        steps = {step: found['targets'][step] for step in found['order'] if step in found['targets']}
        if args.validate_only:
            print(json.dumps({'plan': found, 'convergence_untouched': convergence(store, objects, settings, steps)},
                             indent=1, sort_keys=True, default=str))
            return 0
        sidecar.write_text(json.dumps(found, indent=1, sort_keys=True, default=str) + '\n')
        transformed = {}
        for step in found['order']:
            if step in REPEATS:
                publish_call(step, found['targets'][REPEATS[step]], transformed[REPEATS[step]], objects, store, settings, args.results)
                continue
            target = found['targets'][step]
            transformed[step] = transform_call(step, target, objects, store, settings, args.results)
            publish_call(step, target, transformed[step], objects, store, settings, args.results)
        args.convergence.write_text(json.dumps(convergence(store, objects, settings, steps), indent=1, sort_keys=True) + '\n')
        return 0
    except Exception as error:
        print(f'FAILED: {type(error).__name__}: {error}', file=sys.stderr)
        return 1
    finally:
        store.close()


if __name__ == '__main__':
    sys.exit(main())
