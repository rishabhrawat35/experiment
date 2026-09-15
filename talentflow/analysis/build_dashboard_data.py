#!/usr/bin/env python3
"""Bundles every output CSV into one JSON file for the HTML summary dashboard."""
import csv
import json
from common import OUT_DIR

bundle = {}
for path in sorted(OUT_DIR.glob("*.csv")):
    with path.open() as f:
        rows = list(csv.DictReader(f))
    bundle[path.stem] = rows

out_path = OUT_DIR.parent / "dashboard_data.json"
out_path.write_text(json.dumps(bundle, ensure_ascii=False))
print(f"wrote {out_path} ({out_path.stat().st_size/1024:.0f} KB, {len(bundle)} views)")
