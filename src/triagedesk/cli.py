"""Command-line interface for TriageDesk."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from triagedesk import __version__
from triagedesk.classifier import classify
from triagedesk.dedupe import cluster_tickets, similarity
from triagedesk.models import Ticket
from triagedesk.policy import Policy, PolicyError
from triagedesk.sample import sample_tickets
from triagedesk.triage import triage


def _load_tickets(path: Path) -> list[Ticket]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("tickets", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("tickets file must contain a list of tickets")
    return [Ticket.from_dict(item) for item in items]


def _print_table(rows: list[dict]) -> None:
    headers = ("id", "priority", "queue", "category", "conf", "response_due")
    widths = {key: len(key) for key in headers}
    for row in rows:
        for key in headers:
            widths[key] = max(widths[key], len(str(row[key])))
    print("  ".join(key.upper().ljust(widths[key]) for key in headers))
    for row in rows:
        print("  ".join(str(row[key]).ljust(widths[key]) for key in headers))


def _triage(args: argparse.Namespace) -> int:
    policy = Policy.from_json(args.policy)
    tickets = _load_tickets(Path(args.file))
    results = [triage(ticket, policy) for ticket in tickets]
    if args.json:
        print(json.dumps([result.as_dict() for result in results], indent=2))
        return 0
    _print_table(
        [
            {
                "id": result.ticket_id,
                "priority": result.priority,
                "queue": result.queue,
                "category": result.category,
                "conf": f"{result.confidence:.2f}",
                "response_due": result.sla.response_due.strftime("%Y-%m-%d %H:%MZ"),
            }
            for result in results
        ]
    )
    print(f"\n{len(results)} ticket(s) triaged")
    return 0


def _explain(args: argparse.Namespace) -> int:
    policy = Policy.from_json(args.policy)
    classification = classify(args.text, policy, subject=args.subject)
    ticket = Ticket.from_dict(
        {"id": "adhoc", "subject": args.subject, "body": args.text, "tier": args.tier}
    )
    result = triage(ticket, policy)
    payload = {
        "classification": classification.as_dict(),
        "priority": result.priority,
        "queue": result.queue,
        "reasons": list(result.reasons),
        "matched": list(result.matched),
    }
    print(json.dumps(payload, indent=2))
    return 0


def _clusters(args: argparse.Namespace) -> int:
    tickets = _load_tickets(Path(args.file))
    clusters = cluster_tickets(tickets, threshold=args.threshold)
    for index, cluster in enumerate(clusters, start=1):
        print(f"cluster {index} · {cluster.size} ticket(s) · lead: {cluster.representative.id}")
        for member in cluster.members:
            score = similarity(member.text, cluster.representative.text)
            print(f"  - {member.id:<10} {score:.2f}  {member.subject}")
    print(f"\n{len(clusters)} cluster(s) from {len(tickets)} ticket(s)")
    return 0


def _demo(args: argparse.Namespace) -> int:
    print(json.dumps({"tickets": sample_tickets()}, indent=2))
    return 0


def _check_policy(args: argparse.Namespace) -> int:
    policy = Policy.from_json(args.policy)
    print(
        f"policy v{policy.version}: {len(policy.categories)} categories, "
        f"{len(policy.escalators)} escalators, SLA levels {', '.join(policy.sla)}"
    )
    for name, spec in policy.categories.items():
        print(
            f"  {name:<16} queue={spec.queue:<11} base={spec.base_priority} keywords={len(spec.keywords)}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="triagedesk",
        description="Deterministic support-ticket triage: category, priority, queue and SLA.",
    )
    parser.add_argument("--version", action="version", version=f"triagedesk {__version__}")
    parser.add_argument("--policy", help="path to a policy JSON file")
    sub = parser.add_subparsers(dest="command", required=True)

    triage_cmd = sub.add_parser("triage", help="triage a JSON file of tickets")
    triage_cmd.add_argument("file")
    triage_cmd.add_argument("--json", action="store_true")
    triage_cmd.set_defaults(func=_triage)

    explain = sub.add_parser("explain", help="show the scoring for one message")
    explain.add_argument("text")
    explain.add_argument("--subject", default="")
    explain.add_argument("--tier", default="standard")
    explain.set_defaults(func=_explain)

    clusters = sub.add_parser("clusters", help="group near-duplicate tickets")
    clusters.add_argument("file")
    clusters.add_argument("--threshold", type=float, default=0.55)
    clusters.set_defaults(func=_clusters)

    demo = sub.add_parser("demo", help="print the sample tickets as JSON")
    demo.set_defaults(func=_demo)

    check = sub.add_parser("check-policy", help="validate a policy file and list categories")
    check.set_defaults(func=_check_policy)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (PolicyError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
