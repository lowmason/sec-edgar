"""Validated builders shared by offline acquisition tests."""
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sec_edgar_ingest.config import Settings
    from sec_edgar_ingest.models import RunContext, Source, SourceWorkset

FIXTURE_CONFIG = Path(__file__).parent / "fixtures/config/local.json"


def fixture_settings(**overrides: object) -> "Settings":
    from sec_edgar_ingest.config import Settings
    value = json.loads(FIXTURE_CONFIG.read_text())
    for key, override in overrides.items():
        if isinstance(override, dict) and isinstance(value.get(key), dict):
            value[key].update(override)
        else:
            value[key] = override
    return Settings.from_mapping(value)


def fixture_context(command: str = "collect", priority: str = "backfill") -> "RunContext":
    from sec_edgar_ingest.config import pin_context
    from sec_edgar_ingest.models import RunContext
    settings = fixture_settings()
    started = datetime(2026, 10, 6, tzinfo=timezone.utc)
    context = RunContext(
        run_id="fixture-run", execution_id="fixture-execution", command=command,
        attempt_id="fixture-attempt", image_digest=settings.worker.image_digest,
        parser_version=settings.etl.parser_version, schema_version=settings.etl.schema_version,
        config_sha256=settings.config_sha256, started_at=started,
        deadline=started + timedelta(seconds=3600), priority=priority,
    )
    return pin_context(settings, context, date(2026, 10, 6))[0]


def fixture_source(period: str = "2015Q1", kind: str = "quarterly") -> "Source":
    from sec_edgar_ingest.models import Source
    from sec_edgar_ingest.urls import child_url, source_id
    if kind == "quarterly":
        year, quarter = period.split("Q")
        parent = f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/index.json"
        name, representation = "master.zip", "zip"
    else:
        day = date.fromisoformat(period)
        quarter = (day.month - 1) // 3 + 1
        parent = f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{quarter}/index.json"
        name, representation = f"master.{day:%Y%m%d}.idx", "idx"
    url = child_url(parent, name, name, False)
    return Source(source_id(url), url, kind, period, representation)


def fixture_workset(members: tuple["Source", ...], discovery_complete: bool = True) -> "SourceWorkset":
    from sec_edgar_ingest.models import DirectoryOutcome, Error
    from sec_edgar_ingest.worksets import make_source_workset
    by_directory = {}
    for source in members:
        url = source.canonical_url.rsplit("/", 1)[0] + "/index.json"
        by_directory.setdefault(url, []).append(source)
    if not by_directory:
        by_directory["https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json"] = []
    directories = tuple(
        DirectoryOutcome(url, group[0].period if group else "2015Q1",
                         "available" if group else "no_new_sources", "a" * 64,
                         tuple(member.source_id for member in group), None)
        for url, group in by_directory.items()
    )
    if not discovery_complete:
        failed = DirectoryOutcome(
            "https://www.sec.gov/Archives/edgar/full-index/2015/QTR2/index.json",
            "2015Q2", "discovery_failed", None, (), Error("listing", "failed", True, None, {}),
        )
        directories += (failed,)
    return make_source_workset(fixture_context(), "2026Q4", "fixture-discovery",
                               tuple(members), directories, date(2026, 10, 1))
