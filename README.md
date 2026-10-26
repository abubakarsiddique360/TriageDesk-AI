# TriageDesk AI

**Ticket in → category, priority, queue and SLA out. Deterministic, auditable, dependency-free.**

Support triage is usually either a spreadsheet rule sheet nobody follows or a
black-box model nobody can defend. TriageDesk keeps the rules in a JSON policy
file, scores every keyword hit, shows the reasoning behind each priority, and
computes SLA deadlines from the moment the ticket arrived.

[![CI](https://github.com/abubakarsiddique360/TriageDesk-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/abubakarsiddique360/TriageDesk-AI/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.12-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](pyproject.toml)

## Quick start

```bash
git clone https://github.com/abubakarsiddique360/TriageDesk-AI.git
cd TriageDesk-AI
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

triagedesk triage examples/tickets.json
triagedesk clusters examples/tickets.json
triagedesk explain "production is down, all requests failing, urgent"
```

```
ID         PRIORITY  QUEUE   CATEGORY  CONF  RESPONSE_DUE
TCK-1001   P1        sre     outage    0.79  2026-03-02 09:15Z
TCK-1002   P1        sre     outage    0.88  2026-03-02 09:35Z
TCK-1003   P3        billing billing   0.72  2026-03-02 19:00Z
```

## How a ticket is triaged

1. **Classify** — every keyword in a category adds its weight; a match in the
   subject doubles. Regex patterns add a flat bonus. Confidence is the winning
   category's share of the total score.
2. **Prioritise** — start from the category baseline (P1–P4), let an enterprise
   tier accelerate it, then apply escalators.
3. **Route** — the category maps to a queue (`sre`, `security`, `billing`,
   `engineering`, `support`, `product`).
4. **Schedule** — response and resolution deadlines come from the SLA table.

Two invariants keep triage safe:

- **Escalators only raise priority.** A message saying "urgent" cannot demote a
  P1 outage.
- **A tier never demotes.** Enterprise accelerates; standard leaves the baseline
  untouched.

## Policy as data

```json
{
  "categories": {
    "outage": {
      "queue": "sre",
      "base_priority": "P1",
      "keywords": { "outage": 5, "unavailable": 4 },
      "patterns": ["5[0-9][0-9] (error|response)"]
    }
  },
  "escalators": [
    { "pattern": "data loss|lost (all|my) data", "to": "P1", "reason": "possible data loss" }
  ],
  "tier_shift": { "enterprise": -1, "business": 0, "standard": 0 },
  "sla_minutes": { "P1": [15, 240], "P2": [60, 480], "P3": [480, 1440], "P4": [1440, 4320] }
}
```

Validate edits before deploying:

```bash
triagedesk --policy my-policy.json check-policy
```

## Duplicate clustering

`clusters` compares tickets with cosine similarity over term frequencies and
groups anything above a threshold (default 0.55). On the demo file, the two
checkout tickets collapse into one cluster — the useful signal when an outage
generates fifty reports.

```bash
triagedesk clusters examples/tickets.json --threshold 0.6
```

## CLI

| Command | Purpose |
| --- | --- |
| `triage FILE [--json]` | Triage every ticket in a JSON file |
| `explain TEXT [--subject S] [--tier T]` | Show scores, matched keywords and reasons |
| `clusters FILE [--threshold 0.6]` | Group near-duplicate tickets |
| `check-policy` | Validate a policy and list categories |
| `demo` | Print the built-in sample tickets |

## Project layout

```text
src/triagedesk/
├── models.py      tickets, classification, priority, SLA, results
├── policy.py      JSON policy loading and validation
├── classifier.py  weighted keyword + pattern scoring
├── triage.py      priority invariants and SLA computation
├── dedupe.py      tokenising, cosine similarity, clustering
├── sample.py      demo tickets
└── cli.py         triage · explain · clusters · check-policy · demo
tests/             35 pytest cases
```

## Design notes

- **Explainable by construction.** `explain` returns the exact keywords that
  fired, so disagreements become policy edits, not arguments.
- **Policy validation is strict.** A missing SLA level, an unknown priority or a
  dangling fallback category fails fast instead of silently mis-routing.
- **No NLP dependency.** Weighted keywords plus cosine similarity cover the
  volume a support queue actually sees, and they run in milliseconds.
- **Timezones are explicit.** Timestamps are ISO-8601 and always timezone-aware.

## Roadmap

- [ ] Optional CSV and email (`.eml`) loaders
- [ ] SLA breach simulation (`--at "2026-03-02T15:00Z"`)
- [ ] Per-agent capacity balancing

## License

[MIT](LICENSE) © 2026 **ABU BAKAR SIDDIQUE**
