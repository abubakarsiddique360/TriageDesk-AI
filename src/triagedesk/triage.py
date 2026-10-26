"""Triage pipeline: classify → set priority → compute SLA."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from triagedesk.classifier import classify
from triagedesk.models import PRIORITY_LEVELS, SlaWindow, Ticket, TriageResult
from triagedesk.policy import Policy


def decide_priority(
    ticket: Ticket,
    category_priority: str,
    policy: Policy,
) -> tuple[str, list[str]]:
    """Return the final priority plus the reasons behind every change.

    Two rules keep this safe: escalators can only raise priority, and a tier can
    accelerate a ticket but never demote it below its category baseline.
    """

    base_index = PRIORITY_LEVELS.index(category_priority)
    index = base_index
    reasons = [f"category baseline {category_priority}"]

    shift = policy.tier_shift.get(ticket.tier, 0)
    if shift < 0:
        index = max(0, min(index, base_index + shift))
        reasons.append(f"{ticket.tier} tier accelerates from {category_priority}")
    elif shift > 0:
        reasons.append(f"{ticket.tier} tier does not lower priority")

    text = ticket.text.lower()
    for escalator in policy.escalators:
        if not re.search(escalator.pattern, text):
            continue
        target = PRIORITY_LEVELS.index(escalator.level)
        if target < index:
            index = target
            reasons.append(f"{escalator.reason} → {escalator.level}")

    final = PRIORITY_LEVELS[index]
    if final == category_priority and len(reasons) == 1:
        reasons.append("no escalation matched")
    return final, reasons


def compute_sla(level: str, policy: Policy, created_at: datetime) -> SlaWindow:
    response, resolve = policy.sla[level]
    return SlaWindow(
        response_minutes=response,
        resolve_minutes=resolve,
        response_due=created_at + timedelta(minutes=response),
        resolve_due=created_at + timedelta(minutes=resolve),
    )


def triage(ticket: Ticket, policy: Policy, now: datetime | None = None) -> TriageResult:
    classification = classify(ticket.body, policy, subject=ticket.subject)
    spec = policy.categories[classification.category]
    level, reasons = decide_priority(ticket, spec.base_priority, policy)
    created = ticket.created_at or now or datetime.now(timezone.utc)
    return TriageResult(
        ticket_id=ticket.id,
        category=classification.category,
        confidence=classification.confidence,
        queue=spec.queue,
        priority=level,
        reasons=tuple(reasons),
        sla=compute_sla(level, policy, created),
        matched=classification.matched,
    )


def triage_many(tickets: list[Ticket], policy: Policy) -> list[TriageResult]:
    return [triage(ticket, policy) for ticket in tickets]
