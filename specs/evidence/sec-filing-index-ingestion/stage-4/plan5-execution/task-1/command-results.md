# Task 1 actual command evidence

Every test log uses this exact command in the isolated worktree:

`uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_contracts.py -v`

- completion-red.log: subprocess exit 1; 26 methods, one missing CompletionEvaluation import error; retained 25 methods pass.
- skipped-red.log: subprocess exit 1; 27 methods, one missing sixth reducer argument TypeError; completion and retained methods pass.
- integration-red.log: subprocess exit 1; 29 methods, one empty-daily boundary failure and two missing reducer/integration errors.
- green.log: subprocess exit 0; 29 methods pass, 0.087 seconds, no warnings/errors.
- `git -c core.whitespace=cr-at-eol diff --check`: exit 0; whitespace.log retains result.
- Explicit two-path git add: exit 0.
- `git commit -m "feat: define validated workflow completion evidence"`: exit 0; 49924611, 2 files changed, 75 insertions(+), 12 deletions(-).

The Python log harness reports the subprocess exit explicitly; harness process exit 0 is not the test exit. Logs are create-only original command output.
