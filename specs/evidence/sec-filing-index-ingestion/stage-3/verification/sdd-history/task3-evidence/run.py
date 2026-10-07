import json
import pathlib
import subprocess
import sys
root = pathlib.Path(__file__).resolve().parents[3]
name = sys.argv[1]
argv = sys.argv[2:]
result = subprocess.run(argv, cwd=root, capture_output=True, text=True)
prefix = pathlib.Path(__file__).parent / name
prefix.with_name(name + '-command.json').write_text(json.dumps({'argv': argv, 'cwd': str(root), 'exit': result.returncode}, indent=2))
prefix.with_name(name + '-stdout.txt').write_text(result.stdout)
prefix.with_name(name + '-stderr.txt').write_text(result.stderr)
print(result.stdout + result.stderr)
print('EXIT:', result.returncode)
