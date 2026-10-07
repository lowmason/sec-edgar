import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
label, *argv = sys.argv[1:]
root = Path(".sdd/2-sec-filing-index-ingestion-stage-2-spec/final-review-fix1-evidence")
assert not (root / (label + ".command.json")).exists(), label
start = time.monotonic()
completed = subprocess.run(argv, capture_output=True, env=os.environ.copy())
(root / (label + ".stdout.txt")).write_bytes(completed.stdout)
(root / (label + ".stderr.txt")).write_bytes(completed.stderr)
receipt = {"argv": argv, "cwd": str(Path.cwd()), "exit": completed.returncode, "elapsed_seconds": time.monotonic() - start}
(root / (label + ".command.json")).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt))
print(completed.stdout.decode(errors="replace")[-14000:])
print(completed.stderr.decode(errors="replace")[-14000:])
sys.exit(completed.returncode)
