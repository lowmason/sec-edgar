# Task 1 derived quarantine gap interface (F5)

The public `summarize(members, gaps, discovered_new, unresolved_before=0, command="daily")` signature stays unchanged. Baseline-publication gaps remain present in `WorkflowResult.gaps` and serialize without suppression.

Task 4 may mark a gap derived solely from selected whole-source refusals using this exact JSON-compatible shape:

```python
Error(
    'baseline_publication_missing', message, False, None,
    {'coverage_cause': 'selected_source_quarantine',
     'source_ids': sorted(exact_selected_refused_source_ids),
     # Existing details such as quarter may also be retained.
    },
)
```

For the pure `quarantined` aggregate, every member must be terminal failed and whole-source quarantined. Every workflow gap must either be absent or meet all these conditions: exact `baseline_publication_missing` code; exact `coverage_cause` marker; nonempty unique array of source IDs, each belonging to those selected quarantined members; and `gap.source_id`, if supplied, belonging to that exact gap attribution array. Missing, malformed, duplicate, foreign, or differently coded attribution keeps the workflow `incomplete`. A mixture of valid progress and refusals remains `incomplete`; existing fatal precedence applies first.

Each gap may name a subset of the selected refused identities because different quarters can have different implicated sources. The subset must exactly describe the causes of that particular missing-publication gap. The reducer checks structural consistency against selected members; it cannot establish stored-object authority from this marker. Task 4 must validate successful complete discovery/listing evidence and exact selection, bindings, child whole-source refusal evidence, and publication absence before deriving the marker. It must not attribute independent failed directory reads, missing expected sources, unresolved legacy provenance, or unselected sources to a selected refusal. Preserve those independent gaps unmarked; any independent gap prevents the pure quarantine aggregate.

Task 1 regression scope is contract reduction and preserved nested report roundtrip. Tasks 4/6 must prove attribution using the real conflicting-duplicate workflow with no preexisting pointers and retain every gap plus no accepted observations/publication. This interface does not change retained SEC-0141/0142/0143 acceptance or authorize zero-row parser acceptance, live access, or any Stage 7 check.
