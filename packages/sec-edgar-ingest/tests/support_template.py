"""Read the committed infrastructure definitions with the stdlib alone (spec §10)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INFRA = REPO / 'infra/azure/sec-edgar-ingest'
CONTAINERS = ('raw', 'worksets', 'quarantine', 'locks', 'results', 'generations', 'manifests', 'approvals')
TABLES = ('SourceState', 'Attempts', 'ActivePointers', 'Approvals')


def load(relative: str):
    return json.loads((INFRA / relative).read_text())


def template() -> dict:
    return load('main.json')


def nodes(value):
    """Every JSON object in a value, depth first."""
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from nodes(item)


def resources(value, kind: str | None = None) -> list[dict]:
    """ARM resources anywhere in the tree, nested deployments included, whether Bicep lists or keys them."""
    return [node for node in nodes(value) if isinstance(node.get('type'), str) and 'apiVersion' in node
            and (kind is None or node['type'] == kind)]


def deployment(value, name: str) -> dict:
    found = [node for node in resources(value, 'Microsoft.Resources/deployments') if node.get('name') == name]
    assert len(found) == 1, (name, len(found))
    return found[0]


def module(value, name: str) -> dict:
    """The compiled template of the module deployed under `name`."""
    return deployment(value, name)['properties']['template']


def text(value) -> str:
    return json.dumps(value, sort_keys=True)
