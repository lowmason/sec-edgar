"""A deliberately strict interpreter for the subset of Azure Data Factory that the Stage 6 pipelines use.

It runs the committed pipeline JSON itself, not a restatement of it. Behaviour the ADF documentation leaves
open is a `Semantics` parameter, and the scenarios must reach the same outcome under every combination. A
function, activity type or property outside the subset raises `AdfUnsupported`, so the tests fail instead of
guessing.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from itertools import product
from typing import Callable

ACTIVITY_TYPES = frozenset({'WebActivity', 'Until', 'Wait', 'IfCondition', 'Switch', 'SetVariable',
                            'ExecutePipeline', 'Fail'})
CONTAINERS = {'Until': ('activities',), 'IfCondition': ('ifTrueActivities', 'ifFalseActivities'),
              'Switch': ('defaultActivities',)}
CONDITIONS = frozenset({'Succeeded', 'Failed', 'Skipped', 'Completed'})
VARIABLE_TYPES = {'String': str, 'Bool': bool, 'Array': list}
# Documented ADF limits: activities per pipeline (inner activities included), characters per expression,
# bytes per pipeline object, and cases per Switch.
MAX_ACTIVITIES = 120
MAX_EXPRESSION = 8_192
MAX_PIPELINE_BYTES = 200 * 1024
MAX_CASES = 25


class AdfUnsupported(Exception):
    """The definition uses something outside the modelled subset."""


class ExpressionError(Exception):
    """An expression fails at run time, which fails its activity."""


class WebFailure(Exception):
    """No usable HTTP response: a transport error, a status of 400 or more, or a body that is not a JSON object."""


class _Timeout(Exception):
    pass


@dataclass(frozen=True)
class Semantics:
    missing: str = 'throw'           # a missing property or index: 'throw' fails the activity, 'null' yields null
    lazy: bool = True                # if, and, or evaluate only the arguments they need
    equals_ignores_case: bool = False


ALL_SEMANTICS = tuple(Semantics(missing, lazy, folded)
                      for missing, lazy, folded in product(('throw', 'null'), (True, False), (False, True)))


# ---------------------------------------------------------------- expressions

_TOKEN = re.compile(r"\s*(?:(?P<string>'(?:[^']|'')*')|(?P<number>-?\d+)|(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
                    r"|(?P<punct>[(),.\[\]}]))")


def _tokens(text: str, start: int):
    position = start
    while True:
        match = _TOKEN.match(text, position)
        if match is None:
            rest = text[position:].strip()
            if rest:
                raise AdfUnsupported(f'cannot tokenize expression at {text[position:position + 20]!r}')
            yield ('end', None, len(text))
            return
        kind = match.lastgroup
        value = match.group(kind)
        yield (kind, value, match.end())
        if kind == 'punct' and value == '}':
            return
        position = match.end()


class _Parser:
    def __init__(self, text: str, start: int = 0):
        self.text = text
        self.stream = _tokens(text, start)
        self.current = next(self.stream)

    def take(self, kind=None, value=None):
        token = self.current
        if (kind and token[0] != kind) or (value and token[1] != value):
            raise AdfUnsupported(f'unexpected token {token[1]!r} in {self.text!r}')
        if token[0] != 'end' and token[1] != '}':
            self.current = next(self.stream)
        return token

    def expression(self):
        kind, value, _ = self.take()
        if kind == 'string':
            node = ('literal', value[1:-1].replace("''", "'"))
        elif kind == 'number':
            node = ('literal', int(value))
        elif kind == 'name':
            if self.current[1] != '(':
                raise AdfUnsupported(f'bare identifier {value!r} is outside the subset')
            self.take(value='(')
            arguments = []
            if self.current[1] != ')':
                arguments.append(self.expression())
                while self.current[1] == ',':
                    self.take(value=',')
                    arguments.append(self.expression())
            self.take(value=')')
            node = ('call', value, arguments)
        else:
            raise AdfUnsupported(f'unexpected token {value!r} in {self.text!r}')
        while self.current[1] in ('.', '['):
            if self.take()[1] == '.':
                node = ('property', node, self.take('name')[1])
            else:
                node = ('index', node, self.expression())
                self.take(value=']')
        return node


def parse(text: str):
    """Parse the body of an `@` expression."""
    parser = _Parser(text)
    node = parser.expression()
    if parser.current[0] != 'end':
        raise AdfUnsupported(f'trailing text in {text!r}')
    return node


def _segments(text: str):
    """A JSON string as ('literal', text) and ('expression', node, interpolated) segments."""
    if text.startswith('@@'):
        return [('literal', text[1:])]
    if text.startswith('@') and not text.startswith('@{'):
        return [('expression', parse(text[1:]), False)]
    segments, position = [], 0
    while (start := text.find('@{', position)) >= 0:
        segments.append(('literal', text[position:start]))
        parser = _Parser(text, start + 2)
        node = parser.expression()
        if parser.current[1] != '}':
            raise AdfUnsupported(f'unterminated interpolation in {text!r}')
        segments.append(('expression', node, True))
        position = parser.current[2]
    segments.append(('literal', text[position:]))
    return segments


def functions_used(node) -> set[str]:
    if node[0] == 'literal':
        return set()
    if node[0] == 'call':
        return {node[1]}.union(*(functions_used(argument) for argument in node[2]))
    return functions_used(node[1]) | (functions_used(node[2]) if node[0] == 'index' else set())


def _o_format(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f') + '0Z'


def _timestamp(value) -> datetime:
    if not isinstance(value, str):
        raise ExpressionError('timestamp must be a string')
    try:
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ExpressionError(str(error)) from None
    if moment.tzinfo is None:
        raise ExpressionError('timestamp must carry a zone')
    return moment


def _text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool) or value is None:
        raise ExpressionError(f'no modelled string form for {value!r}')
    if isinstance(value, int):
        return str(value)
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False)


def _require(value, kind, name):
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ExpressionError(f'{name} received {value!r}')
    return value


def _integer(value):
    if isinstance(value, str) and re.fullmatch(r'-?\d+', value):
        return int(value)
    return _require(value, int, 'int')


def _parse_json(value):
    if value is None:
        return {}
    try:
        return json.loads(_require(value, str, 'json'))
    except json.JSONDecodeError as error:
        raise ExpressionError(str(error)) from None


def _contains(collection, item):
    if isinstance(collection, str):
        return _require(item, str, 'contains') in collection
    if isinstance(collection, (list, dict)):
        return item in collection
    raise ExpressionError('contains needs a string, array or object')


def _length(value):
    return len(_require(value, (str, list), 'length'))


def _format(value, pattern):
    if pattern != 'yyyy-MM-ddTHH:mm:ss':
        raise AdfUnsupported(f'unmodelled format {pattern!r}')
    return _timestamp(value).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')


def _split(text, separator):
    if not _require(separator, str, 'split'):
        raise ExpressionError('split needs a separator')
    return _require(text, str, 'split').split(separator)


def _ticks(value):
    delta = _timestamp(value) - datetime(1, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86_400 + delta.seconds) * 10_000_000 + delta.microseconds * 10


def _folded(name):
    return lambda text, affix: getattr(_require(text, str, name).casefold(), name.lower())(
        _require(affix, str, name).casefold())


# Functions whose result depends only on their arguments. ADF documents startsWith and endsWith as
# case-insensitive and contains as case-sensitive; utcNow and addSeconds return the 'o' format.
PURE = {
    'concat': lambda *values: ''.join(_require(value, str, 'concat') for value in values),
    'not': lambda value: not _require(value, bool, 'not'),
    'add': lambda left, right: _require(left, int, 'add') + _require(right, int, 'add'),
    'max': lambda left, right: max(_require(left, int, 'max'), _require(right, int, 'max')),
    'less': lambda left, right: _require(left, int, 'less') < _require(right, int, 'less'),
    'greaterOrEquals': lambda left, right: _require(left, int, 'greaterOrEquals') >= _require(right, int, 'greaterOrEquals'),
    'string': _text,
    'int': _integer,
    'json': _parse_json,
    'contains': _contains,
    'coalesce': lambda *values: next((value for value in values if value is not None), None),
    'createArray': lambda *values: list(values),
    'addSeconds': lambda value, seconds: _o_format(_timestamp(value) + timedelta(seconds=_require(seconds, int, 'addSeconds'))),
    'ticks': _ticks,
    'startsWith': _folded('startsWith'),
    'endsWith': _folded('endsWith'),
    'toLower': lambda text: _require(text, str, 'toLower').lower(),
    'empty': lambda value: value is None or (isinstance(value, (str, list, dict)) and not value),
    'formatDateTime': _format,
    'split': _split,
    'length': _length,
}
# name -> (minimum, maximum) arity; None means unbounded
ARITY = {'concat': (1, None), 'equals': (2, 2), 'and': (2, 2), 'or': (2, 2), 'not': (1, 1), 'if': (3, 3),
         'add': (2, 2), 'max': (2, 2), 'less': (2, 2), 'greaterOrEquals': (2, 2), 'string': (1, 1),
         'int': (1, 1), 'json': (1, 1), 'contains': (2, 2), 'coalesce': (1, None), 'createArray': (2, None),
         'utcNow': (0, 0), 'addSeconds': (2, 2), 'ticks': (1, 1), 'startsWith': (2, 2), 'endsWith': (2, 2),
         'toLower': (1, 1), 'empty': (1, 1), 'formatDateTime': (2, 2), 'split': (2, 2), 'length': (1, 1),
         'variables': (1, 1), 'pipeline': (0, 0), 'activity': (1, 1)}
FUNCTIONS = frozenset(ARITY)


class Evaluator:
    def __init__(self, run: 'PipelineRun', scope: 'Scope'):
        self.run, self.scope, self.semantics = run, scope, run.semantics

    def value(self, value):
        """Evaluate a JSON value from an activity definition."""
        if isinstance(value, dict):
            if set(value) == {'value', 'type'} and value['type'] == 'Expression':
                return self.string(_require(value['value'], str, 'Expression value'))
            return {key: self.value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.value(item) for item in value]
        if isinstance(value, str):
            return self.string(value)
        return value

    def string(self, text: str):
        segments = _segments(text)
        if len(segments) == 1 and segments[0][0] == 'expression' and not segments[0][2]:
            return self.node(segments[0][1])
        if len(segments) == 1:
            return segments[0][1]
        return ''.join(item[1] if item[0] == 'literal' else _text(self.node(item[1])) for item in segments)

    def missing(self, what):
        if self.semantics.missing == 'throw':
            raise ExpressionError(f'missing {what}')
        return None

    def node(self, node):
        kind = node[0]
        if kind == 'literal':
            return node[1]
        if kind == 'property':
            base = self.node(node[1])
            if base is None:
                return self.missing(node[2])
            if not isinstance(base, dict):
                raise ExpressionError(f'property {node[2]!r} of a non-object')
            return base[node[2]] if node[2] in base else self.missing(node[2])
        if kind == 'index':
            base, key = self.node(node[1]), self.node(node[2])
            if base is None:
                return self.missing(key)
            if isinstance(base, list) and isinstance(key, int) and not isinstance(key, bool):
                return base[key] if 0 <= key < len(base) else self.missing(key)
            if isinstance(base, dict) and isinstance(key, str):
                return base[key] if key in base else self.missing(key)
            raise ExpressionError(f'cannot index {type(base).__name__} by {key!r}')
        return self.call(node[1], node[2])

    def call(self, name, arguments):
        if name not in ARITY:
            raise AdfUnsupported(f'function {name!r} is outside the subset')
        low, high = ARITY[name]
        if len(arguments) < low or (high is not None and len(arguments) > high):
            raise AdfUnsupported(f'{name} called with {len(arguments)} arguments')
        lazy = self.semantics.lazy
        if name == 'if':
            condition = _require(self.node(arguments[0]), bool, 'if')
            if lazy:
                return self.node(arguments[1] if condition else arguments[2])
            chosen, other = (arguments[1], arguments[2]) if condition else (arguments[2], arguments[1])
            self.node(other)
            return self.node(chosen)
        if name in ('and', 'or'):
            first = _require(self.node(arguments[0]), bool, name)
            if lazy and first == (name == 'or'):
                return first
            second = _require(self.node(arguments[1]), bool, name)
            return (first and second) if name == 'and' else (first or second)
        values = [self.node(argument) for argument in arguments]
        return PURE[name](*values) if name in PURE else getattr(self, '_' + name)(*values)

    def _equals(self, left, right):
        if isinstance(left, str) and isinstance(right, str) and self.semantics.equals_ignores_case:
            return left.casefold() == right.casefold()
        return isinstance(left, bool) == isinstance(right, bool) and left == right

    def _utcNow(self):
        return _o_format(self.run.clock)

    def _variables(self, name):
        if name not in self.run.variables:
            raise AdfUnsupported(f'undeclared variable {name!r}')
        return self.run.variables[name]

    def _pipeline(self):
        return {'parameters': self.run.parameters, 'RunId': self.run.run_id}

    def _activity(self, name):
        record = self.scope.lookup(name)
        if record is None:
            raise ExpressionError(f'activity {name!r} has not run in scope')
        return {'output': record['output']}


# ---------------------------------------------------------------- static checks

def walk_activities(activities, depth=()):
    """Every activity with the chain of container types above it."""
    for activity in activities:
        yield activity, depth
        for child_list in children(activity):
            yield from walk_activities(child_list, depth + (activity['type'],))


def children(activity):
    properties = activity.get('typeProperties', {})
    lists = [properties.get(key, []) for key in CONTAINERS.get(activity['type'], ())]
    if activity['type'] == 'Switch':
        lists.extend(case['activities'] for case in properties.get('cases', []))
    return lists


def expressions(activity):
    """(text, node) for every expression in an activity's own properties."""
    found = []

    def visit(value, key=None):
        if key in ('activities', 'ifTrueActivities', 'ifFalseActivities', 'defaultActivities'):
            return
        if isinstance(value, dict):
            if key == 'cases' or (activity['type'] == 'Switch' and set(value) == {'value', 'activities'}):
                return
            for name, item in value.items():
                visit(item, name)
        elif isinstance(value, list):
            for item in value:
                visit(item, key)
        elif isinstance(value, str):
            for segment in _segments(value):
                if segment[0] == 'expression':
                    found.append((value, segment[1]))

    visit(activity.get('typeProperties', {}))
    return found


def validate_pipeline(definition) -> None:
    """Raise AdfUnsupported where the definition leaves the subset or breaks a documented ADF rule."""
    activities = definition['activities']
    variables = definition.get('variables', {})
    for name, declaration in variables.items():
        if declaration.get('type') not in VARIABLE_TYPES:
            raise AdfUnsupported(f'variable {name!r} has an unsupported type')
    seen = set()
    total = 0
    for activity, depth in walk_activities(activities):
        total += 1
        name, kind = activity['name'], activity['type']
        if name in seen:
            raise AdfUnsupported(f'duplicate activity name {name!r}')
        seen.add(name)
        if kind not in ACTIVITY_TYPES:
            raise AdfUnsupported(f'activity type {kind!r} is outside the subset')
        if kind in ('IfCondition', 'Switch') and any(outer in ('IfCondition', 'Switch') for outer in depth):
            raise AdfUnsupported(f'{name!r}: If/Switch cannot nest inside If/Switch')
        if kind == 'Until' and 'Until' in depth:
            raise AdfUnsupported(f'{name!r}: Until allows one level of nesting')
        if kind == 'Switch':
            properties = activity['typeProperties']
            cases = properties.get('cases', [])
            if 'on' not in properties or not cases or len(cases) > MAX_CASES or 'defaultActivities' not in properties:
                raise AdfUnsupported(f'{name!r}: a Switch needs on, 1-25 cases and default activities')
            values = [case['value'] for case in cases]
            if len(set(values)) != len(values) or not all(isinstance(value, str) for value in values):
                raise AdfUnsupported(f'{name!r}: case values must be distinct strings')
        for text, node in expressions(activity):
            if len(text) > MAX_EXPRESSION:
                raise AdfUnsupported(f'{name!r} has an expression of {len(text)} characters')
            unknown = functions_used(node) - FUNCTIONS
            if unknown:
                raise AdfUnsupported(f'{name!r} uses {sorted(unknown)} in {text!r}')
            for found in re.findall(r"variables\('([^']*)'\)", text):
                if found not in variables:
                    raise AdfUnsupported(f'{name!r} reads undeclared variable {found!r}')
        if kind == 'SetVariable':
            target = activity['typeProperties']['variableName']
            if target not in variables:
                raise AdfUnsupported(f'{name!r} sets undeclared variable {target!r}')
            if f"variables('{target}')" in json.dumps(activity['typeProperties']['value']):
                raise AdfUnsupported(f'{name!r}: a Set Variable cannot reference its own variable')
    if total > MAX_ACTIVITIES:
        raise AdfUnsupported(f'{total} activities exceed the ADF limit of {MAX_ACTIVITIES}')
    if len(json.dumps(definition, separators=(',', ':')).encode()) > MAX_PIPELINE_BYTES:
        raise AdfUnsupported('the pipeline object exceeds the ADF limit of 200 KB')
    for container in [activities] + [child for activity, _ in walk_activities(activities)
                                     for child in children(activity)]:
        names = {activity['name'] for activity in container}
        outgoing: dict[str, set[str]] = {}
        for activity in container:
            for dependency in activity.get('dependsOn', []):
                source, conditions = dependency['activity'], set(dependency['dependencyConditions'])
                if source not in names:
                    raise AdfUnsupported(f"{activity['name']!r} depends on {source!r} outside its container")
                if not conditions or not conditions <= CONDITIONS:
                    raise AdfUnsupported(f"{activity['name']!r} has dependency conditions {sorted(conditions)}")
                outgoing.setdefault(source, set()).update(conditions)
        for source, conditions in outgoing.items():
            if 'Completed' in conditions and conditions & {'Succeeded', 'Failed'}:
                raise AdfUnsupported(f'{source!r}: an Upon Completion path cannot coexist with Success or Failure')


# ---------------------------------------------------------------- execution

@dataclass
class Request:
    method: str
    url: str
    headers: dict
    body: object
    resource: str | None
    at: datetime


@dataclass
class Response:
    status: int = 200
    body: object = field(default_factory=dict)
    headers: dict = field(default_factory=dict)


class Scope:
    def __init__(self, parent: 'Scope | None' = None):
        self.parent, self.records = parent, {}

    def lookup(self, name):
        scope = self
        while scope is not None:
            if name in scope.records:
                return scope.records[name]
            scope = scope.parent
        return None


def _timespan(text: str) -> timedelta:
    match = re.fullmatch(r'(?:(\d+)\.)?(\d{2}):(\d{2}):(\d{2})', text)
    if match is None:
        raise AdfUnsupported(f'timespan {text!r} is not d.hh:mm:ss')
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


@dataclass
class Outcome:
    status: str
    failures: list
    variables: dict
    run_id: str


class PipelineRun:
    def __init__(self, pipelines: dict, web: Callable[[Request], Response], semantics: Semantics = Semantics(),
                 faults: frozenset = frozenset(), start: datetime = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc),
                 max_iterations: int = 20_000):
        self.pipelines, self.web, self.semantics, self.faults = pipelines, web, semantics, frozenset(faults)
        self.clock, self.max_iterations, self.iterations = start, max_iterations, 0
        self.requests: list[Request] = []
        self.trace: list[tuple[str, str, object]] = []
        self.failures: list[dict] = []
        self.deadline: datetime | None = None
        self.runs = 0
        self.parameters: dict = {}
        self.variables: dict = {}
        self.declarations: dict = {}
        self.run_id = ''

    def run(self, name: str, parameters: dict) -> Outcome:
        definition = self.pipelines[name]
        declared = definition.get('parameters', {})
        if set(parameters) - set(declared):
            raise AdfUnsupported(f'undeclared parameters {sorted(set(parameters) - set(declared))}')
        values = {}
        for key, declaration in declared.items():
            if key in parameters:
                values[key] = parameters[key]
            elif 'defaultValue' in declaration:
                values[key] = declaration['defaultValue']
            else:
                raise AdfUnsupported(f'parameter {key!r} has no value')
        saved = (self.parameters, self.variables, self.declarations, self.run_id)
        self.runs += 1
        self.parameters = values
        self.declarations = definition.get('variables', {})
        self.variables = {key: declaration.get('defaultValue', [] if declaration['type'] == 'Array' else '')
                          for key, declaration in self.declarations.items()}
        self.run_id = f'00000000-0000-4000-8000-{self.runs:012d}'
        failures_before = len(self.failures)
        try:
            status = self.container(definition['activities'], Scope())
            return Outcome(status, self.failures[failures_before:], dict(self.variables), self.run_id)
        finally:
            self.parameters, self.variables, self.declarations, self.run_id = saved

    def container(self, activities, scope: Scope) -> str:
        statuses: dict[str, str] = {}
        pending = list(activities)
        while pending:
            for activity in pending:
                dependencies = activity.get('dependsOn', [])
                if all(item['activity'] in statuses for item in dependencies):
                    break
            else:
                raise AdfUnsupported('dependency cycle or unknown dependency')
            pending.remove(activity)
            if all(self.met(statuses[item['activity']], item['dependencyConditions']) for item in dependencies):
                statuses[activity['name']] = self.activity(activity, scope)
            else:
                statuses[activity['name']] = 'Skipped'
                self.trace.append((activity['name'], 'Skipped', None))
        return self.leaf_status(activities, statuses)

    @staticmethod
    def met(status, conditions):
        return any(condition == status or (condition == 'Completed' and status in ('Succeeded', 'Failed'))
                   for condition in conditions)

    @staticmethod
    def leaf_status(activities, statuses) -> str:
        """Pipeline result is success iff every evaluated leaf succeeds; a skipped leaf defers to its parents."""
        parents = {activity['name']: [item['activity'] for item in activity.get('dependsOn', [])]
                   for activity in activities}
        dependents = {source for names in parents.values() for source in names}
        evaluated, frontier = set(), [name for name in parents if name not in dependents]
        while frontier:
            name = frontier.pop()
            if statuses[name] == 'Skipped':
                frontier.extend(parents[name])
            else:
                evaluated.add(name)
        return 'Succeeded' if all(statuses[name] == 'Succeeded' for name in evaluated) else 'Failed'

    def tick(self, seconds: int = 1):
        if self.deadline is not None and self.clock + timedelta(seconds=seconds) > self.deadline:
            self.clock = self.deadline
            raise _Timeout()
        self.clock += timedelta(seconds=seconds)

    def activity(self, activity, scope: Scope) -> str:
        self.tick()
        name, kind = activity['name'], activity['type']
        output = None
        if name in self.faults:
            status = 'Failed'
        else:
            try:
                status, output = getattr(self, '_' + kind)(activity, scope)
            except (ExpressionError, WebFailure) as error:
                status, output = 'Failed', {'error': str(error)}
        scope.records[name] = {'status': status, 'output': output}
        self.trace.append((name, status, output))
        return status

    def evaluator(self, scope):
        return Evaluator(self, scope)

    def _SetVariable(self, activity, scope):
        properties = activity['typeProperties']
        name = properties['variableName']
        value = self.evaluator(scope).value(properties['value'])
        kind = VARIABLE_TYPES[self.declarations[name]['type']]
        if not isinstance(value, kind):
            raise ExpressionError(f'{name} is {kind.__name__}, not {value!r}')
        self.variables[name] = value
        return 'Succeeded', {'name': name, 'value': value}

    def _Wait(self, activity, scope):
        seconds = self.evaluator(scope).value(activity['typeProperties']['waitTimeInSeconds'])
        if not isinstance(seconds, int) or isinstance(seconds, bool) or seconds < 0:
            raise ExpressionError(f'wait of {seconds!r}')
        self.tick(seconds)
        return 'Succeeded', {}

    def _WebActivity(self, activity, scope):
        properties = activity['typeProperties']
        evaluate = self.evaluator(scope).value
        authentication = evaluate(properties.get('authentication', {}))
        request = Request(method=evaluate(properties['method']), url=evaluate(properties['url']),
                          headers=evaluate(properties.get('headers', {})),
                          body=evaluate(properties['body']) if 'body' in properties else None,
                          resource=authentication.get('resource') if authentication.get('type') == 'MSI' else None,
                          at=self.clock)
        self.requests.append(request)
        response = self.web(request)
        if response.status >= 400 or not isinstance(response.body, dict):
            raise WebFailure(f'{request.method} {request.url} gave {response.status}')
        return 'Succeeded', {**response.body, 'ADFWebActivityResponseHeaders': dict(response.headers)}

    def _Fail(self, activity, scope):
        evaluate = self.evaluator(scope).value
        properties = activity['typeProperties']
        code, message = evaluate(properties['errorCode']), evaluate(properties['message'])
        if not isinstance(code, str) or not code:
            code = 'ErrorCodeNotString'
        self.failures.append({'activity': activity['name'], 'errorCode': code, 'message': message})
        return 'Failed', {'errorCode': code, 'message': message}

    def _IfCondition(self, activity, scope):
        properties = activity['typeProperties']
        condition = self.evaluator(scope).value(properties['expression'])
        if not isinstance(condition, bool):
            raise ExpressionError('If needs a boolean')
        chosen = properties.get('ifTrueActivities' if condition else 'ifFalseActivities', [])
        return self.container(chosen, Scope(scope)), {}

    def _Switch(self, activity, scope):
        properties = activity['typeProperties']
        value = self.evaluator(scope).value(properties['on'])
        if not isinstance(value, str):
            raise ExpressionError('Switch needs a string')
        chosen = next((case['activities'] for case in properties['cases'] if case['value'] == value),
                      properties['defaultActivities'])
        return self.container(chosen, Scope(scope)), {}

    def _Until(self, activity, scope):
        properties = activity['typeProperties']
        outer = self.deadline
        own = self.clock + _timespan(properties.get('timeout', '7.00:00:00'))
        self.deadline = own if outer is None else min(outer, own)
        try:
            while True:
                self.iterations += 1
                if self.iterations > self.max_iterations:
                    raise AdfUnsupported('Until did not terminate within the iteration cap')
                status = self.container(properties['activities'], Scope(scope))
                done = self.evaluator(scope).value(properties['expression'])
                if not isinstance(done, bool):
                    raise ExpressionError('Until needs a boolean')
                if done:
                    return status, {}
        except _Timeout:
            if outer is not None and self.clock >= outer:
                raise
            return 'Failed', {'error': 'Until timed out'}
        finally:
            self.deadline = outer

    def _ExecutePipeline(self, activity, scope):
        properties = activity['typeProperties']
        if properties.get('waitOnCompletion') is not True:
            raise AdfUnsupported('only waitOnCompletion true is modelled')
        parameters = self.evaluator(scope).value(properties.get('parameters', {}))
        child = self.run(properties['pipeline']['referenceName'], parameters)
        return child.status, {'pipelineRunId': child.run_id}
