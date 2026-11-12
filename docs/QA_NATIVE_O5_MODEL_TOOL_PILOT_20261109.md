# ELSE-ITIL-SUP — native O5 QA receipt and model-invoked tool pilot

Date: 2026-11-09. Status: isolated QA pilot only; NO change to the existing
persistent support listener on 127.0.0.1:18883.

## What was executed

A previously authorized .NET/SIELSEAccesoDatos query on Windows QA ELSE62
produced one exact 2026-09 ITIL record and a read-only transfer receipt. A
protected, operator-owned configuration pins the original receipt SHA-256 and
the Windows C# reader's source SHA and byte count.

ELSE CORE's native HandCapability
itil.qa.nuget.receipt.readonly.v1 consumed the fixed bundle through the O5
router, Guardian O13, independent QA verifier, and O15 ledger.

Two pilot variants completed on elsecluster5:

1. Owner-invoked O5 verification, then Qwen3.5-9B diagnostic procedure:
   DIAGNOSTIC_GUIDANCE; O13/O15 PASS; model QA gate PASS.
2. Model-invoked exact tool call qa_exact_read, then O5 verification and
   Qwen3.5-9B diagnostic procedure: DIAGNOSTIC_GUIDANCE;
   model_requested_tool=true, O13/O15 PASS, QA gate PASS.

In both variants the model never received the historical human solution.
The incident description was a separately redacted QA historical export, not
asserted byte-equal to the NuGet SQL request. There was NO new SQL query as part
of either O5 execution, NO observed current device/application state, no
functional root-cause certificate, and no repairs.

Private receipts and case text remain outside Git under the authenticated
operator's private QA directory; only code and generic QA tests are committed.

## API and trust boundary

qa_native_runtime.py provides the operator-invoked O5 diagnostic and
qa_o5_tool_runtime.py supports a model-initiated, single-tool dialogue.
Only exact query_id ITIL_2026_09_CASE_EXACT_READ and the preapproved case SHA
are accepted. No SQL, host, source path, credential, or arbitrary parameters
may be supplied by Qwen.

The model receives a factual source-metadata observation only after O5/O13/O15
pass. A wrong query/case, extra arguments, wrong service/module, false
provenance, unverified evidence, attempted SQL, or a malformed response fails
closed. The QA runners accept loopback inference endpoints only.

These tools are isolated, direct owner-invoked CLI workflows. They are not
enabled on the persistent support HTTP listener, and cannot change its
USER_SUBMITTED_ONLY status. They are not generic autonomous new SQL reads.

## Running in a trusted operator environment

Install or select reviewed ELSE CORE and ELSE-ITIL-SUP source trees. In an
authorized private Python environment, make both Python packages importable
without copying their source into any corporate application. Preconfigure
private 0600 JSON owner and case files with independently verified pins.

Example command (paths are placeholders, not a public endpoint):

    python -m else_dominance.qa_o5_tool_runtime \
      --owner /private/owner.json \
      --case /private/redacted-case.json \
      --out /private/result.json

This emits only aggregate status and SHA on stdout. Detailed diagnostic
content remains in a create-only private output file.

## What remains before live autonomous NuGet queries

A persistent, authenticated, auditable execution channel must reach the
authorized Windows QA .NET reader. Windows ELSE62 SSH inbound is not currently
enabled. Existing Windows-to-Linux outbound SSH was sufficient only for
operator-mediated private file transfer. Do not enable inbound SSH, attach a
database connection or schedule a persistent SQL poller without an owner
approved access protocol and independent security review.

O5 PASS here certifies the exact receipt-read operation, not a ticket repair.
The normal human-functional validation and 2026 holdout embargo remain.
