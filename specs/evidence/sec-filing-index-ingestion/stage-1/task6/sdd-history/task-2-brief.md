## Global Constraints

- Repository: `/Users/lowell/Projects/sec-edgar`; owner and decider: Lowell Mason.
- Workload remains filing indexes: historical quarterly backfill, ongoing daily ingestion, metadata ETL and reconciliation. One implementation package is `packages/sec-edgar-ingest/`, distribution/CLI `sec-edgar-ingest`, import `sec_edgar_ingest`; see parent §§2, 4.1, 4.9 and ADR Decision.
- Intended historical range: 2010 Q1 through the open quarter, inclusive. Initial development range: 2015 Q1 through the open quarter, inclusive. End-quarter rule: Resolve and pin the end quarter at each run's start.
- Daily handoff: 2026-10-01, retaining baseline overlap under parent §4.2.
- SEC User-Agent: Lowell Mason sec-edgar-ingest mason.lowell@mac.com.
- Azure target: A new dedicated resource group in an existing subscription. Region order: eastus, then eastus2, then centralus.
- Networking: Public HTTPS endpoints, managed identities, scoped roles, anonymous blob access disabled. Infrastructure as code: Bicep.
- Python/container candidate: Python 3.14; Linux amd64 container.
- Initial compute candidate: General-purpose Consumption workload profile; 2 vCPU and 4 GiB RAM. Initial execution settings: One replica; parallelism 1; completion count 1; replica timeout 3,600 seconds.
- Initial storage candidate: Standard general-purpose v2; hierarchical namespace enabled; Hot tier; ZRS.
- Ingestion-artifact retention: Indefinite during initial development: raw snapshots, observations, generations, manifests, approvals, quarantine evidence and run reports.
- Operational-log retention: 90 days. Alert owner and destination: Lowell Mason; mason.lowell@mac.com.
- Accepted parent §4.8 defaults: daily 05:00 Eastern; Sunday reconciliation 06:00 Eastern; 3 requests/second, no bursts; 1 active collector; 5 total HTTP attempts; 2 s exponential/jitter base and 120 s local cap while honoring longer server delays; 15 s connection / 60 s read timeout; zero native job retries; at most 1 confirmed-transient-failure replay. Parent §§4.3, 4.8 and §5 govern all SEC investigation access.
- Preserve existing local deletions in `packages/sec-edgar-index-ingest/` and the untracked roadmap. Preserve any additional execution-time changes. No broad staging, stash, reset, restoration or package repair.
- Read-only inspection, bounded source/archive inspection and isolated dependency/container probes are authorized. No production ingestion modules, parser/catalog implementation, golden parser tests, workspace repairs, Bicep resource definitions, provisioning, publication or trigger activation.
- No resource-profile comparison. Actual worker memory/runtime and live integrated Azure behavior belong to Stage 7. A local probe has no deployment authority.

### Task 2: Inventory requested quarterly and relevant daily sources

**Files:** Create `requests.csv`, `quarterly.csv`, `daily.csv`, `listings/`; update access and evidence registers.

**Interfaces:** Consumes Task 1 endpoint/window. Produces exhaustive requested-quarter accounting, actual discovered URLs, representations, daily retention observations and specimen candidates for Task 3.

- [ ] **Step 1: Define row contracts before requesting directories.** Quarterly columns: `quarter,development_subset,requested_at,listing_evidence_id,discovered_url,representation,listed_size,listed_size_unit,source_status,selection_reason,gap_id`. Keep one summary outcome per requested quarter plus child representation rows. Daily columns: `directory_period,listing_evidence_id,discovered_url,listed_date,representation,handoff_relation,outcome,gap_id`. Request ledger columns: `attempt_id,issuer,start_utc,end_utc,url,status,received_bytes,body_sha256,response_headers_artifact,exit_code,retry_reason,next_allowed_at,outcome`. Sidecars preserve URL, UTC receipt, HTTP status, headers, transport/content encoding, redirect chain, schema, discovered children and selection decision. Avoid automatic client retry/redirect behavior that escapes the shared attempt ledger.

- [ ] **Step 2: Discover the full-index hierarchy from official roots.** Start at `https://www.sec.gov/Archives/edgar/full-index/index.json`; follow validated child entries through years and quarters within the requested range. Inspect current-quarter root representations too; record the actual relationship between root and year/QTR full indexes rather than assuming they are equivalent. Resolve canonical HTTPS SEC URLs only within the accepted Archives index families. Capture exact listing bytes and hash before inspecting JSON. If JSON is absent or malformed, inspect the documented XML/HTML representation under the same budget and record the fallback/schema. Generated quarter labels are allowed for expected coverage; generated file URLs are not evidence of availability.

- [ ] **Step 3: Inventory every intended quarter and mark the development subset.** Repeat listing capture per unit and enumerate master representations/extensions, sizes and dates. Record `available`, `valid_no_source`, `discovery_failed`, or `listed_source_pending` based on evidence. A missing/inaccessible directory is not a successful empty listing; a listed file's 404 is pending. Follow parent §§4.2–4.4, retain all failed outcomes and do not infer withdrawals. Record selected representation per observed family; no need to support optional codecs when an inspected alternative covers the source.

- [ ] **Step 4: Inspect daily discovery from the handoff and across outage boundaries.** Start at `https://www.sec.gov/Archives/edgar/daily-index/index.json`; follow its actual hierarchy. Inspect current and preceding quarters, the handoff quarter, available year directories throughout the intended range and at least the first/last available quarter of each discovered historical year. Record which historical directories exist and which remain uninspected. If the proposed supported outage horizon exceeds observed daily availability, inspect the relevant additional directories in another bounded window or obtain an explicit gap resolution. Discover dates from listings; never manufacture weekend/holiday filenames. Keep 2026-10-01 as a required inspection even if absent, and select an already-published daily body from a successful listing.

- [ ] **Step 5: Check inventory completeness against the pinned requested set.** Independently recompute inclusive quarter count; verify no duplicate/missing quarter summary and correct 2015 Q1 subset boundary. Cross-check each successful row against retained child entries. Record receipt-date-sensitive open-quarter status. Record every gap and its effect on supported range/recovery; obtain owner acceptance of an actual range/contract revision if needed rather than calling absence harmless.

**Checkpoint:** All requested quarters have evidence-linked outcomes; daily discovery has a documented historical observation boundary. Listings alone do not establish format support or historical ingestion coverage.
