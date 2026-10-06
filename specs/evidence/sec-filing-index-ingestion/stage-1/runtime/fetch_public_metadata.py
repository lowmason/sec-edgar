"""Retain public publisher metadata; never print Docker registry bearer tokens."""
import hashlib
import json
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

destination = Path(sys.argv[1])
destination.mkdir(parents=True, exist_ok=False)
receipts = []
MAX_METADATA_BYTES = 32 * 1024 * 1024

def public_url(url):
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, '[REDACTED]' if parts.query else '', ''))

def fetch(url, filename, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    failure = None
    try:
        response = urllib.request.urlopen(request, timeout=60)
    except urllib.error.HTTPError as error:
        response = error
        failure = error.code
    with response:
        body = response.read(MAX_METADATA_BYTES + 1)
        assert len(body) <= MAX_METADATA_BYTES, 'Public metadata body exceeds bound'
        public_headers = dict(response.headers)
        status = response.status
        final_url = response.url
    public_headers = {key: public_url(value) if key.lower() == 'location' else value for key, value in public_headers.items()}
    (destination / filename).write_bytes(body)
    receipts.append({'url': url, 'final_url': public_url(final_url), 'status': status, 'file': filename, 'sha256': hashlib.sha256(body).hexdigest(),
                     'bytes': len(body), 'response_headers': public_headers,
                     'received_utc': datetime.now(timezone.utc).isoformat()})
    (destination / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
    assert failure is None, ('Public metadata HTTP failure', url, failure)
    return json.loads(body)

token_url = 'https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull'
with urllib.request.urlopen(token_url, timeout=60) as response:
    token_body = response.read(1024 * 1024 + 1)
    assert len(token_body) <= 1024 * 1024
    token = json.loads(token_body)['token']
headers = {'Authorization': 'Bearer ' + token,
           'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'}
tags = fetch('https://registry-1.docker.io/v2/library/python/tags/list?n=10000', 'python-tags.json', headers)['tags']
assert not any(key.lower() == 'link' for key in receipts[-1]['response_headers']), 'Paginated tag list: stop before selecting global newest patch'
choices = [tag for tag in tags if re.fullmatch(r'3\.14\.\d+-slim-bookworm', tag)]
assert choices, 'No exact stable Python 3.14 Debian bookworm slim tag'
tag = max(choices, key=lambda value: int(value.split('-')[0].split('.')[-1]))
index = fetch('https://registry-1.docker.io/v2/library/python/manifests/' + tag, 'python-index.json', headers)
children = [item for item in index['manifests'] if item.get('platform', {}).get('os') == 'linux'
            and item.get('platform', {}).get('architecture') == 'amd64']
assert len(children) == 1, children
child = children[0]
manifest = fetch('https://registry-1.docker.io/v2/library/python/manifests/' + child['digest'], 'python-amd64-manifest.json', headers)
assert 'sha256:' + receipts[-1]['sha256'] == child['digest']
config = fetch('https://registry-1.docker.io/v2/library/python/blobs/' + manifest['config']['digest'], 'python-amd64-config.json', headers)
assert 'sha256:' + receipts[-1]['sha256'] == manifest['config']['digest']
assert config['architecture'] == 'amd64' and config['os'] == 'linux'
selection = {'tag': 'docker.io/library/python:' + tag, 'index_digest': 'sha256:' + hashlib.sha256((destination / 'python-index.json').read_bytes()).hexdigest(),
             'child_digest': child['digest'], 'platform': child['platform']}
index_receipt = next(item for item in receipts if item['file'] == 'python-index.json')
registry_digest = next((value for key, value in index_receipt['response_headers'].items() if key.lower() == 'docker-content-digest'), None)
assert registry_digest is None or registry_digest == selection['index_digest']
for name, candidate in [('requests', None), ('pyarrow', None), ('pip', None),
                        ('azure-identity', '1.26.0'), ('azure-storage-blob', '12.31.0'), ('azure-data-tables', '12.7.0')]:
    metadata = fetch('https://pypi.org/pypi/' + name + (('/' + candidate) if candidate else '') + '/json', name + '.json')
    selection[name] = metadata['info']['version']
(destination / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n')
(destination / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
print(json.dumps(selection, indent=2))
