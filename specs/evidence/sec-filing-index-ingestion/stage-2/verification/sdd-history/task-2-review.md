# Fresh task 2 Spec/Quality review
Reviewer /root/task2_review: gpt-6.1-sol xhigh, fresh, read-only. Range 046f240..1d1bd25.
Spec FAIL; Quality FAIL. Three Important findings; no Critical or Minor.
1. models.py:419-420 requires bare hash and source-ID component, rejecting approved Task7 kind/period/sha256=<hash>/master.zip or master.idx raw paths. Test helper uses invented alternative layout. Accept/validate approved layout and add both representation round trips.
2. worksets.py:145 infers acquisition_mode only from context.command == refresh. Actual consumer discover(refresh=True) needs explicit mode with discover command provenance intact. Add explicit acquisition-mode producer input and source/snapshot identity/round-trip cases.
3. worksets.py:71 discards pin_context resolved endpoint; :75 checks equality only for fixed endpoints. Recomputed-ID Q3 workset with ordinary Q4 open config decodes. Validate exact resolved endpoint for constructor and decoder, including fixture pin-date information where needed.
Focused read-only python -B probe reproduced all three, exit 0. Existing 32/32 evidence pristine, not rerun.
Strengths: all named/clarified paths present, pure broad config validation, typed/deeply immutable/detached records, strong URL and codec subtests, complete TDD evidence.
Cannot verify from task diff: persisted binding, server-time/lease, integrated no-client-on-invalid config, stored raw/workset checks (later tasks). Primary preservation and F1 integrity rely on separately recorded controller checks.
