"""Duplicate detection for incoming tickets.

Cosine similarity over term frequencies is enough for the volumes a support team
sees in a day, and it needs no model download.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from triagedesk.models import Ticket

_WORD_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "can",
        "could",
        "do",
        "does",
        "for",
        "from",
        "get",
        "has",
        "have",
        "i",
        "if",
        "in",
        "is",
        "it",
        "my",
        "not",
        "of",
        "on",
        "or",
        "our",
        "please",
        "so",
        "that",
        "the",
        "their",
        "there",
        "they",
        "this",
        "to",
        "us",
        "was",
        "we",
        "were",
        "what",
        "when",
        "which",
        "who",
        "will",
        "with",
        "you",
        "your",
    ]
)


def tokens(text: str) -> list[str]:
    return [word for word in _WORD_RE.findall(text.lower()) if word not in STOPWORDS]


def similarity(left: str, right: str) -> float:
    a = Counter(tokens(left))
    b = Counter(tokens(right))
    if not a or not b:
        return 0.0
    dot = sum(count * b.get(term, 0) for term, count in a.items())
    norm = math.sqrt(sum(c * c for c in a.values())) * math.sqrt(sum(c * c for c in b.values()))
    return round(dot / norm, 3) if norm else 0.0


@dataclass
class Cluster:
    representative: Ticket
    members: list[Ticket]

    @property
    def size(self) -> int:
        return len(self.members)


def cluster_tickets(tickets: list[Ticket], threshold: float = 0.55) -> list[Cluster]:
    clusters: list[Cluster] = []
    for ticket in tickets:
        for cluster in clusters:
            if similarity(ticket.text, cluster.representative.text) >= threshold:
                cluster.members.append(ticket)
                break
        else:
            clusters.append(Cluster(representative=ticket, members=[ticket]))
    return sorted(clusters, key=lambda cluster: cluster.size, reverse=True)
