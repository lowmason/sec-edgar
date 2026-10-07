"""Validate acquisition intent before constructing the explicitly selected backend."""
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

from . import __version__
from .collection import collect
from .config import Settings, load_config, pin_context
from .coordination import Clock, Coordinator
from .discovery import discover
from .etl.commands import (PublicationRepairPending, read_etl_result, run_transform, run_publish,
                           write_etl_result, validate_workset_ref)
from .etl.parser import supported_parser, SCHEMA_VERSION
from .etl.publication import repair_publication
from .etl.state import EtlState
from .download import BoundedSender, FixturePack, RequestClient
from .models import CommandResult, Error, RunContext, canonical_json, parse_json, quarter_for, safe_relative_path
from .results import exit_code, log_event, read_result, result_path, write_result
from .state import AcquisitionState, attempt_key
from .storage import open_stores
from .storage.contracts import CAS_ATTEMPTS, ClockUncertain, Conflict, OwnershipLost
from .worksets import decode_source_workset

SOURCE_REF = re.compile(r'worksets/sec/source/sha256=[0-9a-f]{64}/workset\.json\Z')


class _ExpiredAttempt(ValueError):
    pass


class _NoFaults:
    def hit(self, point: str) -> None:
        pass


class _CheckedSender:
    # RequestClient retains an unconfirmed transport; CLI must also retain an unexpected command error.
    def __init__(self, sender):
        self.sender, self.failure = sender, None

    def send(self, *args, **kwargs):
        try:
            return self.sender.send(*args, **kwargs)
        except (OwnershipLost, ClockUncertain):
            raise
        except Exception as error:
            self.failure = error
            raise

    def close(self):
        if hasattr(self.sender, 'close'):
            self.sender.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='sec-edgar-ingest')
    parser.add_argument('--version', action='version', version=__version__)
    commands = parser.add_subparsers(dest='command')
    for command in ('discover', 'collect', 'transform', 'publish'):
        sub = commands.add_parser(command)
        for name in ('config', 'run-id', 'execution-id', 'attempt-id', 'deadline'):
            sub.add_argument('--' + name, required=True)
        for name in ('state-dir', 'today'):
            sub.add_argument('--' + name)
        if command in ('discover', 'collect'):
            sub.add_argument('--fixture-pack')
        if command == 'discover':
            sub.add_argument('--mode', required=True, choices=('quarterly', 'daily'))
            sub.add_argument('--discovery-id', required=True)
            sub.add_argument('--refresh', action='store_true')
        else:
            sub.add_argument('--workset', required=True)
        if command == 'transform':
            sub.add_argument('--force', action='store_true')
    return parser


def _segment(value: str, name: str) -> None:
    if '/' in safe_relative_path(value, name):
        raise ValueError(name + ' must be a single path segment')


def _validate(args) -> tuple[Settings, date | None, datetime, FixturePack | None]:
    for name in ('run_id', 'execution_id', 'attempt_id'):
        _segment(getattr(args, name), name)
    if args.command == 'discover':
        _segment(args.discovery_id, 'discovery_id')
    elif args.command in ('transform', 'publish'):
        validate_workset_ref(args.workset, 'snapshot' if args.command == 'transform' else 'transformed')
    elif SOURCE_REF.fullmatch(args.workset) is None:
        raise ValueError('workset must name the exact immutable source-workset object path')
    settings = load_config(Path(args.config))
    etl = args.command in ('transform', 'publish')
    if etl:
        supported_parser(settings.etl.parser_version, fixture=settings.storage.backend == 'local-fixture')
        if settings.etl.schema_version != SCHEMA_VERSION:
            raise ValueError('unsupported ETL schema version')
    if not settings.coordination.lease_seconds.is_integer():
        raise ValueError('coordination requires whole finite lease seconds')
    deadline = datetime.fromisoformat(args.deadline.replace('Z', '+00:00'))
    if deadline.utcoffset() != timezone.utc.utcoffset(deadline):
        raise ValueError('deadline must be timezone-aware UTC')
    today = date.fromisoformat(args.today) if args.today else None
    if args.today and today.isoformat() != args.today:
        raise ValueError('today must be a canonical ISO date')
    if settings.storage.backend == 'azure':
        if getattr(args, 'fixture_pack', None) or args.state_dir or args.today:
            raise ValueError('fixture pack, state directory and date override are fixture-only')
        pack = None
    else:
        if not etl and not args.fixture_pack:
            raise ValueError('local-fixture commands require an explicit fixture pack')
        if not settings.fixture or (args.today and not settings.fixture.allow_clock_override):
            if args.today:
                raise ValueError('today requires the explicit fixture clock override marker')
        pack = None if etl else FixturePack.load(Path(args.fixture_pack))
    # A completed result may outlive its deadline; only its saved context can authorize replay.
    now = Clock().now()
    if deadline > now:
        checked = _new_context(args, settings, deadline, today, now)
        if args.command == 'discover' and args.mode == 'daily':
            _, end = pin_context(settings, checked, checked.pinned_on)
            if end != quarter_for(checked.pinned_on):
                raise ValueError('daily discovery endpoint must include the current quarter')
    return settings, today, deadline, pack


def _new_context(args, settings, deadline, today, started) -> RunContext:
    priority = 'daily' if args.command == 'discover' and args.mode == 'daily' else 'backfill'
    context = RunContext(args.run_id, args.execution_id, args.command, args.attempt_id,
                         settings.worker.image_digest, settings.etl.parser_version, settings.etl.schema_version,
                         settings.config_sha256, started, deadline, priority)
    return pin_context(settings, context, today or started.date())[0]


def _intent(args, pack) -> dict[str, object]:
    if args.command in ('transform', 'publish'):
        return {'command': args.command, 'today': args.today, 'workset': args.workset,
                'force': args.force if args.command == 'transform' else None}
    return {'command': args.command, 'today': args.today,
            'fixture_sha256': pack.manifest_sha256 if pack is not None else None,
            'mode': args.mode if args.command == 'discover' else None,
            'discovery_id': args.discovery_id if args.command == 'discover' else None,
            'refresh': args.refresh if args.command == 'discover' else None,
            'workset': args.workset if args.command == 'collect' else None}


def _matching_context(saved, current, *, explicit_today) -> RunContext:
    expected = current.to_mapping()
    actual = saved.to_mapping()
    expected['started_at'] = actual['started_at']
    if not explicit_today:
        expected['pinned_on'] = actual['pinned_on']
    if expected != actual:
        raise Conflict('attempt replay differs from its exact saved correlation/config/image/versions/deadline')
    # Validate the original start and pin date; never fabricate a fresh start for replay.
    pin_context(Settings.from_mapping(actual['effective_config']), saved, saved.pinned_on)
    return saved


def _existing_context(current, state, objects, intent, explicit_today):
    path = result_path(current)
    intent_path = path.rsplit('/', 1)[0] + '/command.json'
    try:
        saved = read_result(path, objects)
    except FileNotFoundError:
        saved = None
    if saved is not None:
        context = _matching_context(saved.context, current, explicit_today=explicit_today)
        if objects.read(intent_path) != canonical_json(intent):
            raise Conflict('completed attempt command inputs differ from the frozen invocation')
        state.begin_attempt(context)
        state.finish_attempt(saved)
        return context, saved
    row = state.store.get('Attempt', attempt_key(current))
    context = _matching_context(RunContext.from_mapping(row.to_mapping()['value']['context']), current,
                                explicit_today=explicit_today) if row is not None else current
    state.begin_attempt(context)
    objects.put_once(intent_path, canonical_json(intent))
    return context, None


def _existing_etl_context(current, state, objects, intent, explicit_today):
    path = result_path(current)
    intent_path = path.rsplit('/', 1)[0] + '/command.json'
    try:
        saved = read_etl_result(path, objects)
    except FileNotFoundError:
        saved = None
    try:
        frozen_body = objects.read(intent_path)
    except FileNotFoundError:
        frozen_body = None
    if frozen_body is not None:
        frozen = parse_json(frozen_body)
        if (not isinstance(frozen, dict) or set(frozen) != {'context', 'intent'}
                or canonical_json(frozen) != frozen_body or frozen['intent'] != intent):
            raise Conflict('ETL command differs from its frozen invocation')
        prior = RunContext.from_mapping(frozen['context'])
    else:
        if saved is not None:
            raise Conflict('completed ETL result has no command intent')
        # Attempt keys include image/execution, while immutable command paths do not.
        # Find an interrupted begin even if the caller now supplies a different key.
        matching = [RunContext.from_mapping(row.to_mapping()['value']['context'])
                    for row in state.store.scan('Attempt', {})
                    if all(row.value['context'][name] == getattr(current, name)
                           for name in ('run_id', 'command', 'attempt_id'))]
        if len(matching) > 1:
            raise Conflict('multiple attempts claim the same command path')
        prior = matching[0] if matching else current
    context = _matching_context(prior, current, explicit_today=explicit_today)
    if saved is not None and saved.context != context:
        raise Conflict('ETL result differs from its frozen command context')
    frozen = canonical_json({'context': context.to_mapping(), 'intent': intent})
    if frozen_body is not None and frozen != frozen_body:
        raise Conflict('ETL intent context differs from its exact canonical context')
    state.begin_attempt(context)
    objects.put_once(intent_path, frozen)
    if saved is not None:
        for quarter in saved.quarters:
            if quarter.outcome in ('published', 'unchanged'):
                repair_publication(quarter.quarter, objects, EtlState(state.store))
        state.finish_attempt(saved)
    return context, saved


def _discover_result(workset, context, clock):
    gaps = tuple(directory.error for directory in workset.directories if directory.error is not None)
    outcome = 'discovery_failed' if not workset.discovery_complete else ('success' if workset.members else 'no_new_sources')
    return CommandResult(context, outcome, f'worksets/sec/source/sha256={workset.workset_id}/workset.json',
                         None, len(workset.members), 0, 0, 0, len(gaps), 0, gaps,
                         context.started_at, max(context.started_at, clock.now()))


def _collection_outcome(result):
    if result.outcome != 'incomplete' or len({gap.source_id for gap in result.gaps if gap.source_id}) != 1 or result.discovered != 1:
        return result
    gap = next((gap for gap in result.gaps if gap.source_id), None)
    if gap is None:
        return result
    transport = gap.details.get('outcome')
    outcome = {'pending': 'pending', 'exhausted': 'retry_exhausted', 'deferred': 'deferred',
               'quarantined': 'quarantined'}.get(transport)
    return replace(result, outcome=outcome) if outcome else result


def _retain_error(state, context, outcome, error):
    for _ in range(CAS_ATTEMPTS):
        row = state.store.get('Attempt', attempt_key(context))
        if row is None:
            return
        value = row.to_mapping()['value']
        if value['context'] != context.to_mapping() or value['result'] is not None:
            return
        value.update(outcome=outcome, ended_at=Clock().now().isoformat(),
                     structured_errors=[error.to_mapping()])
        try:
            state.store.replace('Attempt', attempt_key(context), value, row.version)
            return
        except Conflict:
            continue
    raise Conflict('error retention exhausted conditional races')


def _stdout(result, reference):
    if result.context.command in ('transform', 'publish'):
        sys.stdout.write(canonical_json({'outcome': result.outcome, 'result_ref': reference,
            'input_ref': result.input_ref, 'transformed_workset_ref': result.transformed_workset_ref}).decode() + '\n')
        return exit_code(result.outcome)
    sys.stdout.write(canonical_json({'outcome': result.outcome, 'result_ref': reference,
        'source_workset_ref': result.source_workset_ref, 'snapshot_workset_ref': result.snapshot_workset_ref}).decode() + '\n')
    return exit_code(result.outcome)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        settings, today, deadline, pack = _validate(args)
    except (ValueError, OSError, TypeError) as error:
        sys.stderr.write(canonical_json({'outcome': 'configuration', 'error': str(error)}).decode() + '\n')
        return 2
    state = context = sender = None
    opened = ()
    try:
        clock = Clock()
        opened = open_stores(settings, base_path=Path(args.state_dir) if args.state_dir else None)
        store, objects, leases = opened
        state = AcquisitionState(store, clock=clock)
        path = f'runs/sec/{args.run_id}/{args.command}/{args.attempt_id}/result.json'
        try:
            prior = (read_etl_result if args.command in ('transform', 'publish') else read_result)(path, objects)
        except FileNotFoundError:
            prior = None
        if prior is None and deadline <= clock.now():
            raise _ExpiredAttempt('an expired deadline permits only an exact completed-result replay')
        started = prior.context.started_at if prior is not None else clock.now()
        pin_date = today or (prior.context.pinned_on if prior is not None else None)
        context = _new_context(args, settings, deadline, pin_date, started)
        workset = None
        if args.command == 'collect':
            try:
                workset = decode_source_workset(objects.read(args.workset))
            except (ValueError, OSError):
                state.begin_attempt(context)
                raise
            if args.workset != f'worksets/sec/source/sha256={workset.workset_id}/workset.json':
                raise Conflict('workset object path differs from its content identity')
            context = replace(context, priority=workset.context.priority)
        if args.command in ('transform', 'publish'):
            context, saved = _existing_etl_context(context, state, objects, _intent(args, pack), bool(args.today))
        else:
            context, saved = _existing_context(context, state, objects, _intent(args, pack), bool(args.today))
        if saved is not None:
            log_event(context, 'result_replayed', {'result_ref': result_path(context)})
            return _stdout(saved, result_path(context))
        if args.command in ('transform', 'publish'):
            log_event(context, 'command_started', {'command': args.command, 'input_ref': args.workset})
            result = (run_transform(args.workset, context, settings, objects, store, force=args.force)
                      if args.command == 'transform' else run_publish(args.workset, context, settings, objects, store))
            reference = write_etl_result(result, objects, state)
            log_event(context, 'command_finished', {'outcome': result.outcome, 'result_ref': reference,
                      'counters': {name: getattr(result, name) for name in
                          ('transformed', 'published', 'unchanged', 'quarantined', 'awaiting_approval', 'failed')}})
            return _stdout(result, reference)
        coordinator = Coordinator(settings, store, leases, clock)
        sender = _CheckedSender(pack.sender(store) if pack is not None else BoundedSender(settings, clock))
        client = RequestClient(settings, coordinator, sender, state, clock)
        log_event(context, 'command_started', {'command': args.command})
        if args.command == 'discover':
            workset = discover(settings, context, args.mode, args.discovery_id, client, state, objects,
                               context.pinned_on, refresh=args.refresh)
            result = _discover_result(workset, context, clock)
        else:
            result = _collection_outcome(collect(workset, context, settings, client, state, objects, _NoFaults()))
        if sender.failure is not None:
            raise sender.failure
        reference = write_result(result, objects, state)
        log_event(context, 'command_finished', {'outcome': result.outcome, 'result_ref': reference,
            'counters': {name: getattr(result, name) for name in ('discovered', 'downloaded', 'unchanged', 'pending', 'failed', 'quarantined')}})
        return _stdout(result, reference)
    except Exception as exception:
        outcome = 'configuration' if isinstance(exception, _ExpiredAttempt) else 'ownership_lost' if isinstance(exception, (OwnershipLost, ClockUncertain)) else ('state_conflict' if isinstance(exception, (Conflict, ValueError, OSError, KeyError)) else 'internal_error')
        details = {'type': type(exception).__name__}
        repair_pending = isinstance(exception, PublicationRepairPending)
        if repair_pending:
            details.update(exception.details)
        error = Error(outcome, str(exception), repair_pending, None, details)
        if state is not None and context is not None:
            try:
                _retain_error(state, context, outcome, error)
            except Exception as retention:
                error = Error('internal_error', 'attempt error could not be retained: ' + str(retention), False, None, {'cause': error.to_mapping()})
                outcome = 'internal_error'
        if context is not None:
            log_event(context, 'command_error', {'outcome': outcome, 'error': error.to_mapping()})
        else:
            sys.stderr.write(canonical_json({'outcome': outcome, 'error': error.to_mapping()}).decode() + '\n')
        sys.stdout.write(canonical_json({'outcome': outcome, 'result_ref': None, 'source_workset_ref': None, 'snapshot_workset_ref': None}).decode() + '\n')
        return exit_code(outcome)
    finally:
        if sender is not None and hasattr(sender, 'close'):
            sender.close()
        for resource in reversed(opened):
            if hasattr(resource, 'close'):
                resource.close()
