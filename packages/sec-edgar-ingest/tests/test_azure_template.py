"""The committed compiled template (main.json) deploys exactly the spec §5 and §9 definitions (spec §10)."""
from network_guard import install
install()

import json
import re
import unittest

from support_adf import PARAMETER_TYPES
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


if __name__ == '__main__':
    unittest.main()
