# August 2026 — two native verified QA Hands for operational OT + SAP exchange

## Proven scope and limitations

- Authoritative frozen source: exactly **1,819** August 2026 ITIL request snapshots, solutions withheld; exactly **five** have a unique OT number still visible in the redacted request and qualify for these fixed queries.
- **ELSE62** executes fixed byte-pinned, read-only .NET 8 NuGet readers against **ELSE70/dbDistribucion_D**; it does not execute any SQL from Qwen.
- Two logically distinct native O5/O13/O15 receipt Hands independently verify (a) operational **dbo.taOrdenTrabajo** and (b) **dbo.taOrdenTrabajoSAP** plus **dbo.taOrdenTrabajoSAPEnvioRespuesta**. Windows HMAC delivery is bound to source files, original August case hash, reported OT hash, job and result bytes.
- Five of five verified SAP exchange reads: **no match in these two tables**. Five of five verified operational reads: **no match in dbo.taOrdenTrabajo**. A negative query under these exact predicates does **not** establish enterprise-wide nonexistence, a root cause, or a corporate ITIL↔OT business-key relationship.
- Evidence-aware Qwen9B rerun over five: **3/5 functional addenda accepted**, two fail closed (generic check / unsupported global inference). These are contract passes, **not confirmed correct diagnoses**.
- The new private loopback-only service `127.0.0.1:18890` requires a bearer token and an exact allowlisted case SHA; the server replays both native Hand verifications on each evidence read. Duplicate requests return idempotent stored results. No database read occurs from the HTTP process; it consumes verified prior reads, and never initiates repairs.
- No change to production or to existing 18883/18889 QA. No IAM or broader commercial integration has been authorized by these experiments.

## Reproducible QA and provenance

- Linux independent verifier and actual source receipt replay: `else_dominance/aug2026_sap_ot_verified.py`, `operational_ot_verified.py`, `operational_ot_o5_hand.py`, `operational_ot_o5_verifier.py`.
- Fixed Windows readers and workers: `qa/AugOperationalOtRead.cs`, `qa/aug2026_operational_ot_windows.py`, `qa/aug2026_sap_ot_windows.py`.
- Actual model evidence gate: `else_dominance/functional_live_sap_v2.py`.
- HTTP with exact owner SHA and idempotency: `else_dominance/functional_verified_http_v2.py`.
- Synthetic negative tests: `tests/test_aug_operational_o5.py`, `tests/test_aug_dual_domain.py` (**23/23 PASS**).
- Private QA receipts and journals remain in `/home/u23u/else_itil_aug_domain_hand_qa_20261110` and **must not** be published to GitHub.

## Next technical gap

The five explicit IDs were absent in both tables in this QA environment. The next meaningful domain capability is to investigate **what identifier ITIL actually refers to**, e.g. sanctioned module-specific business keys and semantic joins, rather than equating a textual OT token to an enterprise database key. For cases with redacted identifiers, ask for the specific source or identifier; do not invent it. Extend to commercial and IAM Hands only with explicitly bounded independent receipts. Independent human functional correctness assessment still pending.

**Release decision:** QA pilot only, not general-purpose autonomous V1 Beta.
