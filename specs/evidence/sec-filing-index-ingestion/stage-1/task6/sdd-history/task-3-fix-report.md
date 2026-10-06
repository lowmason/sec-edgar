# Task 3 historical-reference repair

The review finding is verified: historical `E-ACCESS` and `E-T2-DAILY` referenced mutable files whose current bytes no longer matched their recorded hashes. Repair preserves the historical claim, category, observation date, result, limitation and hash; only each historical artifact reference changes to an immutable retained version.

Exact historical access bytes were extracted from Task 1 checkpoint diff and match `3e1079135db1a741fc1d49ddc77d7ee8ae5555e2e43d2872a47105be2923904b`. Exact historical daily bytes were extracted from Task 2 diff and match `fb8c5dfa54d56c14a1bc1041475519d4c9138f63f7b79cd652f90ccc47a29bf8`. Byte-preserving extraction retains CRLF where present and the final newline. No old claim was rehashed or assigned a new historical timestamp.

Both original Task 2 matrices now have hash-named retained versions. Historical quarterly SHA-256 is `d738bebd7f73ddf278f701551eafb51574f7ea74e45536543be0384dd85bfdf8`, independently verified with `shasum`. `versions/version-map.json` retains exact frozen-diff provenance and hashes. `check_matrix_preservation.py` now consumes these versioned matrix bodies, verifies their hard-coded original hashes and performs the same full row/order/original-field comparison. It has no runtime dependency on ignored `.sdd` files. The historical review diffs remain extraction provenance rather than required checkout inputs.

Current closed access-window and Task 3 annotated daily bytes were separately frozen under their current hashes. New `E-ACCESS-CLOSED-T3` and `E-T3-DAILY-CURRENT` entries use the new snapshot receipt UTC and source-observation category. Existing owner-decision records remain owner decisions; no access reopening, contract revision or production support approval is inferred. All other index rows were preserved.

The initial retention command wrongly compared the quarterly CSV against `E-T2-COVERAGE`, which hashes the inventory-check JSON. That assertion failed before any index write. Its exact stdout/stderr are retained as `retention-first-invalid-quarterly-validation.*`; this failure was not overwritten. The corrected command validates quarterly bytes through frozen extraction and independent digest/shasum, without claiming that the inventory-check JSON hash is the quarterly hash. Final retention exited 0, with exact command and retained script in `retention-command.json`/`retain_evidence_versions.py`. A preceding shell redirection failed because the new directory did not yet exist; the retention script did not execute then.

Fresh independent verification:

- `check_matrix_preservation.py`: exit 0 with retained versions. All 372 quarterly and 2,176 daily rows preserve original order/fields except the authorized ten quarterly field changes and five daily outcome changes. Four recovered tail rows match original versioned evidence.
- `check_index_reference_hashes.py`: exit 0. All 164 local references across 164 evidence rows independently hash to their recorded values, including references paired with remote URLs. No external requests occur.
- `shasum -a 256`: exit 0 for all five retained historical/current snapshots, output in `retention-final.stdout.txt`.

Commands, start/end UTC where captured, full stdout/stderr and exit codes are in the version directory. This repair changes evidence references and checkout reproducibility only; live source bytes, selected matrix metadata, owner workspace files and production packages remain unchanged. No network requests, staging or commits occurred.
