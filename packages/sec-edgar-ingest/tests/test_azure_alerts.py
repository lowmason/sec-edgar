"""Alert queries name only what the worker and pipelines emit; staleness alerts deploy disabled (spec §8, §10)."""
from network_guard import install
install()

import re
import unittest
from dataclasses import fields

from support_template import INFRA, REPO, module, resources, template
from sec_edgar_ingest.models import RunContext
from sec_edgar_ingest.results import EXIT_CODES
from sec_edgar_ingest.workflows.summary import SUMMARY_FIELDS

SOURCE = REPO / 'packages/sec-edgar-ingest/src/sec_edgar_ingest'
RUN_WORKER = (INFRA / 'pipelines/pl-sec-edgar-run-worker.json').read_text()
# What each spec §8 row requires its query to say.
EXPECTED = {
    'failed-job': ('ADFActivityRun', '!in ("awaiting_approval", "execution_unknown")'),
    'ambiguous-start': ('ADFActivityRun', 'ErrorCode == "execution_unknown"'),
    'lease-failure': ('== "ownership_lost"', 'member_outcomes.ownership_lost) > 0'),
    'access-block': ('== "access_blocked"', 'member_outcomes.access_blocked) > 0'),
    'retry-exhausted': ('member_outcomes.retry_exhausted) > 0',),
    'quarantine': ('== "quarantined"', 'member_outcomes.quarantined) > 0'),
    'publication-conflict': ('== "publication_conflict"', 'member_outcomes.publication_conflict) > 0'),
    'pending-approval': ('fields.pending_approvals) > 0',),
    'reconcile-staleness': ('fields.last_successful_reconcile_at', 'isnull(last) or last < ago(8d)'),
    'daily-staleness': ('ago(30h)', 'entry.context.command) == "daily"', 'fields.discovery_complete', 'found == 0'),
}
STALENESS = {'alert-sec-edgar-reconcile-staleness', 'alert-sec-edgar-daily-staleness'}
PIPELINE_ONLY = {'execution_unknown', 'execution_stopped', 'execution_mismatch', 'result_missing', 'result_mismatch',
                 'stale'}


def queries() -> dict[str, str]:
    return {path.stem: path.read_text() for path in sorted((INFRA / 'alerts').glob('*.kql'))}


def hoisted(compiled: dict, value):
    """A value of a compiled template, following Bicep's [variables('$fxv#N')] hoisting of loadTextContent."""
    while isinstance(value, str) and (reference := re.fullmatch(r"\[variables\('([^']+)'\)\]", value)):
        value = compiled['variables'][reference.group(1)]
    return value


def emitted_events() -> set[str]:
    code = '\n'.join(path.read_text() for path in SOURCE.rglob('*.py'))
    return set(re.findall(r"log_event\([^,()]+, '([a-z_]+)'", code))


class AlertQueryTests(unittest.TestCase):
    def test_each_spec_alert_has_its_query(self):
        found = queries()
        self.assertEqual(set(found), set(EXPECTED))
        for slug, phrases in EXPECTED.items():
            for phrase in phrases:
                self.assertIn(phrase, found[slug], slug)

    def test_queries_name_only_emitted_events_fields_and_outcomes(self):
        events = emitted_events()
        self.assertLessEqual({'command_finished', 'command_error', 'workflow_summary'}, events)
        for code in PIPELINE_ONLY:
            self.assertIn(f"'{code}'", RUN_WORKER)
        self.assertIn('job: \'job-sec-edgar-dev\'', (INFRA / 'main.bicep').read_text())
        self.assertIn('"type": "Fail"', RUN_WORKER)
        literals = events | set(EXIT_CODES) | PIPELINE_ONLY | {'pl-sec-edgar-run-worker', 'Fail', 'Failed',
                                                               'job-sec-edgar-dev', 'daily'}
        context = {field.name for field in fields(RunContext)}
        for slug, query in queries().items():
            with self.subTest(slug):
                self.assertLessEqual(set(re.findall(r'"([^"]*)"', query)), literals)
                for path in re.findall(r'entry((?:\.\w+)+)', query):
                    root, *rest = path.strip('.').split('.')
                    self.assertIn(root, ('event', 'fields', 'context'), path)
                    if root == 'event':
                        self.assertEqual(rest, [], path)
                    elif root == 'context':
                        self.assertTrue(len(rest) == 1 and rest[0] in context, path)
                    elif rest[:1] == ['member_outcomes']:
                        self.assertTrue(len(rest) == 2 and rest[1] in EXIT_CODES, path)
                    else:
                        self.assertTrue(len(rest) == 1 and rest[0] in SUMMARY_FIELDS, path)


class AlertDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.alerts_module = module(template(), 'alerts')
        self.alerts = {alert['name']: alert for alert in self.alerts_module['variables']['alerts']}

    def test_every_alert_deploys_its_committed_query(self):
        self.assertEqual(set(self.alerts), {f'alert-sec-edgar-{slug}' for slug in EXPECTED})
        for slug, query in queries().items():
            deployed = hoisted(self.alerts_module, self.alerts[f'alert-sec-edgar-{slug}']['query'])
            self.assertEqual(deployed, query, slug)

    def test_only_the_staleness_alerts_deploy_disabled_and_stateful(self):
        self.assertEqual({name for name, alert in self.alerts.items() if not alert['enabled']}, STALENESS)
        self.assertEqual({name for name, alert in self.alerts.items() if alert['stateful']}, STALENESS)
        for name, alert in self.alerts.items():
            expected = ('PT1H', 'P2D') if name in STALENESS else ('PT15M', 'PT30M')
            self.assertEqual((alert['frequency'], alert['window']), expected, name)

    def test_rules_count_any_row_and_notify_the_action_group(self):
        rule, = resources(self.alerts_module, 'Microsoft.Insights/scheduledQueryRules')
        criterion, = rule['properties']['criteria']['allOf']
        self.assertEqual((rule['kind'], criterion['operator'], criterion['threshold'], criterion['timeAggregation']),
                         ('LogAlert', 'GreaterThan', 0, 'Count'))
        self.assertEqual(rule['properties']['actions'], {'actionGroups': ["[parameters('actionGroupId')]"]})
        self.assertEqual(rule['properties']['scopes'], ["[parameters('workspaceId')]"])


class OperationsRunbookTests(unittest.TestCase):
    def test_the_runbook_covers_every_alert_and_pipeline_outcome(self):
        runbook = (REPO / 'docs/runbooks/sec-edgar-azure-operations.md').read_text()
        for slug in EXPECTED:
            self.assertIn(f'`alert-sec-edgar-{slug}`', runbook)
        for code in PIPELINE_ONLY | {'success', 'awaiting_approval', 'pending'}:
            self.assertIn(f'| `{code}` |', runbook)
        for phrase in ('reserved/not_run', 'deploy stopped', 'launch-<n>', 'Never start a launch by hand'):
            self.assertIn(phrase, runbook)


if __name__ == '__main__':
    unittest.main()
