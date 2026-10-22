from datetime import datetime, timezone

from dai_safi.engine import evaluate
from dai_safi.models import ClaimDraft, Intervention
from dai_safi.rules import load_rules

NOW = datetime(2026, 10, 22, tzinfo=timezone.utc)
RULES = load_rules("rules", include_draft=True)


def draft(codes: list[str], scheme: str = "SHA") -> ClaimDraft:
    return ClaimDraft(claim_ref="CLM-TEST", scheme=scheme,
                      interventions=[Intervention(code=c) for c in codes])


def ids(codes: list[str], scheme: str = "SHA") -> set[str]:
    return {i.rule_id for i in evaluate(draft(codes, scheme), RULES, NOW).issues}


def test_outpatient_must_be_alone() -> None:
    assert "COMBO-SHA-001" in ids(["SHA-12-001", "SHA-09-001"])


def test_inpatient_with_imaging_is_allowed() -> None:
    assert "COMBO-SHA-001" not in ids(["SHA-07-001", "SHA-09-001"])


def test_first_intervention_decides() -> None:
    # SHA-09 must be alone, so adding SHA-07 after it is flagged
    assert "COMBO-SHA-001" in ids(["SHA-09-001", "SHA-07-001"])


def test_pomsf_uses_its_own_table() -> None:
    assert "COMBO-POMSF-001" not in ids(["PMF-07-001", "SHA-19-001"], scheme="POMSF")
    assert "COMBO-SHA-001" not in ids(["PMF-07-001", "SHA-19-001"], scheme="POMSF")


def test_unknown_package_gives_no_opinion() -> None:
    assert ids(["SHA-02-001", "SHA-12-001"]) == set()
