"""roles.json is the spec §5 role matrix, exactly; the template deploys only what it lists."""
from network_guard import install
install()

import unittest

from support_template import CONTAINERS, TABLES, load

B = 'Microsoft.Storage/storageAccounts/blobServices/containers/blobs'
T = 'Microsoft.Storage/storageAccounts/tableServices/tables/entities'
ROLES = {
    'SecEdgar Job Controller': ({'Microsoft.App/jobs/read', 'Microsoft.App/jobs/start/action',
                                 'Microsoft.App/jobs/execution/read', 'Microsoft.App/jobs/executions/read'}, set()),
    'SecEdgar Job Async Observer': ({'Microsoft.App/locations/containerappsjoboperationresults/read',
                                     'Microsoft.App/locations/containerappsjoboperationstatuses/read'}, set()),
    'SecEdgar Blob Reader': (set(), {f'{B}/read'}),
    'SecEdgar Blob Writer': (set(), {f'{B}/read', f'{B}/write'}),
    'SecEdgar Entity Reader': (set(), {f'{T}/read'}),
    'SecEdgar Entity Writer': (set(), {f'{T}/read', f'{T}/add/action', f'{T}/update/action'}),
}


def grants(principal, role, *scopes):
    return {(principal, role, scope) for scope in scopes}


GRANTS = (grants('adf', 'SecEdgar Job Controller', 'job')
          | grants('adf', 'SecEdgar Job Async Observer', 'subscription')
          | grants('adf', 'SecEdgar Blob Reader', 'container:results')
          | grants('worker', 'SecEdgar Blob Writer', *(f'container:{name}' for name in (
              'raw', 'worksets', 'results', 'quarantine', 'generations', 'manifests', 'locks')))
          | grants('worker', 'SecEdgar Blob Reader', 'container:approvals')
          | grants('worker', 'SecEdgar Entity Writer', 'table:SourceState', 'table:Attempts', 'table:ActivePointers')
          | grants('worker', 'SecEdgar Entity Reader', 'table:Approvals')
          | grants('pull', 'AcrPull', 'registry')
          | grants('operator', 'SecEdgar Blob Reader', *(f'container:{name}' for name in (
              'locks', 'worksets', 'generations', 'manifests', 'approvals')))
          | grants('operator', 'SecEdgar Blob Writer', 'container:approvals')
          | grants('operator', 'SecEdgar Entity Reader', 'table:SourceState')
          | grants('operator', 'SecEdgar Entity Writer', 'table:ActivePointers', 'table:Approvals'))


class RoleMatrixTests(unittest.TestCase):
    def setUp(self):
        self.roles = load('roles.json')

    def test_custom_roles_carry_only_the_listed_permissions(self):
        found = {role['roleName']: (set(role['actions']), set(role['dataActions'])) for role in self.roles['definitions']}
        self.assertEqual(found, ROLES)
        for role in self.roles['definitions']:
            self.assertEqual(len(role['actions']) + len(role['dataActions']),
                             len(set(role['actions'])) + len(set(role['dataActions'])))
            self.assertTrue(role['description'])

    def test_the_only_built_in_role_is_acr_pull(self):
        self.assertEqual(self.roles['builtins'], {'AcrPull': '7f951dda-4ed3-4680-a7ca-43fe172d538d'})

    def test_assignments_are_the_principal_table(self):
        listed = [(item['principal'], item['role'], item['scope']) for item in self.roles['assignments']]
        self.assertEqual(len(listed), len(set(listed)))
        self.assertEqual(set(listed), GRANTS)
        self.assertTrue(all(set(item) == {'principal', 'role', 'scope'} for item in self.roles['assignments']))

    def test_every_scope_key_is_one_the_template_handles(self):
        handled = {'job', 'registry', 'subscription', *(f'container:{name}' for name in CONTAINERS),
                   *(f'table:{name}' for name in TABLES)}
        self.assertLessEqual({item['scope'] for item in self.roles['assignments']}, handled)

    def test_the_worker_never_writes_approvals(self):
        writes = {(role, scope) for principal, role, scope in GRANTS if principal == 'worker'}
        self.assertNotIn(('SecEdgar Blob Writer', 'container:approvals'), writes)
        self.assertNotIn(('SecEdgar Entity Writer', 'table:Approvals'), writes)

    def test_no_wildcard_or_secret_listing_permission(self):
        for role in self.roles['definitions']:
            for permission in role['actions'] + role['dataActions']:
                self.assertNotIn('*', permission)
                self.assertNotRegex(permission.lower(), r'list(keys|secrets|credentials)')


if __name__ == '__main__':
    unittest.main()
