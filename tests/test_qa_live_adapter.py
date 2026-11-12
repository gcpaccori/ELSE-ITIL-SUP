"""Bound real live adapter: pending is NOT evidence and models cannot scope-hop."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from else_dominance.qa_dispatch_queue import QaDispatchQueue,load_allowed
from else_dominance.qa_live_adapter import QaDispatchLiveAdapter,QA_QUERY
from else_dominance.agent import InvestigationAgent
from else_dominance.memory import CaseMemory
from else_dominance.sources import EvidenceTools,SourceCatalog


def setup(root):
    hashes=sorted(sha256(f"synthetic-id-{i}".encode()).hexdigest()
                  for i in range(545))
    file=root/"allowed.txt"
    file.write_text("\n".join(hashes)+"\n")
    return hashes,QaDispatchQueue(root/"queue.sqlite",load_allowed(file))


def test_query_live_starts_actual_queued_work_and_pending_not_evidence(tmp_path):
    hashes,q=setup(tmp_path)
    with q:
        a=QaDispatchLiveAdapter(q)
        scope={"case_sha256":hashes[0]}
        first=a.run(QA_QUERY,{"case_sha256":hashes[0]},scope=scope)
        assert first["status"]=="PENDING"
        assert first["provenance_verified"] is False
        assert first["error"]=="NO_CORPORATE_RECEIPT_YET"
        second=a.run(QA_QUERY,{"case_sha256":hashes[0],
                              "job_id":first["job_id"]},scope=scope)
        assert second["job_id"]==first["job_id"]
        assert q.conn.execute("SELECT count(*) FROM qa_jobs").fetchone()[0]==1


def test_tools_model_cannot_change_case_or_query_and_no_sql(tmp_path):
    hashes,q=setup(tmp_path)
    with q:
        a=QaDispatchLiveAdapter(q)
        s={"case_sha256":hashes[0]}
        for args in [
            {"case_sha256":hashes[1]},
            {"case_sha256":hashes[0],"sql":"DELETE FROM x"},
            {"case_sha256":hashes[0],"host":"ELSE70"},
            {"case_sha256":hashes[0],"job_id":"5"*32},
        ]:
            out=a.run(QA_QUERY,args,scope=s)
            assert out["status"]=="BLOCKED"
        assert a.run("SELECT_USER_DATA",{"case_sha256":hashes[0]},
                     scope=s)["status"]=="BLOCKED"
        assert q.conn.execute("SELECT count(*) FROM qa_jobs").fetchone()[0]==0


def test_completed_without_independent_proof_is_denied(tmp_path):
    hashes,q=setup(tmp_path)
    with q:
        a=QaDispatchLiveAdapter(q)
        s={"case_sha256":hashes[0]}
        job=a.run(QA_QUERY,{"case_sha256":hashes[0]},scope=s)
        q.conn.execute(
            "UPDATE qa_jobs SET state='COMPLETED',result_json=? WHERE job_id=?",
            (json.dumps({"o5_o13_o15_verified":True,
                         "fresh_read_after_model_request":False,
                         "repair_certified":False}),job["job_id"]))
        response=a.run(QA_QUERY,{"case_sha256":hashes[0],
                                "job_id":job["job_id"]},scope=s)
        assert response["status"]=="BLOCKED"
        assert response["error"]=="QA_RECEIPT_NOT_VERIFIED"


class FakeModel:
    def __init__(self,sha):
        self.sha=sha
        self.responses=iter([
            {"type":"tool","name":"query_live",
             "args":{"query_id":QA_QUERY,
                     "parameters":{"case_sha256":sha}}},
            {"type":"final","status":"PLAN_PROPUESTO",
             "system_and_operation":"Diagnóstico ITIL",
             "problem":"Problema sin comprobar en sistema externo",
             "hypotheses":[{"cause":"Error hipotético",
                            "evidence_refs":["TOOL:1"],
                            "test":"Verificar observación técnica."}],
             "proposed_steps":[{"action":"Consultar datos QA",
                                "source":"ITIL.taIncidente",
                                "precondition":"Acceso de lectura",
                                "evidence_refs":["TOOL:1"],
                                "verification":"Comparar estado del servicio"}],
             "missing_evidence":["Lectura de origen aún pendiente"],
             "next_question":"¿Podemos obtener recibo validado?",
             "reasoning_summary":"Aún no existe la lectura",
             "confidence":"HIGH",
             "change_domains":["GESTION_SERVICIO"]}
        ])
    def complete(self,messages):
        return json.dumps(next(self.responses))


def test_actual_multistep_investigation_agent_cannot_claim_pending_as_evidence(
        tmp_path):
    hashes,q=setup(tmp_path)
    with q:
        memory=CaseMemory(tmp_path/"history.sqlite")
        try:
            catalog=SourceCatalog(
                Path(__file__).resolve().parents[1]/"data"/"source_catalog.json")
            tools=EvidenceTools(memory,catalog,QaDispatchLiveAdapter(q))
            model=FakeModel(hashes[0])
            case={"case_ref":"itil-synthetic-1",
                  "case_sha256":hashes[0],
                  "description":"Incidencia administrativa de prueba sin datos SQL todavía",
                  "service_code":"1",
                  "module_code":"A","classification_code":"101",
                  "as_of":"2026-01-01T00:00:00"}
            result=InvestigationAgent(model,tools,memory,max_steps=3).investigate(
                case,now="2026-11-10T12:00:00")
            assert result["tool_calls"]==1
            assert result["status"]=="INVESTIGACION_PENDIENTE"
            assert "TOOL:1" in result["invalid_references"]
            assert result["live_source_evidence_available"] is False
            assert result["can_claim_resolved"] is False
            assert memory.verify_ledger(result["session_id"])
        finally:
            memory.close()
