"""Authoring source for the ADF pipeline JSON beside this file (spec §7). Offline; it calls nothing.

Run `uv run --offline --frozen --package sec-edgar-ingest python infra/azure/sec-edgar-ingest/pipelines/render.py`
after editing. The JSON it writes is what Bicep deploys and what the offline interpreter tests run; a test
fails when the two differ.
"""
from __future__ import annotations

import json
from pathlib import Path

from sec_edgar_ingest.results import EXIT_CODES

HERE = Path(__file__).resolve().parent
ARM = 'https://management.azure.com/'
STORAGE = 'https://storage.azure.com/'
WEB_POLICY = {'timeout': '0.00:10:00', 'retry': 0, 'retryIntervalInSeconds': 30, 'secureOutput': False,
              'secureInput': False}
COMMANDS = ('backfill', 'daily', 'reconcile')


def expression(text: str) -> dict:
    return {'value': text, 'type': 'Expression'}


def after(name: str, *conditions: str) -> dict:
    return {'activity': name, 'dependencyConditions': list(conditions or ('Succeeded',))}


def assign(name: str, variable: str, value: str, *depends: dict) -> dict:
    activity = {'name': name, 'type': 'SetVariable'}
    if depends:
        activity['dependsOn'] = list(depends)
    activity['typeProperties'] = {'variableName': variable,
                                  'value': expression(value) if value.startswith('@') else value}
    return activity


def web(name: str, method: str, url: str, resource: str, *depends: dict, headers=None, body=None) -> dict:
    properties = {'method': method, 'url': expression(url)}
    if headers is not None:
        properties['headers'] = headers
    if body is not None:
        properties['body'] = body
    properties.update({'httpRequestTimeout': '00:01:00', 'turnOffAsync': True,
                       'authentication': {'type': 'MSI', 'resource': resource}})
    return {'name': name, 'type': 'WebActivity', 'dependsOn': list(depends), 'policy': WEB_POLICY,
            'typeProperties': properties}


# §7.2: observation ends 4,200 s (observeSeconds) after the launch's start request, stamped just before it. The
# stamp is cut to its whole second (STAMP), so the deadline is a whole second too, up to 1 s earlier than the
# uncut one, and --deadline, which formatDateTime already cuts, is unchanged.
STAMP = "@concat(formatDateTime(utcNow(), 'yyyy-MM-ddTHH:mm:ss'), 'Z')"
DEADLINE = "addSeconds(variables('launchedAt'), pipeline().parameters.observeSeconds)"
BEFORE_DEADLINE = f"less(ticks(utcNow()), ticks({DEADLINE}))"
# At least a full second still to go before the deadline.
A_SECOND_BEFORE_DEADLINE = f"less(ticks(addSeconds(utcNow(), 1)), ticks({DEADLINE}))"


def whole_second_ticks(moment: str) -> str:
    """The ticks of `moment` cut to its whole second, so a difference of two is a multiple of 10^7."""
    return f"ticks(concat(formatDateTime({moment}, 'yyyy-MM-ddTHH:mm:ss'), 'Z'))"


# The whole seconds from the first whole second after now to the whole-second deadline, never negative and never
# more than the time actually left. A wait cut to it therefore ends inside the budget's last second, whatever the
# fraction of now. The offline interpreter models no sub, div or min, so the tick difference is taken by adding a
# negated value, and divided by 10^7 by cutting its seven trailing zeros as text (the padding keeps a zero
# difference readable).
REMAINING_TICKS = (f"max(add({whole_second_ticks(DEADLINE)}, "
                   f"int(concat('-', string({whole_second_ticks('addSeconds(utcNow(), 1)')})))), 0)")
REMAINING = f"int(split(concat('0000000', string({REMAINING_TICKS}), '|'), '0000000|')[0])"
WAIT = "int(variables('waitSeconds'))"
CAPPED_WAIT = f"@if(less({WAIT}, {REMAINING}), {WAIT}, {REMAINING})"


def wait(name: str, *depends: dict) -> dict:
    """Waits the poll base or Retry-After, cut so that it ends by the observation deadline."""
    return {'name': name, 'type': 'Wait', 'dependsOn': list(depends),
            'typeProperties': {'waitTimeInSeconds': expression(CAPPED_WAIT)}}


# Set just before each observation GET. In the budget's last second int() of a word fails it, so the GET is not
# sent; the phase's After activity, which still counts that second as time left, sends the run round the phase on
# 0 s waits until the deadline passes and then classifies. A wait the deadline cut short ends inside that second, so
# it is never followed by a GET, whatever the sub-second timing; a GET follows only a full wait, and a GET in the
# last second is refused. A GET whose check passed, at least a second before the deadline, can still go out one
# activity dispatch later (a few seconds in ADF), at most once per launch; its result is accepted as usual.
RESET_WAIT = f"@string(int(if({A_SECOND_BEFORE_DEADLINE}, string(pipeline().parameters.pollSeconds), 'deadline')))"

STATE = "variables('state')"
RESULT = "json(variables('result'))"
LOCATION = "activity('Start job').output.ADFWebActivityResponseHeaders['Location']"
LOCATION_PATH = f"split({LOCATION}, '?')[0]"
LOCATION_QUERY = f"split({LOCATION}, '?')[1]"


def contains_any(text: str, characters: str) -> str:
    """True when `text` holds any of `characters`: nested two-argument ors over one contains each."""
    checks = [f"contains({text}, '{character}')" for character in characters]
    expression = checks[-1]
    for check in reversed(checks[:-1]):
        expression = f"or({check}, {expression})"
    return expression


# A fragment, a backslash (a URL parser reads it as a slash) and the ASCII tab, line feed and carriage
# return (a URL parser strips them, so '.<TAB>.' is a dot segment and 'api<TAB>-version' a second
# api-version). Written as Python escapes, so the rendered JSON holds \t, \n and \r, not raw characters.
LOCATION_REFUSED = contains_any(LOCATION, '#\\\t\n\r')
# §7.1: only an HTTPS management.azure.com Location on the selected async route, one operation segment,
# no dot segment, no fragment and exactly the selected API version, named once in any letter case. Any
# percent sign anywhere refuses the Location too: ADF has no decode function, so an encoded parameter
# name or segment cannot be inspected. LOCATION_REFUSED lists the other characters refused anywhere.
LOCATION_VALID = (
    f"and(and(or(startsWith({LOCATION}, concat(pipeline().parameters.asyncPrefix, "
    f"'containerappsjoboperationresults/')), startsWith({LOCATION}, concat(pipeline().parameters.asyncPrefix, "
    f"'containerappsjoboperationstatuses/'))), equals(length(split({LOCATION}, '?')), 2)), "
    f"and(and(equals(length(split({LOCATION_PATH}, '/')), add(length(split(pipeline().parameters.asyncPrefix, "
    f"'/')), 1)), not(or(endsWith({LOCATION_PATH}, '/'), or(contains({LOCATION_PATH}, '/.'), "
    f"contains({LOCATION}, '%'))))), and(not({LOCATION_REFUSED}), "
    f"and(contains(split({LOCATION_QUERY}, '&'), 'api-version=2026-07-01'), "
    f"equals(length(split(toLower({LOCATION_QUERY}), 'api-version')), 2)))))")


def retry_after(activity: str) -> str:
    """D-18: the 30 s poll base, or a longer Retry-After. An absent or unreadable header fails the read."""
    return (f"@string(max(pipeline().parameters.pollSeconds, int(activity('{activity}')"
            ".output.ADFWebActivityResponseHeaders['Retry-After'])))")


def execution_reference(activity: str) -> tuple[str, str]:
    """A response names an execution only when its id is exactly that name under this job."""
    output = f"activity('{activity}').output"
    name = f'{output}.name'
    valid = (f"and(and(not(empty({name})), equals(toLower({output}.id), toLower(concat(pipeline().parameters.jobPath, "
             f"'/executions/', {name})))), and(not(or(contains({name}, '/'), contains({name}, '?'))), "
             f"not(or(contains({name}, '#'), contains({name}, '%')))))")
    return valid, name


START_VALID, START_NAME = execution_reference('Start job')
LOCATED_VALID, LOCATED_NAME = execution_reference('Get operation')

START_BODY = {'containers': [{
    'name': '@pipeline().parameters.containerName',
    'image': '@pipeline().parameters.imageRef',
    'resources': '@pipeline().parameters.containerResources',
    'env': '@pipeline().parameters.containerEnv',
    'args': ("@createArray(pipeline().parameters.command, '--config-env', 'SEC_EDGAR_INGEST_CONFIG', "
             "'--run-id', pipeline().parameters.runId, '--attempt-id', concat('launch-', variables('launch')), "
             "'--deadline', concat(formatDateTime(addSeconds(variables('launchedAt'), "
             "pipeline().parameters.workerSeconds), 'yyyy-MM-ddTHH:mm:ss'), 'Z'))"),
}]}

# Each phase first sets the conservative next phase; a fault anywhere after it can only end in
# classification, never in another launch.
START = [
    assign('Start begins', 'nextPhase', 'classify'),
    assign('Count launch', 'nextLaunch', "@string(add(int(variables('launch')), 1))", after('Start begins')),
    assign('Set launch', 'launch', "@variables('nextLaunch')", after('Count launch')),
    assign('Clear outcome', 'outcome', '', after('Set launch')),
    assign('Clear execution name', 'executionName', '', after('Clear outcome')),
    assign('Clear location', 'location', '', after('Clear execution name')),
    assign('Clear state', 'state', '', after('Clear location')),
    assign('Clear image', 'image', '', after('Clear state')),
    assign('Clear result', 'result', '', after('Clear image')),
    assign('Set start wait', 'waitSeconds', '@string(pipeline().parameters.pollSeconds)', after('Clear result')),
    assign('Stamp launch', 'launchedAt', STAMP, after('Set start wait')),
    web('Start job', 'POST',
        "@concat('https://management.azure.com', pipeline().parameters.jobPath, '/start?api-version=2026-07-01')",
        ARM, after('Stamp launch'), headers={'Content-Type': 'application/json'}, body=START_BODY),
    assign('Read start wait', 'waitSeconds', retry_after('Start job'), after('Start job')),
    assign('Read start location', 'location', f"@if({LOCATION_VALID}, {LOCATION}, '')",
           after('Read start wait', 'Completed')),
    assign('Read start name', 'executionName', f"@if(and(empty(variables('location')), {START_VALID}), {START_NAME}, '')",
           after('Read start location', 'Completed')),
    assign('After start', 'nextPhase', "@if(not(empty(variables('executionName'))), 'observe', "
                                       "if(empty(variables('location')), 'classify', 'locate'))",
           after('Read start name', 'Completed')),
]

LOCATE = [
    assign('Locate begins', 'nextPhase', 'classify'),
    wait('Wait to locate', after('Locate begins')),
    assign('Reset locate wait', 'waitSeconds', RESET_WAIT, after('Wait to locate')),
    web('Get operation', 'GET', "@variables('location')", ARM, after('Reset locate wait')),
    assign('Read locate wait', 'waitSeconds', retry_after('Get operation'), after('Get operation')),
    assign('Read located name', 'executionName', f"@if({LOCATED_VALID}, {LOCATED_NAME}, '')",
           after('Read locate wait', 'Completed')),
    assign('After locate', 'nextPhase', f"@if(not(empty(variables('executionName'))), 'observe', "
                                        f"if({BEFORE_DEADLINE}, 'locate', 'classify'))",
           after('Wait to locate'), after('Read located name', 'Completed', 'Skipped')),
]

OBSERVE = [
    assign('Observe begins', 'nextPhase', 'classify'),
    wait('Wait to observe', after('Observe begins')),
    assign('Reset observe wait', 'waitSeconds', RESET_WAIT, after('Wait to observe')),
    web('Get execution', 'GET', "@concat('https://management.azure.com', pipeline().parameters.jobPath, "
                                "'/executions/', variables('executionName'), '?api-version=2026-07-01')",
        ARM, after('Reset observe wait')),
    assign('Read observe wait', 'waitSeconds', retry_after('Get execution'), after('Get execution')),
    assign('Read state', 'state', "@activity('Get execution').output.properties.status",
           after('Read observe wait', 'Completed')),
    assign('Read image', 'image', "@activity('Get execution').output.properties.template.containers[0].image",
           after('Read state', 'Completed')),
    assign('After observe', 'nextPhase',
           f"@if(or(equals({STATE}, 'Succeeded'), equals({STATE}, 'Failed')), 'read', "
           f"if(and(or(empty({STATE}), or(equals({STATE}, 'Running'), equals({STATE}, 'Processing'))), "
           f"{BEFORE_DEADLINE}), 'observe', 'classify'))",
           after('Wait to observe'), after('Read image', 'Completed', 'Skipped')),
]

READ = [
    assign('Read begins', 'nextPhase', 'classify'),
    web('Get result', 'GET', "@concat(pipeline().parameters.resultsUrl, pipeline().parameters.runId, '/', "
                             "pipeline().parameters.command, '/launch-', variables('launch'), '/result.json')",
        STORAGE, after('Read begins'), headers={'x-ms-version': '2026-04-06'}),
    assign('Keep result', 'result', "@string(activity('Get result').output)", after('Get result')),
]

# §7.3. The execution decides first; a result is read only when the execution allows it. Any fault
# leaves `outcome` empty (execution_unknown) or `resultOutcome` at its result_mismatch preset.
CLASSIFY = [
    assign('Classify begins', 'nextPhase', 'done'),
    assign('Classify execution', 'executionOutcome',
           f"@if(not(or(or(equals({STATE}, 'Succeeded'), equals({STATE}, 'Failed')), equals({STATE}, 'Stopped'))), "
           f"'execution_unknown', if(equals({STATE}, 'Stopped'), 'execution_stopped', "
           f"if(not(equals(variables('image'), pipeline().parameters.imageRef)), 'execution_mismatch', "
           f"if(empty(variables('result')), 'result_missing', ''))))",
           after('Classify begins')),
    assign('Preset result outcome', 'resultOutcome', 'result_mismatch', after('Classify execution')),
    assign('Classify result', 'resultOutcome',
           f"@if(and(and(and(equals({RESULT}.format_version, 'sec-workflow-result-v1'), "
           f"equals({RESULT}.context.run_id, pipeline().parameters.runId)), "
           f"and(equals({RESULT}.context.command, pipeline().parameters.command), "
           f"equals({RESULT}.context.attempt_id, concat('launch-', variables('launch'))))), "
           f"and(and(equals({RESULT}.context.execution_id, variables('executionName')), "
           f"equals({RESULT}.context.image_digest, pipeline().parameters.imageDigest)), "
           f"and(equals({RESULT}.context.config_sha256, pipeline().parameters.configSha256), "
           f"contains(variables('knownOutcomes'), {RESULT}.outcome)))), "
           f"if(contains(variables('exitZeroOutcomes'), {RESULT}.outcome), "
           f"if(equals({STATE}, 'Succeeded'), 'success', 'result_mismatch'), "
           f"if(contains(variables('staleOutcomes'), {RESULT}.outcome), 'stale', {RESULT}.outcome)), "
           f"'result_mismatch')",
           after('Preset result outcome')),
    assign('Classify outcome', 'outcome', "@if(empty(variables('executionOutcome')), variables('resultOutcome'), "
                                          "variables('executionOutcome'))",
           after('Classify result', 'Completed')),
    assign('Mark classified', 'classified', "@variables('launch')", after('Classify outcome')),
    assign('Classify next', 'nextPhase', "@if(and(equals(variables('outcome'), 'pending'), "
                                         "less(int(variables('launch')), pipeline().parameters.maxLaunches)), "
                                         "'start', 'done')",
           after('Mark classified')),
]

# A launch starts only from 'start', within the cap, and only once the previous launch is classified.
PHASE = ("@if(and(equals(variables('phase'), 'start'), or(greaterOrEquals(int(variables('launch')), "
         "pipeline().parameters.maxLaunches), not(equals(variables('launch'), variables('classified'))))), "
         "'refuse', variables('phase'))")
OUTCOME_CODE = "if(empty(variables('outcome')), 'execution_unknown', variables('outcome'))"
STRING_VARIABLES = (('phase', 'start'), ('nextPhase', ''), ('launch', '0'), ('nextLaunch', '0'), ('classified', '0'),
                    ('launchedAt', ''), ('executionName', ''), ('location', ''), ('state', ''), ('image', ''),
                    ('waitSeconds', ''), ('result', ''), ('executionOutcome', ''), ('resultOutcome', ''),
                    ('outcome', ''))


def run_worker() -> dict:
    """pl-sec-edgar-run-worker without its parameters, which main.bicep declares with their defaults."""
    phases = {'name': 'Launch phase', 'type': 'Switch', 'typeProperties': {
        'on': expression(PHASE),
        'cases': [{'value': 'start', 'activities': START}, {'value': 'locate', 'activities': LOCATE},
                  {'value': 'observe', 'activities': OBSERVE}, {'value': 'read', 'activities': READ},
                  {'value': 'classify', 'activities': CLASSIFY}],
        'defaultActivities': [assign('Stop launches', 'nextPhase', 'done')]}}
    return {
        'activities': [
            {'name': 'Run launches', 'type': 'Until', 'typeProperties': {
                'expression': expression("@equals(variables('phase'), 'done')"),
                'timeout': '0.03:00:00',
                'activities': [phases, assign('Advance', 'phase', "@variables('nextPhase')",
                                              after('Launch phase', 'Completed'))]}},
            {'name': 'Check outcome', 'type': 'IfCondition', 'dependsOn': [after('Run launches', 'Completed')],
             'typeProperties': {
                 'expression': expression("@equals(variables('outcome'), 'success')"),
                 'ifTrueActivities': [],
                 # The message names the result to read: results/runs/sec/<runId>/<command>/launch-<n>/result.json.
                 'ifFalseActivities': [{'name': 'Fail run', 'type': 'Fail', 'typeProperties': {
                     'message': expression(f"@concat('pl-sec-edgar-run-worker ', pipeline().parameters.command, "
                                           f"' run ', pipeline().parameters.runId, ' launch-', variables('launch'), "
                                           f"' ended ', {OUTCOME_CODE})"),
                     'errorCode': expression(f'@{OUTCOME_CODE}')}}]}},
        ],
        'variables': {
            **{name: {'type': 'String', 'defaultValue': default} for name, default in STRING_VARIABLES},
            'knownOutcomes': {'type': 'Array', 'defaultValue': list(EXIT_CODES)},
            'exitZeroOutcomes': {'type': 'Array', 'defaultValue': [name for name, code in EXIT_CODES.items() if code == 0]},
            'staleOutcomes': {'type': 'Array', 'defaultValue': [name for name, code in EXIT_CODES.items() if code == 11]},
        },
    }


def caller(command: str) -> dict:
    return {'activities': [{'name': 'Run worker', 'type': 'ExecutePipeline', 'typeProperties': {
        'pipeline': {'referenceName': 'pl-sec-edgar-run-worker', 'type': 'PipelineReference'},
        'waitOnCompletion': True,
        'parameters': {'command': command, 'runId': expression('@pipeline().RunId')}}}]}


def definitions() -> dict[str, dict]:
    return {'pl-sec-edgar-run-worker': run_worker(), **{f'pl-sec-edgar-{command}': caller(command) for command in COMMANDS}}


def rendered(definition: dict) -> str:
    return json.dumps(definition, indent=2) + '\n'


def main() -> None:
    for name, definition in definitions().items():
        (HERE / f'{name}.json').write_text(rendered(definition))


if __name__ == '__main__':
    main()
