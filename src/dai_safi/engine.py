from __future__ import annotations

from datetime import datetime

from .checks import CHECKS
from .models import CheckResult, ClaimDraft, Issue, Severity
from .rules import RuleSet


def evaluate(draft: ClaimDraft, ruleset: RuleSet, as_of: datetime) -> CheckResult:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    for name, value in (
        ("admitted_at", draft.admitted_at),
        ("procedure_at", draft.procedure_at),
        ("discharged_at", draft.discharged_at),
    ):
        if value is not None and value.tzinfo is None:
            raise ValueError(f"{name} must be timezone-aware")
    for i in draft.interventions:
        if i.started_at is not None and i.started_at.tzinfo is None:
            raise ValueError(f"started_at for {i.code} must be timezone-aware")

    issues: list[Issue] = []
    for rule in ruleset.rules:
        check = CHECKS.get(rule.check)
        if check is None:
            raise ValueError(f"Unknown check type: {rule.check}")
        issues.extend(check(rule, draft, as_of))

    return CheckResult(
        claim_ref=draft.claim_ref,
        ready=not any(i.severity == Severity.ERROR for i in issues),
        issues=issues,
        rules_version=ruleset.version,
    )
