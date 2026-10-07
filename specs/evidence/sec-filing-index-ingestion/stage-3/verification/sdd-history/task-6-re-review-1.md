**I1 — ADDRESSED.** etl/commands.py:161 now reads/decodes the snapshot, checks decoded content-ID path and compares original bytes with encode_workset(snapshots) before scanning Processing or invoking transformation. Acquisition decoder unchanged.

The two tests use whitespace/property-order variants at matching snapshot path, preserve acquisition decoding behavior and assert exit9/no result ref/empty Processing and pointers/unchanged non-run objects. Controller-verified retained evidence records28 guarded passing tests.

NEW Critical/Important/Minor: None.
