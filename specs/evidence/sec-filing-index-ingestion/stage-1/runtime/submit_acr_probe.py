"""Root-only reviewed ACR submission; no automatic scheduling retries or secret logs."""
import argparse
import hashlib
import json
import logging
import os
import re
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

SUBSCRIPTION = '3c92a216-8ed6-4897-b741-11ed287b8617'
GROUP = 'rg-sec-edgar-stage1-probe-20261005'
REGISTRY = 'secedgarstage1probe20261005b8617'
API_VERSION = '2025-03-01-preview'

def verify_context(context, manifest):
    expected = manifest['files']
    assert str(context) == manifest['context']
    paths = list(context.rglob('*'))
    assert not any(path.is_symlink() for path in paths)
    actual = {str(path.relative_to(context)) for path in paths if path.is_file()}
    assert actual == set(expected), 'Context contains missing/extra files'
    for name, item in expected.items():
        path = context/name
        assert path.stat().st_size == item['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
    assert manifest['total_bytes'] <= 20*1024*1024
    assert 'Dockerfile' in expected and '.dockerignore' in expected

def persist(destination, receipt):
    body = json.dumps(receipt,indent=2)+'\n'
    with destination.open('w') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())

def build_request(source):
    from azure.mgmt.containerregistrytasks.models import AgentProperties, DockerBuildRequest, PlatformProperties
    request = DockerBuildRequest(docker_file_path='Dockerfile',platform=PlatformProperties(os='Linux',architecture='amd64'),
        agent_configuration=AgentProperties(cpu=2),no_cache=True,is_push_enabled=False,image_names=[],
        timeout=1800,source_location=source,arguments=[],is_archive_enabled=False)
    serialized = request.as_dict()
    assert serialized['agentConfiguration']['cpu'] == 2
    assert serialized['noCache'] is True and serialized['isPushEnabled'] is False
    assert serialized['timeout'] == 1800
    assert serialized['platform'] == {'os':'Linux','architecture':'amd64'}
    return request,serialized

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context',required=True)
    parser.add_argument('--allowlist',required=True)
    parser.add_argument('--receipt-dir',required=True)
    parser.add_argument('--ordinal',type=int,required=True)
    parser.add_argument('--prepare-only',action='store_true')
    args = parser.parse_args()
    assert 1 <= args.ordinal <= 4
    context = Path(args.context)
    manifest = json.loads(Path(args.allowlist).read_text())
    verify_context(context,manifest)
    destination = Path(args.receipt_dir)
    destination.mkdir(exist_ok=False)
    receipt_path = destination/'submission.json'
    archive = destination/'context.tar.gz'
    with tarfile.open(archive,'w:gz') as bundle:
        for name in sorted(manifest['files']):
            bundle.add(context/name,arcname=name,recursive=False)
    request,serialized = build_request('REDACTED_RELATIVE_UPLOADED_CONTEXT')
    receipt = {'subscription':SUBSCRIPTION,'group':GROUP,'registry':REGISTRY,'api_version':API_VERSION,
        'ordinal':args.ordinal,'context':str(context),'allowlist_sha256':hashlib.sha256(Path(args.allowlist).read_bytes()).hexdigest(),
        'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size,
        'request':serialized,'started_utc':datetime.now(timezone.utc).isoformat(),'phase':'prepared_not_submitted',
        'no_secret_or_sas_logging':True,'retry_total':0}
    persist(receipt_path,receipt)
    if args.prepare_only:
        print(json.dumps({'phase':receipt['phase'],'receipt':str(receipt_path),'request':serialized},indent=2))
        return 0
    logging.disable(logging.CRITICAL)
    client = uploader = None
    try:
        from azure.cli.core import get_default_cli
        from azure.cli.core.commands.client_factory import get_mgmt_service_client
        from azure.cli.core.profiles import ResourceType
        from azure.storage.blob import BlobClient
        client = get_mgmt_service_client(get_default_cli(),ResourceType.MGMT_CONTAINERREGISTRYTASKS,
                                         subscription_id=SUBSCRIPTION,api_version=API_VERSION,retry_total=0,
                                         connection_timeout=30,read_timeout=60)
        registry = client.registries
        receipt['phase'] = 'upload_requested_not_scheduled'
        persist(receipt_path,receipt)
        upload = registry.get_build_source_upload_url(GROUP,REGISTRY)
        assert upload.upload_url and upload.relative_path
        assert not re.match(r'https?://',upload.relative_path) and '?' not in upload.relative_path
        uploader = BlobClient.from_blob_url(upload.upload_url,connection_timeout=60,read_timeout=60,retry_total=0)
        with archive.open('rb') as stream:
            uploader.upload_blob(data=stream,blob_type='BlockBlob',overwrite=True,max_concurrency=1,timeout=300)
        verify_context(context,manifest)
        request,_ = build_request(upload.relative_path)
        receipt['phase'] = 'schedule_started_unknown_outcome'
        receipt['schedule_started_utc'] = datetime.now(timezone.utc).isoformat()
        persist(receipt_path,receipt)
        queued = registry.schedule_run(resource_group_name=GROUP,registry_name=REGISTRY,run_request=request)
        assert queued.run_id and re.fullmatch(r'[A-Za-z0-9-]+',queued.run_id)
        receipt.update({'phase':'scheduled_run_id_retained','run_id':queued.run_id,
                        'initial_status':queued.status,'scheduled_utc':datetime.now(timezone.utc).isoformat()})
        persist(receipt_path,receipt)
        print(json.dumps({'run_id':queued.run_id,'receipt':str(receipt_path),'initial_status':queued.status}),flush=True)
        return 0
    except Exception as error:
        receipt['error_type'] = type(error).__name__
        receipt['http_status'] = getattr(getattr(error,'response',None),'status_code',None)
        service_code = getattr(getattr(error,'error',None),'code',None)
        receipt['service_error_code'] = service_code if isinstance(service_code,str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',service_code) else None
        receipt['ended_utc'] = datetime.now(timezone.utc).isoformat()
        persist(receipt_path,receipt)
        print(json.dumps({'phase':receipt['phase'],'error_type':receipt['error_type'],'http_status':receipt['http_status'],
                          'receipt':str(receipt_path),'instruction':'Root must reconcile unknown schedule outcome before any resubmission.'}),flush=True)
        return 1
    finally:
        for service in (uploader,client):
            if service is not None:
                try:
                    service.close()
                except Exception:
                    pass

if __name__ == '__main__':
    sys.exit(main())
