"""Shared helpers for the TalentFlow analysis scripts. Stdlib only, no deps.
No statistical confidence intervals anywhere in this project -- plain counts and
percentages only, always shown together so the reader can judge sample size themselves.
"""
import json
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_DIR = Path(__file__).parent / "output"
TODAY = date(2026, 8, 27)  # latest createdTime in the pulled dataset


def load(table):
    return json.loads((DATA_DIR / f"{table}.json").read_text())


def by_id(records):
    return {r["id"]: r["fields"] for r in records}


def pd(s):
    """Parse an Airtable date string (YYYY-MM-DD) to a date, or None."""
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


def median(values):
    v = sorted(x for x in values if x is not None)
    if not v:
        return None
    n = len(v)
    mid = n // 2
    if n % 2:
        return v[mid]
    return (v[mid - 1] + v[mid]) / 2


def canonical_persons(candidates):
    """Group candidate records by normalized phone number (the only field that reliably
    identifies the same physical person across duplicate records in this dataset).
    Returns: {canonical_key(=earliest member id): {"members": [ids], "source": first-touch
    source, "created": earliest Created On}}.
    """
    cands = by_id(candidates)
    by_phone = {}
    for cid, f in cands.items():
        p = (f.get("Phone") or "").strip()
        by_phone.setdefault(p, []).append(cid)

    canonical = {}
    member_to_canonical = {}
    seen = set()
    for cid in cands:
        if cid in seen:
            continue
        phone = (cands[cid].get("Phone") or "").strip()
        group = by_phone.get(phone, [cid]) if phone else [cid]
        members_sorted = sorted(group, key=lambda x: cands[x].get("Created On") or "")
        key = members_sorted[0]
        for m in members_sorted:
            seen.add(m)
            member_to_canonical[m] = key
        canonical[key] = {
            "members": members_sorted,
            "source": cands[members_sorted[0]].get("Source"),
            "created": cands[members_sorted[0]].get("Created On"),
        }
    return canonical, member_to_canonical
