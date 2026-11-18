"""Opt-in private per-principal guided access, never a corporate SSO assertion.

Each token is generated OUTSIDE the API and stored only as SHA256 in a
permission-restricted manifest. SHA256 is appropriate for uniformly random
high-entropy tokens, NOT human passwords. No token provisioning endpoint.
Legacy service token remains for the old API but is disallowed for guided
routes when principal mode is enabled.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import hmac
import json
import re

_SUBJECT=re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
_HEX=re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Principal:
    subject: str
    token_sha256: str
    enabled: bool


class PrincipalRegistry:
    def __init__(self, principals:tuple[Principal,...]):
        if not 1<=len(principals)<=128:
            raise ValueError("GUIDED_PRINCIPALS_COUNT_INVALID")
        self._principals=principals

    @classmethod
    def from_file(cls,path:Path):
        path=Path(path)
        if path.is_symlink() or not path.is_file():
            raise ValueError("GUIDED_PRINCIPALS_FILE_MISSING_OR_SYMLINK")
        if path.stat().st_mode & 0o077:
            raise ValueError("GUIDED_PRINCIPALS_FILE_PERMISSIONS_TOO_BROAD")
        obj=json.loads(path.read_text(encoding="utf8"))
        if not isinstance(obj,dict) or set(obj)!={"schema","principals"} or (
                obj["schema"]!="else.itil.guided-principals.v1"):
            raise ValueError("GUIDED_PRINCIPALS_SCHEMA_INVALID")
        raw=obj["principals"]
        if not isinstance(raw,list) or not 1<=len(raw)<=128:
            raise ValueError("GUIDED_PRINCIPALS_COUNT_INVALID")
        principals=[]
        seen_subject=set()
        seen_digest=set()
        for item in raw:
            if not isinstance(item,dict) or set(item)!={"subject","token_sha256","enabled","roles"}:
                raise ValueError("GUIDED_PRINCIPAL_SCHEMA_INVALID")
            sub=item["subject"]
            digest=item["token_sha256"]
            roles=item["roles"]
            if not isinstance(sub,str) or not _SUBJECT.fullmatch(sub):
                raise ValueError("GUIDED_SUBJECT_INVALID")
            if not isinstance(digest,str) or not _HEX.fullmatch(digest):
                raise ValueError("GUIDED_TOKEN_DIGEST_INVALID")
            if type(item["enabled"]) is not bool or roles!=["guided_user"]:
                raise ValueError("GUIDED_PRINCIPAL_ROLE_INVALID")
            if sub in seen_subject or digest in seen_digest:
                raise ValueError("GUIDED_PRINCIPALS_DUPLICATE")
            seen_subject.add(sub);seen_digest.add(digest)
            principals.append(Principal(sub,digest,item["enabled"]))
        return cls(tuple(principals))

    def authenticate(self,header:object)->str|None:
        if not isinstance(header,str) or not header.startswith("Bearer "):
            return None
        secret=header[7:]
        if not 32<=len(secret)<=256 or not secret.isascii():
            return None
        digest=sha256(secret.encode("ascii")).hexdigest()
        match=None
        # Always compare all digests; no user IDs or tokens in response.
        for item in self._principals:
            valid=hmac.compare_digest(digest,item.token_sha256)
            if valid and item.enabled:
                match=item.subject
        return match
