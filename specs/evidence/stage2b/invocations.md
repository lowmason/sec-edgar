# Stage 2b campaign invocations

| k | Config | Run ID | Launcher exit | Outcome | Elapsed (s) | Complete / pending / failed sources | Published quarters | Timed / B4 members | Max member wall (s) | Attempts (run / campaign) | Received bytes (campaign) | Eligible after | Untouched after | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | live | `0746b217-d4ca-4f1d-9b05-d0c447b734ce` | 3 | incomplete | 1810.1 | 0 (0 already complete) / 113 / 0 | 0 | 0 / 0 | none | 37 / 37 | 111,692 | 113 | 0 | Rerun (rule 10, k = 1). No member was dispatched: the 1,800 s cutoff passed during selection. See `startup-overhead.md`. |
| 2 | live | `bdefaa5d-856d-4bc4-a621-018e66b6ef1e` | 3 | incomplete | 2717.0 | 0 (0 already complete) / 117 / 0 | 0 | 0 / 0 | none | 39 / 76 | 244,388 | 117 | 0 | Halt (rule 10): eligible 113 → 117 and no member was dispatched. The cutoff passed during discovery. See `startup-overhead.md`. |
