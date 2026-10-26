from __future__ import annotations

from triagedesk.dedupe import cluster_tickets, similarity, tokens
from triagedesk.models import Ticket


def ticket(tid: str, subject: str, body: str = "") -> Ticket:
    return Ticket.from_dict({"id": tid, "subject": subject, "body": body})


def test_tokens_drop_stopwords() -> None:
    assert "the" not in tokens("the checkout is down")
    assert "checkout" in tokens("the checkout is down")


def test_similarity_is_high_for_near_duplicates() -> None:
    a = "checkout page shows a 500 error in production"
    b = "checkout page is showing a 500 error in production"
    assert similarity(a, b) > 0.7


def test_similarity_is_low_for_unrelated_tickets() -> None:
    assert similarity("invoice address is wrong", "checkout returns 500 error") < 0.2


def test_similarity_handles_empty_text() -> None:
    assert similarity("", "anything") == 0.0


def test_clusters_group_duplicates() -> None:
    tickets = [
        ticket("1", "Checkout returns 500 error for every request"),
        ticket("2", "Checkout page returns 500 error for every request"),
        ticket("3", "Invoice shows wrong billing address"),
    ]
    clusters = cluster_tickets(tickets, threshold=0.6)
    assert len(clusters) == 2
    sizes = sorted(cluster.size for cluster in clusters)
    assert sizes == [1, 2]
    assert clusters[0].size == 2  # largest first
    assert {member.id for member in clusters[0].members} == {"1", "2"}


def test_every_ticket_is_kept() -> None:
    tickets = [ticket(str(index), f"unique topic number {index}") for index in range(5)]
    clusters = cluster_tickets(tickets, threshold=0.9)
    assert sum(cluster.size for cluster in clusters) == 5
