from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .models import Severity


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    severity: Severity
    status: str = "draft"  # draft | active
    check: str
    params: dict[str, Any] = Field(default_factory=dict)
    fix: str
    source: str | None = None


class RuleSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    rules: list[Rule]
    version: str


def load_rules(directory: str | Path, include_draft: bool = False) -> RuleSet:
    digest = hashlib.sha256()
    rules: list[Rule] = []
    for path in sorted(Path(directory).glob("*.yaml")):
        raw = path.read_bytes()
        digest.update(raw)
        data = yaml.safe_load(raw)
        rules.extend(Rule(**r) for r in data["rules"])
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate rule IDs")
    if not include_draft:
        rules = [r for r in rules if r.status == "active"]
    return RuleSet(rules=rules, version=digest.hexdigest()[:12])
