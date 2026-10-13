"""Scripted Azure for the run-worker pipeline: every request must hit the exact host, route and audience."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from adf_interpreter import PipelineRun, Request, Response, Semantics, WebFailure

REPO = Path(__file__).resolve().parents[3]
PIPELINES = REPO / 'infra/azure/sec-edgar-ingest/pipelines'
SUBSCRIPTION = '3c92a216-8ed6-4897-b741-11ed287b8617'
JOB = (f'/subscriptions/{SUBSCRIPTION}/resourceGroups/rg-sec-edgar-dev-eastus'
       '/providers/Microsoft.App/jobs/job-sec-edgar-dev')
ARM = 'https://management.azure.com'
ARM_AUDIENCE = 'https://management.azure.com/'
STORAGE_AUDIENCE = 'https://storage.azure.com/'
ASYNC_PREFIX = f'{ARM}/subscriptions/{SUBSCRIPTION}/providers/Microsoft.App/locations/eastus/'
RESULTS = 'https://secedgardevb8617.blob.core.windows.net/results/runs/sec/'
DIGEST = 'sha256:' + '1' * 64
IMAGE = f'secedgardevb8617.azurecr.io/sec-edgar-ingest@{DIGEST}'
CONFIG_SHA256 = 'c' * 64
WORKER_CLIENT_ID = '11111111-2222-4333-8444-555555555555'
RESOURCES = {'cpu': 2, 'memory': '4Gi'}
ENV = [{'name': 'SEC_EDGAR_INGEST_WORKER_CLIENT_ID', 'value': WORKER_CLIENT_ID},
       {'name': 'SEC_EDGAR_INGEST_CONFIG', 'secretRef': 'ingest-config'}]
DEFAULTS = {'containerName': 'sec-edgar-ingest', 'imageRef': IMAGE, 'containerResources': RESOURCES,
            'containerEnv': ENV, 'imageDigest': DIGEST, 'configSha256': CONFIG_SHA256, 'jobPath': JOB,
            'asyncPrefix': ASYNC_PREFIX, 'resultsUrl': RESULTS, 'maxLaunches': 2, 'pollSeconds': 30,
            'observeSeconds': 4200, 'workerSeconds': 3300}
# Names and types match the parameters main.bicep declares on pl-sec-edgar-run-worker.
PARAMETER_TYPES = {'command': 'String', 'runId': 'String', 'containerName': 'String', 'imageRef': 'String',
                   'containerResources': 'Object', 'containerEnv': 'Array', 'imageDigest': 'String',
                   'configSha256': 'String', 'jobPath': 'String', 'asyncPrefix': 'String', 'resultsUrl': 'String',
                   'maxLaunches': 'Int', 'pollSeconds': 'Int', 'observeSeconds': 'Int', 'workerSeconds': 'Int'}
RUN_ID = '0f0e0d0c-0b0a-4908-8706-050403020100'
UNAVAILABLE = object()  # an execution GET that fails
ABSENT, UNREADABLE = object(), object()  # result blob states


def load(name: str) -> dict:
    return json.loads((PIPELINES / f'{name}.json').read_text())


def pipelines() -> dict:
    """The committed definitions, with run-worker's parameters declared as main.bicep declares them."""
    worker = load('pl-sec-edgar-run-worker')
    worker['parameters'] = {name: ({'type': kind, 'defaultValue': DEFAULTS[name]} if name in DEFAULTS
                                   else {'type': kind}) for name, kind in PARAMETER_TYPES.items()}
    return {'pl-sec-edgar-run-worker': worker,
            **{f'pl-sec-edgar-{command}': load(f'pl-sec-edgar-{command}')
               for command in ('backfill', 'daily', 'reconcile')}}


def execution_name(launch: int) -> str:
    return f'job-sec-edgar-dev-{launch:07d}'


def started(launch: int, **changes) -> Response:
    name = execution_name(launch)
    body = {'id': f'{JOB}/executions/{name}', 'name': name, **changes}
    return Response(200, {key: value for key, value in body.items() if value is not None})


def accepted(location: str | None = None, retry_after: str | None = '15', body=None) -> Response:
    headers = {}
    if location is not None:
        headers['Location'] = location
    if retry_after is not None:
        headers['Retry-After'] = retry_after
    return Response(202, {} if body is None else body, headers)


def operation(operation_id: str = 'op-1', route: str = 'containerappsjoboperationresults') -> str:
    return f'{ASYNC_PREFIX}{route}/{operation_id}?api-version=2026-07-01'


def result(command: str, launch: int, outcome: str, run_id: str = RUN_ID, context: dict | None = None) -> dict:
    """The fields of a worker result that the pipeline reads, matching launch `launch` unless `context` overrides."""
    return {'format_version': 'sec-workflow-result-v1', 'outcome': outcome, 'ended_at': '2026-10-12T09:30:00+00:00',
            'context': {'run_id': run_id, 'command': command, 'attempt_id': f'launch-{launch}',
                        'execution_id': execution_name(launch), 'image_digest': DIGEST,
                        'config_sha256': CONFIG_SHA256, **(context or {})}}


@dataclass
class Launch:
    """What Azure does with one start: its start response, Location polls, execution states and result."""
    outcome: object = 'success'          # a result outcome name, a result dict, ABSENT or UNREADABLE
    states: tuple = ('Succeeded',)       # successive execution GETs; the last repeats; UNAVAILABLE fails
    start: object = None                 # a Response or WebFailure; None is a 200 naming the execution
    locate: tuple = ()                   # successive Location GET responses; the last repeats
    image: str = IMAGE
    context: dict = field(default_factory=dict)
    retry_after: str | None = None       # Retry-After on execution GETs


class FakeAzure:
    def __init__(self, command: str, launches, run_id: str = RUN_ID):
        self.command, self.launches, self.run_id, self.posts = command, list(launches), run_id, 0
        self.polls = {'locate': 0, 'observe': 0}

    @property
    def current(self) -> Launch:
        return self.launches[self.posts - 1]

    def __call__(self, request: Request) -> Response:
        if request.method == 'POST':
            assert (request.url, request.resource) == (f'{ARM}{JOB}/start?api-version=2026-07-01', ARM_AUDIENCE), request
            assert request.headers == {'Content-Type': 'application/json'}, request.headers
            self.posts += 1
            assert self.posts <= len(self.launches), f'unscripted launch {self.posts}'
            self.polls = {'locate': 0, 'observe': 0}
            launch = self.current
            response = launch.start if launch.start is not None else started(self.posts)
            if isinstance(response, Exception):
                raise response
            return response
        assert request.method == 'GET' and self.posts, request
        launch, name = self.current, execution_name(self.posts)
        if request.url == f'{ARM}{JOB}/executions/{name}?api-version=2026-07-01':
            assert request.resource == ARM_AUDIENCE and request.headers == {}, request
            state = launch.states[min(self.polls['observe'], len(launch.states) - 1)]
            self.polls['observe'] += 1
            if state is UNAVAILABLE:
                raise WebFailure('execution GET unavailable')
            body = {'id': f'{JOB}/executions/{name}', 'name': name, 'properties': {
                'status': state, 'template': {'containers': [{'name': 'sec-edgar-ingest', 'image': launch.image}]}}}
            if state is None:
                del body['properties']['status']
            headers = {} if launch.retry_after is None else {'Retry-After': launch.retry_after}
            return Response(200, body, headers)
        start = launch.start
        if isinstance(start, Response) and request.url == start.headers.get('Location'):
            assert request.resource == ARM_AUDIENCE and request.headers == {}, request
            assert launch.locate, 'unscripted Location poll'
            response = launch.locate[min(self.polls['locate'], len(launch.locate) - 1)]
            self.polls['locate'] += 1
            if isinstance(response, Exception):
                raise response
            return response
        expected = f'{RESULTS}{self.run_id}/{self.command}/launch-{self.posts}/result.json'
        assert request.url == expected, f'unexpected request {request.method} {request.url}'
        assert request.resource == STORAGE_AUDIENCE and request.headers == {'x-ms-version': '2026-04-06'}, request
        if launch.outcome is ABSENT:
            raise WebFailure('404 BlobNotFound')
        if launch.outcome is UNREADABLE:
            return Response(200, 'not a JSON object')
        body = launch.outcome if isinstance(launch.outcome, dict) else result(
            self.command, self.posts, launch.outcome, self.run_id, launch.context)
        return Response(200, body, {'Content-Type': 'application/json'})


@dataclass
class WorkerRun:
    outcome: str            # 'success' or the Fail activity's error code
    status: str
    posts: int
    requests: list
    variables: dict
    trace: list
    failures: list


def run_worker(launches, command: str = 'daily', semantics: Semantics = Semantics(), faults=(),
               parameters=None) -> WorkerRun:
    azure = FakeAzure(command, launches)
    engine = PipelineRun(pipelines(), azure, semantics, frozenset(faults))
    outcome = engine.run('pl-sec-edgar-run-worker', {'command': command, 'runId': RUN_ID, **(parameters or {})})
    codes = [failure['errorCode'] for failure in outcome.failures]
    assert len(codes) <= 1, codes
    if outcome.status == 'Succeeded':
        assert not codes
    label = 'success' if outcome.status == 'Succeeded' else (codes[0] if codes else None)
    return WorkerRun(label, outcome.status, azure.posts, engine.requests, outcome.variables, engine.trace,
                     outcome.failures)
