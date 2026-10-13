"""Render the versioned Azure config template into deployment inputs. Offline: no Azure call."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .config import Settings
from .models import canonical_json, parse_json, to_mapping_value

ARM_PARAMETERS_SCHEMA = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#'


def render_azure_config(template: bytes, image_digest: str, provenance: str) -> tuple[bytes, str]:
    """The template plus the image digest and provenance, validated through Settings, as canonical bytes
    and their config_sha256."""
    value = parse_json(template)
    if not isinstance(value, dict) or 'worker' in value:
        raise ValueError('the Azure template must be an object without a worker section')
    settings = Settings.from_mapping({**value, 'worker': {'image_digest': image_digest, 'provenance': provenance}})
    if settings.storage.backend != 'azure':
        raise ValueError('the Azure template must select the azure backend')
    body = canonical_json(to_mapping_value(settings.to_mapping()))
    if hashlib.sha256(body).hexdigest() != settings.config_sha256:
        raise ValueError('rendered bytes differ from the configuration identity')
    return body, settings.config_sha256


def arm_parameters(body: bytes, config_sha256: str) -> dict[str, object]:
    return {'$schema': ARM_PARAMETERS_SCHEMA, 'contentVersion': '1.0.0.0',
            'parameters': {'configJson': {'value': body.decode('utf-8')},
                           'configSha256': {'value': config_sha256}}}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m sec_edgar_ingest.deployment')
    parser.add_argument('--template', required=True)
    parser.add_argument('--image-digest', required=True)
    parser.add_argument('--provenance', required=True)
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args(argv)
    try:
        body, config_sha256 = render_azure_config(Path(args.template).read_bytes(), args.image_digest,
                                                  args.provenance)
    except (ValueError, OSError, TypeError) as error:
        sys.stderr.write(json.dumps({'outcome': 'configuration', 'error': str(error)}) + '\n')
        return 2
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    config, parameters = out / 'sec-edgar-ingest.azure.json', out / 'main.parameters.json'
    config.write_bytes(body)
    parameters.write_text(json.dumps(arm_parameters(body, config_sha256), indent=2, sort_keys=True) + '\n')
    sys.stdout.write(json.dumps({'config_sha256': config_sha256, 'config': str(config),
                                 'parameters': str(parameters)}, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
