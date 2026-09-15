#!/usr/bin/env python3
"""Builds a single JSON payload for the HTML data viewer: every table's
records with linked-record IDs resolved to human-readable labels."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
TABLES = [
    ("departments", "Departments"),
    ("people", "People"),
    ("job_openings", "Job Openings"),
    ("candidates", "Candidates"),
    ("applications", "Applications"),
    ("interviews", "Interviews"),
    ("offers", "Offers"),
    ("findings", "Findings"),
]

raw = {}
for slug, _ in TABLES:
    raw[slug] = json.loads((DATA_DIR / f"{slug}.json").read_text())

# Build recId -> label lookup, table-specific label field
LABEL_FIELD = {
    "departments": "Name",
    "people": "Full Name",
    "job_openings": "Req ID",
    "candidates": "Full Name",
    "applications": "Application ID",
    "interviews": "Interview ID",
    "offers": "Offer ID",
}
lookup = {}
for slug, field in LABEL_FIELD.items():
    for r in raw[slug]:
        label = r["fields"].get(field, r["id"])
        lookup[r["id"]] = str(label)

def resolve(value):
    if isinstance(value, list):
        if not value:
            return ""
        return ", ".join(lookup.get(v, v) for v in value)
    return value

out = {}
for slug, display in TABLES:
    records = raw[slug]
    columns = []
    for r in records:
        for k in r["fields"].keys():
            if k not in columns:
                columns.append(k)
    rows = []
    for r in records:
        row = {"Record ID": r["id"]}
        for col in columns:
            row[col] = resolve(r["fields"].get(col, ""))
        rows.append(row)
    out[slug] = {
        "display": display,
        "columns": ["Record ID"] + columns,
        "rows": rows,
    }

out_path = Path(__file__).parent / "viewer_data.json"
out_path.write_text(json.dumps(out, ensure_ascii=False))
print(f"wrote {out_path} ({out_path.stat().st_size / 1024:.0f} KB)")
for slug, _ in TABLES:
    print(f"  {slug}: {len(out[slug]['rows'])} rows, {len(out[slug]['columns'])} cols")
