from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timedelta

from .models import ClaimDraft, Intervention, Issue, Severity
from .rules import Rule

Check = Callable[[Rule, ClaimDraft, datetime], list[Issue]]

_PKG = re.compile(r"^([A-Z]{3})-(\d{2})")
# Nights covered by the surgical case rate (DHA surgical rules: "up to" for major and specialized)
GLOBAL_NIGHTS = {"minor": 1, "major": 3, "specialized": 7}
SURGICAL_PACKAGES = {"SHA-19"}


def package_of(code: str) -> str | None:
    m = _PKG.match(code)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _issue(rule: Rule, message: str, severity: Severity | None = None) -> Issue:
    return Issue(
        rule_id=rule.id,
        severity=severity or rule.severity,
        message=message,
        fix=rule.fix,
        source=rule.source,
    )


def required_documents(rule: Rule, draft: ClaimDraft, as_of: datetime) -> list[Issue]:
    have = {d.type for d in draft.documents}
    needed = {t for i in draft.interventions for t in i.required_document_types}
    missing = sorted(needed - have)
    if not missing:
        return []
    return [_issue(rule, f"Missing required documents: {', '.join(missing)}")]


def _global_period_end(procedure_at: datetime, complexity: str) -> datetime:
    # Boundary convention (which night counts first) is NOT confirmed: see rule notes.
    return procedure_at + timedelta(days=GLOBAL_NIGHTS[complexity])


def _global_period_issue(
    rule: Rule, draft: ClaimDraft, surgical: Intervention, other: Intervention
) -> list[Issue]:
    if draft.procedure_at is None or surgical.complexity is None or other.started_at is None:
        return [_issue(
            rule,
            f"Cannot verify the surgical global period before adding {other.code}: "
            "procedure date, complexity or start date is missing",
            Severity.WARNING,
        )]
    end = _global_period_end(draft.procedure_at, surgical.complexity)
    if other.started_at < end:
        return [_issue(
            rule,
            f"{other.code} starts inside the surgical global period (ends about {end.date()})",
            Severity.WARNING,  # warning until the boundary convention is verified
        )]
    return []


def combination_rules(rule: Rule, draft: ClaimDraft, as_of: datetime) -> list[Issue]:
    p = rule.params
    if draft.scheme != p["scheme"]:
        return []
    skip = set(p.get("skip_packages", []))
    ivs = [i for i in draft.interventions
           if (pkg := package_of(i.code)) is not None and pkg not in skip]
    if len(ivs) < 2:
        return []
    first = ivs[0]
    first_pkg = package_of(first.code)
    row = p["rows"].get(first_pkg)
    if row is None:
        return []  # no published row for this package: no opinion
    allow = set(row.get("allow", []))
    after = set(row.get("after_global_period", []))
    issues: list[Issue] = []
    for other in ivs[1:]:
        other_pkg = package_of(other.code)
        if other_pkg == first_pkg:
            continue  # same package: DHA is ambiguous, so no opinion
        if row.get("alone"):
            issues.append(_issue(
                rule,
                f"{first_pkg} must be billed alone, but {other.code} belongs to {other_pkg}",
            ))
        elif other.code in allow or other_pkg in allow:
            continue
        elif other_pkg in after:
            issues.extend(_global_period_issue(rule, draft, first, other))
        else:
            issues.append(_issue(
                rule, f"{other_pkg} cannot be combined with {first_pkg} in the same visit"
            ))
    return issues


def no_per_diem_in_global_period(rule: Rule, draft: ClaimDraft, as_of: datetime) -> list[Issue]:
    if draft.procedure_at is None:
        return []
    issues: list[Issue] = []
    for s in draft.interventions:
        if package_of(s.code) not in SURGICAL_PACKAGES or s.complexity is None:
            continue
        end = _global_period_end(draft.procedure_at, s.complexity)
        for o in draft.interventions:
            if o.is_per_diem and o.started_at is not None and o.started_at < end:
                issues.append(_issue(
                    rule,
                    f"Per-diem intervention {o.code} starts inside the surgical global period "
                    f"of {s.code} (ends about {end.date()}); this double-bills those nights",
                ))
    return issues


def surgical_dates_captured(rule: Rule, draft: ClaimDraft, as_of: datetime) -> list[Issue]:
    if not any(package_of(i.code) in SURGICAL_PACKAGES for i in draft.interventions):
        return []
    missing = [name for name, val in (
        ("admission date", draft.admitted_at),
        ("procedure date", draft.procedure_at),
        ("discharge date", draft.discharged_at),
    ) if val is None]
    return [_issue(rule, f"Surgical claim is missing: {', '.join(missing)}")] if missing else []


CHECKS: dict[str, Check] = {
    "required_documents": required_documents,
    "combination_rules": combination_rules,
    "no_per_diem_in_global_period": no_per_diem_in_global_period,
    "surgical_dates_captured": surgical_dates_captured,
}
