#!/usr/bin/env python3
"""Independently re-derives every headline number in output/q1_source_summary.csv,
output/q2_offer_acceptance_two_ways.csv and output/materiality_summary.csv using
sqlite3 (a genuinely different execution engine
from the dict/list aggregation in build_all_views.py), then asserts they agree.
This is the challenger pass -- a code-level self-check, not a second model reading
the first one's output. Prints PASS/FAIL per check; exits non-zero on any FAIL.
"""
import csv
import sqlite3

from common import load, OUT_DIR

conn = sqlite3.connect(":memory:")
cur = conn.cursor()

cur.execute("""CREATE TABLE candidates (id TEXT, phone TEXT, name TEXT, source TEXT, created TEXT)""")
cur.execute("""CREATE TABLE applications (id TEXT, app_id TEXT, candidate TEXT, stage TEXT, status TEXT)""")
cur.execute("""CREATE TABLE offers (id TEXT, offer_id TEXT, status TEXT, application TEXT)""")
cur.execute("""CREATE TABLE interviews (id TEXT, interview_id TEXT, completed_on TEXT, scheduled_on TEXT,
                                        interviewer TEXT, application TEXT, outcome TEXT, score REAL)""")
cur.execute("""CREATE TABLE openings (id TEXT, req_id TEXT, status TEXT, department TEXT)""")
cur.execute("""CREATE TABLE people (id TEXT, department TEXT)""")

for r in load("candidates"):
    f = r["fields"]
    cur.execute("INSERT INTO candidates VALUES (?,?,?,?,?)",
                (r["id"], f.get("Phone"), f.get("Full Name"), f.get("Source"), f.get("Created On")))

cur.execute("""ALTER TABLE applications ADD COLUMN screened_on TEXT""")
for r in load("applications"):
    f = r["fields"]
    cid = (f.get("Candidate") or [None])[0]
    cur.execute("INSERT INTO applications VALUES (?,?,?,?,?,?)",
                (r["id"], f.get("Application ID"), cid, f.get("Stage"), f.get("Status"), f.get("Screened On")))

for r in load("offers"):
    f = r["fields"]
    aid = (f.get("Application") or [None])[0]
    cur.execute("INSERT INTO offers VALUES (?,?,?,?)",
                (r["id"], f.get("Offer ID"), f.get("Status"), aid))

for r in load("interviews"):
    f = r["fields"]
    interviewer = (f.get("Interviewer") or [None])[0]
    app_id = (f.get("Application") or [None])[0]
    cur.execute("INSERT INTO interviews VALUES (?,?,?,?,?,?,?,?)",
                (r["id"], f.get("Interview ID"), f.get("Completed On"), f.get("Scheduled On"),
                 interviewer, app_id, f.get("Outcome"), f.get("Score")))

for r in load("job_openings"):
    f = r["fields"]
    dept = (f.get("Department") or [None])[0]
    cur.execute("INSERT INTO openings VALUES (?,?,?,?)", (r["id"], f.get("Req ID"), f.get("Status"), dept))

for r in load("people"):
    f = r["fields"]
    dept = (f.get("Department") or [None])[0]
    cur.execute("INSERT INTO people VALUES (?,?)", (r["id"], dept))

# opening_hired: an opening is "hired" if any application linked to it reached Stage=Hired
cur.execute("""CREATE TABLE app_openings (app_id TEXT, opening_id TEXT)""")
for r in load("applications"):
    f = r["fields"]
    for oid in f.get("Opening", []):
        cur.execute("INSERT INTO app_openings VALUES (?,?)", (r["id"], oid))

# interview_apps: which applications have a formal Interview record logged
cur.execute("""CREATE TABLE interview_apps (interview_id TEXT, app_id TEXT)""")
for r in load("interviews"):
    f = r["fields"]
    for aid in f.get("Application", []):
        cur.execute("INSERT INTO interview_apps VALUES (?,?)", (r["id"], aid))

conn.commit()

checks = []


def check(name, sql_value, expected, tolerance=0.05):
    ok = expected is not None and abs(sql_value - expected) <= tolerance
    checks.append((name, sql_value, expected, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: sql={sql_value}  build_all_views={expected}")


# --- Re-derive: raw Job Board / Referral hire share, via pure SQL joins ---
print("=== Re-deriving Claim 1 (raw, hired-touch) via SQL ===")
cur.execute("""
    SELECT c.source, COUNT(*) FROM applications a
    JOIN candidates c ON a.candidate = c.id
    WHERE a.stage = 'Hired'
    GROUP BY c.source
""")
sql_hires_by_source = dict(cur.fetchall())
total_hired_sql = sum(sql_hires_by_source.values())
jb_share_sql = round(sql_hires_by_source.get("Job Board", 0) / total_hired_sql * 100, 1)
ref_share_sql = round(sql_hires_by_source.get("Referral", 0) / total_hired_sql * 100, 1)

# --- Re-derive: offer acceptance rate, both definitions ---
print("=== Re-deriving Claim 2 (both definitions) via SQL ===")
cur.execute("SELECT status, COUNT(*) FROM offers GROUP BY status")
off_status_sql = dict(cur.fetchall())
accepted = off_status_sql.get("Accepted", 0)
declined = off_status_sql.get("Declined", 0)
pending = off_status_sql.get("Pending", 0)
rate_pending_fail_sql = round(accepted / (accepted + declined + pending) * 100, 1)
rate_pending_excl_sql = round(accepted / (accepted + declined) * 100, 1)

# --- Re-derive: reused Application IDs ---
print("=== Re-deriving reused Application ID count via SQL ===")
cur.execute("""
    SELECT COUNT(*) FROM applications WHERE app_id IN (
        SELECT app_id FROM applications GROUP BY app_id HAVING COUNT(*) > 1
    )
""")
dup_appid_sql = cur.fetchone()[0]

# --- Re-derive: declined offers whose application still says Stage=Offer ---
print("=== Re-deriving declined-offer/stage-lag count via SQL ===")
cur.execute("""
    SELECT COUNT(*) FROM offers o
    JOIN applications a ON o.application = a.id
    WHERE o.status = 'Declined' AND a.stage = 'Offer'
""")
stage_lag_sql = cur.fetchone()[0]

# --- Re-derive: duplicate candidate phone pairs (record-level, not canonical-person count) ---
print("=== Re-deriving duplicate-candidate-record count via SQL ===")
cur.execute("""
    SELECT COUNT(*) FROM candidates WHERE phone IN (
        SELECT phone FROM candidates WHERE phone IS NOT NULL AND phone != ''
        GROUP BY phone HAVING COUNT(*) > 1
    )
""")
dup_cand_sql = cur.fetchone()[0]

# --- Re-derive: 'Filled' openings with no matching Hired application ---
print("=== Re-deriving Filled-without-Hired-application count via SQL ===")
cur.execute("""
    SELECT COUNT(*) FROM openings o
    WHERE o.status = 'Filled' AND o.id NOT IN (
        SELECT ao.opening_id FROM app_openings ao
        JOIN applications a ON ao.app_id = a.id
        WHERE a.stage = 'Hired'
    )
""")
filled_no_hire_sql = cur.fetchone()[0]

# --- Re-derive: Job Board rejections with no formal interview logged, but a
# real screening call happened (Screened On filled) ---
print("=== Re-deriving Job Board screening-call-without-interview count via SQL ===")
cur.execute("""
    SELECT COUNT(*) FROM applications a
    JOIN candidates c ON a.candidate = c.id
    WHERE a.stage = 'Rejected' AND c.source = 'Job Board'
    AND a.id NOT IN (SELECT app_id FROM interview_apps)
""")
no_interview_reject_sql = cur.fetchone()[0]
cur.execute("""
    SELECT COUNT(*) FROM applications a
    JOIN candidates c ON a.candidate = c.id
    WHERE a.stage = 'Rejected' AND c.source = 'Job Board'
    AND a.id NOT IN (SELECT app_id FROM interview_apps)
    AND a.screened_on IS NOT NULL AND a.screened_on != ''
""")
had_screen_sql = cur.fetchone()[0]
screen_pct_sql = round(had_screen_sql / no_interview_reject_sql * 100, 1)

# --- Re-derive: same-dept vs cross-dept interview non-completion rate ---
# Non-completion must be computed over ALL interviews in the group, not just
# the ones that happen to have a Score (a No Show/Cancelled interview usually
# has no score at all, so scoring the denominator on scored-only interviews
# silently shrinks it and inflates the rate).
print("=== Re-deriving same-dept/cross-dept non-completion rate via SQL ===")
cur.execute("""
    SELECT
        CASE WHEN o.department = p.department THEN 'Same-dept' ELSE 'Cross-dept' END AS label,
        COUNT(*) AS total,
        SUM(CASE WHEN i.outcome != 'Completed' THEN 1 ELSE 0 END) AS noncomplete
    FROM interviews i
    JOIN applications a ON i.application = a.id
    JOIN app_openings ao ON a.id = ao.app_id
    JOIN openings o ON ao.opening_id = o.id
    JOIN people p ON i.interviewer = p.id
    WHERE i.interviewer IS NOT NULL AND i.application IS NOT NULL
    GROUP BY label
""")
affinity_sql = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
same_total_sql, same_noncomplete_sql = affinity_sql.get("Same-dept", (0, 0))
cross_total_sql, cross_noncomplete_sql = affinity_sql.get("Cross-dept", (0, 0))
same_pct_sql = round(same_noncomplete_sql / same_total_sql * 100, 1)
cross_pct_sql = round(cross_noncomplete_sql / cross_total_sql * 100, 1)

# --- Load build_all_views.py's own outputs to compare against ---
def read_csv(name):
    with (OUT_DIR / f"{name}.csv").open() as f:
        return list(csv.DictReader(f))

hire_share = read_csv("q1_source_summary")
offer_two_ways = read_csv("q2_offer_acceptance_two_ways")
materiality = read_csv("materiality_summary")


def find(rows, **kwargs):
    for r in rows:
        if all(r.get(k) == v for k, v in kwargs.items()):
            return r
    return None


bav_jb_share = find(hire_share, Source="Job Board")
bav_ref_share = find(hire_share, Source="Referral")
bav_pending_fail = find(offer_two_ways, Method="Pending = No")
bav_pending_excl = find(offer_two_ways, Method="Pending Excluded")
bav_dup_appid = find(materiality, Issue="Application records with a reused Application ID")
bav_stage_lag = find(materiality, Issue="Declined offers whose Application.Stage still says Offer (not Rejected)")
bav_dup_cand = find(materiality, Issue="Duplicate candidate records (phone+name match)")
bav_filled_no_hire = find(materiality, Issue="Job openings marked 'Filled' with no matching Hired application")
jobboard_screen = read_csv("jobboard_screening_check")[0]
affinity_rows = read_csv("affinity_quality_check")
bav_same = find(affinity_rows, Assignment="Same-dept")
bav_cross = find(affinity_rows, Assignment="Cross-dept")
REC_FIELD = "Records Affected"
SHARE_FIELD = "Hire Share Raw (%)"

print()
check("Claim1 Job Board hire share %", jb_share_sql, float(bav_jb_share[SHARE_FIELD]) if bav_jb_share else None)
check("Claim1 Referral hire share %", ref_share_sql, float(bav_ref_share[SHARE_FIELD]) if bav_ref_share else None)
check("Claim2 acceptance rate (Pending=fail) %", rate_pending_fail_sql, float(bav_pending_fail["Rate (%)"]))
check("Claim2 acceptance rate (Pending excluded) %", rate_pending_excl_sql, float(bav_pending_excl["Rate (%)"]))
check("Reused Application ID record count", dup_appid_sql, int(bav_dup_appid[REC_FIELD]), tolerance=0)
check("Declined-offer Stage-lag count", stage_lag_sql, int(bav_stage_lag[REC_FIELD]), tolerance=0)
check("Duplicate candidate record count", dup_cand_sql, int(bav_dup_cand[REC_FIELD]), tolerance=0)
check("'Filled' openings with no matching Hired application", filled_no_hire_sql, int(bav_filled_no_hire[REC_FIELD]), tolerance=0)
check("Job Board no-interview rejection count", no_interview_reject_sql, int(jobboard_screen["No Formal Interview Rejections"]), tolerance=0)
check("Job Board screening-call-logged %", screen_pct_sql, float(jobboard_screen["Share (%)"]))
check("Same-dept interview count", same_total_sql, int(bav_same["Interviews"]), tolerance=0)
check("Same-dept non-completion %", same_pct_sql, float(bav_same["Non-Completion (%)"]))
check("Cross-dept interview count", cross_total_sql, int(bav_cross["Interviews"]), tolerance=0)
check("Cross-dept non-completion %", cross_pct_sql, float(bav_cross["Non-Completion (%)"]))

n_fail = sum(1 for c in checks if not c[3])
print(f"\n{len(checks)} checks run, {n_fail} FAILED.")
if n_fail:
    raise SystemExit(1)
print("All headline numbers independently reproduced via SQL. Safe to cite.")
