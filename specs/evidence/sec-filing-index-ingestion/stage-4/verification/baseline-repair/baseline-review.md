# Baseline repair review

Reviewer: baseline_review, default role with full task-reviewer rubric, gpt-6.1-sol/medium. No test reruns or mutations.

Spec compliance: approved. Only support.py acquisition_race_entry changed; synchronization at client.fetch entry follows recovery/download choice and precedes coordinator ownership. Staged/binding barriers and timeouts unchanged.

Quality: approved. No Critical, Important or Minor findings. Comment explains both boundaries; original client implementation retained. Focused inspection confirmed original named test still checks three binding attempts, one winner/two conflicts, pacing/serialization, common adoption, replay withoutfetch and retained raw integrity.

Concrete checks: collection.py:201-207 chooses download after recovery returns no snapshot then calls client.fetch; download.py:258-280 enters original fetch before coordinator exchange. support.py:1501-1509 wrapper and test_acquisition_processes.py:55-88 invariants inspected.

Controller prerequisites: full guarded baseline remains pending; primary/evidence/all22Stage7 state outside diff already checked by controller/authority auditor. Diagnostic exit120 retained accurately. Resolve full-baseline gate beforeTask1.
