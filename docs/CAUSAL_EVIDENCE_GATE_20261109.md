# ELSE-ITIL — Evidence-based causal calibration gate (2026-11-09)

This branch adds an isolated, fail-closed review intake, not additional static help-desk rules. It does not change the live V1 listener, enable database writes, or authorize model training.

## Corporate QA evidence

The audit was created on authorized ELSE62, against the existing January 2026 ITIL QA NuGet export. The calibration cohort was deterministically selected based only on case metadata and human note length at least 400 characters. All original incident text and human solutions remain in the private ELSE62 directory, never in this repository. This is a calibration exercise, not a fresh final blind test.

Six Qwen3.5-9B diagnostic plans were sealed before historical solution text was given to the generator; only solution lengths were used as selection metadata. Five passed the schema/safety gate; one failed on undeclared source references. An independent Qwen3.5-4B reviewer returned one SUPPORTED documentary compatibility (with an actionable historical note), and five INDETERMINATE relationships. These are model-based assessments, not human or functional root-cause validation. Zero repairs, zero functional root causes and zero training samples are certified.

Private audit SHA-256 anchor:

    9fcb3fd06a2299f9fb5edfa0b97cd0167f3f63f1465d11f526fa6c96a7eac289

The original audit resides at C:\Temp\ELSE_ITIL_CAUSAL_QA_20261109\AUDIT_SUMMARY.json on ELSE62. An authenticated, byte-for-byte copy was independently verified in /home/u23u/else_itil_causal_audit_private_20261109/ on elsecluster5. The audit is not version-controlled.

## Hard boundaries

The function else_dominance.causal_review.verify_audit(raw, pinned_sha256=...) checks byte identity against an externally trusted hash before accepting metadata, row counts, uniqueness, safety states, QA gate outcomes and documentary reviewer claims. The caller must obtain the pin from a trusted operator, never from the same untrusted file.

The function make_review_queue issues only UNDER_REVIEW entries with eligible_for_training=false, repair_certified=false, and root_cause_certified=false.

The queue distinguishes three paths: (1) invalid source binding requires corrected references and rerun; (2) documentary compatibility requires independent functional QA and human sign-off; (3) indeterminate comparison requires causal evidence and expert adjudication.

The QA-side auditor blocked three deliberate attacks: modified plan bytes, wrong-case review and falsified historical digest. The local gate includes additional synthetic adversarial tests.

## Remaining gates

No NuGet SQL Hand is registered in the live V1 service; its /health still reports source_access=USER_SUBMITTED_ONLY. The 2026 cohort is excluded from model training. Before a true resolution claim, obtain a separate approved read-only operational observation, explicit diagnostic discrimination, reproducible functional outcome, and independent expert approval. A model-only review cannot substitute for any of these.

Nothing in this branch modifies the corporate database or changes ELSE CORE's canonical main baseline.
