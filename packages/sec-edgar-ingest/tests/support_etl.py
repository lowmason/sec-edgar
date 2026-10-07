"""Real immutable fixture setup for offline ETL tests."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from sec_edgar_ingest.config import pin_context
from support import fixture_context, fixture_settings


def etl_context(parser_version='fixture-index-parser-v1', command='transform', attempt='etl1'):
    settings = fixture_settings(etl={'parser_version': parser_version})
    started = datetime.now(timezone.utc)
    context = replace(fixture_context(), command=command, attempt_id=attempt,
                      parser_version=parser_version, config_sha256=settings.config_sha256,
                      started_at=started, deadline=started + timedelta(seconds=3600),
                      effective_config={}, pinned_on=None)
    return settings, pin_context(settings, context, started.date())[0]


def seed_snapshot(root, source, body):
    from sec_edgar_ingest.models import Binding
    from sec_edgar_ingest.state import AcquisitionState
    from sec_edgar_ingest.worksets import encode_workset, make_snapshot_workset
    from support import fixture_snapshot, fixture_workset, store_bundle
    store, objects, leases = store_bundle(root)
    leases.close()
    source_set = fixture_workset(members=(source,))
    snapshot = fixture_snapshot(source, body)
    objects.put_once(snapshot.raw_path, body)
    objects.put_once(f'worksets/sec/source/sha256={source_set.workset_id}/workset.json',
                     encode_workset(source_set))
    acquisition = AcquisitionState(store)
    acquisition.remember_snapshot(snapshot)
    acquisition.bind_once(Binding(source_set.workset_id, source.source_id, snapshot.sha256))
    snapshot_set = make_snapshot_workset(source_set, (snapshot,))
    objects.put_once(f'worksets/sec/snapshot/sha256={snapshot_set.workset_id}/workset.json',
                     encode_workset(snapshot_set))
    return store, objects, snapshot_set
