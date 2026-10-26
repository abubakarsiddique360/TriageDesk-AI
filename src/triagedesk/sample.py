"""Sample tickets used by the demo command and the documentation."""

from __future__ import annotations

SAMPLE_TICKETS: list[dict] = [
    {
        "id": "TCK-1001",
        "subject": "Checkout is down for everyone",
        "body": "Checkout returns a 500 error for every request. This is a production outage, urgent.",
        "tier": "enterprise",
        "channel": "chat",
    },
    {
        "id": "TCK-1002",
        "subject": "Checkout page 500 error",
        "body": "The checkout page is showing a 500 error in production and all requests fail.",
        "tier": "business",
        "channel": "email",
    },
    {
        "id": "TCK-1003",
        "subject": "Invoice shows the wrong billing address",
        "body": "Our latest invoice lists an old address. Can you correct it?",
        "tier": "standard",
        "channel": "email",
    },
    {
        "id": "TCK-1004",
        "subject": "Suspicious login from another country",
        "body": "I got a suspicious login alert and my account may be compromised. Please help urgently.",
        "tier": "business",
        "channel": "email",
    },
    {
        "id": "TCK-1005",
        "subject": "How do I rotate an API key?",
        "body": "Could you point me to the documentation for rotating an API key?",
        "tier": "standard",
        "channel": "docs",
    },
    {
        "id": "TCK-1006",
        "subject": "Feature request: export to CSV",
        "body": "It would be nice to have CSV export on the reports page. Any plans to add it?",
        "tier": "enterprise",
        "channel": "email",
    },
]


def sample_tickets() -> list[dict]:
    return [dict(ticket) for ticket in SAMPLE_TICKETS]
