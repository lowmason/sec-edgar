# Task 6 fresh review
Reviewer: /root/task6_review, GPT-6.1 Max, read-only; frozen 50b2756330cbef91b5c664a5f4cc72c2f5c35626..c51fe3b3350d71195ed94880359304ab3634aca9.
Spec Compliance: FAIL. Task Quality: Needs fixes. Critical: none. Minor: none.

## Important 1: source-workset producer path breaks approved collection handoff
Discovery.py:335 writes only worksets/source/<id>.json. Task7 brief:73/119 requires worksets/sec/source/sha256=<id>/workset.json and digest/path confirmation. support.py:941 repeats private wrong path and conceals mismatch.
Remedy: publish same canonical immutable bytes at approved Task7 source path. Update harness and add an independent contract assertion decoding exact workset identity. Preserve existing hash/model contract.

## Important 2: cached receipt transport provenance ignored
Discovery.py:225 verifies body/receipt bytes, URL/status/completeness/hash/count, selection and members, but ignores metadata.context. Focused real-store probe changed config_sha256 to b*64, recomputed receipt object hash/path/count, replaced actual DirectoryProgress using row.version. Resume accepted same complete workset with zero new requests.
Remedy: parse persisted transport RunContext; validate immutable run/command/config/image/parser/schema provenance against frozen session. Permit execution/attempt differences required for resumed requests. Add focused mismatch regression beside metadata corruption tests.
Probe output (exit0, offline frozen no-sync, temporary cache/stores):
result: mismatching cached config accepted; complete=True; same_workset=True; new_requests=0
origin_config=a26ccc30b63f12a6118425855575bc73ec04d9409342650a87bb4926b0636ccf; cached_receipt_config=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
Exact behavioral probe reconstructed:
from support import discovery_harness, listing_response
from datetime import date
import hashlib,json
from sec_edgar_ingest.models import canonical_json
h=discovery_harness(None, {'2026Q4':[listing_response('2026Q4',['master.20261001.idx'])]})
first=h.run('daily',date(2026,10,6),'receipt-context-probe')
url=h.url('2026Q4'); row=h.state.directory_progress('receipt-context-probe',url); value=row.to_mapping()['value']
metadata=json.loads(h.objects.read(value['evidence']['receipt_path'])); metadata['context']['config_sha256']='b'*64
changed=canonical_json(metadata); digest=hashlib.sha256(changed).hexdigest(); path=f'worksets/discovery/listings/receipts/sha256={digest}.json'
h.objects.put_once(path,changed); value['evidence'].update(receipt_path=path,receipt_sha256=digest,receipt_byte_count=len(changed))
key=hashlib.sha256(canonical_json(['receipt-context-probe',url])).hexdigest(); h.store.replace('DirectoryProgress',key,value,row.version)
before=len(h.attempted_urls); resumed=h.run('daily',date(2026,10,6),'receipt-context-probe')
print(resumed.discovery_complete,resumed.workset_id==first.workset_id,len(h.attempted_urls)-before); h.close()

## Verification and strengths
Read supplied diff once in sequential chunks; no Git/source mutations/nested agents/live access. Existing logs: discovery40 tests/6.433s OK; full215/19.767s OK; warning/error searches no matches. No suite reruns. First probe failed before Python because default UV cache restricted; successful probe explicitly temporary cache. Metadata-only instrumentation confirmed path line335; earlier False anchor was Instruction.starts_line instrumentation artifact.
Trusted retained listing schemas/immediate children/duplicates; original evidence durable before progress; generation-safe gap CAS; full frozen inventory boundary checks; older pending/failed sources and ancestors revisited; all9ownedpaths corresponding hunks. Original/sidecar hashes verified, synthetic provenance separate.
Azure logical routing probe actual table_for: DirectoryProgress/DiscoverySession/DiscoveryBoundary -> SourceState; Failure -> Attempts. Exit0.

## Controller cross-task obligations
- Verify actual discovery-to-collection digest/path integration in Task7 after path fix.
- Earlier ownership/transport gates remain authoritative; Task6 budget/accounting test does not prove live deployment.
- Task8 endpoint owner decision pending. New daily-session current-quarter guard rejects impossible endpoint before HTTP. No waiver.
Full reviewer response, exact command/stdout and line links also retained in conversation; this receipt preserves operative findings and behavior.
