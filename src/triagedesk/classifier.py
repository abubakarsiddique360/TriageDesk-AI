"""Weighted keyword classification.

Deliberately transparent: every point in the score can be traced to a keyword in
the policy file, so a support lead can argue with the numbers.
"""

from __future__ import annotations

import re

from triagedesk.models import Classification
from triagedesk.policy import Policy

SUBJECT_WEIGHT = 2.0
PATTERN_WEIGHT = 3.0


def classify(text: str, policy: Policy, subject: str = "") -> Classification:
    haystack = f"{subject}\n{text}".lower()
    subject_lower = subject.lower()
    scores: dict[str, float] = {}
    matched: dict[str, list[str]] = {}

    for name, spec in policy.categories.items():
        score = 0.0
        hits: list[str] = []
        for keyword, weight in spec.keywords.items():
            if keyword in haystack:
                occurrences = haystack.count(keyword)
                score += weight * occurrences
                if keyword in subject_lower:
                    score += weight * SUBJECT_WEIGHT
                hits.append(keyword)
        for pattern in spec.patterns:
            if re.search(pattern, haystack):
                score += PATTERN_WEIGHT
                hits.append(f"/{pattern}/")
        if score:
            scores[name] = score
            matched[name] = hits

    if not scores:
        return Classification(
            category=policy.fallback_category, confidence=0.0, matched=(), scores={}
        )

    best = max(scores, key=lambda name: scores[name])
    total = sum(scores.values())
    confidence = round(scores[best] / total, 2) if total else 0.0
    return Classification(
        category=best,
        confidence=confidence,
        matched=tuple(dict.fromkeys(matched.get(best, []))),
        scores=scores,
    )
