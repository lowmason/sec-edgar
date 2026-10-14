"""The committed run-worker pipeline, run by the ADF interpreter against scripted Azure (spec §7, §10)."""
from network_guard import install
install()

import importlib.util
import unittest
from dataclasses import fields
from datetime import datetime, timedelta

from adf_interpreter import ALL_SEMANTICS, PipelineRun, Response, Semantics, WebFailure, validate_pipeline, walk_activities
from support_adf import (ABSENT, ARM_AUDIENCE, ASYNC_PREFIX, ENV, IMAGE, JOB, PIPELINES, RESOURCES, RESULTS, RUN_ID,
                         STORAGE_AUDIENCE, SUBSCRIPTION, UNAVAILABLE, UNREADABLE, FakeAzure, Launch, accepted,
                         execution_name, load, operation, pipelines, result, run_worker, started)
from sec_edgar_ingest.cli import _parser
from sec_edgar_ingest.models import RunContext
from sec_edgar_ingest.results import EXIT_CODES
from sec_edgar_ingest.workflows.contracts import FORMAT_VERSION, WorkflowResult


def expected_outcome(outcome: str, state: str) -> str:
    """Spec §7.3 for a matching result: what the pipeline must end with."""
    if EXIT_CODES[outcome] == 0:
        return 'success' if state == 'Succeeded' else 'result_mismatch'
    if EXIT_CODES[outcome] == 11:
        return 'stale'
    return outcome


OBSERVE_SECONDS = 4200
PACE = 0.5  # seconds per activity, for the runs that must hold with fractional timing
PACES = (PACE, 0.3)  # 0.3 s lets the deadline's and the wait's fractions drift apart
# Each Retry-After points past the 4,200 s observation deadline; what Azure would answer after it is terminal.
CROSSING = {
    'an execution Retry-After past the deadline is unknown': [
        Launch(states=('Running', 'Succeeded'), retry_after='6000')],
    'a pending result after the deadline never relaunches': [
        Launch(states=('Running', 'Succeeded'), retry_after='6000', outcome='pending'), Launch()],
    'a Location Retry-After past the deadline is unknown': [
        Launch(start=accepted(operation()), locate=(accepted(None, '6000'), started(1)))],
    'a 202 start Retry-After past the deadline is unknown': [
        Launch(start=accepted(operation(), retry_after='6000'), locate=(started(1),))],
    'a 200 start Retry-After past the deadline is unknown': [
        Launch(start=Response(200, started(1).body, {'Retry-After': '6000'}))],
}

SCENARIOS = {
    # §7.1 start responses
    'a 200 start is observed to success': ([Launch()], 'success', 1),
    'a failed start is unknown': ([Launch(start=WebFailure('timeout'))], 'execution_unknown', 1),
    'a refused start is unknown': ([Launch(start=Response(409, {'error': {'code': 'Conflict'}}))],
                                   'execution_unknown', 1),
    'a start naming another job is unknown': (
        [Launch(start=started(1, id=f'{JOB}-other/executions/{execution_name(1)}'))], 'execution_unknown', 1),
    'a start without a name is unknown': ([Launch(start=started(1, name=None))], 'execution_unknown', 1),
    'a start without an id is unknown': ([Launch(start=started(1, id=None))], 'execution_unknown', 1),
    'a start naming a nested path is unknown': (
        [Launch(start=started(1, name='a/b', id=f'{JOB}/executions/a/b'))], 'execution_unknown', 1),
    'a 202 without a Location is unknown': ([Launch(start=accepted())], 'execution_unknown', 1),
    'a 202 Location is followed to the execution': (
        [Launch(start=accepted(operation()), locate=(accepted(None, '10'), started(1)))], 'success', 1),
    'a 202 status-route Location is followed': (
        [Launch(start=accepted(operation(route='containerappsjoboperationstatuses')), locate=(started(1),))],
        'success', 1),
    'a 202 Location with signed parameters is followed': (
        [Launch(start=accepted(operation() + '&t=638000000000000000&c=MIIHhzCCBm-gAwIB_x&s=AbC-_123&h=AbC-_123'),
                locate=(started(1),))], 'success', 1),
    'a failed Location poll keeps locating': (
        [Launch(start=accepted(operation()), locate=(WebFailure('503'), started(1)))], 'success', 1),
    'a Location that never names the execution is unknown': (
        [Launch(start=accepted(operation()), locate=(accepted(None),))], 'execution_unknown', 1),
    'a Location naming another job is unknown': (
        [Launch(start=accepted(operation()), locate=(started(1, id=f'{JOB}-other/executions/{execution_name(1)}'),))],
        'execution_unknown', 1),
    'an operation status is not an execution reference': (
        [Launch(start=accepted(operation()), locate=(Response(200, {
            'id': f'{ASYNC_PREFIX}containerappsjoboperationstatuses/op-1', 'name': 'op-1', 'status': 'Succeeded'}),))],
        'execution_unknown', 1),
    # §7.2 observation
    'running and processing keep polling': ([Launch(states=('Processing', 'Running', 'Running', 'Succeeded'))],
                                            'success', 1),
    'a failed GET keeps polling': ([Launch(states=(UNAVAILABLE, 'Running', UNAVAILABLE, 'Succeeded'))], 'success', 1),
    'a missing status keeps polling': ([Launch(states=(None, 'Succeeded'))], 'success', 1),
    'never terminal by the deadline is unknown': ([Launch(states=('Running',))], 'execution_unknown', 1),
    'every GET failing is unknown': ([Launch(states=(UNAVAILABLE,))], 'execution_unknown', 1),
    'degraded is unknown': ([Launch(states=('Running', 'Degraded'))], 'execution_unknown', 1),
    'unknown is unknown': ([Launch(states=('Unknown',))], 'execution_unknown', 1),
    'an unrecognized state is unknown': ([Launch(states=('Suspended',))], 'execution_unknown', 1),
    'stopped is stopped': ([Launch(states=('Running', 'Stopped'))], 'execution_stopped', 1),
    'another image is a mismatch': ([Launch(image=IMAGE.replace('1' * 64, '2' * 64))], 'execution_mismatch', 1),
    # §7.2 deadline: a Retry-After that does not fit before it ends observation there, whatever comes after
    **{name: (launches, 'execution_unknown', 1) for name, launches in CROSSING.items()},
    # §7.3 results
    'an absent result is missing': ([Launch(outcome=ABSENT)], 'result_missing', 1),
    'an unreadable result is missing': ([Launch(outcome=UNREADABLE)], 'result_missing', 1),
    'an absent result after Failed is missing': ([Launch(states=('Failed',), outcome=ABSENT)], 'result_missing', 1),
    'another format is a mismatch': ([Launch(outcome={**result('daily', 1, 'success'),
                                                      'format_version': 'sec-workflow-result-v2'})],
                                     'result_mismatch', 1),
    'an outcome outside EXIT_CODES is a mismatch': ([Launch(outcome='finished')], 'result_mismatch', 1),
    'a result without an outcome is a mismatch': (
        [Launch(outcome={key: value for key, value in result('daily', 1, 'success').items() if key != 'outcome'})],
        'result_mismatch', 1),
    'a result without a context is a mismatch': (
        [Launch(outcome={key: value for key, value in result('daily', 1, 'success').items() if key != 'context'})],
        'result_mismatch', 1),
    # §7.3 replay
    'pending relaunches once': ([Launch(outcome='pending'), Launch()], 'success', 2),
    'pending on a Failed execution relaunches': ([Launch(states=('Failed',), outcome='pending'), Launch()],
                                                 'success', 2),
    'pending at the replay cap stays pending': ([Launch(outcome='pending'), Launch(outcome='pending')], 'pending', 2),
    'a relaunch that cannot start is unknown': ([Launch(outcome='pending'), Launch(start=WebFailure('timeout'))],
                                                'execution_unknown', 2),
    'a relaunch is classified on its own result': ([Launch(outcome='pending'), Launch(outcome='awaiting_approval')],
                                                   'awaiting_approval', 2),
}
for field_name, wrong in (('run_id', 'another-run'), ('command', 'reconcile'), ('attempt_id', 'launch-2'),
                          ('execution_id', 'job-sec-edgar-dev-9999999'), ('image_digest', 'sha256:' + '2' * 64),
                          ('config_sha256', 'd' * 64)):
    SCENARIOS[f'a result with another {field_name} is a mismatch'] = (
        [Launch(context={field_name: wrong})], 'result_mismatch', 1)

INVALID_LOCATIONS = {
    'http': operation().replace('https://', 'http://'),
    'another host': operation().replace('management.azure.com', 'management.azure.com.example.net'),
    'userinfo': operation().replace('https://management.azure.com', 'https://management.azure.com@example.net'),
    'a port': operation().replace('management.azure.com', 'management.azure.com:8443'),
    'another subscription': operation().replace(SUBSCRIPTION, '00000000-0000-4000-8000-000000000000'),
    'another region': operation().replace('/locations/eastus/', '/locations/westus/'),
    'another route': operation(route='containerappsoperationresults'),
    'no API version': operation().split('?')[0],
    'another API version': operation().replace('2026-07-01', '2025-01-01'),
    'a preview API version': operation().replace('2026-07-01', '2026-07-01-preview'),
    'a fragment': operation() + '#x',
    'a second query': operation() + '?x=1',
    'a dot segment': operation('..'),
    'a single dot segment': operation('.'),
    'a conflicting api-version after the selected one': operation() + '&api-version=2025-01-01',
    'a conflicting api-version before the selected one': operation().replace(
        '?api-version=2026-07-01', '?api-version=2025-01-01&api-version=2026-07-01'),
    'a repeated api-version': operation() + '&api-version=2026-07-01',
    'a conflicting api-version in another case': operation() + '&API-VERSION=2025-01-01',
    'a valueless api-version': operation() + '&api-version',
    'a percent-encoded api-version hyphen': operation() + '&api%2Dversion=2025-01-01',
    'a percent-encoded api-version letter': operation() + '&%61pi-version=2025-01-01',
    'a backslash single dot segment': operation('\\.'),
    'a backslash dot segment': operation('\\..'),
    'a backslash climb': operation('\\..' * 7 + '\\subscriptions\\00000000-0000-4000-8000-000000000000'),
    # A URL parser strips ASCII tab and newline before it reads the path or the query.
    'a tab before a dot segment': operation('\t..'),
    'a tab before a single dot segment': operation('\t.'),
    'a line feed before a dot segment': operation('\n..'),
    'a carriage return before a dot segment': operation('\r..'),
    'a tab inside the api-version name': operation() + '&api\t-version=2025-01-01',
    'an encoded segment': operation('op%2F..%2Fx'),
    'an extra segment': operation('op-1/extra'),
    'no operation id': operation(''),
}


class RunWorkerScenarioTests(unittest.TestCase):
    def check(self, launches, expected, posts, command='daily'):
        for semantics in ALL_SEMANTICS:
            with self.subTest(semantics=semantics):
                run = run_worker(launches, command, semantics)
                self.assertEqual((run.outcome, run.posts), (expected, posts))
        return run

    def test_every_scenario_under_every_reading_of_the_documentation(self):
        for name, (launches, expected, posts) in SCENARIOS.items():
            with self.subTest(name):
                self.check(launches, expected, posts)

    def test_every_exit_code_outcome_is_classified_by_name(self):
        for outcome in EXIT_CODES:
            for state in ('Succeeded', 'Failed'):
                with self.subTest(outcome=outcome, state=state):
                    if outcome == 'pending':
                        self.check([Launch(states=(state,), outcome='pending'), Launch()], 'success', 2)
                    else:
                        self.check([Launch(states=(state,), outcome=outcome)], expected_outcome(outcome, state), 1)

    def test_an_invalid_location_is_never_requested(self):
        for label, location in INVALID_LOCATIONS.items():
            with self.subTest(label):
                run = self.check([Launch(start=accepted(location), locate=(started(1),))], 'execution_unknown', 1)
                self.assertEqual([request.method for request in run.requests], ['POST'])

    def test_unknown_starts_make_no_further_request(self):
        for launches in ([Launch(start=WebFailure('timeout'))], [Launch(start=started(1, name=None))]):
            run = self.check(launches, 'execution_unknown', 1)
            self.assertEqual([request.method for request in run.requests], ['POST'])

    def test_the_start_carries_the_job_container_and_the_launch_arguments(self):
        run = run_worker([Launch(outcome='pending'), Launch()])
        posts = [request for request in run.requests if request.method == 'POST']
        self.assertEqual(len(posts), 2)
        for launch, request in enumerate(posts, start=1):
            container, = request.body['containers']
            self.assertEqual({key: container[key] for key in ('name', 'image', 'resources', 'env')},
                             {'name': 'sec-edgar-ingest', 'image': IMAGE, 'resources': RESOURCES, 'env': ENV})
            arguments = _parser().parse_args(container['args'])
            self.assertEqual((arguments.command, arguments.config_env, arguments.config, arguments.run_id,
                              arguments.attempt_id, arguments.execution_id),
                             ('daily', 'SEC_EDGAR_INGEST_CONFIG', None, RUN_ID, f'launch-{launch}', None))
            deadline = datetime.fromisoformat(arguments.deadline)
            self.assertEqual(arguments.deadline, deadline.strftime('%Y-%m-%dT%H:%M:%SZ'))
            self.assertLessEqual(abs(deadline - (request.at + timedelta(seconds=3300))), timedelta(seconds=2))

    def test_polling_waits_thirty_seconds_or_a_longer_retry_after(self):
        for retry_after, low in ((None, 30), ('5', 30), ('120', 120), ('soon', 30)):
            with self.subTest(retry_after=retry_after):
                run = run_worker([Launch(states=('Running', 'Running', 'Succeeded'), retry_after=retry_after)])
                times = [request.at for request in run.requests if '/executions/' in request.url]
                gaps = [(later - earlier).total_seconds() for earlier, later in zip(times[1:], times[2:])]
                self.assertTrue(gaps and all(low <= gap < low + 15 for gap in gaps), gaps)
        run = run_worker([Launch(start=accepted(operation(), retry_after='90'), locate=(started(1),))])
        post, located = run.requests[0], run.requests[1]
        self.assertGreaterEqual((located.at - post.at).total_seconds(), 90)

    def test_observation_stops_at_the_deadline_and_never_cancels(self):
        run = run_worker([Launch(states=('Running',))])
        post, *gets = run.requests
        self.assertTrue(all(request.method == 'GET' and '/executions/' in request.url for request in gets))
        # A poll cycle here is 30 s plus ten activities: the last GET is the last cycle's at least a second before
        # the deadline, and the deadline is 4,200 s after the stamp taken just before the start request.
        deadline, last = self.deadline(run), timedelta(seconds=1)
        self.assertLessEqual(gets[-1].at, deadline - last)
        self.assertGreater(gets[-1].at, deadline - last - timedelta(seconds=40))
        self.assertLess(abs((deadline - post.at).total_seconds() - 4200), 5)
        self.assertNotIn('stop', ' '.join(request.url for request in run.requests))

    @staticmethod
    def deadline(run) -> datetime:
        return datetime.fromisoformat(run.variables['launchedAt']) + timedelta(seconds=OBSERVE_SECONDS)

    @staticmethod
    def observation_gets(run) -> list:
        """The Location and execution GETs; the result read is not observation."""
        return [request for request in run.requests if request.method == 'GET' and not request.url.startswith(RESULTS)]

    def test_no_wait_or_observation_get_outlasts_the_deadline(self):
        for name, launches in CROSSING.items():
            with self.subTest(name):
                run = run_worker(launches)
                deadline = self.deadline(run)
                self.assertEqual((run.outcome, [request.method for request in run.requests].count('POST')),
                                 ('execution_unknown', 1))
                gets = self.observation_gets(run)
                self.assertTrue(all(request.at <= deadline - timedelta(seconds=1) for request in gets),
                                [request.at for request in gets])
                # The last wait is cut to end inside the budget's last second: the run then only classifies and fails.
                self.assertGreaterEqual(run.ended, deadline)
                self.assertLessEqual(run.ended, deadline + timedelta(seconds=60))

    def test_a_retry_after_that_fits_is_honoured_in_full(self):
        for launch, marker in ((Launch(states=('Running', 'Running', 'Succeeded'), retry_after='300'), '/executions/'),
                               (Launch(start=accepted(operation()), locate=(accepted(None, '300'), started(1))),
                                '/containerappsjoboperationresults/')):
            for pace in (1, *PACES):
                with self.subTest(marker, pace=pace):
                    run = run_worker([launch], pace=pace)
                    self.assertEqual(run.outcome, 'success')
                    times = [request.at for request in run.requests if marker in request.url]
                    gaps = [(later - earlier).total_seconds() for earlier, later in zip(times, times[1:])]
                    self.assertTrue(gaps and all(300 <= gap < 315 for gap in gaps), gaps)

    def test_a_get_a_second_before_the_deadline_counts_and_none_follows_it(self):
        # The last second of the budget is refused: a wait the deadline cut short ends inside it.
        last = timedelta(seconds=1)
        ends = {}
        for seconds in range(4100, 4200):
            run = run_worker([Launch(states=('Running', 'Succeeded'), retry_after=str(seconds))])
            deadline = self.deadline(run)
            gets = self.observation_gets(run)
            self.assertTrue(all(request.at <= deadline - last for request in gets), seconds)
            expected = 'success' if len(gets) == 2 else 'execution_unknown'
            self.assertEqual((run.posts, run.outcome), (1, expected), seconds)
            ends.setdefault(run.outcome, set()).add(gets[-1].at == deadline - last)
        # The sweep crosses the boundary, and a terminal state from a GET sent exactly one second before the
        # deadline, the latest any GET can go, is accepted.
        self.assertEqual(set(ends), {'success', 'execution_unknown'})
        self.assertIn(True, ends['success'])

    def test_a_cut_wait_ends_observation_whatever_the_activity_pace(self):
        # Activities taking half a second must not let a GET follow a wait that the deadline cut short.
        for pace in PACES:
            for semantics in ALL_SEMANTICS:
                with self.subTest(pace=pace, semantics=semantics):
                    run = run_worker([Launch(states=('Running', 'Succeeded'), retry_after='6000')],
                                     semantics=semantics, pace=pace)
                    gets = self.observation_gets(run)
                    posts = [request.method for request in run.requests].count('POST')
                    self.assertEqual((run.outcome, posts, len(gets)), ('execution_unknown', 1, 1))

    def test_a_cut_wait_ends_observation_whatever_the_sub_second_timing(self):
        # Every pace from 0.05 s to 0.95 s per activity, each from ten start offsets, so the deadline's and the wait's
        # fractions take every relation. A deadline with a fraction would let a GET follow a cut wait here.
        for hundredths in range(5, 96):
            for tenths in range(10):
                pace, offset = hundredths / 100, tenths / 10
                run = run_worker([Launch(states=('Running', 'Succeeded'), retry_after='6000')], pace=pace,
                                 offset=offset)
                gets = self.observation_gets(run)
                self.assertEqual((run.outcome, run.posts, len(gets)), ('execution_unknown', 1, 1), (pace, offset))

    def test_every_get_follows_its_full_wait_whatever_the_activity_pace(self):
        for pace in PACES:
            outcomes = set()
            for seconds in range(4100, 4200):
                run = run_worker([Launch(states=('Running', 'Succeeded'), retry_after=str(seconds))], pace=pace)
                deadline = self.deadline(run)
                gets = self.observation_gets(run)
                gaps = [(later.at - earlier.at).total_seconds() for earlier, later in zip(gets, gets[1:])]
                self.assertTrue(all(gap >= seconds for gap in gaps), (pace, seconds, gaps))
                self.assertTrue(all(request.at < deadline for request in gets), (pace, seconds))
                expected = 'success' if len(gets) == 2 else 'execution_unknown'
                self.assertEqual((run.posts, run.outcome), (1, expected), (pace, seconds))
                outcomes.add(run.outcome)
            self.assertEqual(outcomes, {'success', 'execution_unknown'}, pace)

    def test_the_fail_message_names_the_result_to_read(self):
        # results/runs/sec/<run ID>/<command>/launch-<n>/result.json: the alert row shows this message.
        for launches, launch, code in (([Launch(start=WebFailure('timeout'))], 1, 'execution_unknown'),
                                       ([Launch(outcome='pending'), Launch(outcome='pending')], 2, 'pending')):
            with self.subTest(code):
                failure, = self.check(launches, code, launch).failures
                self.assertEqual(failure['message'],
                                 f'pl-sec-edgar-run-worker daily run {RUN_ID} launch-{launch} ended {code}')

    def test_the_callers_pass_their_run_id_and_command(self):
        for command in ('backfill', 'daily', 'reconcile'):
            for launch, expected in ((Launch(), 'Succeeded'), (Launch(outcome='awaiting_approval'), 'Failed')):
                with self.subTest(command=command, expected=expected):
                    caller_run_id = '00000000-0000-4000-8000-000000000001'
                    azure = FakeAzure(command, [launch], run_id=caller_run_id)
                    engine = PipelineRun(pipelines(), azure)
                    outcome = engine.run(f'pl-sec-edgar-{command}', {})
                    self.assertEqual((outcome.run_id, outcome.status, azure.posts), (caller_run_id, expected, 1))
                    arguments = engine.requests[0].body['containers'][0]['args']
                    self.assertEqual((arguments[0], arguments[arguments.index('--run-id') + 1]),
                                     (command, caller_run_id))
                    # The Fail message names the caller's run ID, the result path's, not the run-worker's own.
                    self.assertEqual([failure['message'] for failure in engine.failures],
                                     [] if expected == 'Succeeded' else
                                     [f'pl-sec-edgar-run-worker {command} run {caller_run_id} launch-1 ended '
                                      'awaiting_approval'])


FAULT_BASES = {
    'success': lambda: [Launch()],
    'pending then success': lambda: [Launch(outcome='pending'), Launch()],
    'located': lambda: [Launch(start=accepted(operation()), locate=(started(1),))],
    'awaiting approval': lambda: [Launch(outcome='awaiting_approval')],
    'stopped': lambda: [Launch(states=('Stopped',))],
}


class RunWorkerFaultTests(unittest.TestCase):
    def test_a_fault_in_any_activity_never_relaunches_blindly_or_succeeds_falsely(self):
        names = [activity['name'] for activity, _ in walk_activities(load('pl-sec-edgar-run-worker')['activities'])]
        self.assertEqual(len(names), 47)
        for base, launches in FAULT_BASES.items():
            clean = run_worker(launches())
            for name in names:
                for semantics in (Semantics(), Semantics('null', False, True)):
                    with self.subTest(base=base, fault=name, semantics=semantics):
                        run = run_worker(launches(), semantics=semantics, faults={name})
                        self.assertLessEqual(run.posts, 2)
                        if run.outcome == 'success':
                            self.assertEqual(clean.outcome, 'success')
                        for failure in run.failures:
                            self.assertNotIn(failure['errorCode'], ('', 'ErrorCodeNotString'))
                        if run.status == 'Failed' and name not in ('Check outcome', 'Fail run'):
                            self.assertEqual(len(run.failures), 1)
                        starts = [index for index, event in enumerate(run.trace)
                                  if event[:2] == ('Start job', 'Succeeded') or event[:2] == ('Start job', 'Failed')]
                        for second in starts[1:]:
                            classified = [event[2]['value'] for event in run.trace[:second]
                                          if event[:2] == ('Classify outcome', 'Succeeded')]
                            self.assertEqual(classified[-1:], ['pending'])


class RunWorkerDefinitionTests(unittest.TestCase):
    def test_the_committed_json_is_the_rendered_source(self):
        spec = importlib.util.spec_from_file_location('pipeline_render', PIPELINES / 'render.py')
        render = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(render)
        definitions = render.definitions()
        self.assertEqual(sorted(path.stem for path in PIPELINES.glob('*.json')), sorted(definitions))
        for name, definition in definitions.items():
            self.assertEqual((PIPELINES / f'{name}.json').read_text(), render.rendered(definition), name)

    def test_no_string_needs_arm_escaping(self):
        def strings(value):
            if isinstance(value, dict):
                return [item for child in value.values() for item in strings(child)]
            if isinstance(value, list):
                return [item for child in value for item in strings(child)]
            return [value] if isinstance(value, str) else []
        for name in pipelines():
            self.assertFalse([text for text in strings(load(name)) if text.startswith('[')], name)

    def test_the_definitions_stay_inside_the_modelled_subset(self):
        for name, definition in pipelines().items():
            with self.subTest(name):
                validate_pipeline(definition)

    def test_web_activities_never_retry_or_follow_async_and_use_their_audience(self):
        expected = {'Start job': ('POST', ARM_AUDIENCE), 'Get operation': ('GET', ARM_AUDIENCE),
                    'Get execution': ('GET', ARM_AUDIENCE), 'Get result': ('GET', STORAGE_AUDIENCE)}
        found = {}
        for activity, _ in walk_activities(load('pl-sec-edgar-run-worker')['activities']):
            if activity['type'] == 'WebActivity':
                properties = activity['typeProperties']
                self.assertEqual((activity['policy']['retry'], properties['turnOffAsync'],
                                  properties['httpRequestTimeout'], properties['authentication']['type']),
                                 (0, True, '00:01:00', 'MSI'))
                found[activity['name']] = (properties['method'], properties['authentication']['resource'])
        self.assertEqual(found, expected)

    def test_the_outcome_vocabularies_are_the_exit_code_table(self):
        variables = load('pl-sec-edgar-run-worker')['variables']
        self.assertEqual(variables['knownOutcomes']['defaultValue'], list(EXIT_CODES))
        self.assertEqual(variables['exitZeroOutcomes']['defaultValue'],
                         [name for name, code in EXIT_CODES.items() if code == 0])
        self.assertEqual(variables['staleOutcomes']['defaultValue'],
                         [name for name, code in EXIT_CODES.items() if code == 11])

    def test_the_result_fields_read_are_the_worker_result_contract(self):
        text = str(load('pl-sec-edgar-run-worker'))
        context = {field.name for field in fields(RunContext)}
        for name in ('run_id', 'command', 'attempt_id', 'execution_id', 'image_digest', 'config_sha256'):
            self.assertIn(f".context.{name}", text)
            self.assertIn(name, context)
        self.assertTrue({'format_version', 'context', 'outcome'} <= {field.name for field in fields(WorkflowResult)})
        self.assertIn(f"'{FORMAT_VERSION}'", text)

    def test_the_until_budget_covers_every_launch(self):
        until = load('pl-sec-edgar-run-worker')['activities'][0]
        self.assertEqual((until['type'], until['typeProperties']['timeout']), ('Until', '0.03:00:00'))
        self.assertGreaterEqual(3 * 3600, 2 * (4200 + 600))

    def test_the_callers_each_run_the_worker_with_their_command(self):
        for command in ('backfill', 'daily', 'reconcile'):
            activity, = load(f'pl-sec-edgar-{command}')['activities']
            self.assertEqual(activity['typeProperties'], {
                'pipeline': {'referenceName': 'pl-sec-edgar-run-worker', 'type': 'PipelineReference'},
                'waitOnCompletion': True,
                'parameters': {'command': command, 'runId': {'value': '@pipeline().RunId', 'type': 'Expression'}}})


if __name__ == '__main__':
    unittest.main()
