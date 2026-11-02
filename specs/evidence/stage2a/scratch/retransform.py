"""Stage 2a scratch re-transform (plan 7, Task 10).

On a scratch copy of the store, re-transform the 35 sources that the 1c code quarantined (F9), then time the
first v2 publish of 2023Q1 and a v2 candidate for 2026Q3. Run it on the 2a interpreter:

    releases/sha256=<2A>/venv/bin/python -I -B -X pycache_prefix=/dev/null retransform.py \
        <root> <config> <sources.json> <results.json> {locate,transform,publish-2023Q1,candidate-2026Q3} [--only ID]

It opens <root> with its stored binding (the diag2.py method), creates no network client and never approves.
Every command appends one JSON line per step to <results.json>.
"""
import argparse
import json
import sys
import tempfile
import time
import traceback
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

from sec_edgar_ingest.config import load_config, pin_context
from sec_edgar_ingest.etl.commands import run_publish, run_transform
from sec_edgar_ingest.etl.contracts import Candidate, decode_transformed, processing_key
from sec_edgar_ingest.etl.manifest import validate_candidate_content
from sec_edgar_ingest.etl.reader import capture_quarter, checked_manifest, read_quarter
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.models import RunContext
from sec_edgar_ingest.runtime import configured_descriptor, preflight_current, retain_manifest
from sec_edgar_ingest.storage.contracts import REGISTRY_PATH
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.worksets import decode_snapshot_workset

CAMPAIGN = Path(__file__).resolve().parents[2] / 'baseline-campaign'
F9_DAILY_PERIODS = ('2026-07-08', '2026-07-13', '2026-07-22', '2026-07-27', '2026-09-17', '2026-09-24', '2026-10-21')
REBUILD_QUARTERS = {'publish-2023Q1': '2023Q1', 'candidate-2026Q3': '2026Q3'}
SNAPSHOT_DIR = 'worksets/sec/snapshot'


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append(results: Path, record: dict) -> None:
    line = json.dumps({'at': now(), **record}, sort_keys=True, default=str)
    with results.open('a') as stream:
        stream.write(line + '\n')
    print(line)


def new_context(settings, command: str) -> RunContext:
    """A fresh pinned context for one production call: the tests/support.py fields, a real UTC start and deadline."""
    started = datetime.now(timezone.utc)
    run_id = 'stage2a-scratch-' + uuid.uuid4().hex
    context = RunContext(run_id=run_id, execution_id=run_id, command=command, attempt_id=uuid.uuid4().hex,
                         runtime=configured_descriptor(settings), format_version='sec-local-run-context-v1',
                         parser_version=settings.etl.parser_version, schema_version=settings.etl.schema_version,
                         config_sha256=settings.config_sha256, started_at=started,
                         deadline=started + timedelta(seconds=settings.execution.max_run_seconds), priority='backfill')
    return pin_context(settings, context, started.date())[0]


def f9_sources() -> tuple[dict[str, str], dict[str, str]]:
    """F9: quarterly raw SHA-256 -> quarter (quarantine first lines), daily source_id -> date (coverage.json)."""
    quarterly = {}
    for path in sorted((CAMPAIGN / 'quarantine').glob('20[0-9][0-9]Q[1-4].txt')):
        quarterly[path.read_text().splitlines()[0].split()[-1]] = path.stem
    coverage = json.loads((CAMPAIGN / 'final/coverage.json').read_text())
    daily = {item['source_id']: item['period'] for item in coverage['daily_sources'] if item['quarantined']}
    return quarterly, daily


def locate(root: Path, objects, sources_path: Path, results: Path) -> int:
    quarterly, daily = f9_sources()
    holders, undecodable = defaultdict(list), []
    for directory in sorted((root / 'objects' / SNAPSHOT_DIR).iterdir()):
        ref = f'{SNAPSHOT_DIR}/{directory.name}/workset.json'
        try:
            workset = decode_snapshot_workset(objects.read(ref))
        except Exception as error:
            undecodable.append({'ref': ref, 'error': f'{type(error).__name__}: {error}'})
            continue
        for snapshot in workset.snapshots:
            if snapshot.sha256 in quarterly or snapshot.source_id in daily:
                holders[(snapshot.source_id, snapshot.sha256)].append((len(workset.snapshots), ref, snapshot))
    entries = []
    for (source_id, sha256), found in holders.items():
        members, ref, snapshot = min(found, key=lambda item: item[:2])
        kind = 'quarterly' if snapshot.representation == 'zip' else 'daily'
        period = snapshot.raw_path.split('/period=')[1].split('/')[0]
        entries.append({'source_id': source_id, 'kind': kind, 'period': period, 'raw_sha256': sha256,
                        'workset_ref': ref, 'members': members, 'holding_worksets': len(found)})
    entries.sort(key=lambda entry: (entry['kind'] != 'quarterly', entry['period']))
    problems = []
    if sorted(e['period'] for e in entries if e['kind'] == 'quarterly') != sorted(quarterly.values()):
        problems.append('quarterly sources found differ from the 28 quarantine files')
    if sorted(e['period'] for e in entries if e['kind'] == 'daily') != sorted(F9_DAILY_PERIODS) or \
            sorted(daily.values()) != sorted(F9_DAILY_PERIODS):
        problems.append('daily sources found differ from the 7 F9 dates')
    for entry in entries:
        if entry['kind'] == 'quarterly' and entry['period'] in REBUILD_QUARTERS.values() and entry['members'] > 1:
            problems.append(f"{entry['period']} quarterly source workset has {entry['members']} members")
    counts = {kind: sum(e['kind'] == kind for e in entries) for kind in ('quarterly', 'daily')}
    append(results, {'step': 'locate', 'entries': len(entries), **counts, 'undecodable_worksets': undecodable,
                     'problems': problems})
    if problems:
        return 2
    sources_path.write_text(json.dumps({'sources': entries}, indent=1, sort_keys=True) + '\n')
    return 0


def merged_keys(objects, ref) -> dict[str, int]:
    """Repeated keys of one observation by class: what differs between its lines (spec section 1.1)."""
    with tempfile.TemporaryDirectory(prefix='s2a-rows-') as directory:
        path = Path(directory) / 'rows.parquet'
        objects.materialize(ref.rows_ref, path)
        table = pq.read_table(path, columns=['cik', 'archive_path', 'form_types', 'company_names'])
    for name in ('form_types', 'company_names'):
        if pc.min(pc.list_value_length(table[name])).as_py() != 1 or pc.max(pc.list_value_length(table[name])).as_py() != 1:
            raise ValueError(f'an observation row must hold exactly one {name} item')
    flat = table.select(['cik', 'archive_path']).append_column('form', pc.list_flatten(table['form_types'])) \
        .append_column('name', pc.list_flatten(table['company_names']))
    groups = flat.group_by(['cik', 'archive_path']).aggregate(
        [('form', 'count'), ('form', 'count_distinct'), ('name', 'count_distinct')]).to_pylist()
    classes = {'combined_filing': 0, 'rename': 0, 'both': 0, 'identical_repeat': 0}
    for group in groups:
        if group['form_count'] < 2:
            continue
        forms, names = group['form_count_distinct'] > 1, group['name_count_distinct'] > 1
        classes['both' if forms and names else 'combined_filing' if forms else 'rename' if names else 'identical_repeat'] += 1
    return {'keys_counted': len(groups), **classes}


def transform(objects, store, settings, sources: list[dict], only: str | None, results: Path) -> int:
    chosen = [s for s in sources if only is None or s['source_id'] == only]
    if not chosen:
        raise ValueError('no F9 source matches --only')
    by_workset = defaultdict(list)
    for source in chosen:
        by_workset[source['workset_ref']].append(source)
    failed = 0
    for workset_ref, members in by_workset.items():
        context = new_context(settings, 'transform')
        reused = {s['source_id']: store.get('Processing', processing_key(
            s['source_id'], s['raw_sha256'], context.parser_version, context.schema_version)) is not None for s in members}
        started = time.monotonic()
        result = run_transform(workset_ref, context, settings, objects, store)
        wall = time.monotonic() - started
        workset = decode_transformed(objects.read(result.transformed_workset_ref))
        observations = {ref.source.source_id: ref for ref in workset.observations}
        failures = {gap.source_id: gap for gap in workset.failures}
        for source in members:
            record = {'step': 'transform', **source, 'run_id': context.run_id, 'wall_seconds': round(wall, 3),
                      'workset_outcome': result.outcome, 'workset_transformed': result.transformed,
                      'workset_unchanged': result.unchanged, 'workset_failed': result.failed,
                      'transformed_workset_ref': result.transformed_workset_ref, 'workset_complete': workset.complete,
                      'reused_observation': reused[source['source_id']]}
            ref = observations.get(source['source_id'])
            if ref is not None:
                record.update(outcome='transformed', rows=ref.source_row_count, distinct_keys=ref.distinct_key_count,
                              quarter_counts=dict(ref.quarter_counts), merged=merged_keys(objects, ref))
            else:
                failed += 1
                gap = failures.get(source['source_id'])
                record.update(outcome='quarantined', reason=gap.to_mapping() if gap else 'source absent from workset')
            append(results, record)
    return 1 if failed else 0


def transformed_ref_for(results: Path, source_id: str) -> str:
    """The last complete v2 transformed workset that the transform step recorded for this source."""
    refs = [json.loads(line) for line in results.read_text().splitlines()]
    refs = [r['transformed_workset_ref'] for r in refs if r.get('step') == 'transform'
            and r['source_id'] == source_id and r['outcome'] == 'transformed' and r['workset_complete']]
    if not refs:
        raise ValueError('no complete transformed workset is recorded for ' + source_id)
    return refs[-1]


def changes(manifest) -> dict[str, int]:
    return {name: getattr(manifest, name) for name in
            ('added', 'updated', 'withdrawn', 'unresolved_absence', 'provenance_refreshed')}


def publish(command: str, objects, store, settings, sources: list[dict], results: Path) -> int:
    quarter = REBUILD_QUARTERS[command]
    source = next(s for s in sources if s['kind'] == 'quarterly' and s['period'] == quarter)
    state = EtlState(store)
    before = state.pointer(quarter)
    before_manifest = checked_manifest(capture_quarter(quarter, objects, state), objects) if before else None
    input_ref = transformed_ref_for(results, source['source_id'])
    context = new_context(settings, 'publish')
    record = {'step': command, 'quarter': quarter, 'source_id': source['source_id'], 'input_ref': input_ref,
              'run_id': context.run_id, 'pointer_before': before.to_mapping() if before else None,
              'base_schema_version': before_manifest.schema_version if before_manifest else None}
    started = time.monotonic()
    try:
        result = run_publish(input_ref, context, settings, objects, store)
    except Exception as error:
        # Keep the measured time of a failed publish; the traceback goes to stderr.
        traceback.print_exc()
        record.update(wall_seconds=round(time.monotonic() - started, 3), error=f'{type(error).__name__}: {error}',
                      details=getattr(error, 'details', None), expected=False)
        append(results, record)
        return 1
    record.update(wall_seconds=round(time.monotonic() - started, 3), outcome=result.outcome,
                  quarters=[q.to_mapping() for q in result.quarters], gaps=[g.to_mapping() for g in result.gaps])
    own = next((q for q in result.quarters if q.quarter == quarter), None)
    record['quarter_outcome'] = own.outcome if own else None
    if command == 'publish-2023Q1':
        ok = own is not None and own.outcome == 'published'
        if ok:
            capture = capture_quarter(quarter, objects, state)
            manifest = checked_manifest(capture, objects)
            read_started = time.monotonic()
            rows = sum(1 for _ in read_quarter(capture, objects))
            record.update(generation_id=manifest.generation_id, base_generation_id=manifest.base_generation_id,
                          schema_version=manifest.schema_version, gate=manifest.gate, changes=changes(manifest),
                          row_count=manifest.row_count, rows_read=rows,
                          read_wall_seconds=round(time.monotonic() - read_started, 3))
            ok = manifest.gate == 'clear' and rows > 0 and rows == manifest.row_count
    else:
        ok = own is not None and own.outcome == 'awaiting_approval'
        if ok:
            generation_id = own.candidate_ref.split('/sha256=')[1].split('/')[0]
            candidate = Candidate.from_mapping(store.get('Candidate', generation_id).to_mapping()['value'])
            validate_candidate_content(candidate, objects)
            after = state.pointer(quarter)
            pointed = checked_manifest(capture_quarter(quarter, objects, state), objects)
            unchanged = after is not None and after.to_mapping() == before.to_mapping()
            record.update(generation_id=generation_id, base_generation_id=candidate.manifest.base_generation_id,
                          schema_version=candidate.manifest.schema_version, gate=candidate.manifest.gate,
                          changes=changes(candidate.manifest), row_count=candidate.manifest.row_count,
                          candidate_valid=True, pointer_after=after.to_mapping(), pointer_unchanged=unchanged,
                          pointer_schema_version=pointed.schema_version)
            ok = unchanged and pointed.schema_version == 'sec-index-v1' and candidate.manifest.gate == 'awaiting_approval'
    record['expected'] = ok
    append(results, record)
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('root', type=Path)
    parser.add_argument('config', type=Path)
    parser.add_argument('sources', type=Path)
    parser.add_argument('results', type=Path)
    parser.add_argument('command', choices=('locate', 'transform', *REBUILD_QUARTERS))
    parser.add_argument('--only')
    args = parser.parse_args(argv)
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
        if args.command == 'locate':
            return locate(root, objects, args.sources, args.results)
        sources = json.loads(args.sources.read_text())['sources']
        if args.command == 'transform':
            return transform(objects, store, settings, sources, args.only, args.results)
        return publish(args.command, objects, store, settings, sources, args.results)
    except Exception as error:
        append(args.results, {'step': args.command, 'only': args.only, 'error': f'{type(error).__name__}: {error}'})
        raise
    finally:
        store.close()


if __name__ == '__main__':
    sys.exit(main())
