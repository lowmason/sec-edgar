"""Offline bounded source observations; this is not a production parser."""
import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import zipfile

BASE = pathlib.Path(__file__).resolve().parents[1]
EXPANSION_CAP = 512 * 1024 * 1024
QUARTERLY_HEADER = 'CIK|Company Name|Form Type|Date Filed|Filename'
DAILY_HEADER = 'CIK|Company Name|Form Type|Date Filed|File Name'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect_archive(original, scratch):
    with zipfile.ZipFile(original) as archive:
        members = archive.infolist()
        report = [{'name': m.filename, 'codec': m.compress_type, 'compressed_bytes': m.compress_size,
                   'expanded_bytes': m.file_size, 'crc32': f'{m.CRC:08x}', 'flags': m.flag_bits} for m in members]
        if len(members) != 1 or members[0].filename != 'master.idx':
            raise ValueError(f'Unexpected archive members: {report}')
        member = members[0]
        if member.flag_bits & 1 or member.file_size > EXPANSION_CAP:
            raise ValueError('Encrypted or over-cap member')
        target = scratch / 'master.idx'
        total = 0
        with archive.open(member) as source, target.open('xb') as out:
            while block := source.read(1024 * 1024):
                total += len(block)
                if total > EXPANSION_CAP:
                    raise ValueError('Actual expansion cap exceeded')
                out.write(block)
        if total != member.file_size:
            raise ValueError('Expanded length mismatch')
        return target.read_bytes(), report


def observe_text(data):
    failures = []
    for encoding in ('ascii', 'utf-8'):
        try:
            text = data.decode(encoding, errors='strict')
            break
        except UnicodeDecodeError as exc:
            failures.append({'encoding': encoding, 'offset': exc.start, 'reason': exc.reason})
    else:
        raise ValueError(f'Strict selected decoders failed: {failures}')
    lines = text.splitlines()
    recognized_headers = [header for header in (QUARTERLY_HEADER, DAILY_HEADER) if header in lines]
    if len(recognized_headers) != 1:
        raise ValueError('Unknown or ambiguous column header')
    column_header = recognized_headers[0]
    header_position = lines.index(column_header)
    text_family = 'quarterly ISO-date master' if column_header == QUARTERLY_HEADER else 'daily compact-date master'
    rows = [line for line in lines[header_position + 1:] if line and not set(line) <= {'-'}]
    field_counts = collections.Counter()
    path_families = collections.Counter()
    date_counts = collections.Counter()
    samples = {}
    nonextractable = []
    invalid_dates = []
    date_shapes = collections.Counter()
    for row in rows:
        fields = row.split('|')
        field_counts[len(fields)] += 1
        if len(fields) != 5:
            samples.setdefault('unexpected_field_count', row)
            continue
        date_counts[fields[3]] += 1
        date_shapes['YYYY-MM-DD' if re.fullmatch(r'\d{4}-\d{2}-\d{2}', fields[3]) else 'YYYYMMDD' if re.fullmatch(r'\d{8}', fields[3]) else 'other'] += 1
        try:
            datetime.date.fromisoformat(fields[3])
        except ValueError:
            invalid_dates.append(fields[3])
        path = fields[4]
        if re.fullmatch(r'edgar/data/\d+/\d{10}-\d{2}-\d{6}\.txt', path):
            family = 'edgar/data/CIK/dashed-accession.txt'
        elif re.fullmatch(r'edgar/data/\d+/\d{18}/[^/]+', path):
            family = 'edgar/data/CIK/undashed-accession/member'
        else:
            family = 'other (nullable accession; needs disposition)'
            if len(nonextractable) < 8:
                nonextractable.append(row)
        path_families[family] += 1
        samples.setdefault(family, row)
    return {'text_family': text_family, 'column_header': column_header, 'date_shape_counts': dict(date_shapes), 'strict_encoding': encoding, 'decoder_failures': failures, 'bom_hex': data[:3].hex() if data.startswith(b'\xef\xbb\xbf') else None,
            'newline_counts': {'crlf': data.count(b'\r\n'), 'lone_lf': data.count(b'\n') - data.count(b'\r\n'), 'lone_cr': data.count(b'\r') - data.count(b'\r\n')},
            'header_lines': lines[:header_position + 2], 'separator': '|', 'scan_boundary': 'Every nonempty post-header row in retained body',
            'row_count': len(rows), 'field_count_distribution': dict(field_counts), 'path_families': dict(path_families),
            'minimum_filing_date': min(date_counts) if date_counts else None, 'maximum_filing_date': max(date_counts) if date_counts else None,
            'date_bound_raw_rows': {'minimum': next((row for row in rows if len(row.split('|')) == 5 and row.split('|')[3] == min(date_counts)), None), 'maximum': next((row for row in rows if len(row.split('|')) == 5 and row.split('|')[3] == max(date_counts)), None)} if date_counts else {},
            'invalid_dates': invalid_dates[:8], 'representative_raw_rows': samples, 'nonextractable_examples': nonextractable,
            'representative_fields': rows[0].split('|') if rows else [], 'non_ascii_byte_count': sum(c > 127 for c in data)}


def inspect(evidence_id):
    metadata = json.loads((BASE / 'listings' / f'{evidence_id}.headers.json').read_text())
    if metadata['outcome'] != 'success' or not metadata['specimen'] or metadata['content_encoding'] != 'identity':
        raise ValueError('Not a successful selected identity specimen')
    body = (BASE / metadata['body_artifact']).read_bytes()
    if len(body) != metadata['received_bytes'] or digest(body) != metadata['sha256']:
        raise ValueError('Original receipt integrity mismatch')
    headers = {key.lower(): value for key, value in metadata['headers']}
    if 'content-length' in headers and int(headers['content-length']) != len(body):
        raise ValueError('Content-Length mismatch')
    extension = pathlib.PurePosixPath(metadata['url']).suffix
    if extension not in {'.zip', '.idx'}:
        raise ValueError('Unselected representation')
    directory = BASE / 'specimens'
    directory.mkdir(exist_ok=True)
    original = directory / f'{digest(body)}{extension}'
    if original.exists() and original.read_bytes() != body:
        raise ValueError('Hash-named original collision')
    if not original.exists():
        original.write_bytes(body)
    with tempfile.TemporaryDirectory(prefix='sec-edgar-task3-', dir='/private/tmp') as scratch_name:
        scratch = pathlib.Path(scratch_name)
        if extension == '.zip':
            expanded, members = inspect_archive(original, scratch)
            derivative = directory / f'{digest(expanded)}.decoded.idx'
            if not derivative.exists():
                shutil.copyfile(scratch / 'master.idx', derivative)
        else:
            expanded, members, derivative = body, [], None
        observations = observe_text(expanded)
    paths = [original] + ([derivative] if derivative else [])
    verification = subprocess.run(['shasum', '-a', '256', *map(str, paths)], capture_output=True, text=True, check=True)
    report = {'evidence_id': evidence_id, 'url': metadata['url'], 'receipt_artifact': f'listings/{evidence_id}.headers.json',
              'original_path': str(original.relative_to(BASE)), 'original_bytes': len(body), 'original_sha256': digest(body),
              'original_extension': extension, 'transport_interpretation': metadata['transport'], 'content_encoding': metadata['content_encoding'],
              'advertised_content_length': headers.get('content-length'), 'content_length_comparison': 'equal' if 'content-length' in headers else 'not advertised',
              'mime_type': headers.get('content-type'), 'last_modified': headers.get('last-modified'), 'etag': headers.get('etag'),
              'receipt_utc': metadata['receipt_utc'], 'status': metadata['status'], 'user_agent': 'Lowell Mason sec-edgar-ingest mason.lowell@mac.com',
              'archive_members': members, 'archive_integrity': 'zipfile streaming read checked member CRC, exact expanded length; exit 0' if members else 'not an archive',
              'expansion_cap_bytes': EXPANSION_CAP, 'expanded_bytes': len(expanded), 'expansion_ratio': len(expanded) / len(body),
              'derivative_path': str(derivative.relative_to(BASE)) if derivative else None, 'derivative_sha256': digest(expanded) if derivative else None,
              'independent_shasum_command': verification.args, 'independent_shasum_exit_code': verification.returncode, 'independent_shasum_stdout': verification.stdout,
              'observations': observations}
    (directory / f'{evidence_id}.inspection.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'evidence_id': evidence_id, 'original_bytes': len(body), 'expanded_bytes': len(expanded), 'observations': observations}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('evidence_id')
    inspect(parser.parse_args().evidence_id)
