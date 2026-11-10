"""Batch real SAP OT evidence from uniquely identified numbers in 100 QA cases.

This is the second concrete corporate read capability beyond ITIL.
A reported OT number is a *claim* until the fixed database SELECT verifies
its existence. Historical solutions and raw SAP response messages withheld.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,re,subprocess,zipfile
from qa_feb100_windows import read_allowlist
ROOT=Path(r"C:\Temp\ELSE_ITIL_FEB100_QA_20261110")
ALLOW=ROOT/"feb100_allowlist.private.jsonl"
SOURCE=ROOT/"qa/Feb100SapOtRead.cs"
DLL=ROOT/"qa/bin/Release/net8.0/Feb100SapOtRead.dll"
OUT=ROOT/"ot_sap_receipts"
ZIP=ROOT/"feb100_ot_sap_receipts.private.zip"
SUMMARY=ROOT/"feb100_ot_sap_summary.json"
RE=re.compile(r"(?:\bOT\b|orden\s+(?:de\s+)?trabajo|c[oó]digo\s*OT)"
              r"\s*[:#=-]?\s*(\d{4,19})\b",re.I)

def case_ot(row):
    numbers=set(RE.findall(row["description_redacted"]))
    return next(iter(numbers)) if len(numbers)==1 else None

def run_one(row,ot):
    case_sha=row["case_sha256"]
    raw=subprocess.run(["dotnet",str(DLL),ot],capture_output=True,timeout=60)
    if raw.returncode!=0:
        return {"case_sha256":case_sha,"status":"OT_QA_SQL_UNAVAILABLE",
                "error_type":"SAP_QUERY_ERROR"}
    source=json.loads(raw.stdout.splitlines()[-1])
    if (source.get("schema")!="else.itil.qa.feb100.sap-ot-readonly.v1"
         or source.get("order_sha256")!=sha256(ot.encode()).hexdigest()
         or source.get("qa_target")!="ELSE70/dbDistribucion_D"
         or source.get("query_ids")!=[
            "QA_DISTRIB_SAP_ORDER_BY_OT",
            "QA_DISTRIB_SAP_RESPONSE_BY_OT"]
         or source.get("sources")!=[
            "dbo.taOrdenTrabajoSAP",
            "dbo.taOrdenTrabajoSAPEnvioRespuesta"]
         or source.get("read_only") is not True
         or source.get("changes_executed") is not False):
        return {"case_sha256":case_sha,"status":"OT_RECEIPT_INVALID"}
    body={"schema":"else.itil.feb100.ot-sap-case-evidence.v1",
          "case_sha256":case_sha,
          "binding_provenance":"REPORTED_OT_FROM_REDACTED_CASE_TEXT_ONLY",
          "reported_ot_sha256":source["order_sha256"],
          "reader_source_sha256":sha256(SOURCE.read_bytes()).hexdigest(),
          "observation":source,
          "read_only":True,
          "mutations":False,
          "functional_repair_certified":False,
          "root_cause_certified":False,
          "requires_technician_review":True}
    file=OUT/(case_sha+".private.json")
    file.write_text(json.dumps(body,sort_keys=True,ensure_ascii=False),
                    encoding="utf-8")
    return {"case_sha256":case_sha,"status":"RECEIPT_VERIFIED_LOCALLY",
            "order_found":source["order_found"],
            "response_rows_up_to5":source["response_rows_up_to5"],
            "receipt_sha256":sha256(file.read_bytes()).hexdigest()}

def main():
    if OUT.exists() or ZIP.exists() or SUMMARY.exists():
        raise FileExistsError("OT_BATCH_NO_OVERWRITE")
    rows=read_allowlist(ALLOW)
    accepted=[]
    for row in rows.values():
        ot=case_ot(row)
        if ot:accepted.append((row,ot))
    OUT.mkdir(mode=0o700)
    results=[run_one(row,ot) for row,ot in accepted]
    with zipfile.ZipFile(ZIP,"x",compression=zipfile.ZIP_STORED) as zip:
        for r in results:
            if r["status"]!="RECEIPT_VERIFIED_LOCALLY":continue
            file=OUT/(r["case_sha256"]+".private.json")
            zip.write(file,arcname=file.name)
    summary={
       "schema":"else.itil.feb100.ot-sap-batch.v1",
       "cases_in_sample":len(rows),
       "unique_reported_ot_candidates":len(accepted),
       "query_receipts_passed":sum(x["status"]=="RECEIPT_VERIFIED_LOCALLY" for x in results),
       "sql_query_errors":sum(x["status"]!="RECEIPT_VERIFIED_LOCALLY" for x in results),
       "orders_found_in_specific_qa_table":sum(x.get("order_found") is True for x in results),
       "no_rows_in_specific_qa_table":sum(
           x["status"]=="RECEIPT_VERIFIED_LOCALLY" and x.get("order_found") is False for x in results),
       "results":results,
       "archive_sha256":sha256(ZIP.read_bytes()).hexdigest(),
       "source_sha256":sha256(SOURCE.read_bytes()).hexdigest(),
       "repair_certified":0,
       "claimed_business_entity_proof":False,
    }
    SUMMARY.write_text(json.dumps(summary,sort_keys=True,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="results"},sort_keys=True))
if __name__=="__main__":main()
