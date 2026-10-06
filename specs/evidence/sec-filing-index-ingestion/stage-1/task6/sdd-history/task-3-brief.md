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

### Task 3: Retain specimens and assess formats, paths and space

**Files:** Create `specimens/`, `source-assessment.md`; update `quarterly.csv`, `daily.csv`, discrepancies and index.

**Interfaces:** Consumes discovered sources. Produces format/representation support boundary, original-byte samples, archive decoding inputs for Task 4 and bounded volume/space assessment.

- [ ] **Step 1: Choose the bounded specimen matrix from actual inventory.** Include 2010 Q1, 2015 Q1, latest closed and open quarter; handoff daily and already-published daily; closed/open transition daily pair where listed; a year-transition pair; every distinct selected format/legacy path family exposed by inventory or inspection. Multiple samples can cover one requirement. For absent handoff/transition files record absence and inspect the nearest listed files on both sides; seek explicit accepted resolution of unmet required coverage. Expand beyond the initial 12 only through a recorded continuation budget. Do not download all representations speculatively.

- [ ] **Step 2: Retain original bodies and receipt evidence.** Each archive stays an archive named by hash plus original extension; decoded content is a separate derivative. Preserve HTTP transport bytes/content-encoding interpretation explicitly: use Accept-Encoding identity where supported and disable transparent body decoding in the acquisition tool. Hash the bytes actually retained; preserve advertised Content-Length and compare when applicable. Record User-Agent, validators, MIME type, received byte count, UTC receipt, status and body hash. Quarantine HTML/truncation/error bodies as evidence; they are not source specimens. Use bounded reads and parent failure rules.

- [ ] **Step 3: Inspect archives safely and retain member reports.** List member names, codec, compressed/expanded sizes and checksums; reject unexpected members, traversal/absolute paths, excess count or expansion before extraction. Decode to the isolated directory, not repository package paths. Proposed investigation expansion cap is 512 MiB per specimen; an over-cap source remains unexamined pending a bounded revision. Record actual expanded byte count and derivative hash, integrity-check output and exit code. Do not overwrite archive bytes with `master.idx`.

- [ ] **Step 4: Inspect source text and legacy conventions without building the parser.** Record encoding evidence and decoding failures (never use lossy replacement), BOM, newline distribution, header/column separator, representative raw rows/fields/paths and observed minimum/maximum filing dates with the inspection method. Inspect early-range path families, accession-shaped and non-extractable paths; preserve nullable accession under parent §4.4. If a complete format-family scan is not performed, state the inspected-row boundary. Additional bodies may be needed when metadata cannot reveal format changes. No unexamined family becomes supported merely by analogy; later golden parser verification remains required under parent §6.

- [ ] **Step 5: Reconcile raw representation with parent §4.5 examples.** Record selected archive extension/member and original-byte raw naming. Parent `master.idx` is an example and does not permit storing decoded content as original bytes. If a chosen durable naming scheme changes an accepted contract, record the proposed revision and owner acceptance before readiness. Otherwise explain how original extension/format metadata and derivative paths preserve the contract.

- [ ] **Step 6: Calculate bounded volume and disk requirements.** Sum listed quarterly sizes by representation with explicit units/unknowns; use observed download sizes separately. Report largest listed and largest retained source, expansion ratio per inspected archive, sample count and uninspected-tail uncertainty. Calculate temporary peak as simultaneous original archives + expanded derivatives + planned observation/output scratch + candidate-generation scratch + installer/runtime/log reserve. Identify which terms are measured and which are assumptions; recommend bounded source units without designing the worker. Compare with documented candidate temporary capacity, never call it a measured 4 GiB-memory or 3,600-second-runtime fit. Blocking incompatibility requires an accepted setting revision; actual memory/runtime belongs to Stage 7.

**Checkpoint:** Every supported selected representation/family has retained evidence; unknowns/gaps have explicit dispositions. Hashes independently recompute with `shasum -a 256` on each original and derivative. Directory size estimates are not expansion or processing measurements.
