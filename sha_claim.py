from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ..models import ClaimDraft, Complexity, Document, Intervention


def from_virtual_claim(
    vc: Any,
    *,
    scheme: str = "SHA",
    procedure_at: datetime | None = None,
    complexity_by_code: Mapping[str, Complexity] | None = None,
) -> ClaimDraft:
    """Map a sha_claim VirtualClaim snapshot into a ClaimDraft.

    Deliberately drops consent_token: it is a bearer handle for the visit.

    The caller supplies what the snapshot does not carry:
      - scheme ("SHA" or "POMSF"),
      - procedure_at (surgical procedure date),
      - complexity_by_code (surgical complexity per intervention, from Intervention Coverage).

    Assumptions to verify against real data: visit_start is treated as the admission
    date and visit_end as the discharge date.
    """
    complexity_by_code = complexity_by_code or {}
    interventions = [
        Intervention(
            code=str(i.code),
            required_document_types=[str(t) for t in i.applicable_document_types],
            started_at=getattr(i, "bill_from", None),
            complexity=complexity_by_code.get(str(i.code)),
            is_per_diem=bool(getattr(i, "is_per_diem", False)),
        )
        for i in vc.interventions
    ]
    service_type = getattr(vc.service_type, "value", vc.service_type)
    return ClaimDraft(
        claim_ref=str(vc.invoice_number or vc.guid or "unknown"),
        scheme=scheme,
        claim_type=str(service_type) if service_type else "unknown",
        interventions=interventions,
        documents=[Document(type=str(a.attachment_type)) for a in vc.attachments],
        admitted_at=getattr(vc, "visit_start", None),
        procedure_at=procedure_at,
        discharged_at=getattr(vc, "visit_end", None),
    )
