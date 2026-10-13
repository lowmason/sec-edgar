"""The worker image definition: F1's base and lock, no platform selection, UID 1000, no configuration."""
from network_guard import install
install()

import hashlib
import os
import re
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
IMAGE = REPO / 'infra/azure/sec-edgar-ingest/image'
F1_LOCK = REPO / 'specs/evidence/sec-filing-index-ingestion/stage-1/runtime/requirements.lock'
BASE = 'docker.io/library/python@sha256:d1e795fbdab8a4744432467f32f348c6baa99f07abc05ffde710913f65c8261d'
LOCK_SHA256 = '523b2da36079ce4a7c6b11ac06feb0a7992a8c3aef757c32909850685023b5c2'


def normalize(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def instructions(text: str) -> list[str]:
    """Dockerfile instructions with line continuations joined and comments dropped."""
    joined = re.sub(r'\\\n\s*', ' ', text)
    return [line.strip() for line in joined.splitlines() if line.strip() and not line.lstrip().startswith('#')]


class ImageDefinitionTests(unittest.TestCase):
    def setUp(self):
        self.text = (IMAGE / 'Dockerfile').read_text()
        self.lines = instructions(self.text)

    def test_base_is_f1s_child_digest_on_the_first_line_without_platform_selection(self):
        self.assertEqual(self.text.splitlines()[0], 'FROM ' + BASE)
        self.assertEqual([line for line in self.lines if line.startswith('FROM ')], ['FROM ' + BASE])
        self.assertNotIn('--platform', self.text)

    def test_runtime_user_entrypoint_and_temporary_space(self):
        self.assertIn('USER 1000:1000', self.lines)
        self.assertEqual(self.lines[-1], 'ENTRYPOINT ["sec-edgar-ingest"]')
        self.assertIn('ENV TMPDIR=/tmp/sec-edgar-ingest', self.lines)
        run, = [line for line in self.lines if line.startswith('RUN ')]
        for fragment in ('pip install --require-hashes --no-deps --only-binary=:all: -r /build/requirements.lock',
                         'pip install --no-deps /build/sec_edgar_ingest-', 'pip check',
                         'chown 1000:1000 /home/worker /tmp/sec-edgar-ingest'):
            self.assertIn(fragment, run)
        self.assertFalse(any(line.startswith(('VOLUME', 'ADD ')) for line in self.lines))
        self.assertNotIn('SEC_EDGAR_INGEST_CONFIG', self.text)

    def test_lock_is_f1s_exact_bytes_and_matches_uv_lock(self):
        body = (IMAGE / 'requirements.lock').read_bytes()
        self.assertEqual(hashlib.sha256(body).hexdigest(), LOCK_SHA256)
        self.assertEqual(body, F1_LOCK.read_bytes())
        pins = {}
        for line in body.decode().splitlines():
            name, pinned = re.fullmatch(r'([A-Za-z0-9_.-]+)==(\S+) --hash=sha256:[0-9a-f]{64}', line).groups()
            pins[normalize(name)] = pinned
        resolved = {normalize(package['name']): package['version']
                    for package in tomllib.loads((REPO / 'uv.lock').read_text())['package']}
        self.assertEqual(len(pins), 21)
        self.assertEqual(pins, {name: resolved[name] for name in pins})

    def test_the_context_script_is_executable(self):
        self.assertTrue(os.access(REPO / 'scripts/build-image-context.sh', os.X_OK))


if __name__ == '__main__':
    unittest.main()
