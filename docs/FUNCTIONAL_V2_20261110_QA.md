# ELSE-ITIL-SUP — Functional V2 candidate, evaluation as of 10 Nov 2026 (Peru)

This is an opt-in QA implementation. It does **not** replace production or certify real repairs.

## Why

The August 2026 independent 50-case qualitative review found only 10/40 service-stratified random cases had a useful functional next check; 29/40 used historical ITIL ticket metadata as part of the diagnostic condition rather than measuring the affected domain system. The historic 1810/1819 structural pass percentage was not evidence of real root-cause accuracy.

## Three functional changes

1. Deterministic bounded domain router (`else_dominance/functional_domain_v2.py`): commercial OT, schedule, billing, FISE, cash, materials, SAP, tax, IAM, mail, endpoint, network, meter, HR, MGD, etc. It sends unknown/ambiguous incident descriptions to clarification. **Routing is not a live read**, and uninstalled domain Hands remain unavailable.
2. Functional contract (`functional_contract_v2.py`): target-system specific observation, expected result, differentiated conditional next steps, exact source anchors, no misleading ITIL evidence substitution, no fabricated current data, strict fail-closed execution/repair flags. Checks reject unsupported numeric expected values and named IAM roles, requests for passwords, and unverified SQL source names. The `com.pe` SMTP false positive is covered by a regression.
3. Readonly Qwen9B investigator and private isolated QA API (`functional_investigator_v2.py`, `functional_api_v2.py`): model gets only immutable redacted request, router output and original ITIL historical metadata. **No historical solution, no peer labels and no previous model answer.** It does not perform the proposed actions. The engine, not Qwen, binds exact quotations to source bytes, records source-quote substitution, and cannot rewrite domain assertions to pass. Private API requires token and exact August case SHA; SQLite prevents duplicate runs. No arbitrary SQL, no externally exposed listener, no repair.

## Tests

- Deterministic and API regression with native ELSE CORE: **389/389 tests PASS**, including 46 functional adversarial/API tests and 4 source-binding investigator tests.
- First 50-case replay (V2 initial): 35 functional-contract PASS, 7 clarification, 8 rejection.
- Second 50-case replay (V2.1 tightened): **36 contract PASS, 7 clarification, 7 rejection**. This is only contract acceptance, **NOT** independently assessed accuracy or usefulness; no verified business read. These 50 were development cases, so this is not a holdout score.
- Separate 30-case random service-proportional holdout, disjoint from those 50, launched for QA. Await final file `unseen30_v2_2_progress.json` before quoting results. Its source and selection SHA are bound, no gold supplied.
- All archived August original model outputs and sealed histories remain unchanged.

## QA deployment

- Loopback `127.0.0.1:18889` private server, `else-itil-functional-v2-qa.service`. Health endpoint currently `READY`.
- Historical `18883` original specialist and `18887` beta fresh QA remain independently active.
- Domain Hands **actually verified in this new candidate:** 0. The router does not magically grant access to business data.
- Model has no ability to mutate data or certify repairs.

## Decision gate

**Not GO for unrestricted V1 Beta functional specialist yet.** This candidate makes a substantial improvement to *what the model proposes to check* but has not supplied real domain evidence or independently assessed the final 50/30 explanations for technical usefulness.

To consider release: independently score new 50/30 functional outputs (not just JSON gates); confirm no critical intent inversion, no fake data or credentials; wire actual read-only domain Hands with native O5/O13/O15 receipts and verify cross-domain causal workflow. A proposed engineering target is 30/40 useful on a fresh stratified sample, not a corporate-authorized standard.

## Private evidence, never committed

`/home/u23u/else_itil_functional_v2_qa_20261110/`: model per-case proposals, logs, checkpoints, source snapshots, holdout selection.
`/home/u23u/else_itil_aug2026_review_private_20261110/human50_audit_20261110/`: audited development cases and private historical solutions.

Only aggregate tests, implementation, and this doc go to GitHub.
