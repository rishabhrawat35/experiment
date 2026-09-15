# TalentFlow Q3 — Submission

Work for the TalentFlow product exercise. All files are inside the [`talentflow/`](talentflow/) folder.

## The 4 things asked for

| # | What was asked | File | Where |
|---|---|---|---|
| 1 | Memo, roadmap, and metric spec (one document) | [Analysis Dashboard](https://claude.ai/code/artifact/0afe2e6c-80b1-479e-beb9-45153188ab46) — click "Case Solution" (also saved as [`talentflow-q3-roadmap.md`](talentflow/docs/talentflow-q3-roadmap.md)) | Dashboard, or `talentflow/docs/` |
| 2 | Findings table (claim, metric, value, method, confidence) | [`findings.md`](talentflow/findings.md) | `talentflow/` |
| 3 | Code and queries | [`talentflow/analysis/`](talentflow/analysis/) folder | `talentflow/analysis/` |
| 4 | Claude Code session transcript | [`session-transcript.jsonl`](talentflow/session-transcript.jsonl) | `talentflow/` |

**Note on #4:** this is the raw session log (JSONL — one event per line), copied directly from Claude Code's local session storage. It's the complete, authentic record, but not light reading. If the Claude Code app offers a cleaner export (e.g. a readable markdown transcript) from its own menu, feel free to swap that in instead — this file is a safe fallback either way.

## How to open the dashboard

The dashboard is a single web page. Two ways to see it:

- **Live link:** [TalentFlow Analysis Dashboard](https://claude.ai/code/artifact/0afe2e6c-80b1-479e-beb9-45153188ab46)
- **Run it yourself:** open a terminal in this repo and run:
  ```bash
  cd talentflow && python3 -m http.server
  ```
  Then open [http://localhost:8000/artifacts/talentflow-analysis-dashboard.html](http://localhost:8000/artifacts/talentflow-analysis-dashboard.html) in a browser.

Once it's open, click **"Case Solution"** in the left menu first — that's the full answer (D1 to D5). Every other page is one data table behind a number used in that answer.

## How to read this repo

```
talentflow/
├── README.md                    Full technical guide (longer than this file)
├── findings.md                  Deliverable #2
├── data/                        Raw data pulled from Airtable (the only real input)
├── analysis/                    Deliverable #3 — the code
│   ├── build_all_views.py       Reads data/, writes all the numbers used everywhere
│   ├── challenge_all_views.py   Re-checks those numbers a second, different way
│   └── output/                  The numbers themselves, one file per table
├── artifacts/                   The dashboard web page (source file)
└── docs/                        Deliverable #1
```

Start with [`talentflow/README.md`](talentflow/README.md) for exact commands to rebuild every number from scratch.
