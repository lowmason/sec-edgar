> For agentic workers: REQUIRED SKILL: derive-roadmap — resume via its
> reconcile step; route each unticked stage per its ROUTING line; never plan
> this document wholesale.

## Outcomes

Source: the owner's words, 2026-11-16 (the owner focus of the roadmap-reset brief, and the owner's answers to
its questions). Background: the [local spec](completed/sec-edgar-local-spec.md); the
[ingestion spec](completed/sec-filing-index-ingestion-spec.md), its [methodology](completed/sec-filing-index-ingestion-methodology.md)
and its [roadmap](completed/sec-filing-index-ingestion-roadmap.md); the [platform spec](completed/sec-filing-platform.md), its
[methodology](completed/sec-filing-platform-methodology.md), [critique](completed/sec-filing-platform-critique.md) and
[roadmap](completed/sec-filing-platform-roadmap.md); and the [reset review](findings/sec-filing-data-reset-review.md).
Choices made:
- Repository: `~/Projects/sec-edgar`, Python 3.14, the existing uv workspace.
- Stage 1 process: the lighter process. The code runs from the working tree, and a fix needs no release. No per-run deadline, reserve or member-wall tuning. The findings file is the only evidence record. The stage fixes each problem that its run finds, and a new stage needs the owner's word.
- Input: the 2026Q3 quarterly index file on disk, and nothing else that is built. No code of the old engine or of the platform branch is an input.
- Kept from the old design: the SEC client rules (a declared User-Agent, at most 3 requests a second, retries, byte guards), the original bytes kept with their SHA-256, and fixture and live data kept apart in tests.
- SEC budget for Stage 1: at most 1,500 requests and 5 GB received, at most 3 requests a second, and no other SEC client running.
- The old store stays parked, with no repair of the 2026-11-15 folder rename. The repair routes are in the parked ingestion Stage 2b item of `specs/deferred_items.md`.
- Target: Stage 1 delivers its answer within 3 working sessions or 7 calendar days.

| # | Outcome | Track | Rank | Cost (estimate; basis) |
|---|---|---|---|---|
| O1 | The 2026Q3 filing index: the CIK, company, form type, date filed and path of each listed filing | A | 1 | No SEC request: the file is on disk (3.5 MB). The old engine parsed it in 241 s (reset review). |
| O2 | The original documents of about 500 filings sampled from O1, each split into its header and its document list | A | 2 | About 500 requests and 2–4 GB, at 4–8 MB a filing (platform spec, Motivation: 1.0–1.9 TB per quarter over about 245,683 filings). Measured by Stage 1. |
| O3 | As-filed XBRL facts (concept, value, unit, period) from the sample's 10-K and 10-Q filings | A | 3 | Measured by Stage 1. |
| O4 | Ownership records from the sample's Forms 3, 4 and 5, Schedules 13D and 13G, and Form 13F | A | 3 | Measured by Stage 1. |

Tracks: A — Filing data (known progression). Facts and ownership records answer unrelated questions, and a
split into two tracks was proposed. The owner kept them in one track (2026-11-16).

## Stages

The order follows the owner's progression (2026-11-16). The mechanics come first, end to end on a small real
sample: the index, then the documents, then the facts and ownership records. Point-in-time awareness comes
after, in the order the owner listed its parts: provenance, timing, manifests, hash-bound evidence, release
pinning, as-of views. No spec ranks these outcomes, so the order departs from no spec ranking. Each stage
consumes the output of the stage before it.

- [ ] Stage 1: Filing data mechanics on the 2026Q3 sample
      Objective: Deliver the 2026Q3 filing index, the documents of about 500 filings sampled from it, and their as-filed XBRL facts and ownership records, end to end on real data, from the working tree.
      Outcomes: O1, O2, O3, O4
      Consumes: The 2026Q3 quarterly index file `data/objects/raw/sec/indexes/kind=quarterly/period=2026Q3/sha256=526d2dbf2dd2e4c6ac4b1b6e0b383476997e74c5a5c243dcf71dfeaff7cc9150/master.zip` (3,505,445 bytes), read in place as a plain file, not through the old store. The old engine found repeated keys in every quarterly file, 5 in 2026Q3 (`specs/evidence/stage2a/release.md`, "Per-source results"). The SEC budget and the client rules under Choices made. No other built piece (owner, 2026-11-16).
      Produces: Plain tables of O1–O4, kept outside `data/`. The sample's original bytes with their SHA-256. The code that made them. `specs/sec-filing-data-stage-1-findings.md`, which records the results and the measured cost of the real run.
      Exit: O1: the index table holds every row of the 2026Q3 file, and the findings file gives the row count. O2: each of about 500 sampled filings has its original documents on disk, with a parsed header and document list, or a recorded reason why not. O3: a facts table holds as-filed XBRL facts for the sample's 10-K and 10-Q filings, and the findings file counts the filings that gave none. O4: an ownership table holds records from the sample's Forms 3, 4 and 5, Schedules 13D and 13G and Form 13F, and the findings file counts the filings that gave none. The findings file records the measured cost of the real run: SEC requests and bytes received (inside the budget), wall time and disk use.
      Leaves out: Provenance and timing: Stage 2. Manifests, hash-bound evidence, release pinning and versioned record formats: Stage 3. As-of views and amendment handling: Stage 4. Checks against SEC reference data, other quarters, daily currency, scheduling and deployment: not in this roadmap (owner, 2026-11-16), and the parked roadmaps' deferred items keep them. Per-run deadlines, reserves, member walls, the shared coordinator and whole-file refusal: dropped (owner, 2026-11-16).
      ROUTING: writing-plans

- [ ] Stage 2: Provenance and timing
      Objective: Give each record of O1–O4 its source and the times that point-in-time use needs, such as when the SEC accepted the filing, when it became public and when this project fetched it.
      Outcomes: O1, O2, O3, O4
      Consumes: Stage 1's tables, retained bytes, code and findings file.
      Produces: The O1–O4 tables with provenance (source URL, accession number, raw-byte SHA-256) and the chosen times on each record.
      Exit: For the Stage 1 sample, each record of O1–O4 names its source, its raw-byte SHA-256 and its times. A rebuild from the retained bytes reproduces the tables and sends no SEC request.
      Leaves out: Manifests, hash-bound evidence, release pinning and versioned record formats: Stage 3. As-of views and amendment handling: Stage 4.
      ROUTING: brainstorming

- [ ] Stage 3: Manifests, hash-bound evidence and release pinning
      Objective: Make each output of O1–O4 checkable and reproducible. Each output set gets a manifest, each parsed value is bound to the hash of the bytes it came from, and each run is tied to the code version that made it.
      Outcomes: O1, O2, O3, O4
      Consumes: Stage 2's tables with provenance and times.
      Produces: Manifests, hash-bound evidence for parsed values, versioned record formats, and a pinned code version for each run.
      Exit: A check re-derives a sample of parsed values from the retained bytes through their hashes. Each manifest lists every output file with its SHA-256. Each output names the code version that made it, and the outputs of two code versions are told apart.
      Leaves out: As-of views and amendment handling: Stage 4.
      ROUTING: brainstorming

- [ ] Stage 4: As-of views
      Objective: Answer what was known about each filing, fact and ownership record of the sample on any date, amendments included.
      Outcomes: O1, O2, O3, O4
      Consumes: Stage 2's times, and Stage 3's manifests, evidence and pinned versions.
      Produces: As-of views over O1–O4, with amendment handling.
      Exit: For the 2026Q3 sample, an as-of query for any date returns only what was public by that date, and each answer traces to its manifest and its source bytes. Where a sampled filing has an amendment, the original and the amendment each answer at their own dates.
      Leaves out: nothing
      ROUTING: brainstorming

## Stage-spec stamp

Each stage spec's Rollout note carries this line. With no stage spec (Stage 1, writing-plans), the plan header
carries it:

> Roadmap: specs/sec-filing-data-roadmap.md, Stage N — on plan completion, tick the
> stage and re-validate later stages against what shipped.

On completion, this stamp goes under the stage's entry. It is authoritative:

> Stage N: COMPLETE (YYYY-MM-DD) — implemented by plan <id> (path). Its Handoff section names what <stages> consume.
> Next: resume the roadmap.

Drop the second sentence when the plan has no `## Handoff to later stages` section, or when that section reads
`None`.

## Completion

The owner approved this partition on 2026-11-16. Owner's words: "Approve (Recommended)". This roadmap replaces
the ingestion and platform roadmaps, which were parked on the same day (Background). Their unticked stages are
deferred items in `specs/deferred_items.md`, sections `sec-filing-index-ingestion-roadmap — 2026-11-16` and
`sec-filing-platform-roadmap — 2026-11-16`. Plans 3 and 8 retired as superseded. The owner's SEC budget for
Stage 1 is under Choices made. No other live request is authorized here.

Retire this roadmap only after the completion review (derive-roadmap §6) re-runs the rubric over O1–O4, with
evidence from each stage. An unmet outcome needs a new stage, or a written deferral in
`specs/deferred_items.md`.
