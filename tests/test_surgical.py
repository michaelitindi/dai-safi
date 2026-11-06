from datetime import UTC, datetime, timedelta
from pathlib import Path

from dai_safi.engine import evaluate
from dai_safi.models import ClaimDraft, Document, Intervention, Severity
from dai_safi.rules import load_rules

RULES = load_rules(Path(__file__).resolve().parents[1] / "rules", include_draft=True)
NOW = datetime(2026, 10, 22, tzinfo=UTC)
PROC = datetime(2026, 10, 10, tzinfo=UTC)


def ids(draft: ClaimDraft) -> set[str]:
    return {i.rule_id for i in evaluate(draft, RULES, NOW).issues}


def surgical(*others: Intervention, procedure_at: datetime | None = PROC) -> ClaimDraft:
    return ClaimDraft(
        claim_ref="CLM-TEST",
        interventions=[Intervention(code="SHA-19-001", complexity="major"), *others],
        procedure_at=procedure_at,
        admitted_at=PROC - timedelta(days=1),
        discharged_at=PROC + timedelta(days=5),
    )


def test_critical_care_inside_global_period_is_flagged() -> None:
    d = surgical(Intervention(code="SHA-03-001", started_at=PROC + timedelta(days=1)))
    assert "COMBO-SHA-001" in ids(d)


def test_critical_care_after_global_period_is_allowed() -> None:
    d = surgical(Intervention(code="SHA-03-001", started_at=PROC + timedelta(days=4)))
    assert "COMBO-SHA-001" not in ids(d)


def test_unverifiable_global_period_warns_but_stays_ready() -> None:
    d = surgical(Intervention(code="SHA-03-001"), procedure_at=None)
    result = evaluate(d, RULES, NOW)
    combo = [i for i in result.issues if i.rule_id == "COMBO-SHA-001"]
    assert combo and combo[0].severity == Severity.WARNING
    assert result.ready


def test_per_diem_inside_global_period_is_flagged() -> None:
    d = surgical(Intervention(code="SHA-07-002", is_per_diem=True,
                              started_at=PROC + timedelta(days=1)))
    assert "SURG-001" in ids(d)


def test_surgical_claim_needs_three_dates() -> None:
    d = ClaimDraft(claim_ref="CLM-TEST",
                   interventions=[Intervention(code="SHA-19-001", complexity="major")])
    assert "SURG-002" in ids(d)
    assert "SURG-002" not in ids(surgical())


def test_missing_required_document_is_an_error() -> None:
    iv = Intervention(code="SHA-07-001", required_document_types=["DISCHARGE_SUMMARY"])
    d = ClaimDraft(claim_ref="CLM-TEST", interventions=[iv])
    assert not evaluate(d, RULES, NOW).ready
    with_doc = d.model_copy(update={"documents": [Document(type="DISCHARGE_SUMMARY")]})
    assert "DOC-001" not in ids(with_doc)
