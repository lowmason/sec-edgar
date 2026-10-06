"""Retained local evidence checks; no requests, production modules or golden tests."""
import csv
import importlib.util
import json
import pathlib
import tempfile

path = pathlib.Path(__file__).with_name('sec_inventory.py')
spec = importlib.util.spec_from_file_location('investigation', path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
url = helper.ROOTS['full-index']
for bad in ['../x', 'a/b', '%2e%2e', '..']:
    try:
        helper.child_url(url, bad)
    except ValueError:
        continue
    raise AssertionError(bad)
for bad in ['http://www.sec.gov/Archives/edgar/full-index/index.json', 'https://evil.example/Archives/edgar/full-index/index.json']:
    try:
        helper.validate_url(bad)
    except ValueError:
        continue
    raise AssertionError(bad)
children = helper.parse_listing(url, json.dumps({'directory': {'item': [{'name': '2010', 'type': 'dir'}, {'name': '2026', 'type': 'file'}]}}).encode(), 'json')[1]
assert helper.directories(children, r'20\d{2}') == ['2010']
try:
    helper.parse_listing(url, b'{"directory":{"item":[{"name":"2010"}]}}', 'json')
except ValueError:
    pass
else:
    raise AssertionError('type missing accepted')
assert len(helper.parse_listing(url, b'<directory><item><name>2010</name><type>dir</type></item></directory>', 'xml')[1]) == 1
html = b'<html><a href="2010/">2010</a><a href="https://evil.example/2015/">bad</a><a href="../2016/">bad</a></html>'
assert helper.parse_listing(url, html, 'html')[1] == [{'name': '2010', 'type': 'dir'}]
assert sum(1 for year in range(2010, 2027) for _ in range(4)) == 68
assert sum(1 for year in range(2015, 2027) for _ in range(4)) == 48
with tempfile.TemporaryDirectory() as temp:
    helper.BASE = pathlib.Path(temp)
    helper.STATE = helper.BASE / 'state.json'
    helper.LEDGER = helper.BASE / 'requests.csv'
    try:
        helper.read_state()
    except RuntimeError:
        pass
    else:
        raise AssertionError('inactive window accepted')
    (helper.BASE / 'listings').mkdir()
    (helper.BASE / 'listings' / 'SEC-0001.body').write_bytes(b'partial')
    helper.save_json(helper.STATE, {'attempts': 1, 'received_bytes': 0, 'halted': ''})
    helper.recover_interrupted_attempts()
    state = helper.read_state()
    assert state['received_bytes'] == 7 and state['halted']
    rows = list(csv.DictReader(helper.LEDGER.open()))
    assert len(rows) == 1 and rows[0]['outcome'] == 'interrupted_unknown'
print('PASS canonical URL/child guards; JSON/XML/HTML schema/type; external/parent HTML links rejected; 68 requested/48 development; inactive refusal; interruption recovery and orphan bytes. No SEC traffic.')

class MockSocket:
    def __init__(self):
        self.timeout_updates = []

    def settimeout(self, value):
        self.timeout_updates.append(value)


class MockResponse:
    status = 200

    def __init__(self):
        self.remaining = b'{}'

    def getheaders(self):
        return [('Content-Length', '2'), ('Connection', 'close')]

    def read(self, size):
        result, self.remaining = self.remaining[:size], self.remaining[size:]
        return result


class MockConnection:
    last_instance = None

    def __init__(self, *args, **kwargs):
        self.sock = MockSocket()
        self.retained_socket = self.sock
        MockConnection.last_instance = self

    def connect(self):
        pass

    def request(self, *args, **kwargs):
        assert kwargs['headers']['Accept-Encoding'] == 'identity'

    def getresponse(self):
        self.sock = None
        return MockResponse()

    def close(self):
        pass


with tempfile.TemporaryDirectory() as temp:
    helper.BASE = pathlib.Path(temp)
    helper.STATE = helper.BASE / 'state.json'
    helper.LEDGER = helper.BASE / 'requests.csv'
    start = helper.now()
    helper.save_json(helper.STATE, {'attempts': 0, 'received_bytes': 0, 'specimens': 0, 'halted': '', 'deadline_utc': (start + helper.dt.timedelta(minutes=1)).isoformat(), 'next_allowed_at': start.isoformat()})
    original_connection = helper.http.client.HTTPSConnection
    helper.http.client.HTTPSConnection = MockConnection
    try:
        receipt = helper.fetch(url)
    finally:
        helper.http.client.HTTPSConnection = original_connection
    assert receipt['outcome'] == 'success' and receipt['received_bytes'] == 2
    assert MockConnection.last_instance.sock is None
    assert len(MockConnection.last_instance.retained_socket.timeout_updates) >= 2
assert helper.parse_listing('https://www.sec.gov/Archives/edgar/full-index/', b'<a href="2010/">year</a>', 'html')[1] == [{'name': '2010', 'type': 'dir'}]
print('PASS mocked Connection:close response retains socket timeout updates; canonical directory HTML href parsing. Mock only; no SEC traffic.')

with tempfile.TemporaryDirectory() as temp:
    helper.BASE = pathlib.Path(temp)
    def synthetic_listing(url):
        pieces = url.split('/')
        if url in helper.ROOTS.values():
            children = [{'name': str(year), 'type': 'dir'} for year in range(2010, 2027)]
        elif pieces[-2].isdigit():
            children = [{'name': 'QTR' + str(quarter), 'type': 'dir'} for quarter in range(1, 5)]
        elif 'full-index' in url:
            children = [{'name': 'master.idx', 'type': 'file', 'size': '42'}]
        else:
            children = [{'name': 'master.20261001.idx', 'type': 'file', 'size': '42'}] if '/2026/QTR4/' in url else []
        return {'url': url, 'receipt_utc': '2026-10-05T00:00:00+00:00', 'evidence_id': 'OFFLINE-SYNTHETIC'}, children
    original_discover = helper.discover
    helper.discover = synthetic_listing
    try:
        helper.inventory()
    finally:
        helper.discover = original_discover
    rows = list(csv.DictReader((helper.BASE / 'quarterly.csv').open()))
    summaries = [row for row in rows if row['representation'] == 'quarter_summary']
    assert len(summaries) == len({row['quarter'] for row in summaries}) == 68
    assert sum(row['development_subset'] == 'true' for row in summaries) == 48
    assert all(row['source_status'] == 'available' for row in summaries)
    daily = list(csv.DictReader((helper.BASE / 'daily.csv').open()))
    handoff = [row for row in daily if row['representation'] == 'required_handoff_summary']
    assert len(handoff) == 1 and handoff[0]['outcome'] == 'listed_source_pending'
    assert len({row['directory_period'] for row in daily if row['representation'] == 'directory_summary' and row['directory_period'] != 'root'}) == 68
    try:
        helper.inventory()
    except RuntimeError as exc:
        assert 'overwrite' in str(exc)
    else:
        raise AssertionError('repeat inventory overwrote matrices')
print('PASS synthetic complete hierarchy inventory: 68 unique summaries/48 development, explicit handoff, 68 daily boundary units; repeat inventory refused. Synthetic only; no SEC traffic.')

class MockIncompleteChunkedResponse:
    status = 200

    def __init__(self):
        self.read_calls = 0

    def getheaders(self):
        return [('Transfer-Encoding', 'chunked')]

    def read(self, size):
        self.read_calls += 1
        if self.read_calls == 1:
            return b'prefix'
        assert size >= len(b'partial')
        raise helper.http.client.IncompleteRead(b'partial', 19)


class MockIncompleteConnection(MockConnection):
    def getresponse(self):
        return MockIncompleteChunkedResponse()


for byte_cap in (64, 13):
    with tempfile.TemporaryDirectory() as temp:
        helper.BASE = pathlib.Path(temp)
        helper.STATE = helper.BASE / 'state.json'
        helper.LEDGER = helper.BASE / 'requests.csv'
        start = helper.now()
        helper.save_json(helper.STATE, {'attempts': 4, 'received_bytes': 0, 'specimens': 0, 'halted': '', 'deadline_utc': (start + helper.dt.timedelta(minutes=1)).isoformat(), 'next_allowed_at': start.isoformat()})
        helper.write_csv(helper.LEDGER, helper.REQUEST_COLUMNS, [dict(zip(helper.REQUEST_COLUMNS, [f'SEC-{number:04d}', 'offline mock', '', '', url, '', 0, '', '', 1, 'prior mock attempt', '', 'failed'])) for number in range(1, 5)])
        original_connection, original_cap = helper.http.client.HTTPSConnection, helper.LIMIT_BYTES
        helper.http.client.HTTPSConnection, helper.LIMIT_BYTES = MockIncompleteConnection, byte_cap
        try:
            receipt = helper.fetch(url, specimen=True)
        finally:
            helper.http.client.HTTPSConnection, helper.LIMIT_BYTES = original_connection, original_cap
        retained = (helper.BASE / receipt['body_artifact']).read_bytes()
        assert retained == b'prefixpartial', (byte_cap, retained)
        assert receipt['received_bytes'] == len(retained) == 13
        assert receipt['sha256'] == helper.hashlib.sha256(retained).hexdigest()
        assert receipt['outcome'] == 'failed' and 'IncompleteRead' in receipt['error']
        assert helper.read_state()['received_bytes'] == 13
        assert helper.read_state()['specimens'] == 0
        last_row = list(csv.DictReader(helper.LEDGER.open()))[-1]
        assert int(last_row['received_bytes']) == 13 and last_row['outcome'] == 'failed'
print('PASS mocked chunked IncompleteRead: prefix+partial retained/hash/count, final failure, no completed specimen; sufficient and exact remaining-byte budgets. Mock only; no SEC traffic.')

class MemoryResponseSocket:
    def makefile(self, mode):
        import io
        return io.BytesIO(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n6\r\nprefix\r\n7\r\npart')


class RealChunkedIncompleteConnection(MockConnection):
    def getresponse(self):
        response = helper.http.client.HTTPResponse(MemoryResponseSocket())
        response.begin()
        return response


with tempfile.TemporaryDirectory() as temp:
    helper.BASE = pathlib.Path(temp)
    helper.STATE = helper.BASE / 'state.json'
    helper.LEDGER = helper.BASE / 'requests.csv'
    start = helper.now()
    helper.save_json(helper.STATE, {'attempts': 4, 'received_bytes': 0, 'specimens': 0, 'halted': '', 'deadline_utc': (start + helper.dt.timedelta(minutes=1)).isoformat(), 'next_allowed_at': start.isoformat()})
    helper.write_csv(helper.LEDGER, helper.REQUEST_COLUMNS, [dict(zip(helper.REQUEST_COLUMNS, [f'SEC-{number:04d}', 'offline mock', '', '', url, '', 0, '', '', 1, 'prior mock attempt', '', 'failed'])) for number in range(1, 5)])
    original_connection, original_cap = helper.http.client.HTTPSConnection, helper.LIMIT_BYTES
    helper.http.client.HTTPSConnection, helper.LIMIT_BYTES = RealChunkedIncompleteConnection, 13
    try:
        receipt = helper.fetch(url, specimen=True)
    finally:
        helper.http.client.HTTPSConnection, helper.LIMIT_BYTES = original_connection, original_cap
    retained = (helper.BASE / receipt['body_artifact']).read_bytes()
    assert retained == b'prefixpart', retained
    assert receipt['received_bytes'] == helper.read_state()['received_bytes'] == 10
    assert receipt['sha256'] == helper.hashlib.sha256(retained).hexdigest()
    assert receipt['outcome'] == 'failed' and helper.read_state()['specimens'] == 0
print('PASS real stdlib HTTPResponse over BytesIO truncated chunk: outer completed-prefix and chained current-chunk partial retained/hash/count; failed, no specimen. Offline only; no SEC traffic.')
