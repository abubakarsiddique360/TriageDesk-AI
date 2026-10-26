from __future__ import annotations

import json

from triagedesk.cli import main
from triagedesk.sample import sample_tickets

TICKETS = {
    "tickets": [
        {
            "id": "TCK-1",
            "subject": "Checkout is down",
            "body": "The service is unavailable, every request fails in production.",
            "tier": "enterprise",
            "created_at": "2026-03-02T10:00:00Z",
        },
        {
            "id": "TCK-2",
            "subject": "Invoice wrong",
            "body": "Our invoice shows a billing address we no longer use.",
            "created_at": "2026-03-02T10:00:00Z",
        },
    ]
}


def write_tickets(tmp_path) -> str:
    path = tmp_path / "tickets.json"
    path.write_text(json.dumps(TICKETS), encoding="utf-8")
    return str(path)


def test_triage_table(tmp_path, capsys) -> None:
    assert main(["triage", write_tickets(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "TCK-1" in out
    assert "P1" in out
    assert "2 ticket(s) triaged" in out


def test_triage_json(tmp_path, capsys) -> None:
    assert main(["triage", write_tickets(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["category"] == "outage"
    assert payload[0]["queue"] == "sre"
    assert payload[0]["sla"]["response_minutes"] == 15


def test_explain_outputs_reasons(capsys) -> None:
    assert main(["explain", "our invoice shows the wrong address, please fix urgently"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["classification"]["category"] == "billing"
    assert payload["priority"] == "P2"
    assert any("urgent" in reason for reason in payload["reasons"])


def test_explain_keeps_p1_for_outage(capsys) -> None:
    assert main(["explain", "production outage, all requests failing urgently"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["priority"] == "P1"
    assert payload["queue"] == "sre"


def test_clusters_output(tmp_path, capsys) -> None:
    assert main(["clusters", write_tickets(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "cluster 1" in out
    assert "2 cluster(s)" in out


def test_demo_prints_samples(capsys) -> None:
    assert main(["demo"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["tickets"]) == len(sample_tickets())


def test_check_policy(capsys) -> None:
    assert main(["check-policy"]) == 0
    out = capsys.readouterr().out
    assert "policy v1" in out
    assert "outage" in out


def test_missing_file_is_an_error(tmp_path, capsys) -> None:
    assert main(["triage", str(tmp_path / "missing.json")]) == 2
    assert "error" in capsys.readouterr().err


def test_bad_policy_is_an_error(tmp_path, capsys) -> None:
    bad = tmp_path / "policy.json"
    bad.write_text("[]", encoding="utf-8")
    assert main(["--policy", str(bad), "check-policy"]) == 2
    assert "error" in capsys.readouterr().err
