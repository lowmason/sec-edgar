"""The committed compiled template (main.json) deploys exactly the spec §5 and §9 definitions (spec §10)."""
from network_guard import install
install()

import json
import re
import unittest

from support_adf import DEFAULTS, PARAMETER_TYPES
from support_template import CONTAINERS, INFRA, TABLES, deployment, load, module, nodes, resources, template, text

API_VERSIONS = {
    'Microsoft.Resources/resourceGroups': '2024-03-01',
    'Microsoft.Authorization/roleDefinitions': '2022-04-01',
    'Microsoft.Authorization/roleAssignments': '2022-04-01',
    'Microsoft.ManagedIdentity/userAssignedIdentities': '2024-11-30',
    'Microsoft.ContainerRegistry/registries': '2025-11-01',
    'Microsoft.OperationalInsights/workspaces': '2025-07-01',
    'Microsoft.Insights/actionGroups': '2023-01-01',
    'Microsoft.Insights/diagnosticSettings': '2021-05-01-preview',
    'Microsoft.Insights/scheduledQueryRules': '2023-12-01',
    'Microsoft.Storage/storageAccounts': '2025-06-01',
    'Microsoft.Storage/storageAccounts/blobServices': '2025-06-01',
    'Microsoft.Storage/storageAccounts/blobServices/containers': '2025-06-01',
    'Microsoft.Storage/storageAccounts/tableServices': '2025-06-01',
    'Microsoft.Storage/storageAccounts/tableServices/tables': '2025-06-01',
    'Microsoft.App/managedEnvironments': '2026-07-01',
    'Microsoft.App/jobs': '2026-07-01',
    'Microsoft.DataFactory/factories': '2018-06-01',
    'Microsoft.DataFactory/factories/pipelines': '2018-06-01',
    'Microsoft.DataFactory/factories/triggers': '2018-06-01',
}
NAMES = {'group': 'rg-sec-edgar-dev-eastus', 'environment': 'cae-sec-edgar-dev-eastus', 'job': 'job-sec-edgar-dev',
         'factory': 'adf-sec-edgar-dev', 'workspace': 'law-sec-edgar-dev', 'actionGroup': 'ag-sec-edgar-dev',
         'storage': 'secedgardevb8617', 'registry': 'secedgardevb8617', 'worker': 'id-sec-edgar-dev-worker',
         'pull': 'id-sec-edgar-dev-pull'}
AZURE_CONFIG = INFRA / 'config/sec-edgar-ingest.azure.template.json'


def named(value, kind: str, name: str) -> dict:
    """The one resource of `kind` whose (possibly expression) name mentions `name`."""
    found = [resource for resource in resources(value, kind) if f"'{name}'" in resource['name'] or resource['name'] == name]
    assert len(found) == 1, (kind, name, len(found))
    return found[0]


def resolved(compiled: dict, name: str):
    """A variable of a compiled template, following Bicep's [variables('$fxv#N')] hoisting of loadJsonContent."""
    value = compiled['variables'][name]
    while isinstance(value, str) and (hoisted := re.fullmatch(r"\[variables\('([^']+)'\)\]", value)):
        value = compiled['variables'][hoisted.group(1)]
    return value


class SharedResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = template()

    def test_parameters_have_no_defaults_except_the_region(self):
        parameters = self.template['parameters']
        self.assertEqual(set(parameters), {'location', 'configJson', 'configSha256', 'operatorPrincipalId',
                                           'dailyStartTime', 'reconcileStartTime'})
        self.assertEqual((parameters['location']['defaultValue'], parameters['location']['allowedValues']),
                         ('eastus', ['eastus', 'eastus2', 'centralus']))
        for name in set(parameters) - {'location'}:
            self.assertEqual(parameters[name]['type'], 'string', name)
            self.assertNotIn('defaultValue', parameters[name], name)
        self.assertEqual((parameters['configSha256']['minLength'], parameters['configSha256']['maxLength']), (64, 64))
        for name in ('dailyStartTime', 'reconcileStartTime'):
            # yyyy-MM-ddTHH:mm:ss is 19 characters; a trailing Z, an offset or fractions cannot fit.
            self.assertEqual((parameters[name]['minLength'], parameters[name]['maxLength']), (19, 19))

    def test_every_resource_uses_its_selected_api_version(self):
        for resource in resources(self.template):
            if resource['type'] != 'Microsoft.Resources/deployments':
                self.assertEqual(resource['apiVersion'], API_VERSIONS.get(resource['type']), resource['type'])

    def test_names_collections_and_roles_are_the_committed_ones(self):
        variables = self.template['variables']
        self.assertEqual(variables['names'], NAMES)
        self.assertEqual((variables['containers'], variables['tables']), (list(CONTAINERS), list(TABLES)))
        # Bicep hoists loadJsonContent into a '$fxv#N' variable and points `roles` at it; the content is roles.json.
        hoisted = re.fullmatch(r"\[variables\('(\$fxv#\d+)'\)\]", variables['roles'])
        self.assertIsNotNone(hoisted, variables['roles'])
        self.assertEqual(variables[hoisted.group(1)], load('roles.json'))
        group, =resources(self.template, 'Microsoft.Resources/resourceGroups')
        self.assertEqual(group['name'], "[variables('names').group]")

    def test_custom_roles_come_from_roles_json_at_subscription_scope(self):
        definition, = resources(self.template, 'Microsoft.Authorization/roleDefinitions')
        self.assertEqual(definition['copy']['count'], "[length(variables('roles').definitions)]")
        properties = definition['properties']
        self.assertEqual((properties['type'], properties['assignableScopes']), ('CustomRole', ['[subscription().id]']))
        permissions, = properties['permissions']
        self.assertEqual((permissions['notActions'], permissions['notDataActions']), ([], []))
        self.assertIn("variables('roles').definitions[copyIndex()]", text(properties))

    def test_storage_is_entra_only_hns_zrs_with_the_spec_containers_and_tables(self):
        storage = module(self.template, 'storage')
        account, = resources(storage, 'Microsoft.Storage/storageAccounts')
        self.assertEqual((account['kind'], account['sku']), ('StorageV2', {'name': 'Standard_ZRS'}))
        self.assertEqual(account['properties'], {
            'accessTier': 'Hot', 'isHnsEnabled': True, 'allowBlobPublicAccess': False, 'allowSharedKeyAccess': False,
            'defaultToOAuthAuthentication': True, 'minimumTlsVersion': 'TLS1_2', 'publicNetworkAccess': 'Enabled',
            'supportsHttpsTrafficOnly': True})
        parameters = deployment(self.template, 'storage')['properties']['parameters']
        self.assertEqual((parameters['containers'], parameters['tables']),
                         ({'value': "[variables('containers')]"}, {'value': "[variables('tables')]"}))
        container, = resources(storage, 'Microsoft.Storage/storageAccounts/blobServices/containers')
        self.assertEqual(container['properties'], {'publicAccess': 'None'})
        self.assertEqual(container['copy']['count'], "[length(parameters('containers'))]")
        table, = resources(storage, 'Microsoft.Storage/storageAccounts/tableServices/tables')
        self.assertEqual(table['copy']['count'], "[length(parameters('tables'))]")

    def test_registry_is_basic_classic_rbac_with_arm_token_pulls(self):
        registry, = resources(module(self.template, 'registry'), 'Microsoft.ContainerRegistry/registries')
        self.assertEqual(registry['sku'], {'name': 'Basic'})
        self.assertEqual(registry['properties'], {
            'adminUserEnabled': False, 'anonymousPullEnabled': False, 'publicNetworkAccess': 'Enabled',
            'roleAssignmentMode': 'LegacyRegistryPermissions',
            'policies': {'azureADAuthenticationAsArmPolicy': {'status': 'enabled'}}})

    def test_monitoring_keeps_ninety_days_and_mails_the_operator(self):
        monitoring = module(self.template, 'monitoring')
        workspace, = resources(monitoring, 'Microsoft.OperationalInsights/workspaces')
        self.assertEqual(workspace['properties'], {'sku': {'name': 'PerGB2018'}, 'retentionInDays': 90})
        group, = resources(monitoring, 'Microsoft.Insights/actionGroups')
        self.assertEqual(group['location'], 'Global')
        receiver, = group['properties']['emailReceivers']
        self.assertEqual(receiver, {'name': 'operator', 'emailAddress': "[parameters('email')]",
                                    'useCommonAlertSchema': True})
        self.assertEqual(deployment(self.template, 'monitoring')['properties']['parameters']['email'],
                         {'value': 'mason.lowell@mac.com'})

    def test_two_user_assigned_identities(self):
        identities = module(self.template, 'identities')
        self.assertEqual(len(resources(identities, 'Microsoft.ManagedIdentity/userAssignedIdentities')), 2)
        parameters = deployment(self.template, 'identities')['properties']['parameters']
        self.assertEqual((parameters['workerName'], parameters['pullName']),
                         ({'value': "[variables('names').worker]"}, {'value': "[variables('names').pull]"}))


class JobAndFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = template()
        cls.factory = module(cls.template, 'factory')
        cls.config = json.loads(AZURE_CONFIG.read_text())

    def test_the_job_is_manual_with_the_accepted_values_and_no_volumes(self):
        job_module = module(self.template, 'job')
        job, = resources(job_module, 'Microsoft.App/jobs')
        configuration = job['properties']['configuration']
        self.assertEqual(set(configuration), {'triggerType', 'replicaTimeout', 'replicaRetryLimit',
                                              'manualTriggerConfig', 'secrets', 'registries'})
        self.assertEqual((configuration['triggerType'], configuration['replicaTimeout'],
                          configuration['replicaRetryLimit'], configuration['manualTriggerConfig']),
                         ('Manual', 3600, self.config['jobs']['replica_retry_limit'],
                          {'parallelism': 1, 'replicaCompletionCount': 1}))
        self.assertEqual(configuration['secrets'], [{'name': 'ingest-config', 'value': "[parameters('configJson')]"}])
        self.assertEqual(configuration['registries'], [{'server': "[parameters('registryServer')]",
                                                        'identity': "[parameters('pullIdentityId')]"}])
        self.assertEqual(job['properties']['template'], {'containers': ["[parameters('container')]"]})
        self.assertEqual((job['identity']['type'], len(job['identity']['userAssignedIdentities'])), ('UserAssigned', 2))
        self.assertEqual(job['properties']['workloadProfileName'], 'Consumption')
        self.assertNotIn('volume', text(job_module).lower())
        environment, = resources(job_module, 'Microsoft.App/managedEnvironments')
        self.assertEqual(environment['properties'], {
            'appLogsConfiguration': {'destination': 'azure-monitor'},
            'workloadProfiles': [{'name': 'Consumption', 'workloadProfileType': 'Consumption'}]})

    def test_the_start_override_is_the_job_container(self):
        job_container = deployment(self.template, 'job')['properties']['parameters']['container']
        self.assertEqual(deployment(self.template, 'factory')['properties']['parameters']['container'], job_container)
        value = job_container['value']
        self.assertEqual((value['name'], value['resources']), ('sec-edgar-ingest', {'cpu': 2, 'memory': '4Gi'}))
        self.assertEqual(value['env'][1], {'name': 'SEC_EDGAR_INGEST_CONFIG', 'secretRef': 'ingest-config'})
        self.assertEqual(value['env'][0]['name'], 'SEC_EDGAR_INGEST_WORKER_CLIENT_ID')
        self.assertIn('workerClientId', value['env'][0]['value'])
        self.assertEqual(len(value['env']), 2)
        self.assertIn('sec-edgar-ingest@', value['image'])
        self.assertIn('worker.image_digest', value['image'])
        self.assertEqual(self.template['variables']['registryServer'], "[format('{0}.azurecr.io', variables('names').registry)]")
        worker = named(self.factory, 'Microsoft.DataFactory/factories/pipelines', 'pl-sec-edgar-run-worker')
        defaults = {name: declaration.get('defaultValue') for name, declaration in worker['properties']['parameters'].items()}
        for parameter, key in (('containerName', 'name'), ('imageRef', 'image'), ('containerResources', 'resources'),
                               ('containerEnv', 'env')):
            self.assertEqual(defaults[parameter], f"[parameters('container').{key}]")

    def test_run_worker_is_the_committed_json_with_the_declared_parameters(self):
        worker = named(self.factory, 'Microsoft.DataFactory/factories/pipelines', 'pl-sec-edgar-run-worker')
        parameters = worker['properties']['parameters']
        self.assertEqual({name: declaration['type'] for name, declaration in parameters.items()}, PARAMETER_TYPES)
        self.assertEqual({name: parameters[name].get('defaultValue') for name in
                          ('command', 'runId', 'pollSeconds', 'observeSeconds', 'workerSeconds')},
                         {'command': None, 'runId': None, 'pollSeconds': 30, 'observeSeconds': 4200, 'workerSeconds': 3300})
        everything = list(nodes(self.template))
        self.assertIn(load('pipelines/pl-sec-edgar-run-worker.json'), everything)
        for command in ('backfill', 'daily', 'reconcile'):
            self.assertIn(load(f'pipelines/pl-sec-edgar-{command}.json'), everything)
        passed = deployment(self.template, 'factory')['properties']['parameters']
        self.assertEqual(passed['configSha256'], {'value': "[parameters('configSha256')]"})
        for name, fragments in (('imageDigest', ('worker.image_digest',)), ('maxLaunches', ('transient_replays',)),
                                ('jobPath', ('jobId',)), ('resultsUrl', ('blob_endpoint', '/results/runs/sec/')),
                                ('asyncPrefix', ('https://management.azure.com/subscriptions/',
                                                 '/providers/Microsoft.App/locations/'))):
            for fragment in fragments:
                self.assertIn(fragment, passed[name]['value'], name)
        self.assertEqual(1 + self.config['orchestration']['transient_replays'], 2)

    def test_triggers_are_the_eastern_recurrences_and_deploy_stopped(self):
        expected = {
            'tr-sec-edgar-daily': ('pl-sec-edgar-daily', {'frequency': 'Day', 'interval': 1,
                                   'startTime': "[parameters('dailyStartTime')]", 'timeZone': 'Eastern Standard Time',
                                   'schedule': {'hours': [5], 'minutes': [0]}}),
            'tr-sec-edgar-reconcile': ('pl-sec-edgar-reconcile', {'frequency': 'Week', 'interval': 1,
                                       'startTime': "[parameters('reconcileStartTime')]",
                                       'timeZone': 'Eastern Standard Time',
                                       'schedule': {'weekDays': ['Sunday'], 'hours': [6], 'minutes': [0]}}),
        }
        self.assertEqual(len(resources(self.factory, 'Microsoft.DataFactory/factories/triggers')), 2)
        for name, (pipeline, recurrence) in expected.items():
            trigger = named(self.factory, 'Microsoft.DataFactory/factories/triggers', name)
            self.assertEqual(trigger['properties'], {
                'type': 'ScheduleTrigger',
                'pipelines': [{'pipelineReference': {'referenceName': pipeline, 'type': 'PipelineReference'}}],
                'typeProperties': {'recurrence': recurrence}})
        body = text(self.template)
        self.assertNotIn('runtimeState', body)
        self.assertFalse([resource for resource in resources(self.template) if 'deploymentScripts' in resource['type']])
        passed = deployment(self.template, 'factory')['properties']['parameters']
        self.assertEqual((passed['dailyStartTime'], passed['reconcileStartTime']),
                         ({'value': "[parameters('dailyStartTime')]"}, {'value': "[parameters('reconcileStartTime')]"}))

    def test_job_and_factory_logs_go_to_the_workspace_as_resource_specific_tables(self):
        expected = {'job': ['ContainerAppConsoleLogs', 'ContainerAppSystemLogs'],
                    'factory': ['ActivityRuns', 'PipelineRuns', 'TriggerRuns']}
        for name, categories in expected.items():
            setting, = resources(module(self.template, name), 'Microsoft.Insights/diagnosticSettings')
            self.assertEqual(setting['properties'], {
                'workspaceId': "[parameters('workspaceId')]", 'logAnalyticsDestinationType': 'Dedicated',
                'logs': [{'category': category, 'enabled': True} for category in categories]})
        factory, = resources(self.factory, 'Microsoft.DataFactory/factories')
        self.assertEqual(factory['identity'], {'type': 'SystemAssigned'})

    def test_the_start_body_container_is_the_job_container_except_for_its_arguments(self):
        job_module = module(self.template, 'job')
        job, = resources(job_module, 'Microsoft.App/jobs')
        job_container = deployment(self.template, 'job')['properties']['parameters']['container']['value']
        # The job runs the container it is handed, so the deployment parameter is the job's own container.
        self.assertEqual(job['properties']['template']['containers'], ["[parameters('container')]"])
        starts = [node for node in nodes(resolved(self.factory, 'runWorker')['activities'])
                  if node.get('name') == 'Start job']
        start, = starts
        container, = start['typeProperties']['body']['containers']
        self.assertEqual(set(container) - {'args'}, set(job_container))
        declared = named(self.factory, 'Microsoft.DataFactory/factories/pipelines',
                         'pl-sec-edgar-run-worker')['properties']['parameters']
        for key in job_container:
            # Each job key reaches the start body through exactly one run-worker parameter that defaults to it.
            bound = [name for name, declaration in declared.items()
                     if declaration.get('defaultValue') == f"[parameters('container').{key}]"]
            self.assertEqual(len(bound), 1, key)
            self.assertEqual(container[key], f'@pipeline().parameters.{bound[0]}', key)
        config_variable = job_container['env'][1]
        secret, = job['properties']['configuration']['secrets']
        self.assertEqual(config_variable['secretRef'], secret['name'])
        self.assertTrue(container['args'].startswith(
            f"@createArray(pipeline().parameters.command, '--config-env', '{config_variable['name']}', "), container['args'])

    def test_run_worker_declares_the_scenario_parameters_with_their_defaults(self):
        declared = named(self.factory, 'Microsoft.DataFactory/factories/pipelines',
                         'pl-sec-edgar-run-worker')['properties']['parameters']
        self.assertEqual(set(declared), set(PARAMETER_TYPES))
        self.assertEqual({name for name, declaration in declared.items() if 'defaultValue' in declaration}, set(DEFAULTS))
        # Values the factory module receives are defaults under their own names; the rest are literals.
        for name in ('imageDigest', 'configSha256', 'jobPath', 'asyncPrefix', 'resultsUrl', 'maxLaunches'):
            self.assertEqual(declared[name]['defaultValue'], f"[parameters('{name}')]", name)
            self.assertIn(name, self.factory['parameters'])
        for name in ('pollSeconds', 'observeSeconds', 'workerSeconds'):
            self.assertEqual(declared[name]['defaultValue'], DEFAULTS[name], name)

    def test_the_deployed_pipelines_are_the_committed_json(self):
        worker = named(self.factory, 'Microsoft.DataFactory/factories/pipelines', 'pl-sec-edgar-run-worker')
        committed = load('pipelines/pl-sec-edgar-run-worker.json')
        self.assertEqual(resolved(self.factory, 'runWorker'), committed)
        self.assertEqual((worker['properties']['activities'], worker['properties']['variables']),
                         ("[variables('runWorker').activities]", "[variables('runWorker').variables]"))
        callers = resolved(self.factory, 'callers')
        self.assertEqual([caller['name'] for caller in callers],
                         [f'pl-sec-edgar-{command}' for command in ('backfill', 'daily', 'reconcile')])
        for caller in callers:
            definition = caller['definition']
            while isinstance(definition, str):
                definition = self.factory['variables'][re.fullmatch(r"\[variables\('([^']+)'\)\]", definition).group(1)]
            self.assertEqual(definition, load(f"pipelines/{caller['name']}.json"), caller['name'])
        looped, = [resource for resource in resources(self.factory, 'Microsoft.DataFactory/factories/pipelines')
                   if 'copy' in resource]
        self.assertEqual(looped['properties'], "[variables('callers')[copyIndex()].definition]")


class AccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = template()

    def access_modules(self):
        single = [deployment(self.template, name) for name in ('access-job', 'access-registry', 'access-subscription')]
        looped = [item for item in resources(self.template, 'Microsoft.Resources/deployments')
                  if item.get('copy', {}).get('name') in ('containerAccess', 'tableAccess')]
        return single + looped

    def test_every_scope_is_granted_through_one_access_module(self):
        loops = {item['copy']['name']: item for item in resources(self.template, 'Microsoft.Resources/deployments')
                 if 'copy' in item}
        self.assertEqual(loops['containerAccess']['copy']['count'], "[length(variables('containers'))]")
        self.assertEqual(loops['tableAccess']['copy']['count'], "[length(variables('tables'))]")
        self.assertIn("'container:{0}'", text(loops['containerAccess']['properties']['parameters']['scopeKey']))
        self.assertIn("'table:{0}'", text(loops['tableAccess']['properties']['parameters']['scopeKey']))
        modules = self.access_modules()
        self.assertEqual(len(modules), 5)
        for item in modules:
            parameters = item['properties']['parameters']
            self.assertEqual(parameters['assignments'], {'value': "[variables('roles').assignments]"})
            if item.get('name') == 'access-registry':
                # Only the pull identity, so the registry grant needs nothing that the job's creation needs.
                self.assertEqual(set(parameters['principals']['value']), {'pull'})
            else:
                self.assertEqual(set(parameters['principals']['value']), {'adf', 'worker', 'pull', 'operator'})
                self.assertEqual(parameters['principals']['value']['operator'], "[parameters('operatorPrincipalId')]")
            grant, = resources(item['properties']['template'], 'Microsoft.Authorization/roleAssignments')
            body = text(grant['properties'])
            for fragment in ("parameters('roleIds')", "parameters('principals')", "'operator'", "'User'",
                             "'ServicePrincipal'"):
                self.assertIn(fragment, body)

    def test_no_broad_or_secret_bearing_permission_anywhere(self):
        body = text(self.template)
        for forbidden in ('listKeys', 'listSecrets', 'listCredentials', 'Owner', 'Contributor', '"*"', '/*"'):
            self.assertNotIn(forbidden, body)
        literal_role_ids = set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', body))
        self.assertEqual(literal_role_ids, {'7f951dda-4ed3-4680-a7ca-43fe172d538d'})


# The expected expressions below are the exact forms Bicep 0.38.33 emits. A Bicep upgrade that prints filters,
# lambdas or scopes differently needs them refreshed: a locator change, not a change of meaning.
SELECTED = "filter(parameters('assignments'), lambda('item', equals(lambdaVariables('item').scope, {key})))"


class GrantSetTests(unittest.TestCase):
    """The compiled role assignments are roles.json in both directions: no extra grant, no missing grant, no grant at
    a wrong scope and no principal key bound to the wrong identity."""

    @classmethod
    def setUpClass(cls):
        cls.template = template()

    def check_grant(self, item, key: str, scope):
        """The deployment's one grant is roles.json filtered to `key`, at `scope`, with role and principal from the item."""
        grant, = resources(item['properties']['template'], 'Microsoft.Authorization/roleAssignments')
        selected = SELECTED.format(key=key)
        self.assertEqual(grant['copy']['count'], f'[length({selected})]')
        self.assertEqual(grant.get('scope'), scope)
        item_ = f'{selected}[copyIndex()]'
        self.assertEqual(grant['properties'], {
            'roleDefinitionId': f"[subscriptionResourceId('Microsoft.Authorization/roleDefinitions', "
                                f"parameters('roleIds')[{item_}.role])]",
            'principalId': f"[parameters('principals')[{item_}.principal]]",
            'principalType': f"[if(equals({item_}.principal, 'operator'), 'User', 'ServicePrincipal')]"})
        parameters = item['properties']['parameters']
        self.assertEqual((parameters['assignments'], parameters['roleIds']),
                         ({'value': "[variables('roles').assignments]"}, {'value': "[variables('roleIds')]"}))
        return parameters

    def test_the_template_grants_exactly_the_roles_json_assignments(self):
        self.assertEqual(len(resources(self.template, 'Microsoft.Authorization/roleAssignments')), 5)
        handled = {}
        singles = (('access-job', 'job', "[format('Microsoft.App/jobs/{0}', parameters('jobName'))]"),
                   ('access-registry', 'registry',
                    "[format('Microsoft.ContainerRegistry/registries/{0}', parameters('registryName'))]"),
                   ('access-subscription', 'subscription', None))
        principals = {}
        for name, key, scope in singles:
            item = deployment(self.template, name)
            principals[name] = self.check_grant(item, f"'{key}'", scope)['principals']
            handled.setdefault(key, []).append(name)
        self.assertEqual(deployment(self.template, 'access-job')['properties']['parameters']['jobName'],
                         {'value': "[variables('names').job]"})
        self.assertEqual(deployment(self.template, 'access-registry')['properties']['parameters']['registryName'],
                         {'value': "[variables('names').registry]"})
        self.assertNotIn('resourceGroup', deployment(self.template, 'access-subscription'))
        for loop, collection, kind, path in (('containerAccess', 'containers', 'container', 'blobServices/{1}/containers/{2}'),
                                             ('tableAccess', 'tables', 'table', 'tableServices/{1}/tables/{2}')):
            item, = [node for node in resources(self.template, 'Microsoft.Resources/deployments')
                     if node.get('copy', {}).get('name') == loop]
            self.assertEqual(item['copy']['count'], f"[length(variables('{collection}'))]")
            parameters = self.check_grant(item, "parameters('scopeKey')",
                                          f"[format('Microsoft.Storage/storageAccounts/{{0}}/{path}', "
                                          f"parameters('storageName'), 'default', parameters('{kind}Name'))]")
            self.assertEqual((parameters['scopeKey'], parameters[f'{kind}Name'], parameters['storageName']),
                             ({'value': f"[format('{kind}:{{0}}', variables('{collection}')[copyIndex()])]"},
                              {'value': f"[variables('{collection}')[copyIndex()]]"},
                              {'value': "[variables('names').storage]"}))
            principals[loop] = parameters['principals']
            for name in self.template['variables'][collection]:
                handled.setdefault(f'{kind}:{name}', []).append(loop)
        # Each scope key is handled by exactly one deployment, so no grant is made twice.
        self.assertEqual({key: len(names) for key, names in handled.items()}, dict.fromkeys(handled, 1))
        # Every roles.json grant falls under a handled key (none missing); the five filtered grants above are the
        # only role assignments, so nothing outside roles.json is granted (no extras).
        listed = {(item['principal'], item['role'], item['scope']) for item in load('roles.json')['assignments']}
        self.assertEqual({grant for grant in listed if grant[2] in handled}, listed)
        # Each principal key is the identity the spec names, the same map in every deployment but the registry's.
        registry = principals.pop('access-registry')['value']
        shared = list(principals.values())
        self.assertTrue(all(value == shared[0] for value in shared))
        bound = shared[0]['value']
        for key, (source, output) in {'adf': ('factory', 'principalId'), 'worker': ('identities', 'workerPrincipalId'),
                                      'pull': ('identities', 'pullPrincipalId')}.items():
            self.assertIn(f"'Microsoft.Resources/deployments', '{source}')", bound[key], key)
            self.assertTrue(bound[key].endswith(f'.outputs.{output}.value]'), key)
        self.assertEqual(bound['operator'], "[parameters('operatorPrincipalId')]")
        # The registry deployment binds only the pull identity, to the same output, and names neither the factory
        # nor the job; every roles.json registry grant names a principal it binds.
        self.assertEqual(registry, {'pull': bound['pull']})
        for source in ('factory', 'job'):
            self.assertNotIn(f"'Microsoft.Resources/deployments', '{source}')", text(registry), source)
        self.assertLessEqual({principal for principal, _, scope in listed if scope == 'registry'}, set(registry))
        # Role IDs are the custom definitions' own names plus the AcrPull built-in.
        self.assertEqual(self.template['variables']['roleIds'],
                         "[union(toObject(variables('roles').definitions, lambda('role', lambdaVariables('role').roleName), "
                         "lambda('role', guid(subscription().id, lambdaVariables('role').roleName))), "
                         "variables('roles').builtins)]")
        definition, = resources(self.template, 'Microsoft.Authorization/roleDefinitions')
        self.assertEqual(definition['name'], "[guid(subscription().id, variables('roles').definitions[copyIndex()].roleName)]")


DEPLOYMENT_REFERENCE = re.compile(r"'Microsoft\.Resources/deployments', '([^']+)'\)\]$")


def dependency_graph(compiled: dict) -> dict[str, set[str]]:
    """Each top-level resource, by its deployment or loop name, to what its compiled dependsOn names: deployments by
    name, loops by their copy name, anything else by its raw expression."""
    graph = {}
    for resource in compiled['resources']:
        name = resource['copy']['name'] if 'copy' in resource else resource['name']
        graph[name] = {(found.group(1) if (found := DEPLOYMENT_REFERENCE.search(item)) else item)
                       for item in resource.get('dependsOn', [])}
    return graph


def depends_on(graph: dict[str, set[str]], name: str) -> set[str]:
    """Everything `name` waits for, directly or transitively."""
    seen, frontier = set(), list(graph[name])
    while frontier:
        item = frontier.pop()
        if item not in seen:
            seen.add(item)
            frontier.extend(graph.get(item, ()))
    return seen


class DeploymentOrderTests(unittest.TestCase):
    """Container Apps checks the job's registry identity when it creates the job, so AcrPull must exist first."""

    @classmethod
    def setUpClass(cls):
        cls.graph = dependency_graph(template())

    def test_the_graph_names_every_deployment(self):
        for name in ('identities', 'registry', 'job', 'factory', 'access-registry', 'access-job', 'access-subscription',
                     'containerAccess', 'tableAccess', 'roleDefinitions'):
            self.assertIn(name, self.graph)
        self.assertIn('registry', self.graph['access-registry'])
        self.assertIn('job', self.graph['factory'])

    def test_the_pull_grant_needs_neither_the_job_nor_the_factory(self):
        waits_for = depends_on(self.graph, 'access-registry')
        self.assertNotIn('job', waits_for)
        self.assertNotIn('factory', waits_for)
        self.assertLessEqual({'registry', 'identities', 'roleDefinitions'}, waits_for)

    def test_the_job_waits_for_the_pull_grant(self):
        self.assertIn('access-registry', self.graph['job'])
        self.assertIn('access-registry', depends_on(self.graph, 'factory'))
        self.assertNotIn('job', depends_on(self.graph, 'job'))


if __name__ == '__main__':
    unittest.main()
