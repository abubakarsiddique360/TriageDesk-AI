"""Ticket and result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

PRIORITY_LEVELS = ("P1", "P2", "P3", "P4")
TIERS = ("enterprise", "business", "standard")


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class Ticket:
    id: str
    subject: str
    body: str = ""
    channel: str = "email"
    tier: str = "standard"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_dict(cls, data: dict) -> Ticket:
        tier = str(data.get("tier", "standard")).lower()
        return cls(
            id=str(data.get("id") or "ticket"),
            subject=str(data.get("subject", "")),
            body=str(data.get("body", "")),
            channel=str(data.get("channel", "email")),
            tier=tier if tier in TIERS else "standard",
            created_at=_parse_time(data.get("created_at")),
        )

    @property
    def text(self) -> str:
        return f"{self.subject}\n{self.body}".strip()


@dataclass(frozen=True)
class Classification:
    category: str
    confidence: float
    matched: tuple[str, ...]
    scores: dict[str, float]

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "confidence": self.confidence,
            "matched": list(self.matched),
            "scores": {key: round(value, 2) for key, value in self.scores.items()},
        }


@dataclass(frozen=True)
class PriorityDecision:
    level: str
    reasons: tuple[str, ...]

    @property
    def rank(self) -> int:
        return PRIORITY_LEVELS.index(self.level)


@dataclass(frozen=True)
class SlaWindow:
    response_minutes: int
    resolve_minutes: int
    response_due: datetime
    resolve_due: datetime

    def as_dict(self) -> dict:
        return {
            "response_minutes": self.response_minutes,
            "resolve_minutes": self.resolve_minutes,
            "response_due": self.response_due.isoformat(),
            "resolve_due": self.resolve_due.isoformat(),
        }


@dataclass(frozen=True)
class TriageResult:
    ticket_id: str
    category: str
    confidence: float
    queue: str
    priority: str
    reasons: tuple[str, ...]
    sla: SlaWindow
    matched: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "category": self.category,
            "confidence": self.confidence,
            "queue": self.queue,
            "priority": self.priority,
            "reasons": list(self.reasons),
            "matched": list(self.matched),
            "sla": self.sla.as_dict(),
        }
