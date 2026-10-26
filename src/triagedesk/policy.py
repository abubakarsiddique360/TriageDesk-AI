"""Policy loading and validation.

The routing policy is data, not code: categories with weighted keywords, regex
patterns, escalators that force a priority, tier shifts and SLA minutes. Teams can
change routing without touching Python.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from triagedesk.models import PRIORITY_LEVELS, TIERS

DEFAULT_POLICY = Path(__file__).with_name("policy.json")


class PolicyError(ValueError):
    """Raised when a policy file is missing data or contains invalid values."""


@dataclass(frozen=True)
class CategorySpec:
    queue: str
    base_priority: str
    keywords: dict[str, float] = field(default_factory=dict)
    patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class Escalator:
    pattern: str
    level: str
    reason: str


@dataclass(frozen=True)
class Policy:
    version: int
    categories: dict[str, CategorySpec]
    escalators: tuple[Escalator, ...]
    tier_shift: dict[str, int]
    sla: dict[str, tuple[int, int]]
    fallback_category: str = "general"

    @classmethod
    def from_dict(cls, data: dict) -> Policy:
        if not isinstance(data, dict):
            raise PolicyError("policy root must be a JSON object")
        raw_categories = data.get("categories")
        if not isinstance(raw_categories, dict) or not raw_categories:
            raise PolicyError("policy needs a non-empty 'categories' object")

        categories: dict[str, CategorySpec] = {}
        for name, spec in raw_categories.items():
            if not isinstance(spec, dict):
                raise PolicyError(f"category '{name}' must be an object")
            priority = str(spec.get("base_priority", "P3"))
            if priority not in PRIORITY_LEVELS:
                raise PolicyError(f"category '{name}' has invalid base_priority '{priority}'")
            keywords = spec.get("keywords", {})
            if not isinstance(keywords, dict):
                raise PolicyError(f"category '{name}' keywords must be an object")
            categories[name] = CategorySpec(
                queue=str(spec.get("queue", "support")),
                base_priority=priority,
                keywords={str(k).lower(): float(v) for k, v in keywords.items()},
                patterns=tuple(str(p) for p in spec.get("patterns", [])),
            )

        raw_sla = data.get("sla_minutes", {})
        sla: dict[str, tuple[int, int]] = {}
        for level in PRIORITY_LEVELS:
            pair = raw_sla.get(level)
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise PolicyError(f"sla_minutes needs a [response, resolve] pair for {level}")
            sla[level] = (int(pair[0]), int(pair[1]))

        escalators = tuple(
            Escalator(
                pattern=str(item["pattern"]),
                level=str(item["to"]),
                reason=str(item.get("reason", "escalated")),
            )
            for item in data.get("escalators", [])
            if isinstance(item, dict) and "pattern" in item and "to" in item
        )
        for escalator in escalators:
            if escalator.level not in PRIORITY_LEVELS:
                raise PolicyError(f"escalator target '{escalator.level}' is not a valid priority")

        tier_shift = {str(k): int(v) for k, v in (data.get("tier_shift") or {}).items()}
        for tier in TIERS:
            tier_shift.setdefault(tier, 0)

        fallback = str(data.get("fallback_category", "general"))
        if fallback not in categories:
            raise PolicyError(f"fallback_category '{fallback}' is not defined")

        return cls(
            version=int(data.get("version", 1)),
            categories=categories,
            escalators=escalators,
            tier_shift=tier_shift,
            sla=sla,
            fallback_category=fallback,
        )

    @classmethod
    def from_json(cls, path: Path | str | None = None) -> Policy:
        source = Path(path) if path else DEFAULT_POLICY
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise PolicyError(f"policy not found: {source}") from exc
        except json.JSONDecodeError as exc:
            raise PolicyError(f"{source.name} is not valid JSON: {exc}") from exc
        return cls.from_dict(data)
