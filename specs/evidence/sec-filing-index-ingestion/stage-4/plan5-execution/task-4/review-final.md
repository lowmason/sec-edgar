# Task 4 independent re-review

Reviewer: /root/task4_review. Reviewed fix range 75682afe7fe88d11dc1b08a1578d602e856d5c67..c191ec685a775f69e1307d2707a3a01aba0d3b21 and original Task 4 scope.

Spec compliance: Approved. Task quality: Approved.
Critical: none. Important: none remaining. Minor: none identified.

1. Foreign resolution discharge: ADDRESSED. completion.py:594 requires the indexed resolution's embedded obligation to equal the exact canonical obligation before historical validation. The real two-call regression preserves original Attempt records.
2. Corrupt unfinished inventory exclusion: ADDRESSED. completion.py:499 raises Conflict retained as a blocking gap; line470 distinguishes persisted prebegin calls from absent Attempt indexes with retained begun command/result artifacts. Regressions cover checked command/input/Attempt corruption, ordinary missing command and valid prebegin exclusion.
3. Formerly affected quarter omission: ADDRESSED. completion.py:145 creates immutable original-call anchor; line240 requires every obligation descriptor to equal it. Anchor precedes indexing and missing-index recovery uses it before current-pointer recomputation. Nonempty Q3/Q4 -> Q3-only regression rejects former-Q4 omission and verifies recovery after pointer advance.

Additional malformed Mapping/None descriptor and missing begun Attempt corrections verified. Missing anchors/divergent indexes refuse without rewriting. Recovery regression makes recomputation raise. Public signatures, original descriptor formats, publisher authority and Tasks1–3 APIs preserved.

Reviewer read scoped diff, actual code/regressions, appended report, anchor/signature artifacts and retained red/green logs. Stored-ZIP setup failure excluded from authority-red credit. Final completion20/20 PASS exit0 70.520s, unchanged ETLCLI38/38 PASS and publication24/24 PASS exit0; exact/staged whitespace exit0. No reruns, mutations, subagents or network during re-review. Approval covers Task4 only; orchestration/installed proof/Stage7 remain outside this gate.
