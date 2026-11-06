from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Severity(str, Enum):
    ERROR = "error"      # likely rejection or return
    WARNING = "warning"  # likely query or review


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


Complexity = Literal["minor", "major", "specialized"]


class Document(Strict):
    type: str


class Intervention(Strict):
    code: str                                   # e.g. "SHA-19-001"
    # Maps to DHA's applicableDocumentTypes (documents required for the claim)
    required_document_types: list[str] = Field(default_factory=list)
    started_at: datetime | None = None          # when billing for this intervention began
    complexity: Complexity | None = None        # surgical only; from Intervention Coverage
    is_per_diem: bool = False


class ClaimDraft(Strict):
    claim_ref: str
    scheme: str = "SHA"                         # "SHA" (standard covers) or "POMSF"
    claim_type: str = "unknown"
    # Order matters: the FIRST intervention added sets the combination rules.
    interventions: list[Intervention]
    documents: list[Document] = Field(default_factory=list)
    admitted_at: datetime | None = None
    procedure_at: datetime | None = None
    discharged_at: datetime | None = None


class Issue(Strict):
    rule_id: str
    severity: Severity
    message: str
    fix: str
    source: str | None = None


class CheckResult(Strict):
    claim_ref: str
    ready: bool
    issues: list[Issue]
    rules_version: str
