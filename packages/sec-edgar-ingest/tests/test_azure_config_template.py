"""The versioned Azure config template renders one canonical config whose binding is frozen."""
from network_guard import install
install()

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from sec_edgar_ingest.config import Settings, load_config_env
from sec_edgar_ingest.deployment import main as deployment_main, render_azure_config
from sec_edgar_ingest.models import canonical_json, to_mapping_value
from sec_edgar_ingest.storage.contracts import deployment_binding, payload_bytes

REPO = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO / 'infra/azure/sec-edgar-ingest/config'
TEMPLATE = CONFIG_DIR / 'sec-edgar-ingest.azure.template.json'
GOLDEN = CONFIG_DIR / 'deployment-binding.json'
SHIPPED = REPO / 'conf/sec-edgar-ingest.yaml'
DIGEST = 'sha256:' + '1' * 64


def render(template=None, digest=DIGEST, provenance='stage-6-offline-test'):
    return render_azure_config(TEMPLATE.read_bytes() if template is None else template, digest, provenance)


def binding(body: bytes) -> bytes:
    return payload_bytes(deployment_binding(Settings.from_mapping(json.loads(body))))


class AzureConfigTemplateTests(unittest.TestCase):
    def test_rendered_config_is_canonical_and_identifies_itself(self):
        body, digest = render()
        settings = Settings.from_mapping(json.loads(body))
        self.assertEqual(body, canonical_json(to_mapping_value(settings.to_mapping())))
        self.assertEqual((digest, hashlib.sha256(body).hexdigest()), (settings.config_sha256,) * 2)
        self.assertEqual((settings.storage.backend, settings.etl.parser_version, settings.worker.image_digest),
                         ('azure', 'sec-index-parser-v1', DIGEST))
        self.assertEqual(load_config_env('SEC_EDGAR_INGEST_CONFIG',
                                         {'SEC_EDGAR_INGEST_CONFIG': body.decode()}).config_sha256, digest)

    def test_every_value_outside_storage_and_parser_is_the_accepted_default(self):
        template, shipped = json.loads(TEMPLATE.read_text()), json.loads(SHIPPED.read_text())
        self.assertEqual(set(template), set(shipped) - {'worker'})
        for section in set(shipped) - {'storage', 'etl', 'worker'}:
            self.assertEqual(template[section], shipped[section], section)
        self.assertEqual(template['etl'], {**shipped['etl'], 'parser_version': 'sec-index-parser-v1'})
        self.assertEqual((template['backfill'], template['daily']),
                         ({'start_quarter': '2015Q1', 'end_quarter': 'open'}, {'start_date': '2026-10-01'}))

    def test_endpoints_are_spelled_without_a_trailing_slash(self):
        storage = json.loads(TEMPLATE.read_text())['storage']
        self.assertEqual((storage['blob_endpoint'], storage['table_endpoint']),
                         ('https://secedgardevb8617.blob.core.windows.net',
                          'https://secedgardevb8617.table.core.windows.net'))

    def test_the_golden_binding_freezes_every_bound_value(self):
        for digest in (DIGEST, 'sha256:' + '2' * 64):
            self.assertEqual(binding(render(digest=digest)[0]), GOLDEN.read_bytes())
        template = json.loads(TEMPLATE.read_text())
        template['storage']['blob_endpoint'] += '/'
        self.assertNotEqual(binding(render(json.dumps(template).encode())[0]), GOLDEN.read_bytes())

    def test_the_renderer_refuses_fixture_values_and_a_worker_section(self):
        template = json.loads(TEMPLATE.read_text())
        cases = {'worker section': {**template, 'worker': {'image_digest': DIGEST, 'provenance': 'x'}},
                 'local backend': {**template, 'storage': {**template['storage'], 'backend': 'local-fixture'}},
                 'fixture parser': {**template, 'etl': {**template['etl'], 'parser_version': 'fixture-index-parser-v1'}}}
        for label, value in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                render(json.dumps(value).encode())
        for digest, provenance in (('sha256:' + '0' * 64, 'release'), (DIGEST, 'synthetic-fixture'), ('latest', 'release')):
            with self.subTest(digest=digest, provenance=provenance), self.assertRaises(ValueError):
                render(digest=digest, provenance=provenance)

    def test_the_cli_writes_the_config_and_arm_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'rendered'
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = deployment_main(['--template', str(TEMPLATE), '--image-digest', DIGEST,
                                        '--provenance', 'stage-6-offline-test', '--out-dir', str(out)])
            self.assertEqual(code, 0)
            body = (out / 'sec-edgar-ingest.azure.json').read_bytes()
            digest = hashlib.sha256(body).hexdigest()
            parameters = json.loads((out / 'main.parameters.json').read_text())
            self.assertEqual(parameters['parameters'], {'configJson': {'value': body.decode()},
                                                        'configSha256': {'value': digest}})
            self.assertEqual(json.loads(stdout.getvalue())['config_sha256'], digest)


if __name__ == '__main__':
    unittest.main()
