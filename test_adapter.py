from datetime import datetime, timezone
from types import SimpleNamespace as NS

from dai_safi.adapters.sha_claim import from_virtual_claim


def test_adapter_maps_fields_and_drops_the_consent_token() -> None:
    vc = NS(
        invoice_number="INV-1",
        guid=None,
        service_type=NS(value="INPATIENT"),
        consent_token="SECRET-TOKEN",
        interventions=[NS(code="SHA-19-001", applicable_document_types=("THEATRE_NOTES",),
                          bill_from=None, is_per_diem=False)],
        attachments=[NS(attachment_type="THEATRE_NOTES")],
        visit_start=datetime(2026, 10, 1, tzinfo=timezone.utc),
        visit_end=None,
    )
    draft = from_virtual_claim(vc, complexity_by_code={"SHA-19-001": "major"})
    assert draft.claim_ref == "INV-1"
    assert draft.claim_type == "INPATIENT"
    assert draft.interventions[0].complexity == "major"
    assert draft.documents[0].type == "THEATRE_NOTES"
    assert "SECRET-TOKEN" not in draft.model_dump_json()
