"""The ADF interpreter models only what the documentation states, and refuses everything else."""
from network_guard import install
install()

import unittest

from adf_interpreter import (ALL_SEMANTICS, AdfUnsupported, Evaluator, ExpressionError, PipelineRun, Response, Scope,
                             Semantics, validate_pipeline)


def evaluate(text, semantics=Semantics(), variables=None, parameters=None):
    run = PipelineRun({}, lambda request: Response(), semantics)
    run.variables, run.parameters = dict(variables or {}), dict(parameters or {})
    return Evaluator(run, Scope()).value(text)


def expression(text):
    return {'value': text, 'type': 'Expression'}


def setv(name, variable, value, *depends):
    return {'name': name, 'type': 'SetVariable', 'dependsOn': [{'activity': source, 'dependencyConditions': conditions}
                                                               for source, conditions in depends],
            'typeProperties': {'variableName': variable, 'value': value}}


def fail(name, *depends):
    return {'name': name, 'type': 'Fail', 'dependsOn': [{'activity': source, 'dependencyConditions': conditions}
                                                        for source, conditions in depends],
            'typeProperties': {'message': 'failed', 'errorCode': expression("@variables('code')")}}


def run(activities, variables=('code', 'mark'), faults=(), semantics=Semantics()):
    definition = {'activities': activities, 'variables': {name: {'type': 'String'} for name in variables}}
    validate_pipeline(definition)
    engine = PipelineRun({'p': definition}, lambda request: Response(), semantics, frozenset(faults))
    return engine.run('p', {}), engine


class ExpressionTests(unittest.TestCase):
    def test_literals_escapes_and_interpolation(self):
        self.assertEqual(evaluate("@concat('it''s', ' ', string(42))"), "it's 42")
        self.assertEqual(evaluate('@@not-an-expression'), '@not-an-expression')
        self.assertEqual(evaluate("plain"), 'plain')
        self.assertEqual(evaluate("a-@{variables('x')}-@{createArray(1, 2)}", variables={'x': 'b'}), 'a-b-[1,2]')
        self.assertEqual(evaluate("@createArray('a', variables('x'))", variables={'x': 'b'}), ['a', 'b'])
        self.assertEqual(evaluate({'nested': ["@variables('x')"], 'n': 1}, variables={'x': 'b'}), {'nested': ['b'], 'n': 1})

    def test_accessors_and_missing_values(self):
        value = {'a': {'b': [{'c': 'd'}]}}
        self.assertEqual(evaluate("@pipeline().parameters.v.a.b[0].c", parameters={'v': value}), 'd')
        self.assertEqual(evaluate("@pipeline().parameters.v['a']['b'][0]['c']", parameters={'v': value}), 'd')
        with self.assertRaises(ExpressionError):
            evaluate("@pipeline().parameters.v.a.missing", parameters={'v': value})
        self.assertIsNone(evaluate("@pipeline().parameters.v.a.missing.deeper", Semantics('null'),
                                   parameters={'v': value}))
        self.assertIsNone(evaluate("@pipeline().parameters.v.a.b[3]", Semantics('null'), parameters={'v': value}))
        with self.assertRaises(ExpressionError):
            evaluate("@pipeline().parameters.v.a.b.c", Semantics('null'), parameters={'v': value})

    def test_undocumented_behaviour_is_a_semantics_choice(self):
        failing = "@if(equals(1, 1), 'chosen', int('x'))"
        self.assertEqual(evaluate(failing, Semantics(lazy=True)), 'chosen')
        with self.assertRaises(ExpressionError):
            evaluate(failing, Semantics(lazy=False))
        self.assertEqual(evaluate("@or(equals(1, 1), int('x'))", Semantics(lazy=True)), True)
        with self.assertRaises(ExpressionError):
            evaluate("@or(equals(1, 1), equals(int('x'), 1))", Semantics(lazy=False))
        self.assertFalse(evaluate("@equals('Succeeded', 'succeeded')", Semantics(equals_ignores_case=False)))
        self.assertTrue(evaluate("@equals('Succeeded', 'succeeded')", Semantics(equals_ignores_case=True)))
        self.assertEqual(len(ALL_SEMANTICS), 8)

    def test_documented_case_rules(self):
        self.assertTrue(evaluate("@startsWith('HTTPS://Management.azure.com/x', 'https://management.azure.com/')"))
        self.assertTrue(evaluate("@endsWith('a/B', '/b')"))
        self.assertFalse(evaluate("@contains('Microsoft.App', 'microsoft.app')"))
        self.assertTrue(evaluate("@contains(createArray('a', 'b'), 'b')"))
        self.assertFalse(evaluate("@contains(createArray('a', 'b'), 'B')"))

    def test_time_functions_use_the_o_format(self):
        moment = evaluate("@addSeconds('2026-10-12T09:00:00.0000000Z', 3300)")
        self.assertEqual(moment, '2026-10-12T09:55:00.0000000Z')
        self.assertEqual(evaluate(f"@formatDateTime('{moment}', 'yyyy-MM-ddTHH:mm:ss')"), '2026-10-12T09:55:00')
        self.assertEqual(evaluate("@ticks('0001-01-01T00:00:01Z')"), 10_000_000)
        self.assertLess(evaluate("@ticks('2026-10-12T09:00:00Z')"), evaluate(f"@ticks('{moment}')"))
        with self.assertRaises(AdfUnsupported):
            evaluate("@formatDateTime('2026-10-12T09:00:00Z', 'o')")

    def test_conversions_are_strict(self):
        self.assertEqual(evaluate("@int('42')"), 42)
        self.assertEqual(evaluate("@string(json('{\"a\":[1]}'))"), '{"a":[1]}')
        for text in ("@int('4.2')", "@json('not json')", "@concat('a', 1)", "@string(equals(1, 1))", "@not('true')"):
            with self.subTest(text), self.assertRaises(ExpressionError):
                evaluate(text)

    def test_anything_outside_the_subset_is_refused(self):
        for text in ("@utcnow()", "@union(createArray(1, 2), createArray(3, 4))", "@createArray('one')",
                     "@and(true, false)", "@body('x')?.y", "@or(equals(1, 1), equals(1, 1), equals(1, 1))",
                     "@variables('undeclared')"):
            with self.subTest(text), self.assertRaises(AdfUnsupported):
                evaluate(text)


class ActivityTests(unittest.TestCase):
    def test_dependency_conditions_and_skips(self):
        outcome, engine = run([
            setv('A', 'code', 'a'),
            fail('B', ('A', ['Succeeded'])),
            setv('C', 'mark', 'after failure', ('B', ['Failed'])),
            setv('D', 'mark', 'never', ('B', ['Succeeded'])),
            setv('E', 'code', 'skip seen', ('D', ['Skipped'])),
        ])
        self.assertEqual([event[:2] for event in engine.trace],
                         [('A', 'Succeeded'), ('B', 'Failed'), ('C', 'Succeeded'), ('D', 'Skipped'), ('E', 'Succeeded')])
        self.assertEqual(outcome.variables['mark'], 'after failure')

    def test_the_leaf_rule_decides_pipeline_status(self):
        handled, _ = run([fail('A'), setv('B', 'mark', 'handled', ('A', ['Failed']))])
        self.assertEqual(handled.status, 'Succeeded')
        skipped_leaf, _ = run([fail('A'), setv('B', 'mark', 'x', ('A', ['Succeeded']))])
        self.assertEqual(skipped_leaf.status, 'Failed')
        completed, _ = run([fail('A'), setv('B', 'mark', 'x', ('A', ['Completed']))])
        self.assertEqual(completed.status, 'Succeeded')

    def test_fail_records_its_code_and_an_empty_code_is_not_a_string(self):
        outcome, _ = run([setv('A', 'code', 'execution_unknown'), fail('B', ('A', ['Succeeded']))])
        self.assertEqual([failure['errorCode'] for failure in outcome.failures], ['execution_unknown'])
        outcome, _ = run([fail('B')])
        self.assertEqual([failure['errorCode'] for failure in outcome.failures], ['ErrorCodeNotString'])

    def test_until_continues_after_an_inner_failure_and_times_out(self):
        loop = {'name': 'Loop', 'type': 'Until', 'typeProperties': {
            'expression': expression("@equals(variables('mark'), 'x')"), 'timeout': '0.00:01:00',
            'activities': [fail('Inner'), setv('Count', 'code', 'looped', ('Inner', ['Completed']))]}}
        outcome, engine = run([loop, setv('After', 'mark', 'ran', ('Loop', ['Completed']))])
        self.assertEqual(engine.trace[-2][:2], ('Loop', 'Failed'))
        self.assertEqual(outcome.variables['mark'], 'ran')
        self.assertGreater(sum(event[0] == 'Count' for event in engine.trace), 5)

    def test_a_fault_fails_an_activity_without_running_it(self):
        outcome, engine = run([setv('A', 'code', 'a'), setv('B', 'mark', 'b', ('A', ['Completed']))], faults={'A'})
        self.assertEqual((outcome.variables['code'], outcome.variables['mark']), ('', 'b'))

    def test_set_variable_keeps_the_declared_type(self):
        outcome, engine = run([setv('A', 'code', expression('@createArray(1, 2)'))])
        self.assertEqual((engine.trace[0][1], outcome.variables['code']), ('Failed', ''))


class ValidationTests(unittest.TestCase):
    def refused(self, activities, variables=('code', 'mark')):
        definition = {'activities': activities, 'variables': {name: {'type': 'String'} for name in variables}}
        with self.assertRaises(AdfUnsupported):
            validate_pipeline(definition)

    def test_documented_structural_rules(self):
        self.refused([setv('A', 'code', 'a'), setv('A', 'mark', 'b')])
        self.refused([setv('A', 'code', expression("@concat(variables('code'), 'x')"))])
        self.refused([setv('A', 'code', 'a'), setv('B', 'mark', 'b', ('A', ['Completed'])),
                      setv('C', 'mark', 'c', ('A', ['Succeeded']))])
        self.refused([setv('A', 'code', 'a', ('Elsewhere', ['Succeeded']))])
        self.refused([setv('A', 'undeclared', 'a')])
        self.refused([{'name': 'Copy', 'type': 'Copy', 'typeProperties': {}}])
        inner_if = {'name': 'Inner', 'type': 'IfCondition', 'typeProperties': {
            'expression': expression('@equals(1, 1)'), 'ifTrueActivities': []}}
        self.refused([{'name': 'Outer', 'type': 'Switch', 'typeProperties': {
            'on': expression("@variables('code')"), 'cases': [{'value': 'a', 'activities': [inner_if]}],
            'defaultActivities': []}}])
        self.refused([{'name': 'Outer', 'type': 'Switch', 'typeProperties': {
            'on': expression("@variables('code')"), 'cases': [{'value': 'a', 'activities': []}]}}])
        self.refused([{'name': 'Outer', 'type': 'Switch', 'typeProperties': {
            'expression': expression("@variables('code')"), 'defaultActivities': [],
            'cases': [{'value': 'a', 'activities': []}]}}])
        self.refused([{'name': 'Outer', 'type': 'Switch', 'typeProperties': {
            'on': expression("@variables('code')"), 'defaultActivities': [],
            'cases': [{'value': str(index), 'activities': []} for index in range(26)]}}])
        inner_until = {'name': 'Inner', 'type': 'Until', 'typeProperties': {
            'expression': expression('@equals(1, 1)'), 'activities': []}}
        self.refused([{'name': 'Outer', 'type': 'Until', 'typeProperties': {
            'expression': expression('@equals(1, 1)'), 'activities': [inner_until]}}])
        self.refused([setv(f'A{index}', 'code', 'a') for index in range(121)])
        self.refused([setv('A', 'code', expression('@concat(' + ', '.join(["'x'"] * 2100) + ')'))])
        self.refused([setv(f'A{index}', 'code', 'x' * 2000) for index in range(110)])


if __name__ == '__main__':
    unittest.main()
