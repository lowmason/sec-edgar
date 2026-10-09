# Corrected-runtime final verification refresh

Reviewed runtime code head: `6528a4e7596ed55078cbe31892f448b3075773b3`. Checkout bookkeeping HEAD changes are separately captured by periodic and final command records. All package source/tests, uv.lock and pyproject.toml matched the reviewed runtime throughout the single full-suite run. No implementation change or commit was performed by this verifier.

Required guarded suite: **620 unique tests PASS**, exit 0, unittest duration 883.125s and command runtime 883.531s. The targeted lock suite separately passed six tests; those are not added to the unique full-suite count. Exact argv/cwd, full stdout/stderr, exit and runtime are retained for every check.

| Check | Exit | Runtime seconds |
| --- | --- | --- |
| green | 0 | 0.214 |
| full-suite | 0 | 883.531 |
| build | 0 | 0.034 |
| help | 0 | 0.111 |
| backfill-help | 0 | 0.091 |
| daily-help | 0 | 0.092 |
| version | 0 | 0.090 |
| compile | 0 | 0.036 |
| whitespace | 0 | 0.071 |
| native-command | 0 | 86.618 |
| installed-command | 0 | 33.992 |
| proof-contract-check | 0 | 0.585 |

Native: all 12 real process-death points exited 91 and reopened checked completion passed; exact evidence inventory is 878 files. Two original-call repair authority anchors, immutable report/pointer behavior and actual backfill/daily/legacy/reader captures are retained. Installed: exact evidence inventory is 240 files; all 39 package files match reviewed source, fresh explicitly selected wheel and isolated installed bytes. Import root: `/private/var/folders/3m/6f8zc0l14dn8yz2x8yy2_3mw0000gn/T/sec-workflow-installed-9q_zwlbn/venv/lib/python3.14/site-packages`.

Complete applicable lock proof: 21 active CPython dependencies plus sec-edgar-ingest 0.1.0. Synthetic PyPy evaluation has 19 dependencies, excluding exactly cffi and pycparser. Live disposable installed urllib3 metadata changed to 2.7.0 was refused; all direct pins remained intact and the accepted urllib3 is 2.8.0. Accepted lock hash: `4e41117fa0facbde7289f487a771f8b92e8210ac34ac327ac40a851a45c30a9c`; fresh frozen export hash: `aa450f3493def6b0ab8759bb37d0c5dfd4386271dfe666d10f9c619994ee057d`.

Fresh selected wheel and matching sdist were retained immediately after the successful required offline build, before installed proof. Distribution metadata is sec-edgar-ingest 0.1.0. Explicit selected wheel: `/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/final-verification-refresh/distributions/sec_edgar_ingest-0.1.0-py3-none-any.whl`. Artifact signatures:

```json
{
  "sec_edgar_ingest-0.1.0-py3-none-any.whl": {
    "bytes": 158610,
    "sha256": "f2c6e3c999ab9ccfad8c3726d2b9345e2455799f2f5a4c5d21f65d236c751a62"
  },
  "sec_edgar_ingest-0.1.0.tar.gz": {
    "bytes": 131960,
    "sha256": "407846bf2ecfb97a2a511aa7d02a48bf315bb88b3f93c1f47947ec1f938f3dd7"
  }
}
```

Methods: verification-method.py retains asynchronous subprocess orchestration, separate full stdout/stderr streams, offline frozen command templates and 30-second HEAD/runtime checks. finalization-method.py retains exact graph/package/proof/manifest assertions. Every proof child command retains its own exact argv/cwd/output/exit/runtime. Installation uses existing Stage 2 cached wheels and cached PyArrow 25.0.1, copied into a fresh external disposable venv with -I, no PYTHONPATH, frozen actual lock export, hash requirements and a fixed copied test-only harness. No fetch or pin change occurred.

Exact inventories exclude only each inventory’s own full path, include nested sha256.json files, and verify exact membership and bytes. The complete root inventory is generated last; its final count/hash are in the external .sdd final-verification-refresh-report.md so this report is itself retained in the manifest without self-reference. Original Task 11 evidence was compared byte-and-membership exactly before/after and its existing complete manifest verified unchanged.

Original SEC-0141/0142/0143 entire-source refusal/specimen evidence remains applicable and was not rerun. Conflicts remain 21/24/6 with original raw hashes retained in task-11/verification-summary.json. Parser/transform runtime is unchanged from original Task 11; only workflows/results.py and workflows/runner.py differ in corrected production source. No original refusal execution is represented as freshly run.

Scope limits: this evidence supplies technical checks and actual fixture coverage only. Owner actual coverage approval, controller evidence review and known absent former planning checkout disposition remain separate gates. Controller separately reports physical preservation of 138,438 records and 28,873 blobs at bookkeeping commit de05280a. No integration, historical-range or deployed-capacity claim follows. All 22 Stage 7 checks remain reserved/not_run; no network/provider/live/deploy/merge/push/cleanup or schedule activation occurred. Evidence is uncommitted for controller review and explicit staging.
