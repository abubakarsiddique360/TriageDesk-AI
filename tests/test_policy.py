from __future__ import annotations

import json

import pytest

from triagedesk.policy import Policy, PolicyError

FULL_SLA = {"P1": [10, 60], "P2": [30, 240], "P3": [60, 480], "P4": [120, 960]}


def minimal(**overrides) -> dict:
    data = {
        "version": 2,
        "categories": {
            "bug": {"queue": "eng", "base_priority": "P2", "keywords": {"crash": 3}},
            "general": {"queue": "support", "base_priority": "P3", "keywords": {"help": 1}},
        },
        "sla_minutes": {level: list(pair) for level, pair in FULL_SLA.items()},
        "tier_shift": {"enterprise": -1},
    }
    data.update(overrides)
    return data


def test_from_dict_parses_categories() -> None:
    policy = Policy.from_dict(minimal())
    assert policy.version == 2
    assert policy.categories["bug"].queue == "eng"
    assert policy.categories["bug"].keywords == {"crash": 3.0}
    assert policy.tier_shift["enterprise"] == -1
    assert policy.tier_shift["standard"] == 0  # defaulted


def test_missing_categories_rejected() -> None:
    with pytest.raises(PolicyError, match="categories"):
        Policy.from_dict({"sla_minutes": FULL_SLA})


def test_invalid_base_priority_rejected() -> None:
    data = minimal()
    data["categories"]["bug"]["base_priority"] = "P9"
    with pytest.raises(PolicyError, match="base_priority"):
        Policy.from_dict(data)


def test_missing_sla_level_rejected() -> None:
    data = minimal()
    del data["sla_minutes"]["P4"]
    with pytest.raises(PolicyError, match="P4"):
        Policy.from_dict(data)


def test_invalid_escalator_target_rejected() -> None:
    data = minimal(escalators=[{"pattern": "urgent", "to": "P0"}])
    with pytest.raises(PolicyError, match="P0"):
        Policy.from_dict(data)


def test_fallback_must_exist() -> None:
    with pytest.raises(PolicyError, match="fallback"):
        Policy.from_dict(minimal(fallback_category="nope"))


def test_default_policy_file_is_valid() -> None:
    policy = Policy.from_json()
    assert "outage" in policy.categories
    assert policy.categories["outage"].base_priority == "P1"
    assert set(policy.sla) == {"P1", "P2", "P3", "P4"}


def test_from_json_reports_bad_file(tmp_path) -> None:
    broken = tmp_path / "policy.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(PolicyError, match="valid JSON"):
        Policy.from_json(broken)


def test_from_json_round_trip(tmp_path) -> None:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(minimal()), encoding="utf-8")
    assert Policy.from_json(path).categories["general"].queue == "support"
