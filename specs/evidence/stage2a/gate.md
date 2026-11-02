# Stage 2a branch gate

Plan: `specs/plans/7-sec-filing-index-duplicate-key.md`, Task 8. Spec: `specs/sec-filing-index-duplicate-key.md`.
No SEC request was sent. Every run below used fixture acquisition and the offline guard.

## Gate

- Branch: `stage2a-duplicate-key`
- Merge base with `main`: `c814119d6b62942ab566024e5e11c3d9b6ee88c0`
- Gated commit: `557028c052b2116b177f28cb18e85eec9ab519f8`
- Command, from the worktree root:

```
env -u PYTHONDONTWRITEBYTECODE UV_PROJECT_ENVIRONMENT=/tmp/s2a-venv UV_NO_SYNC=1 SEC_LOCAL_PROOF_CACHE=/Users/lowell/Projects/sec-edgar-local/releases/artifact-cache sh scripts/check-sec-edgar-ingest.sh
```

- Start: `2026-11-01T19:29:57Z`. End: `2026-11-01T20:43:38Z`.
- Result: `Ran 1187 tests in 4417.478s`, then `OK`. The log ends with `exit 0`.
- Modules: 75 test modules (the 73 older modules, `test_etl_schema_v2` and `test_release_2a`).
- Skipped, failed or errored tests: none in the log.
- The check script also built the sdist and the wheel and ran the installed CLI help and version (`0.2.0`).
- Log: `fixture-data/stage2a-gate.log`.

### Earlier gate run

The first full run passed on `f2610ce`: `Ran 1185 tests in 4433.706s`, `OK`, `exit 0`, started 2026-11-01T16:24:24Z and ended 2026-11-01T17:38:22Z (log `fixture-data/stage2a-gate-f2610ce.log`).
The final review then led to two commits: `88ea529` (test only) and `557028c` (a change in `src`). The gate ran again on `557028c`.
The commit that adds this file changes documentation only, so the gated commit is also the code of the branch tip.

### Deviation from the plan text

- The plan says `ln -s /Users/lowell/Projects/sec-edgar-local/.venv .venv`. The link pointed at `/tmp/s2a-venv` instead. The two launcher tests need only an executable project Python, and both passed with this link. The link was removed after the first run and created again for the second run.
- Step 5 ran the `git` commands from the worktree and not with `git -C` into the main checkout, because the harness refuses a redirect out of the worktree. The branch is the same in both places.

## Installed 1c release run (Step 2, P9)

```
SEC_LOCAL_1C_RELEASE=/Users/lowell/Projects/sec-edgar-local/releases/sha256=c4de77b89bb1d8ecc5d094f0e1dc6f8a5f3a7935e3595a9dd086d1e41a6b8aa7/release.json SEC_LOCAL_PROOF_CACHE=/Users/lowell/Projects/sec-edgar-local/releases/artifact-cache /tmp/s2a-venv/bin/python packages/sec-edgar-ingest/tests/network_guard.py test_release_2a -v
```

Result on `557028c`: `Ran 3 tests in 85.916s`, `OK`, `exit 0` (run from 2026-11-02T11:57:24Z to 2026-11-02T11:58:51Z). The import-origin assertion at `test_release_2a.py:129` passed with the installed release layout. The three tests are `test_1c_release_refuses_the_v2_config`, `test_v2_reads_the_1c_generation_unchanged` and `test_v2_release_continues_1c_origin_pending_work`. Log: `fixture-data/stage2a-installed-1c.log`.

## Locked inputs and the platform member (Step 5, P5, D12)

- `git show stage2a-duplicate-key:pyproject.toml | grep -n members` prints `20:members = ["packages/sec-edgar-ingest"]`.
- `git diff --stat 3af121a468fdd6b3ec7d8286d5cf619493992d49 stage2a-duplicate-key -- uv.lock pyproject.toml packages/sec-edgar-ingest/pyproject.toml` prints nothing.

## Spec section 5 to tests

All test names are in `packages/sec-edgar-ingest/tests/`.

| Item | What it checks | Tests |
|---|---|---|
| 1 | Both classes merge, quarterly and daily | `test_etl_schema_v2.ParserV2Tests.test_combined_filing_transforms_in_both_families`, `ParserV2Tests.test_company_rename_transforms_in_both_families`, `CatalogV2Tests.test_combined_filing_and_rename_publish_one_row_each` |
| 2 | A filing-date conflict still quarantines the source, with line and reason | `ParserV2Tests.test_filing_date_conflict_still_refuses_the_source`, `test_etl_transform.EtlTransformTests.test_non_list_conflicting_last_duplicate_after_full_batch_quarantines_source` |
| 3 | Order independence | `CatalogV2Tests.test_permuted_lines_give_byte_identical_generations`, `CatalogV2Tests.test_triple_repeat_across_batch_boundary_is_order_independent` |
| 4 | Merging never crosses sources | `CatalogV2Tests.test_merge_never_crosses_sources`, `CatalogV2Tests.test_validator_refuses_a_cross_source_merge`, `IncrementalV2Tests.test_incremental_does_not_merge_base_and_delta_sources` |
| 5 | A v1 generation reads back byte-identically, a v2 generation with lists | `ReaderV2Tests.test_v1_generation_reads_back_byte_identically`, `ReaderV2Tests.test_v2_generation_reads_back_with_lists` |
| 6 | A v2 candidate on a v1 base: `provenance_refreshed`, or `updated` | `CatalogV2Tests.test_v2_candidate_on_v1_base_counts_provenance_refresh`, `ReaderV2Tests.test_withdrawal_candidates_and_approval_of_a_v2_candidate_on_a_v1_base`, `IncrementalV2Tests.test_incremental_that_touches_a_retained_v1_key_refreshes_its_provenance` |
| 7 | A closed-quarter quarterly that drops a form type is `updated`, gate `clear` | `CatalogV2Tests.test_dropped_form_type_is_updated_with_clear_gate` |
| 8 | Rollback from v2 to v1, then a new v2 publish | `ReaderV2Tests.test_rollback_from_v2_to_v1_then_v2_publish` |
| 9 | Two-release continuation. The 1c release refuses the v2 config | `test_release_2a.TwoReleaseTests.test_v2_release_continues_1c_origin_pending_work`, `TwoReleaseTests.test_1c_release_refuses_the_v2_config`, `TwoReleaseTests.test_v2_reads_the_1c_generation_unchanged`. Both releases on the current pair: `test_release_upgrade` |
| 10 | The duplicate-quarantine tests are updated, not deleted | `test_etl_transform.EtlTransformTests.test_form_or_name_repeat_now_transforms` (new), `EtlTransformTests.test_non_list_conflicting_last_duplicate_after_full_batch_quarantines_source` (updated), `test_workflow_processing.ProcessingTests.test_form_only_repeat_now_completes` (new), `ProcessingTests.test_refusal_retains_exact_line_and_raw_details` (updated), `test_etl_schema_v2.ParserV2Tests.test_v1_form_or_name_repeat_still_refuses_the_source` (v1 path) |

## Plan Review Focus to tests

| Focus | What it checks | Test |
|---|---|---|
| 1 | The incremental path after the first v2 rebuild | `test_etl_schema_v2.IncrementalV2Tests.test_incremental_merges_a_combined_filing_like_the_full_rebuild` |
| 2 | A v2 generation that holds v1-provenance rows (D8) | `ReaderV2Tests.test_retained_v1_row_reads_back_with_lists_and_v1_versions` |
| 3 | A key repeated 3 or more times across an 8,192-row batch boundary | `CatalogV2Tests.test_triple_repeat_across_batch_boundary_is_order_independent` |
| 4 | One process reads a v1 capture and a v2 capture of different quarters | `ReaderV2Tests.test_one_process_reads_v1_and_v2_quarters` |
| 5 | Rollback to v1, then a v2 rebuild with a retained absence | `ReaderV2Tests.test_rollback_to_v1_then_v2_rebuild_keeps_retained_absence` |

## Review

Two reviewers read the branch. A third read only the fixes.

- Seat 1, `code-reviewer` (opus), range `c814119..f2610ce` (19 commits, 58 files). It read the diff only and ran no tests. Verdict: ready to merge with fixes, no Critical finding. It checked the merge points, the validator, the D8 readers, the v1 byte path, the config split, Review Focus 1 to 5 and spec section 5 items 1 to 10.
- Seat 2, Codex (`codex exec review`, read-only sandbox, `--base c814119d6b62942ab566024e5e11c3d9b6ee88c0`), reviewed `f2610ce`. It ran the focused contract tests and randomized full and incremental merge comparisons, and they passed. It did not review `557028c`. The two later commits are the fixes for its own finding, and the scoped re-review below checked them.
- Re-review, `task-reviewer` (opus), range `f2610ce..557028c`: both findings below are addressed. No new Critical or Important finding.

| # | Source | Finding | Result |
|---|---|---|---|
| 1 | Seat 1, Important | No test covers an incremental (C5) build that touches a retained v1 key. | Fixed in `88ea529` (test only). The new test is `IncrementalV2Tests.test_incremental_that_touches_a_retained_v1_key_refreshes_its_provenance`. |
| 2 | Codex P2, and the Seat 1 "library calls" item | `transform_member`, `run_transform`, `build_candidate` and `publish_quarter` can write v1 output, because `_validate_context` has no writable-schema check. | Fixed in `557028c`. The check sits in `_validate_context`. The owner decided that the one existing test that builds v1 output on purpose, `ParserV2Tests.test_v1_form_or_name_repeat_still_refuses_the_source`, is wrapped in `v1_writable()` with every assertion unchanged. |
| 3 | Controller item | Refresh `specs/evidence/source-import.json` for the changed fixture hash. | Withdrawn. The file pins the bytes from the import commit `0e7701a`, and its test checks the format only. |

Rulings on the items that the reviewers did not judge (`Ruling:` lines in the ledger, kept here in short form):

- A v2 base under a v1-layout candidate raises `KeyError 'form_type'`. Kept. No shipped caller builds that pair.
- C6 has no equality check on the candidate context and manifest schema. Kept.
- Fixture mode: a config with parser v1 and schema v2 loads, then fails at transform. Kept. A later load-time pair check must cover only the two release parsers, because `fixture-envelope-v1` in `tests/fixtures/config/local.json` must still load.
- Fixture-mode continuation of v1-origin pending work is refused at the child's `load_config`. Kept.
- A refused `transform_member` still writes one quarantine `error.json`. Kept. It is the existing failure retention, and the new test checks that it is the only new object.
- `approve` and `rollback` do not pass through the new check. Kept. They activate generations that already exist.
- `publish_quarter` checks the deadline before the schema check. Kept. Nothing is written in that case, and the order predates the fix.
- The claim in the plan decision P7 that the driver edit "breaks no retained check" is wrong in one place. `scripts/verify-sec-native-adjudication.py` would now refuse the retained `fc68adef` selection. Its evidence directory no longer exists, so it could not run either way.

## Known limits that the merge keeps

- `scripts/accept-sec-native.py` `validate_read` cannot validate a generation that holds a retained row whose snapshot was replaced. The older provenance check `sources <= expected_sources` (from `2b64551`) refuses it, before and after Task 6.
- The era tests (`test_release_origin`, `test_release_1b`, `test_release_1c`) now bind each test to its own older release on v1 configs. They no longer exercise the new release. `test_release_2a` and `test_release_upgrade` carry that coverage.
