"""Real spawn proof entry points; every target installs the offline guard."""
from network_guard import install
install()
import contextlib
import io
import os
import shutil
import importlib.util
import tempfile
import unittest
from pathlib import Path


class ProcessProofTests(unittest.TestCase):
    def test_driver_exposes_real_process_proof(self):
        self.assertIsNotNone(importlib.util.find_spec('etl_proof'), 'Task 7 process proof driver is missing')

    def test_aligned_insert_replace_and_gate_races(self):
        from etl_proof import process_proof
        with tempfile.TemporaryDirectory() as directory:
            try:
                report = process_proof(Path(directory))
                self.assertEqual(len(report['races']), 3)
                self.assertEqual(len(report['deaths']), 4)
            finally:
                destination = os.environ.get('SEC_EDGAR_TASK7_PROCESS_PROOF')
                if destination:
                    shutil.copytree(directory, destination)

    def test_each_command_help_and_required_proof_output(self):
        from sec_edgar_ingest.cli import main
        from etl_proof import main as proof_main
        for command in ('discover', 'collect', 'transform', 'publish'):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as caught:
                main([command, '--help'])
            self.assertEqual(caught.exception.code, 0)
            self.assertIn('--config', output.getvalue())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            proof_main(['sequence'])
        self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
