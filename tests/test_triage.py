from __future__ import annotations

from datetime import datetime, timezone

import pytest

from triagedesk.classifier import classify
from triagedesk.models import Ticket
from triagedesk.policy import Policy
from triagedesk.triage import compute_sla, decide_priority, triage


@pytest.fixture(scope="module")
def policy() -> Policy:
    return Policy.from_json()


def test_outage_is_detected(policy: Policy) -> None:
    result = classify(
        "Checkout returns a 500 error for every request", policy, subject="Checkout down"
    )
    assert result.category == "outage"
    assert result.confidence > 0.5
    assert result.matched


def test_security_wins_over_generic_bug(policy: Policy) -> None:
    result = classify("My account may be compromised, I saw a suspicious login", policy)
    assert result.category == "security"
    assert result.scores["security"] > result.scores.get("bug", 0)


def test_billing_detected(policy: Policy) -> None:
    assert classify("Please fix the invoice, we were double charged", policy).category == "billing"


def test_how_to_detected(policy: Policy) -> None:
    assert (
        classify("How do I rotate an API key? Where can I find the docs?", policy).category
        == "how_to"
    )


def test_unknown_text_falls_back(policy: Policy) -> None:
    result = classify("xyzzy", policy)
    assert result.category == policy.fallback_category
    assert result.confidence == 0.0


def test_subject_boosts_score(policy: Policy) -> None:
    without = classify("it is broken since the last release", policy)
    with_subject = classify(
        "it is broken since the last release", policy, subject="crash on startup"
    )
    assert with_subject.scores.get("bug", 0) > without.scores.get("bug", 0)


def test_escalator_raises_priority(policy: Policy) -> None:
    ticket = Ticket.from_dict({"id": "1", "subject": "urgent", "body": "please help"})
    level, reasons = decide_priority(ticket, "P3", policy)
    assert level in {"P1", "P2"}
    assert any("urgent" in reason for reason in reasons)


def test_escalator_never_downgrades(policy: Policy) -> None:
    ticket = Ticket.from_dict(
        {"id": "2", "subject": "outage", "body": "urgent: everything is down"}
    )
    level, _ = decide_priority(ticket, "P1", policy)
    assert level == "P1"


def test_enterprise_tier_accelerates(policy: Policy) -> None:
    standard = Ticket.from_dict({"id": "3", "subject": "invoice wrong", "body": "billing question"})
    enterprise = Ticket.from_dict(
        {"id": "4", "subject": "invoice wrong", "body": "billing question", "tier": "enterprise"}
    )
    assert decide_priority(enterprise, "P3", policy)[0] == "P2"
    assert decide_priority(standard, "P3", policy)[0] == "P3"


def test_standard_tier_never_demotes(policy: Policy) -> None:
    ticket = Ticket.from_dict({"id": "5", "subject": "outage", "body": "everything is down"})
    assert decide_priority(ticket, "P1", policy)[0] == "P1"


def test_sla_window_is_computed_from_creation(policy: Policy) -> None:
    created = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    sla = compute_sla("P1", policy, created)
    assert sla.response_minutes == 15
    assert sla.response_due.hour == 9
    assert sla.response_due.minute == 15
    assert sla.resolve_minutes == 240


def test_triage_end_to_end(policy: Policy) -> None:
    ticket = Ticket.from_dict(
        {
            "id": "TCK-1",
            "subject": "Everything is down",
            "body": "The service is unavailable and every request fails. This is a production outage.",
            "tier": "enterprise",
            "created_at": "2026-03-02T10:00:00Z",
        }
    )
    result = triage(ticket, policy)
    assert result.category == "outage"
    assert result.priority == "P1"
    assert result.queue == "sre"
    assert result.sla.response_due.isoformat() == "2026-03-02T10:15:00+00:00"
    payload = result.as_dict()
    assert payload["priority"] == "P1"
    assert payload["sla"]["response_minutes"] == 15
