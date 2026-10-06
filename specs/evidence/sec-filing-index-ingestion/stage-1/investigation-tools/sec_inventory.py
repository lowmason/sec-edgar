"""Bounded Stage 1 investigation only. Root alone executes network commands."""
import argparse
import csv
import datetime as dt
import email.utils
import fcntl
import hashlib
import html.parser
import http.client
import json
import pathlib
import random
import re
import signal
import ssl
import time
import urllib.parse
import xml.etree.ElementTree as ET

BASE = pathlib.Path(__file__).resolve().parents[1]
STATE = BASE / 'sec-window-state.json'
LEDGER = BASE / 'requests.csv'
UA = 'Lowell Mason sec-edgar-ingest mason.lowell@mac.com'
LIMIT_BYTES = 536870912
LIMIT_ATTEMPTS = 240
DOCS = ['https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data',
        'https://www.sec.gov/about/developer-resources']
ROOTS = {f: f'https://www.sec.gov/Archives/edgar/{f}/index.json' for f in ['full-index', 'daily-index']}
REQUEST_COLUMNS = 'attempt_id issuer start_utc end_utc url status received_bytes body_sha256 response_headers_artifact exit_code retry_reason next_allowed_at outcome'.split()
QUARTER_COLUMNS = 'quarter development_subset requested_at listing_evidence_id discovered_url representation listed_size listed_size_unit source_status selection_reason gap_id'.split()
DAILY_COLUMNS = 'directory_period listing_evidence_id discovered_url listed_date representation handoff_relation outcome gap_id'.split()


def now():
    return dt.datetime.now(dt.timezone.utc)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def write_csv(path, columns, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def validate_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'www.sec.gov' or parsed.query or parsed.fragment:
        raise ValueError('Only canonical SEC HTTPS URLs without queries/fragments')
    if url in DOCS:
        return
    if not any(parsed.path.startswith('/Archives/edgar/' + family + '/') for family in ROOTS):
        raise ValueError('Outside accepted source families')
    if any(part in ('..', '.') for part in parsed.path.split('/')) or '%' in parsed.path:
        raise ValueError('Ambiguous path')


def child_url(listing_url, name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..'):
        raise ValueError(f'Unsafe child name {name!r}')
    parent = listing_url if listing_url.endswith('/') else listing_url.rsplit('/', 1)[0] + '/'
    url = parent + name
    validate_url(url)
    return url


def listing_url(parent, name):
    return child_url(parent, name) + '/index.json'


def read_state():
    if not STATE.exists():
        raise RuntimeError('Window is not activated')
    return json.loads(STATE.read_text())


def guard(state):
    if state.get('halted'):
        raise RuntimeError('Window halted: ' + state['halted'])
    if now() >= dt.datetime.fromisoformat(state['deadline_utc']):
        raise RuntimeError('Window expired')
    if state['attempts'] >= LIMIT_ATTEMPTS or state['received_bytes'] >= LIMIT_BYTES:
        raise RuntimeError('Shared budget exhausted')


def retry_delay(headers, attempt):
    delay = min(120, 2 * 2 ** (attempt - 1) + random.uniform(0, 1))
    for key, value in headers:
        if key.lower() == 'retry-after':
            try:
                delay = max(delay, float(value))
            except ValueError:
                try:
                    delay = max(delay, (email.utils.parsedate_to_datetime(value) - now()).total_seconds())
                except (ValueError, TypeError):
                    pass
    return delay


def fetch(url, specimen=False):
    validate_url(url)
    state = read_state()
    if specimen and state['specimens'] >= 12:
        raise RuntimeError('Specimen cap reached')
    prior_attempts = 0
    if LEDGER.exists():
        with LEDGER.open(newline='') as handle:
            prior_attempts = sum(row['url'] == url for row in csv.DictReader(handle))
    if prior_attempts >= 5:
        raise RuntimeError('URL already exhausted its five-attempt allowance')
    for attempt in range(prior_attempts + 1, 6):
        state = read_state()
        guard(state)
        allowed = dt.datetime.fromisoformat(state['next_allowed_at'])
        delay = max(0, (allowed - now()).total_seconds())
        if now() + dt.timedelta(seconds=delay) >= dt.datetime.fromisoformat(state['deadline_utc']):
            raise RuntimeError('Deferred: next allowed start outside window')
        if delay:
            time.sleep(delay)
        guard(state)
        start = now()
        state['attempts'] += 1
        state['next_allowed_at'] = (start + dt.timedelta(seconds=0.34)).isoformat()
        save_json(STATE, state)
        attempt_id = f"SEC-{state['attempts']:04d}"
        (BASE / 'listings').mkdir(parents=True, exist_ok=True)
        stem = BASE / 'listings' / attempt_id
        if stem.with_suffix('.headers.json').exists():
            raise RuntimeError('Refusing to overwrite retained attempt evidence')
        body_path = stem.with_suffix('.body')
        headers_path = stem.with_suffix('.headers.json')
        intent_path = stem.with_suffix('.intent.json')
        save_json(intent_path, {'request_headers': {'User-Agent': UA, 'Accept-Encoding': 'identity'}, 'budget_counter': dict(state), 'evidence_id': attempt_id, 'url': url, 'start_utc': start.isoformat(), 'outcome': 'attempt_started', 'received_bytes': 0, 'issuer': 'root chat only'})
        with LEDGER.open('a', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=REQUEST_COLUMNS)
            if handle.tell() == 0:
                writer.writeheader()
            writer.writerow(dict(zip(REQUEST_COLUMNS, [attempt_id, 'root chat only', start.isoformat(), '', url, '', 0, '', str(intent_path.relative_to(BASE)), '', '', state['next_allowed_at'], 'attempt_started'])))
        headers, status, received, error = [], '', 0, ''
        digest = hashlib.sha256()
        connection = None
        previous_handler = signal.getsignal(signal.SIGALRM)
        deadline = dt.datetime.fromisoformat(state['deadline_utc'])
        def remaining_window():
            remaining = (deadline - now()).total_seconds()
            if remaining <= 0:
                raise TimeoutError('Absolute window deadline reached')
            return remaining
        try:
            parsed = urllib.parse.urlsplit(url)
            connection = http.client.HTTPSConnection('www.sec.gov', timeout=15, context=ssl.create_default_context())
            def connection_alarm(signum, frame):
                raise TimeoutError('Connection including DNS exceeded 15 seconds')
            previous_handler = signal.signal(signal.SIGALRM, connection_alarm)
            signal.setitimer(signal.ITIMER_REAL, min(15, remaining_window()))
            try:
                connection.connect()
            finally:
                signal.setitimer(signal.ITIMER_REAL, remaining_window())
            response_socket = connection.sock
            response_socket.settimeout(min(60, remaining_window()))
            remaining_window()
            connection.request('GET', parsed.path, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'})
            remaining_window()
            response = connection.getresponse()
            status, headers = response.status, response.getheaders()
            with body_path.open('wb') as handle:
                while True:
                    remaining = LIMIT_BYTES - state['received_bytes']
                    if remaining <= 0:
                        state['halted'] = 'Received-byte cap reached during response'
                        raise RuntimeError(state['halted'])
                    response_socket.settimeout(min(60, remaining_window()))
                    incomplete_read = None
                    try:
                        chunk = response.read(min(65536, remaining))
                    except http.client.IncompleteRead as exc:
                        chunk = exc.partial
                        # _read_chunked chains the truncated current chunk separately.
                        cause = exc.__cause__
                        while isinstance(cause, http.client.IncompleteRead):
                            chunk += cause.partial
                            cause = cause.__cause__
                        incomplete_read = exc
                    if not chunk:
                        if incomplete_read is not None:
                            raise incomplete_read
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    state['received_bytes'] += len(chunk)
                    save_json(STATE, state)
                    if incomplete_read is not None:
                        raise incomplete_read
        except Exception as exc:
            error = f'{type(exc).__name__}: {exc}'
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
            if connection:
                connection.close()
        end = now()
        probe = b''
        if body_path.exists():
            with body_path.open('rb') as handle:
                probe = handle.read(262144).lower()
        lengths = [value for key, value in headers if key.lower() == 'content-length']
        if lengths:
            try:
                if len(set(lengths)) != 1 or int(lengths[0]) != received:
                    error = error or 'Content-Length mismatch; partial response quarantined'
            except ValueError:
                error = error or 'Invalid Content-Length; response quarantined'
        denial = status == 403 or any(term in probe for term in [b'undeclared automated tool', b'your request originates from an undeclared', b'request rate threshold exceeded', b'access denied'])
        if denial:
            state['halted'] = 'SEC 403 or explicit access-denial body'
        success = status == 200 and not error and not denial
        retry = not success and not denial and (error or status in (429, 500, 502, 503, 504)) and attempt < 5
        if retry:
            state['next_allowed_at'] = max(dt.datetime.fromisoformat(state['next_allowed_at']), end + dt.timedelta(seconds=retry_delay(headers, attempt))).isoformat()
        if success and specimen:
            state['specimens'] += 1
        outcome = 'success' if success else ('halted_access_denial' if denial else 'failed')
        metadata = {'evidence_id': attempt_id, 'url': url, 'start_utc': start.isoformat(), 'receipt_utc': end.isoformat(), 'status': status,
                    'headers': headers, 'transport': 'HTTPS TLS verified; transfer framing removed by http.client',
                    'content_encoding': next((v for k, v in headers if k.lower() == 'content-encoding'), 'identity'),
                    'redirect_chain': [], 'redirect_policy': 'never followed', 'received_bytes': received,
                    'sha256': digest.hexdigest(), 'body_artifact': str(body_path.relative_to(BASE)), 'error': error,
                    'intent_artifact': str(intent_path.relative_to(BASE)), 'schema': 'uninspected response entity bytes', 'outcome': outcome, 'specimen': specimen}
        save_json(headers_path, metadata)
        with LEDGER.open(newline='') as handle:
            ledger_rows = list(csv.DictReader(handle))
        terminal = dict(zip(REQUEST_COLUMNS, [attempt_id, 'root chat only', start.isoformat(), end.isoformat(), url, status, received, digest.hexdigest(), str(headers_path.relative_to(BASE)), 0 if success else 1, error or (str(status) if not success else ''), state['next_allowed_at'], outcome]))
        ledger_rows[-1] = terminal
        temporary_ledger = LEDGER.with_suffix('.csv.tmp')
        write_csv(temporary_ledger, REQUEST_COLUMNS, ledger_rows)
        temporary_ledger.replace(LEDGER)
        save_json(STATE, state)
        print(json.dumps(metadata), flush=True)
        if denial:
            raise RuntimeError(state['halted'])
        if not retry:
            return metadata
    return metadata


class DirectoryLinks(html.parser.HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.children = []

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        href = dict(attrs).get('href', '')
        if not href or href.startswith(('?', '#')):
            return
        resolved = urllib.parse.urljoin(self.base_url, href)
        path = urllib.parse.urlsplit(resolved).path
        name = path.rstrip('/').rsplit('/', 1)[-1]
        if name and name not in ('.', '..'):
            try:
                expected = child_url(self.base_url, name)
                validate_url(resolved)
            except ValueError:
                return
            if resolved.rstrip('/') == expected:
                self.children.append({'name': name, 'type': 'dir' if path.endswith('/') else 'file'})


def parse_listing(url, raw, representation):
    if representation == 'json':
        directory = json.loads(raw)['directory']
        children = directory['item']
        directory_name = directory.get('name')
    elif representation == 'xml':
        root = ET.fromstring(raw)
        children = [{child.tag: child.text or '' for child in item} for item in root.findall('.//item')]
        if not children and root.tag != 'directory':
            raise ValueError('Unrecognized XML directory schema')
        directory_name = root.findtext('name')
    else:
        parser = DirectoryLinks(url)
        parser.feed(raw.decode('utf-8', errors='strict'))
        children = parser.children
        if not children:
            raise ValueError('HTML has no validated directory entries; cannot establish empty listing')
        directory_name = None
    if not isinstance(children, list):
        raise ValueError('Directory entries must be a list')
    validated = []
    for child in children:
        if not isinstance(child, dict) or child.get('type') not in ('dir', 'file'):
            raise ValueError('Directory entry requires observed dir/file type')
        child_url(url, child['name'])
        validated.append(child)
    return directory_name, validated


def discover(url):
    for representation in ('json', 'xml', 'html'):
        candidate = url.rsplit('/', 1)[0] + '/' if representation == 'html' else url.rsplit('.', 1)[0] + '.' + representation
        metadata = fetch(candidate)
        if metadata['outcome'] != 'success':
            if metadata['status'] not in (404, 406):
                return metadata, None
            continue
        try:
            name, children = parse_listing(candidate, (BASE / metadata['body_artifact']).read_bytes(), representation)
            metadata.update(schema='SEC directory entries: ' + representation, directory_name=name, discovered_children=children,
                            selection_decision='Validated name and dir/file type; no source-body support claim')
            save_json(BASE / 'listings' / (metadata['evidence_id'] + '.headers.json'), metadata)
            return metadata, children
        except (ValueError, KeyError, TypeError, ET.ParseError) as exc:
            metadata['listing_error'] = str(exc)
            save_json(BASE / 'listings' / (metadata['evidence_id'] + '.headers.json'), metadata)
    return metadata, None


def directories(children, pattern):
    return sorted([c['name'] for c in children or [] if c.get('type') == 'dir' and re.fullmatch(pattern, c['name'])])


def inventory():
    if (BASE / 'quarterly.csv').exists() or (BASE / 'daily.csv').exists():
        raise RuntimeError('Refusing to overwrite previous inventory matrices')
    quarters, summaries = [], {}
    daily = [dict(zip(DAILY_COLUMNS, ['2026Q4', '', '', '20261001', 'required_handoff_summary', 'handoff', 'unattempted', 'GAP-D-HANDOFF']))]
    for year in range(2010, 2027):
        for quarter in range(1, 5):
            label = f'{year}Q{quarter}'
            summaries[label] = dict(zip(QUARTER_COLUMNS, [label, str(year >= 2015).lower(), '', '', '', 'quarter_summary', '', '', 'discovery_failed', 'Unattempted: hierarchy not inspected', 'GAP-Q-' + label]))
    try:
        meta, children = discover(ROOTS['full-index'])
        for row in summaries.values():
            row.update(requested_at=meta['receipt_utc'], listing_evidence_id=meta['evidence_id'], selection_reason='Root discovery failed' if children is None else 'Requested hierarchy child absent or uninspected')
        if children is None:
            return
        if children is not None:
            for child in children:
                if child['name'].startswith('master.'):
                    quarters.append(dict(zip(QUARTER_COLUMNS, ['2026Q4', 'true', meta['receipt_utc'], meta['evidence_id'], child_url(meta['url'], child['name']), child['name'], child.get('size', ''), 'listing-declared (unit unverified)', 'listed_source_pending', 'Current full-index root; relationship to year/QTR requires body comparison', ''])))
            for year in directories(children, r'20\d{2}'):
                if not 2010 <= int(year) <= 2026:
                    continue
                ym, yc = discover(listing_url(meta['url'], year))
                for label, row in summaries.items():
                    if label.startswith(year):
                        row.update(requested_at=ym['receipt_utc'], listing_evidence_id=ym['evidence_id'], selection_reason='Year discovery failed' if yc is None else 'Quarter child absent from inspected year listing')
                for qtr in directories(yc, r'QTR[1-4]'):
                    label = year + 'Q' + qtr[-1]
                    qm, qc = discover(listing_url(ym['url'], qtr))
                    row = summaries[label]
                    row.update(requested_at=qm['receipt_utc'], listing_evidence_id=qm['evidence_id'], discovered_url=qm['url'])
                    masters = [c for c in qc or [] if c['name'].startswith('master.')]
                    row.update(source_status='available' if masters else ('valid_no_source' if qc is not None else 'discovery_failed'), selection_reason='Listing only; no body collected', gap_id='' if masters else 'GAP-Q-' + label)
                    for child in masters:
                        quarters.append(dict(zip(QUARTER_COLUMNS, [label, str(int(year) >= 2015).lower(), qm['receipt_utc'], qm['evidence_id'], child_url(qm['url'], child['name']), child['name'], child.get('size', ''), 'listing-declared (unit unverified)', 'listed_source_pending', 'Observed master representation; Task 3 selects inspected alternative', ''])))
        dm, dc = discover(ROOTS['daily-index'])
        daily.append(dict(zip(DAILY_COLUMNS, ['root', dm['evidence_id'], dm['url'], '', 'directory_summary', 'Historical observation boundary', 'available' if dc is not None else 'discovery_failed', '' if dc is not None else 'GAP-D-ROOT'])))
        for year in directories(dc, r'20\d{2}'):
            if not 2010 <= int(year) <= 2026:
                continue
            ym, yc = discover(listing_url(dm['url'], year))
            qtrs = directories(yc, r'QTR[1-4]')
            selected = set(qtrs[:1] + qtrs[-1:])
            if year == '2026':
                selected.update(q for q in qtrs if q in ('QTR3', 'QTR4'))
            daily.append(dict(zip(DAILY_COLUMNS, [year, ym['evidence_id'], ym['url'], '', 'year_summary', 'Historical boundary', 'available' if yc is not None else 'discovery_failed', '' if yc is not None else 'GAP-D-' + year])))
            for qtr in qtrs:
                label = year + 'Q' + qtr[-1]
                if qtr not in selected:
                    daily.append(dict(zip(DAILY_COLUMNS, [label, ym['evidence_id'], listing_url(ym['url'], qtr), '', 'directory_summary', 'Historical boundary', 'listed_uninspected', 'GAP-D-' + label])))
                    continue
                qm, qc = discover(listing_url(ym['url'], qtr))
                daily.append(dict(zip(DAILY_COLUMNS, [label, qm['evidence_id'], qm['url'], '', 'directory_summary', 'handoff/current' if label == '2026Q4' else 'historical/preceding', 'available' if qc is not None else 'discovery_failed', '' if qc is not None else 'GAP-D-' + label])))
                if label == '2026Q4':
                    handoff = daily[0]
                    handoff.update(listing_evidence_id=qm['evidence_id'], discovered_url=qm['url'], outcome='discovery_failed' if qc is None else 'required_date_absent_in_listing')
                    if any('20261001' in c['name'] and c['name'].startswith('master.') for c in qc or []):
                        handoff.update(outcome='listed_source_pending', gap_id='')
                for child in qc or []:
                    if child['name'].startswith('master.'):
                        match = re.search(r'(\d{8})', child['name'])
                        date = match[1] if match else ''
                        daily.append(dict(zip(DAILY_COLUMNS, [label, qm['evidence_id'], child_url(qm['url'], child['name']), date, child['name'], 'handoff' if date == '20261001' else ('after_handoff' if date > '20261001' else 'before_handoff'), 'listed_source_pending', ''])))
    finally:
        observed_daily = {row['directory_period'] for row in daily if row['representation'] == 'directory_summary'}
        root_evidence = next((row['listing_evidence_id'] for row in daily if row['directory_period'] == 'root'), '')
        for label in summaries:
            if label not in observed_daily:
                daily.append(dict(zip(DAILY_COLUMNS, [label, root_evidence, '', '', 'directory_summary', 'Historical observation boundary', 'not_listed_or_uninspected', 'GAP-D-' + label])))
        write_csv(BASE / 'quarterly.csv', QUARTER_COLUMNS, list(summaries.values()) + quarters)
        write_csv(BASE / 'daily.csv', DAILY_COLUMNS, daily)


def recover_interrupted_attempts():
    if not STATE.exists():
        return
    state = read_state()
    rows = []
    if LEDGER.exists():
        with LEDGER.open(newline='') as handle:
            rows = list(csv.DictReader(handle))
    changed = False
    recorded = {row['attempt_id'] for row in rows}
    for number in range(1, state['attempts'] + 1):
        attempt_id = f'SEC-{number:04d}'
        if attempt_id in recorded:
            continue
        intent_path = BASE / 'listings' / (attempt_id + '.intent.json')
        intent = json.loads(intent_path.read_text()) if intent_path.exists() else {}
        rows.append(dict(zip(REQUEST_COLUMNS, [attempt_id, 'root chat only', intent.get('start_utc', ''), '', intent.get('url', 'unknown; interrupted before intent write'), '', 0, '', str(intent_path.relative_to(BASE)), '', '', '', 'attempt_started'])))
    for row in rows:
        if row['outcome'] != 'attempt_started':
            continue
        path = BASE / 'listings' / (row['attempt_id'] + '.body')
        digest = hashlib.sha256()
        count = 0
        if path.exists():
            with path.open('rb') as handle:
                for chunk in iter(lambda: handle.read(65536), b''):
                    digest.update(chunk)
                    count += len(chunk)
        row.update(end_utc=now().isoformat(), received_bytes=count, body_sha256=digest.hexdigest(),
                   exit_code=1, retry_reason='Interrupted attempt: response fields unknown; no automatic replay', outcome='interrupted_unknown')
        changed = True
    actual_bytes = sum(path.stat().st_size for path in (BASE / 'listings').glob('SEC-*.body'))
    state['received_bytes'] = max(state['received_bytes'], actual_bytes)
    if changed:
        state['halted'] = 'Interrupted attempt requires root reconciliation; no silent replay'
        temporary = LEDGER.with_suffix('.csv.tmp')
        write_csv(temporary, REQUEST_COLUMNS, rows)
        temporary.replace(LEDGER)
    save_json(STATE, state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['activate', 'inventory', 'fetch', 'status', 'close'])
    parser.add_argument('--root-issuer', action='store_true')
    parser.add_argument('--url')
    parser.add_argument('--specimen', action='store_true')
    args = parser.parse_args()
    with (BASE / 'sec-window.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == 'activate':
            if not args.root_issuer or STATE.exists():
                raise RuntimeError('Explicit root issuer required; existing window cannot reactivate')
            acceptance = json.loads((BASE / 'sec-window-owner-acceptance.json').read_text())
            if acceptance['exact_owner_reply'] != 'Confirm window; all other SEC traffic paused':
                raise RuntimeError('Owner acceptance does not match')
            start = now()
            save_json(STATE, {'start_utc': start.isoformat(), 'deadline_utc': (start + dt.timedelta(minutes=45)).isoformat(), 'issuer': 'root chat only', 'attempts': 0, 'received_bytes': 0, 'specimens': 0, 'next_allowed_at': start.isoformat(), 'halted': ''})
        elif args.command == 'status':
            recover_interrupted_attempts()
            print(json.dumps(read_state(), indent=2))
        elif args.command == 'close':
            state = read_state()
            state['closed_utc'] = now().isoformat()
            state['halted'] = state['halted'] or 'Window explicitly closed by root'
            save_json(STATE, state)
        else:
            if not args.root_issuer:
                raise RuntimeError('Only explicit root issuer may make SEC requests')
            recover_interrupted_attempts()
            if args.command == 'inventory':
                inventory()
            else:
                fetch(args.url, args.specimen)


if __name__ == '__main__':
    main()
