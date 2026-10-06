# Correction assembly/check failure chronology

These are original tool-captured failures, retained with helper input versions before mutation. No source fact or historical PASS is reclassified. Failure1/2 occurred before any live correction mutation; failure3 occurred after append/citation assembly and caught one missing finding citation.

1. Command: `python3 -B specs/evidence/sec-filing-index-ingestion/stage-1/final-fix/assemble_claims.py`; stdout empty; exit1. Input helper: `before/assemble_claims-failed-v1.py`; exact start/end clocks unavailable.

```text
Traceback (most recent call last):
  File "/Users/lowell/Projects/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-1/final-fix/assemble_claims.py", line 72, in <module>
    doc('E-FF-DOC-'+identifier, claim, record, 'Version/tag in source URL; otherwise retained rolling page', group)
    ~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/lowell/Projects/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-1/final-fix/assemble_claims.py", line 43, in doc
    assert record['outcome']!='failed retrieval'
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError
```

2. Same command; stdout empty; exit1. Input helper `before/assemble_claims-failed-v2.py`; exact start/end clocks unavailable. Exact stderr is in `assembly-failed-v2.json`. Root cause: curated supplement source stores literal `actions` array rather than `extract`; assembly reads that array in successful v3. No historical source file was changed.

3. Command: `python3 -B specs/evidence/sec-filing-index-ingestion/stage-1/final-fix/verify_generation.py`; exit1; exact command/time/stdout/stderr in `checks/generation-v1.*`. One missing E-FF-DOC-JOBS-TEMP citation was added to finding §6; v2 then passed. Regional/sizing documentary supplement followed and v3 separately passed; v2 remains its original generation outcome.
