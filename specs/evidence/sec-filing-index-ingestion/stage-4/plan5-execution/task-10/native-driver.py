from pathlib import Path
import json, sys
sys.path.insert(0, str(Path.cwd() / "packages/sec-edgar-ingest/tests"))
from workflow_proof import native
if __name__ == "__main__":
    print(json.dumps(native(Path(sys.argv[1])), default=str))
