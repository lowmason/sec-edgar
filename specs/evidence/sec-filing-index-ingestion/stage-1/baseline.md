# Stage 1 investigation baseline

Status: independent Task 1 preparation recorded; required owner inputs remain OPEN/BLOCKING.
This is repository evidence and a requested-unit endpoint, not a readiness finding.

## Before-state and authority

Capture: `2026-10-05T23:06:52.076996+00:00` (actual UTC receipt time). Evaluation date: **2026-10-05,
America/New_York**. Endpoint is pinned once for this investigation at **2026 Q4**;
latest closed quarter is **2026 Q3**. Future runs resolve their own endpoint.
Approval HEAD: `321c93af78b54c7e63efbb0e69252c69a238fec6`.
Actual HEAD: `321c93af78b54c7e63efbb0e69252c69a238fec6`. HEAD drift: none.
Working Stage 1 spec is byte-identical to `git show 321c93a:specs/sec-filing-index-ingestion-stage-1-spec.md`;
SHA-256: `bb28b0c27646d4f7b15669660e56c230d3247148966e3b075b96ca196a0b5140`; spec diff output is empty.

`baseline-commands.json` retains every specified command, output, stderr and exit code.
All seven baseline commands exited 0. `protected-before-state.json` is the immutable
before-state manifest, created before this task's evidence artifacts. It hashes every
changed/untracked original file and the authoritative documents/root configuration.
The untracked plan is hashed without reading its contents. Task-created evidence is
excluded from original-worktree records by capture ordering; later additions by other
tasks are execution-time changes and must be preserved separately.

Initial status has four deleted tracked files and two untracked paths (the plan directory
and roadmap). The protected deleted paths are:

- `packages/sec-edgar-index-ingest/README.md`
- `packages/sec-edgar-index-ingest/pyproject.toml`
- `packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/__init__.py`
- `packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/py.typed`

The original untracked plan and roadmap hashes are retained in the manifest. No restoration,
package repair, branch change, staging or commit occurs in this task.

## Repository observation and Stage 2 alignment

Category: Source/probe observation (read-only local inspection). Inventory covers tracked
files and `rg --files --hidden -g '!.git' -g '!.venv'`, including the original untracked
roadmap/plan paths. No ingestion tests, worker, CI or Azure infrastructure appears in
this inventory. No deployed resource inspection was performed.

`packages/sec-edgar-ingest`, `packages/sec-edgar-client` and `packages/sec-edgar-download`
each contain only a `hello()` scaffold and type marker; root and package READMEs are empty.
All package configs require Python >=3.14, declare no dependencies and use
`uv_build>=0.12.15,<0.13.0`. Root config also requires >=3.14, references the deleted
index-ingest workspace member alongside ingest/client/download, and maps the `sec-edgar`
CLI to absent `sec_edgar:main`. Ingest currently declares no CLI entry point.

Stage 2 must align workspace membership and CLI with the accepted single package:
`packages/sec-edgar-ingest/`, distribution/CLI `sec-edgar-ingest`, import `sec_edgar_ingest`
(parent §§4.1, 4.9; ADR Decision). Decisions about the existing scaffolds belong to that
stage; the local deletions remain protected. No root workspace build was attempted,
because repair and production implementation are outside Stage 1.

## Requested quarterly units

Intended range: 2010 Q1–2026 Q4 inclusive, **68 requested units**.
Development subset: 2015 Q1–2026 Q4 inclusive, **48 requested units**.
Calculation uses ordinal `4 * year + quarter - 1`, inclusive count `end - start + 1`.
Daily handoff: 2026-10-01 with parent §4.2 overlap. Requested units below are not discovered
sources, support claims or coverage results. No source inventory/access has occurred.

| Intended ordinal | Requested quarter | Development ordinal | Discovery status |
|---|---|---|---|
| 1 | 2010 Q1 | — | Not investigated |
| 2 | 2010 Q2 | — | Not investigated |
| 3 | 2010 Q3 | — | Not investigated |
| 4 | 2010 Q4 | — | Not investigated |
| 5 | 2011 Q1 | — | Not investigated |
| 6 | 2011 Q2 | — | Not investigated |
| 7 | 2011 Q3 | — | Not investigated |
| 8 | 2011 Q4 | — | Not investigated |
| 9 | 2012 Q1 | — | Not investigated |
| 10 | 2012 Q2 | — | Not investigated |
| 11 | 2012 Q3 | — | Not investigated |
| 12 | 2012 Q4 | — | Not investigated |
| 13 | 2013 Q1 | — | Not investigated |
| 14 | 2013 Q2 | — | Not investigated |
| 15 | 2013 Q3 | — | Not investigated |
| 16 | 2013 Q4 | — | Not investigated |
| 17 | 2014 Q1 | — | Not investigated |
| 18 | 2014 Q2 | — | Not investigated |
| 19 | 2014 Q3 | — | Not investigated |
| 20 | 2014 Q4 | — | Not investigated |
| 21 | 2015 Q1 | 1 | Not investigated |
| 22 | 2015 Q2 | 2 | Not investigated |
| 23 | 2015 Q3 | 3 | Not investigated |
| 24 | 2015 Q4 | 4 | Not investigated |
| 25 | 2016 Q1 | 5 | Not investigated |
| 26 | 2016 Q2 | 6 | Not investigated |
| 27 | 2016 Q3 | 7 | Not investigated |
| 28 | 2016 Q4 | 8 | Not investigated |
| 29 | 2017 Q1 | 9 | Not investigated |
| 30 | 2017 Q2 | 10 | Not investigated |
| 31 | 2017 Q3 | 11 | Not investigated |
| 32 | 2017 Q4 | 12 | Not investigated |
| 33 | 2018 Q1 | 13 | Not investigated |
| 34 | 2018 Q2 | 14 | Not investigated |
| 35 | 2018 Q3 | 15 | Not investigated |
| 36 | 2018 Q4 | 16 | Not investigated |
| 37 | 2019 Q1 | 17 | Not investigated |
| 38 | 2019 Q2 | 18 | Not investigated |
| 39 | 2019 Q3 | 19 | Not investigated |
| 40 | 2019 Q4 | 20 | Not investigated |
| 41 | 2020 Q1 | 21 | Not investigated |
| 42 | 2020 Q2 | 22 | Not investigated |
| 43 | 2020 Q3 | 23 | Not investigated |
| 44 | 2020 Q4 | 24 | Not investigated |
| 45 | 2021 Q1 | 25 | Not investigated |
| 46 | 2021 Q2 | 26 | Not investigated |
| 47 | 2021 Q3 | 27 | Not investigated |
| 48 | 2021 Q4 | 28 | Not investigated |
| 49 | 2022 Q1 | 29 | Not investigated |
| 50 | 2022 Q2 | 30 | Not investigated |
| 51 | 2022 Q3 | 31 | Not investigated |
| 52 | 2022 Q4 | 32 | Not investigated |
| 53 | 2023 Q1 | 33 | Not investigated |
| 54 | 2023 Q2 | 34 | Not investigated |
| 55 | 2023 Q3 | 35 | Not investigated |
| 56 | 2023 Q4 | 36 | Not investigated |
| 57 | 2024 Q1 | 37 | Not investigated |
| 58 | 2024 Q2 | 38 | Not investigated |
| 59 | 2024 Q3 | 39 | Not investigated |
| 60 | 2024 Q4 | 40 | Not investigated |
| 61 | 2025 Q1 | 41 | Not investigated |
| 62 | 2025 Q2 | 42 | Not investigated |
| 63 | 2025 Q3 | 43 | Not investigated |
| 64 | 2025 Q4 | 44 | Not investigated |
| 65 | 2026 Q1 | 45 | Not investigated |
| 66 | 2026 Q2 | 46 | Not investigated |
| 67 | 2026 Q3 | 47 | Not investigated |
| 68 | 2026 Q4 | 48 | Not investigated |
