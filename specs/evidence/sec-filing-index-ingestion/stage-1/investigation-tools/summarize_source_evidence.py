"""Offline synthesis of retained observations and inventory labels."""
import collections
import csv
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parents[1]
reports = [json.loads(path.read_text()) for path in sorted((BASE / 'specimens').glob('SEC-*.inspection.json'))]
by_url = {report['url']: report for report in reports}
for name in ('quarterly.csv', 'daily.csv'):
    with (BASE / name).open(newline='') as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    if name == 'daily.csv':
        fields = fields + [field for field in ('inspection_evidence_id', 'inspection_artifact') if field not in fields]
    for row in rows:
        report = by_url.get(row['discovered_url'])
        if report:
            if name == 'quarterly.csv':
                row['source_status'] = 'retained_inspected_specimen'
                row['selection_reason'] = f"Task 3 selected {report['evidence_id']}; observations specimens/{report['evidence_id']}.inspection.json; original {report['original_path']}; full retained-row scan only; production parser support pending"
            else:
                row['outcome'] = 'retained_inspected_specimen'
                row['inspection_evidence_id'] = report['evidence_id']
                row['inspection_artifact'] = f"specimens/{report['evidence_id']}.inspection.json"
    temporary = (BASE / name).with_suffix('.task3.tmp')
    with temporary.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(BASE / name)
quarterly = list(csv.DictReader((BASE / 'quarterly.csv').open()))
volumes = {}
for representation in sorted({row['representation'] for row in quarterly if row['representation'] != 'quarter_summary'}):
    rows = [row for row in quarterly if row['representation'] == representation and row['discovered_url'] != 'https://www.sec.gov/Archives/edgar/full-index/' + representation]
    labels = collections.Counter()
    estimate = 0
    unknown = []
    for row in rows:
        match = re.fullmatch(r'([\d.]+)\s*(KB|MB|GB|B)', row['listed_size'])
        if match:
            magnitude, unit = match.groups()
            labels[unit] += float(magnitude)
            estimate += float(magnitude) * {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}[unit]
        else:
            unknown.append(row['discovered_url'])
    volumes[representation] = {'quarter_children_count': len(rows), 'sum_by_retained_label_unit': dict(labels), 'assumed_binary_scale_total_bytes': estimate,
                               'unknown_size_children': unknown, 'assumption': 'KB/MB/GB treated as 1024-based for planning only; SEC label scaling and rounding unverified; not actual received bytes'}
zip_rows = [row for row in quarterly if row['representation'] == 'master.zip']
def size_estimate(row):
    match = re.fullmatch(r'([\d.]+)\s*(KB|MB|GB|B)', row['listed_size'])
    return float(match[1]) * {'B':1,'KB':1024,'MB':1024**2,'GB':1024**3}[match[2]] if match else -1
largest_listed = max(zip_rows, key=size_estimate)
largest_retained = max(reports, key=lambda report: report['original_bytes'])
unique_originals = {report['original_path']: report['original_bytes'] for report in reports}
unique_derivatives = {report['derivative_path']: report['expanded_bytes'] for report in reports if report['derivative_path']}
original_sum = sum(unique_originals.values())
derivative_sum = sum(unique_derivatives.values())
largest_expanded = max(report['expanded_bytes'] for report in reports)
plan = {'simultaneous_original_archives_or_idx_bytes': original_sum, 'expanded_derivatives_bytes': derivative_sum,
        'planned_observation_output_scratch_bytes_assumed': largest_expanded, 'candidate_generation_scratch_bytes_assumed': 2 * largest_expanded,
        'installer_runtime_log_reserve_bytes_assumed': 1024**3}
largest_unit = max(reports, key=lambda report: report['original_bytes'] + report['expanded_bytes'])
unit_plan = {'one_original_bytes_measured': largest_unit['original_bytes'], 'one_expanded_bytes_measured': largest_unit['expanded_bytes'], 'observation_output_scratch_bytes_assumed': largest_expanded, 'candidate_generation_scratch_bytes_assumed': 2 * largest_expanded, 'installer_runtime_log_reserve_bytes_assumed': 1024**3}
root = by_url.get('https://www.sec.gov/Archives/edgar/full-index/master.zip')
quarter = by_url.get('https://www.sec.gov/Archives/edgar/full-index/2026/QTR4/master.zip')
result = {'selected_receipts_count':len(reports), 'distinct_original_files_count': len(unique_originals), 'unique_original_bytes': original_sum,
          'distinct_derivative_files_count': len(unique_derivatives), 'unique_derivative_bytes': derivative_sum,
          'quarterly_listed_volume_by_representation':volumes, 'largest_listed_selected_representation':largest_listed,
          'largest_listed_any_representation': max([row for row in quarterly if row['representation'] != 'quarter_summary'], key=size_estimate), 'largest_retained_source': {'evidence_id':largest_retained['evidence_id'], 'bytes':largest_retained['original_bytes']},
          'archive_expansion_ratios': {report['evidence_id']:report['expansion_ratio'] for report in reports if report['archive_members']},
          'bounded_one_source_unit_peak_terms':unit_plan, 'bounded_one_source_unit_peak_assumed_bytes':sum(unit_plan.values()), 'temporary_peak_terms':plan,'temporary_peak_assumed_bytes':sum(plan.values()), 'documented_candidate_ephemeral_capacity_bytes':8*1024**3,
          'capacity_evidence':'provider/preparation/20261005T230634Z/storage-mounts.web-extract.txt lines 44-53; >1 vCPU gives 8 GiB; documentation only',
          'root_relationship': {'original_bytes_equal': root['original_sha256']==quarter['original_sha256'], 'decoded_bytes_equal':root['derivative_sha256']==quarter['derivative_sha256']} if root and quarter else 'pending',
          'limitation':'Largest retained expansion is a sample observation, not an all-quarter upper bound. Scratch/reserve assumptions are not measured process usage, memory fit or runtime fit; no integrated Azure behavior verified.'}
(BASE / 'specimens' / 'volume-assessment.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
planned = [
 ('earliest intended', 'https://www.sec.gov/Archives/edgar/full-index/2010/QTR1/master.zip'),
 ('development boundary', 'https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/master.zip'),
 ('latest closed quarter', 'https://www.sec.gov/Archives/edgar/full-index/2026/QTR3/master.zip'),
 ('open quarter', 'https://www.sec.gov/Archives/edgar/full-index/2026/QTR4/master.zip'),
 ('root/open relationship', 'https://www.sec.gov/Archives/edgar/full-index/master.zip'),
 ('closed/open daily before', 'https://www.sec.gov/Archives/edgar/daily-index/2026/QTR3/master.20260930.idx'),
 ('handoff and closed/open daily after', 'https://www.sec.gov/Archives/edgar/daily-index/2026/QTR4/master.20261001.idx'),
 ('already-published daily', 'https://www.sec.gov/Archives/edgar/daily-index/2026/QTR4/master.20261002.idx'),
 ('year-transition daily before', 'https://www.sec.gov/Archives/edgar/daily-index/2025/QTR4/master.20251231.idx'),
 ('year-transition daily after', 'https://www.sec.gov/Archives/edgar/daily-index/2026/QTR1/master.20260102.idx'),
]
inventory_rows = quarterly + list(csv.DictReader((BASE/'daily.csv').open()))
matrix = []
for role, url in planned:
    listing = next(row for row in inventory_rows if row['discovered_url'] == url)
    entry = {'role':role,'url':url,'listing_evidence_id':listing['listing_evidence_id']}
    report = by_url.get(url)
    if report:
        observation = report['observations']
        entry.update(status='fully inspected retained specimen', evidence_id=report['evidence_id'], inspection=f"specimens/{report['evidence_id']}.inspection.json", original_bytes=report['original_bytes'],expanded_bytes=report['expanded_bytes'],original_sha256=report['original_sha256'],derivative_sha256=report['derivative_sha256'],row_count=observation['row_count'],filing_date_bounds=[observation['minimum_filing_date'],observation['maximum_filing_date']],text_family=observation['text_family'],newline_counts=observation['newline_counts'])
    else:
        entry['status']='pending; no complete inspection support claim'
    matrix.append(entry)
(BASE/'specimens/matrix.json').write_text(json.dumps({'planned_receipt_specimens':10,'fully_inspected':len(reports),'selected_families':['quarterly ZIP/master.idx ISO-date master','daily uncompressed compact-date master'],'owner_continuation':'daily-family-continuation-acceptance.json','matrix':matrix},indent=2)+'\n')
