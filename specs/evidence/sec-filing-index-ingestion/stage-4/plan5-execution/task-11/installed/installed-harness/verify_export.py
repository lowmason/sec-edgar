import json, pathlib, sys
from locked_proof import marker_environment, locked_requirements
root=pathlib.Path(__file__).parent
environment=marker_environment()
expected=locked_requirements((root/'accepted-uv.lock').read_bytes(),
    (root/'requirements.txt').read_text(), environment)
print(json.dumps({'environment':environment,'dependencies':expected},sort_keys=True))
