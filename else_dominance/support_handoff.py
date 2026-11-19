"""Consent-backed, authenticated handoff between a guided user and human support.

A handoff can authenticate *who issued this report in the private pilot*, not
who a corporate employee is nor whether its diagnosis or business data is true.
No corporate SQL, ticket joins, automated repairs, or identity federation.

HMAC key is separate from application bearer tokens and stays in a 0600 file.
Packets are explicitly user-reported; the technician verifies authenticity and
consent before treating the packet as a source of human-provided observations.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import hmac
import json
import re

SCHEMA = "else.itil.guided-handoff-packet.v1"
WRAPPER = "else.itil.guided-handoff-signed.v1"
MAX_AGE = timedelta(hours=72)
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def canonical_bytes(value:object)->bytes:
    return json.dumps(value,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def utc_timestamp(value:object)->datetime:
    if not isinstance(value,str) or len(value)>40:
        raise ValueError("HANDOFF_TIME_INVALID")
    try:
        ts=datetime.fromisoformat(value)
    except ValueError as e:
        raise ValueError("HANDOFF_TIME_INVALID") from e
    if ts.tzinfo is None or ts.utcoffset()!=timedelta(0):
        raise ValueError("HANDOFF_TIME_NOT_UTC")
    return ts


class HandoffSigner:
    def __init__(self,key:bytes):
        if not isinstance(key,bytes) or len(key)!=32:
            raise ValueError("HANDOFF_SIGNER_KEY_INVALID")
        self._key=key

    @classmethod
    def from_file(cls,path:Path):
        path=Path(path)
        if not path.is_file() or path.is_symlink():
            raise ValueError("HANDOFF_SIGNING_KEY_MISSING_OR_SYMLINK")
        if path.stat().st_mode & 0o077:
            raise ValueError("HANDOFF_KEY_PERMISSIONS_TOO_BROAD")
        value=path.read_text(encoding="ascii").strip()
        if not HEX64.fullmatch(value):
            raise ValueError("HANDOFF_SIGNER_KEY_INVALID")
        return cls(bytes.fromhex(value))

    def case_handle(self,sid:str)->str:
        # Opaque pseudonym, cannot be used to authorize QA/business lookup.
        if not isinstance(sid,str) or not re.fullmatch(r"[0-9a-f]{48}",sid):
            raise ValueError("HANDOFF_SESSION_INVALID")
        return hmac.new(self._key,b"case-handle-v1\0"+sid.encode(),
                        "sha256").hexdigest()

    def sign(self,packet:dict)->dict:
        if packet.get("schema")!=SCHEMA:
            raise ValueError("HANDOFF_SCHEMA_INVALID")
        return {
            "schema":WRAPPER,
            "packet":packet,
            "signature":hmac.new(self._key,canonical_bytes(packet),"sha256").hexdigest(),
        }

    def verify(self,envelope:object,*,now:datetime|None=None)->dict:
        if not isinstance(envelope,dict) or set(envelope)!={
            "schema","packet","signature"} or envelope["schema"]!=WRAPPER:
            raise ValueError("HANDOFF_ENVELOPE_INVALID")
        signature=envelope["signature"]
        packet=envelope["packet"]
        if not isinstance(signature,str) or not HEX64.fullmatch(signature):
            raise ValueError("HANDOFF_SIGNATURE_INVALID")
        if not isinstance(packet,dict) or set(packet)!={
            "schema","receipt_id","case_handle","service","issue_reported",
            "issued_utc","expires_utc","last_turn","observations",
            "technical_review","scope","consent_mode",
        } or packet["schema"]!=SCHEMA:
            raise ValueError("HANDOFF_PACKET_SCHEMA_INVALID")
        expected=hmac.new(self._key,canonical_bytes(packet),"sha256").hexdigest()
        if not hmac.compare_digest(signature,expected):
            raise ValueError("HANDOFF_SIGNATURE_MISMATCH")
        if (not isinstance(packet["receipt_id"],str) or
            not HEX32.fullmatch(packet["receipt_id"])):
            raise ValueError("HANDOFF_RECEIPT_ID_INVALID")
        if (not isinstance(packet["case_handle"],str) or
            not HEX64.fullmatch(packet["case_handle"])):
            raise ValueError("HANDOFF_HANDLE_INVALID")
        t0=utc_timestamp(packet["issued_utc"])
        t1=utc_timestamp(packet["expires_utc"])
        utcnow=now or datetime.now(timezone.utc)
        if (utcnow.tzinfo is None or utcnow.utcoffset()!=timedelta(0)
            or t0>utcnow+timedelta(minutes=2)
            or utcnow>=t1 or t1<=t0 or t1-t0>MAX_AGE):
            raise ValueError("HANDOFF_EXPIRED_OR_INVALID_TIME")
        if type(packet["last_turn"]) is not int or not 1<=packet["last_turn"]<=6:
            raise ValueError("HANDOFF_TURN_INVALID")
        if (packet["scope"]!="USER_REPORTED_NO_CORPORATE_BINDING" or
            packet["consent_mode"]!="EXPLICIT_REQUESTER_SHARE_WITH_SUPPORT"):
            raise ValueError("HANDOFF_SCOPE_INVALID")
        observations=packet["observations"]
        if (not isinstance(observations,list)
            or len(observations)!=packet["last_turn"]
            or any(not isinstance(x,dict) or set(x)!={
                "turn","reported_by_user","safe_screen_check",
                "model_format_accepted","workflow_status",
            } for x in observations)
            or any(x["turn"]!=i for i,x in enumerate(observations,1))
            or any(type(x["model_format_accepted"]) is not bool
               or x["workflow_status"] not in {
                 "GUIDED_DIAGNOSTIC_CONDITIONAL","NEEDS_HUMAN_TRIAGE",
                 "USER_REPORTED_IMPROVEMENT_UNVERIFIED",
               } or not isinstance(x["reported_by_user"],str)
               or not 4<=len(x["reported_by_user"])<=500
               or not isinstance(x["safe_screen_check"],str)
               or not 10<=len(x["safe_screen_check"])<=300
               for x in observations)):
            raise ValueError("HANDOFF_OBSERVATIONS_INVALID")
        if (not isinstance(packet["technical_review"],dict)
            or set(packet["technical_review"])!={
                "cause_certified","qa_evidence_bound","repair_performed",
                "human_review_required","source_status","next_action",
            }
            or packet["technical_review"]!={
                "cause_certified":False,
                "qa_evidence_bound":False,
                "repair_performed":False,
                "human_review_required":True,
                "source_status":"REQUESTER_OBSERVATIONS_ONLY",
                "next_action":"VALIDATE_CASE_AND_EVIDENCE_WITH_AUTHORIZED_SUPPORT",
            }):
            raise ValueError("HANDOFF_EVIDENCE_BOUNDARY_INVALID")
        if not all(isinstance(packet[k],str) and 4<=len(packet[k])<=800
                   for k in ("service","issue_reported")):
            raise ValueError("HANDOFF_TEXT_INVALID")
        return packet


def safe_handoff_packet(*,receipt_id:str,case_handle:str,service:str,
                        issue_reported:str,issued:datetime,
                        last_turn:int,observations:list[dict])->dict:
    if issued.tzinfo is None or issued.utcoffset()!=timedelta(0):
        raise ValueError("HANDOFF_ISSUE_TIME_INVALID")
    return {
      "schema":SCHEMA,"receipt_id":receipt_id,
      "case_handle":case_handle,"service":service,
      "issue_reported":issue_reported,
      "issued_utc":issued.isoformat(),
      "expires_utc":(issued+MAX_AGE).isoformat(),
      "last_turn":last_turn,
      "observations":observations,
      "technical_review":{
        "cause_certified":False,
        "qa_evidence_bound":False,
        "repair_performed":False,
        "human_review_required":True,
        "source_status":"REQUESTER_OBSERVATIONS_ONLY",
        "next_action":"VALIDATE_CASE_AND_EVIDENCE_WITH_AUTHORIZED_SUPPORT",
      },
      "scope":"USER_REPORTED_NO_CORPORATE_BINDING",
      "consent_mode":"EXPLICIT_REQUESTER_SHARE_WITH_SUPPORT",
    }


def payload_digest(packet:dict)->str:
    return sha256(canonical_bytes(packet)).hexdigest()
