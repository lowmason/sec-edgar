"""Retain exact local command results for the observational inspection."""
import datetime
import json
import pathlib
import subprocess
import sys
base = pathlib.Path(__file__).resolve().parents[1]
name = sys.argv[1]
suffix = sys.argv[2] if len(sys.argv) > 2 else 'inspection'
command = [sys.executable, str(base / 'investigation-tools' / 'inspect_specimen.py'), name]
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = subprocess.run(command, text=True, capture_output=True)
end = datetime.datetime.now(datetime.timezone.utc).isoformat()
(base / 'specimens' / f'{name}.{suffix}.stdout.txt').write_text(result.stdout)
(base / 'specimens' / f'{name}.{suffix}.stderr.txt').write_text(result.stderr)
(base / 'specimens' / f'{name}.{suffix}-command.json').write_text(json.dumps({'command': command, 'cwd': str(pathlib.Path.cwd()), 'start_utc': start, 'end_utc': end, 'exit_code': result.returncode}, indent=2) + '\n')
print(result.stdout)
print(result.stderr, file=sys.stderr)
raise SystemExit(result.returncode)
