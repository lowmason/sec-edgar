# Task 2 initial independent review

Reviewer task2_review, default available agent applying task-reviewer Full Form. Range133357cd..4780e1ff. Spec APIs/examples/tests present; quality Needs fixes. No Critical/Minor findings. Two Important findings are present in approved example code:

1. provenance.py:181 indexes each WorkflowMember member_ref before validating parent; unrelated malformed missing member_ref raises KeyError and blocks valid sibling projection. Preserve recursion guard while safely inspecting corrupt rows, retain inventory gap, cover real-store malformed record + valid sibling.
2. members.py:35 invokes mutating project_member before comparing supplied member_ref at36; a canonical singleton with different context leaves a correct projection object/registry row despite Conflict. Pure expected projection/ref validation must precede object/registry writes; cover unchanged inventories on refusal.

Strengths: provenance.py:112–170 validates discovery identity, frozen context, required units, real successful ancestors and source metadata;194–220 recomputes exact member and validates snapshot/binding. Existing14+43+20+35 clean logs read; no test regeneration/mutations by reviewer.

Controller checked both findings against actual code and approved corrupt-sibling/isolation/admission requirements. Fix round1 authorized within existing scope, APIs unchanged; approved source/snapshot bytes remain unchanged. Task5 class adoption must retain fixed registry methods. Task2 not complete until covering red/green and independent re-review resolve both findings.
