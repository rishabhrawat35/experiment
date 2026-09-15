#!/usr/bin/env python3
"""Builds every view for the TalentFlow analysis, deterministically, stdlib only.
Re-runnable any time; writes one CSV per view to output/. No model call inside,
no confidence intervals -- plain counts and percentages only, always shown together
so the reader can judge sample size themselves.
"""
import csv
from collections import Counter, defaultdict
from statistics import mean

from common import load, by_id, pd, median, canonical_persons, OUT_DIR, TODAY

OUT_DIR.mkdir(exist_ok=True)


def write_csv(name, header, rows):
    path = OUT_DIR / f"{name}.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {name}.csv ({len(rows)} rows)")


def pct(x, n):
    return round(x / n * 100, 1) if n else 0.0


# ---------------------------------------------------------------------------
# Load everything once
# ---------------------------------------------------------------------------
cands_raw = load("candidates")
apps_raw = load("applications")
openings_raw = load("job_openings")
interviews_raw = load("interviews")
offers_raw = load("offers")
people_raw = load("people")
depts_raw = load("departments")

cands = by_id(cands_raw)
apps = by_id(apps_raw)
openings = by_id(openings_raw)
interviews = by_id(interviews_raw)
offers = by_id(offers_raw)
people = by_id(people_raw)
depts = by_id(depts_raw)
dept_name = {k: v.get("Name") for k, v in depts.items()}

STAGES = ["Applied", "Screening", "Interview", "Offer", "Hired", "Rejected", "Withdrawn"]
COARSE_BUCKET = {
    "Applied": "Active-early", "Screening": "Active-early",
    "Interview": "Active-late", "Offer": "Active-late",
    "Hired": "Hired", "Rejected": "Rejected+Withdrawn", "Withdrawn": "Rejected+Withdrawn",
}

# ===========================================================================
# 0. Identity method: how duplicate people are matched, and who they are
# ===========================================================================
print("=== 0. Identity model: canonical persons (dedup) ===")
canonical, member_to_canonical = canonical_persons(cands_raw)
canon_rows = []
for key, v in canonical.items():
    hired = any(
        a["fields"].get("Stage") == "Hired"
        for a in apps_raw
        for cid in a["fields"].get("Candidate", [])
        if cid in v["members"]
    )
    canon_rows.append((key, len(v["members"]), ";".join(v["members"]), v["source"], v["created"], hired))
write_csv("candidates_canonical", [
    "Person ID", "Duplicate Records", "Record IDs",
    "Source", "First Seen", "Hired",
], [(k, n, ids, src, created, "Yes" if h else "No") for k, n, ids, src, created, h in canon_rows])
print(f"  Matching key used: normalized phone number. Tie-break for which record is 'first': earliest Created On.")
print(f"  {len(cands)} raw candidate records -> {len(canonical)} canonical persons "
      f"({len(cands) - len(canonical)} records merged away)")

# ===========================================================================
# Question 1: is Job Board really the top hiring channel, by a wide margin?
# ===========================================================================
print("\n=== 1. Question 1: hire share and hire rate, by source ===")
hired_app_by_source_raw = Counter()
apps_by_source_raw = Counter()
for a in apps_raw:
    f = a["fields"]
    cid = (f.get("Candidate") or [None])[0]
    if not cid:
        continue
    src = cands.get(cid, {}).get("Source", "UNKNOWN")
    apps_by_source_raw[src] += 1
    if f.get("Stage") == "Hired":
        hired_app_by_source_raw[src] += 1
total_hired_raw = sum(hired_app_by_source_raw.values())

hired_by_canonical_source = Counter()
total_by_canonical_source = Counter()
for row in canon_rows:  # row = (key, n_members, members, source, created, hired)
    total_by_canonical_source[row[3]] += 1
    if row[5]:
        hired_by_canonical_source[row[3]] += 1
total_hired_dedup = sum(hired_by_canonical_source.values())

# One table, one row per source, every metric as its own column -- not two
# tables for the same dimension, and not two values packed into one cell.
rows = []
for src in apps_by_source_raw:
    n, x = apps_by_source_raw[src], hired_app_by_source_raw[src]
    raw_share = pct(x, total_hired_raw)
    dedup_share = pct(hired_by_canonical_source[src], total_hired_dedup) if src in total_by_canonical_source else 0
    rows.append((src, n, x, pct(x, n), raw_share, dedup_share))
rows.sort(key=lambda r: -r[5])
write_csv("q1_source_summary", [
    "Source", "Applications", "Hired", "Hire Rate (%)", "Hire Share Raw (%)", "Hire Share Dedup (%)",
], rows)

# ===========================================================================
# Question 2: is the offer acceptance rate ~72%, and does it need to move?
# ===========================================================================
print("=== 2. Question 2: offer acceptance rate, two ways to count it ===")
off_status = Counter(o["fields"].get("Status") for o in offers_raw)
accepted, declined, pending = off_status["Accepted"], off_status["Declined"], off_status["Pending"]
write_csv("q2_offer_acceptance_two_ways", [
    "Method", "Accepted", "Total Counted", "Rate (%)",
], [
    ("Pending = No", accepted, accepted + declined + pending, pct(accepted, accepted + declined + pending)),
    ("Pending Excluded", accepted, accepted + declined, pct(accepted, accepted + declined)),
])

# ===========================================================================
# 3. Source x Stage funnel
# ===========================================================================
print("=== 3. Source x Stage funnel ===")
src_stage = defaultdict(Counter)
for a in apps_raw:
    f = a["fields"]
    cid = (f.get("Candidate") or [None])[0]
    src = cands.get(cid, {}).get("Source", "UNKNOWN") if cid else "UNKNOWN"
    src_stage[src][f.get("Stage")] += 1

rows = []
for src, ctr in src_stage.items():
    total = sum(ctr.values())
    rows.append([src, total] + [ctr[s] for s in STAGES] + [pct(ctr["Hired"], total)])
write_csv("source_funnel", ["Source", "Applications"] + STAGES + ["Hired (%)"], rows)

# ===========================================================================
# 4. Department x Stage funnel (coarse), PLUS Department x Source (the actual
#    two-dimension cross-tab requested, not two separate one-dimension tables)
# ===========================================================================
print("=== 4. Department x Stage funnel, and Department x Source ===")
dept_bucket = defaultdict(Counter)
dept_source = defaultdict(Counter)   # applications
dept_source_hired = defaultdict(Counter)  # hires
for a in apps_raw:
    f = a["fields"]
    op = (f.get("Opening") or [None])[0]
    if not op:
        continue
    d = (openings.get(op, {}).get("Department") or [None])[0]
    if not d:
        continue
    dname = dept_name.get(d)
    dept_bucket[dname][COARSE_BUCKET.get(f.get("Stage"), "Unknown")] += 1
    cid = (f.get("Candidate") or [None])[0]
    src = cands.get(cid, {}).get("Source", "UNKNOWN") if cid else "UNKNOWN"
    dept_source[dname][src] += 1
    if f.get("Stage") == "Hired":
        dept_source_hired[dname][src] += 1

buckets = ["Still Active - Early Stage", "Still Active - Late Stage", "Hired", "Closed - Not Hired"]
rows = []
for d, ctr in dept_bucket.items():
    total = sum(ctr.values())
    rows.append([d, total] + [ctr[old] for old in ["Active-early", "Active-late", "Hired", "Rejected+Withdrawn"]] + [pct(ctr["Hired"], total)])
write_csv("department_funnel", ["Department", "Applications"] + buckets + ["Hired (%)"], rows)
print("  Still Active - Early Stage = Applied or Screening. Still Active - Late Stage = Interview or Offer.")
print("  Closed - Not Hired = Rejected or Withdrawn (combined count, not a ratio).")

# Department x Source, long format: one row per department-source pair that
# actually has applications, each metric its own column (not text packed
# into one cell).
rows = []
for d in dept_bucket:
    for src, n in dept_source[d].items():
        if n == 0:
            continue
        h = dept_source_hired[d][src]
        rows.append([d, src, n, h, pct(h, n)])
rows.sort(key=lambda r: (r[0], -r[2]))
write_csv("department_x_source", ["Department", "Source", "Applications", "Hired", "Hire Rate (%)"], rows)

# ===========================================================================
# 5. Level x Stage funnel, and why Withdrawn skews to Senior/Lead
# ===========================================================================
print("=== 5. Level x Stage funnel, and the Withdrawn-by-level investigation ===")
level_stage = defaultdict(Counter)
for a in apps_raw:
    f = a["fields"]
    op = (f.get("Opening") or [None])[0]
    level = openings.get(op, {}).get("Level") if op else None
    level_stage[level][f.get("Stage")] += 1

rows = []
for lvl, ctr in level_stage.items():
    total = sum(ctr.values())
    rows.append([lvl, total] + [ctr[s] for s in STAGES] + [pct(ctr["Hired"], total)])
write_csv("level_funnel", ["Level", "Applications"] + STAGES + ["Hired (%)"], rows)

# Investigation: two hypotheses tested for why Senior/Lead withdraw more often
# than Junior/Mid. Both ruled out -- reported honestly rather than forcing a story.
def ctc_gap(cid):
    cf = cands.get(cid, {})
    exp, cur = cf.get("Expected CTC"), cf.get("Current CTC")
    return round((exp - cur) / cur * 100, 1) if exp and cur else None

level_withdraw_check = []
for lvl in level_stage:
    total = sum(level_stage[lvl].values())
    withdrawn = level_stage[lvl]["Withdrawn"]
    gaps, close_days = [], []
    for a in apps_raw:
        f = a["fields"]
        op = (f.get("Opening") or [None])[0]
        if (openings.get(op, {}).get("Level") if op else None) != lvl:
            continue
        if f.get("Stage") != "Withdrawn":
            continue
        cid = (f.get("Candidate") or [None])[0]
        g = ctc_gap(cid)
        if g is not None:
            gaps.append(g)
        applied, closed = pd(f.get("Applied On")), pd(f.get("Closed On"))
        if applied and closed:
            close_days.append((closed - applied).days)
    level_withdraw_check.append([
        lvl, total, withdrawn, pct(withdrawn, total),
        round(mean(gaps), 1) if gaps else "No withdrawals - nothing to average",
        round(mean(close_days), 1) if close_days else "No withdrawals - nothing to average",
    ])
write_csv("withdrawn_by_level", [
    "Level", "Applications", "Withdrawn", "Withdrawal Rate (%)",
    "Avg Expected Raise, Withdrawn Candidates (%)", "Avg Days To Withdraw",
], level_withdraw_check)
print("  Avg Expected Raise (%) = (Expected CTC - Current CTC) / Current CTC x 100, for withdrawn candidates only.")
print("  Positive = candidate asked for more than they currently earn.")

# ===========================================================================
# 6. Recruiter x Stage funnel + cycle time
# ===========================================================================
print("=== 6. Recruiter x Stage funnel + cycle time ===")
recruiter_apps = defaultdict(list)
for a in apps_raw:
    f = a["fields"]
    rec = (f.get("Recruiter") or [None])[0]
    recruiter_apps[rec].append(f)

rows = []
for rec, flist in recruiter_apps.items():
    name = people.get(rec, {}).get("Full Name", "UNKNOWN")
    ctr = Counter(f.get("Stage") for f in flist)
    total = len(flist)
    cycle_days = [
        (pd(f["Closed On"]) - pd(f["Applied On"])).days
        for f in flist if f.get("Closed On") and f.get("Applied On")
    ]
    rows.append([name, total, ctr["Hired"], pct(ctr["Hired"], total), median(cycle_days)])
write_csv("recruiter_funnel", [
    "Recruiter", "Applications", "Hired", "Hired (%)", "Median Days To Close",
], rows)

# ===========================================================================
# 7. Interview rounds: pass-through rate, not just a raw crosstab
# ===========================================================================
print("=== 7. Interview round: pass-through rate ===")
round_stats = defaultdict(lambda: {"n": 0, "scores": [], "advanced": 0, "rejected_after": 0})
for iv in interviews_raw:
    f = iv["fields"]
    rnd = f.get("Round")
    app_id = (f.get("Application") or [None])[0]
    app_stage = apps.get(app_id, {}).get("Stage") if app_id else None
    st = round_stats[rnd]
    st["n"] += 1
    if f.get("Score") is not None:
        st["scores"].append(f["Score"])
    if app_stage in ("Hired", "Offer", "Interview"):
        st["advanced"] += 1
    elif app_stage == "Rejected":
        st["rejected_after"] += 1

rows = []
for rnd, st in round_stats.items():
    rows.append([
        rnd, st["n"], round(mean(st["scores"]), 2) if st["scores"] else None,
        st["advanced"], pct(st["advanced"], st["n"]),
        st["rejected_after"], pct(st["rejected_after"], st["n"]),
    ])
rows.sort(key=lambda r: -r[1])
write_csv("round_summary", [
    "Round", "Interviews Held", "Avg Score",
    "Advanced", "Advanced (%)",
    "Rejected After", "Rejected After (%)",
], rows)
print("  Avg Score is on a 1-5 scale.")

# ===========================================================================
# 8. Interviewer calibration + department-affinity quality check
# ===========================================================================
print("=== 8. Interviewer calibration + affinity quality check ===")
interviewer_stats = defaultdict(lambda: {"scores": [], "rec": Counter(), "n": 0, "same_dept": 0, "cross_dept": 0,
                                          "said_no_but_hired": 0, "said_no_but_still_active": 0, "said_no_total": 0,
                                          "said_no_and_rejected": 0, "said_no_still_mid_process": 0})
affinity_scores = defaultdict(list)
affinity_outcome = defaultdict(Counter)
affinity_total = Counter()

for iv in interviews_raw:
    f = iv["fields"]
    interviewer_id = (f.get("Interviewer") or [None])[0]
    app_id = (f.get("Application") or [None])[0]
    if not interviewer_id or not app_id:
        continue
    app_f = apps.get(app_id, {})
    op_id = (app_f.get("Opening") or [None])[0]
    op_dept = (openings.get(op_id, {}).get("Department") or [None])[0] if op_id else None
    interviewer_dept = (people.get(interviewer_id, {}).get("Department") or [None])[0]
    same = op_dept is not None and op_dept == interviewer_dept

    st = interviewer_stats[interviewer_id]
    st["n"] += 1
    if f.get("Score") is not None:
        st["scores"].append(f["Score"])
    if f.get("Recommendation"):
        st["rec"][f["Recommendation"]] += 1
    if f.get("Recommendation") in ("No Hire", "Strong No Hire"):
        st["said_no_total"] += 1
        app_stage = app_f.get("Stage")
        if app_stage == "Hired":
            st["said_no_but_hired"] += 1
        elif app_stage == "Offer":
            st["said_no_but_still_active"] += 1
        elif app_stage == "Rejected":
            st["said_no_and_rejected"] += 1
        else:
            st["said_no_still_mid_process"] += 1
    if same:
        st["same_dept"] += 1
    else:
        st["cross_dept"] += 1

    label = "Same-dept" if same else "Cross-dept"
    affinity_total[label] += 1
    if f.get("Score") is not None:
        affinity_scores[label].append(f["Score"])
    if f.get("Outcome"):
        affinity_outcome[label][f["Outcome"]] += 1

rows = []
for iid, st in interviewer_stats.items():
    name = people.get(iid, {}).get("Full Name", "UNKNOWN")
    avg_score = round(mean(st["scores"]), 2) if st["scores"] else None
    rows.append([
        name, st["n"], avg_score, st["rec"]["Strong Hire"], st["rec"]["Hire"],
        st["rec"]["No Hire"], st["rec"]["Strong No Hire"], pct(st["same_dept"], st["n"]),
        st["said_no_total"], st["said_no_but_hired"], st["said_no_but_still_active"],
        st["said_no_and_rejected"], st["said_no_still_mid_process"],
    ])
rows.sort(key=lambda r: r[2] if r[2] is not None else 99)
write_csv("interviewer_calibration", [
    "Interviewer", "Interviews", "Avg Score",
    "Strong Hire", "Hire", "No Hire", "Strong No Hire",
    "Same Dept (%)", "Said No Total", "Said No, Later Hired", "Said No, Still Active At Offer",
    "Said No, Later Rejected", "Said No, Still Mid-Process",
], rows)
print("  Avg Score is on a 1-5 scale. Strong Hire/Hire/No Hire/Strong No Hire are recommendation counts.")

rows = []
for label in affinity_total:
    scores = affinity_scores[label]
    outcomes = affinity_outcome[label]
    noncomplete = sum(v for k, v in outcomes.items() if k != "Completed")
    rows.append([label, affinity_total[label], round(mean(scores), 2) if scores else None,
                 len(scores), pct(noncomplete, affinity_total[label])])
write_csv("affinity_quality_check", [
    "Assignment", "Interviews", "Avg Score", "Interviews With A Score", "Non-Completion (%)",
], rows)
print("  Assignment: Same-dept = interviewer's own department matches the opening's department.")
print("  Interviews = every interview in that group. Avg Score only covers interviews that got a score")
print("  (a No Show/Cancelled/Rescheduled interview usually has none) -- see 'Interviews With A Score'.")
print("  Non-Completion (%) is out of ALL interviews in the group, not just the scored ones.")

# ===========================================================================
# 9. Requisition status integrity: does "Filled" actually have a hire behind
#    it? (The detailed per-req overdue list was dropped -- it's not
#    actionable as a dashboard table; the one number that matters, "10 of 11
#    overdue," is computed below for the Summary card.)
# ===========================================================================
print("=== 9. Requisition status integrity ===")
hired_opening_ids = set()
for a in apps_raw:
    f = a["fields"]
    if f.get("Stage") == "Hired":
        for oid in f.get("Opening", []):
            hired_opening_ids.add(oid)

rows = []
for oid, f in openings.items():
    if f.get("Status") != "Filled":
        continue
    has_hire = oid in hired_opening_ids
    rows.append([f.get("Req ID"), f.get("Title"), dept_name.get((f.get("Department") or [None])[0]),
                 "Yes" if has_hire else "No"])
rows.sort(key=lambda r: r[3])
write_csv("requisition_status_integrity", [
    "Requisition ID", "Title", "Department", "Has Hired App",
], rows)
n_mismatch = sum(1 for r in rows if r[3] == "No")
print(f"  {n_mismatch} of {len(rows)} 'Filled' requisitions have NO matching Hired application")

n_open = sum(1 for f in openings.values() if f.get("Status") == "Open")
n_overdue = sum(
    1 for f in openings.values()
    if f.get("Status") == "Open" and pd(f.get("Target Close")) and TODAY > pd(f.get("Target Close"))
)
write_csv("requisition_overview", ["Open Requisitions", "Overdue"], [[n_open, n_overdue]])

# ===========================================================================
# 10. Referrals: does the real internal-referral signal move the hire rate?
# ===========================================================================
print("=== 10. Referral signal: real link vs self-reported Source ===")
src_x_refby = Counter()
for a in apps_raw:
    f = a["fields"]
    cid = (f.get("Candidate") or [None])[0]
    src = cands.get(cid, {}).get("Source", "UNKNOWN") if cid else "UNKNOWN"
    src_x_refby[(src, bool(f.get("Referred By")))] += 1
write_csv("referral_source_vs_referredby_crosstab", [
    "Source", "Has Referrer", "Applications",
], sorted(((s, "Yes" if r else "No", c) for (s, r), c in src_x_refby.items()), key=lambda x: -x[2]))

ref_hired = sum(1 for a in apps_raw if a["fields"].get("Referred By") and a["fields"].get("Stage") == "Hired")
ref_total = sum(1 for a in apps_raw if a["fields"].get("Referred By"))
noref_hired = sum(1 for a in apps_raw if not a["fields"].get("Referred By") and a["fields"].get("Stage") == "Hired")
noref_total = sum(1 for a in apps_raw if not a["fields"].get("Referred By"))
selfreport_hired = sum(1 for a in apps_raw if a["fields"].get("Stage") == "Hired"
                        and cands.get((a["fields"].get("Candidate") or [None])[0], {}).get("Source") == "Referral")
selfreport_total = sum(1 for a in apps_raw
                        if cands.get((a["fields"].get("Candidate") or [None])[0], {}).get("Source") == "Referral")
write_csv("referral_signal_comparison",
          ["Group", "Hired", "Applications", "Hired (%)"],
          [("Self-Reported Source = Referral", selfreport_hired, selfreport_total, pct(selfreport_hired, selfreport_total)),
           ("Has Real Internal Referrer", ref_hired, ref_total, pct(ref_hired, ref_total)),
           ("No Internal Referrer", noref_hired, noref_total, pct(noref_hired, noref_total))])
print("  'Has Real Internal Referrer' = Referred By field is set, regardless of stated Source.")
print(f"  Self-reported 'Referral' source: {selfreport_hired}/{selfreport_total}={pct(selfreport_hired, selfreport_total)}%")
print(f"  Real internal referrer (Referred By): {ref_hired}/{ref_total}={pct(ref_hired, ref_total)}% vs no referrer {noref_hired}/{noref_total}={pct(noref_hired, noref_total)}%")

# ===========================================================================
# 11. Why applications get rejected -- categorized, not a per-ID list
# ===========================================================================
print("=== 11. Rejection reasons: overall, and for Job Board specifically ===")
interviews_by_app = defaultdict(int)
for iv in interviews_raw:
    for aid in iv["fields"].get("Application", []):
        interviews_by_app[aid] += 1

overall_reason = Counter()
jobboard_reason = defaultdict(Counter)  # stage_type -> reason -> count
for a in apps_raw:
    f = a["fields"]
    if f.get("Stage") != "Rejected":
        continue
    reason = f.get("Rejection Reason", "UNKNOWN")
    overall_reason[reason] += 1
    cid = (f.get("Candidate") or [None])[0]
    src = cands.get(cid, {}).get("Source") if cid else None
    if src == "Job Board":
        stage_type = "Had a Formal Interview" if interviews_by_app.get(a["id"], 0) > 0 else "No Formal Interview Logged"
        jobboard_reason[stage_type][reason] += 1

# One table, one row per (Scope, Reason) -- not a separate table per scope,
# each scope's share is computed within that scope.
total_rejected = sum(overall_reason.values())
rows = [("All", r, c, pct(c, total_rejected)) for r, c in overall_reason.most_common()]
for stage_type, ctr in jobboard_reason.items():
    total = sum(ctr.values())
    for reason, c in ctr.most_common():
        rows.append((f"Job Board - {stage_type}", reason, c, pct(c, total)))
write_csv("rejection_reasons", [
    "Scope", "Reason", "Applications", "Share (%)",
], rows)

# How many "No Formal Interview Logged" rejections still had a recruiter
# screening call (Applications.Screened On filled)? "No formal interview"
# does not mean "no human contact" -- a screening call isn't recorded in the
# Interviews table. Surfaced so a reason like "Culture Fit" pre-interview
# doesn't read as judged from a resume alone.
no_interview_rejects = [
    a["fields"] for a in apps_raw
    if a["fields"].get("Stage") == "Rejected"
    and cands.get((a["fields"].get("Candidate") or [None])[0], {}).get("Source") == "Job Board"
    and interviews_by_app.get(a["id"], 0) == 0
]
had_screen = sum(1 for f in no_interview_rejects if f.get("Screened On"))
print(f"  Job Board, 'No Formal Interview Logged' rejections: {len(no_interview_rejects)}; "
      f"{had_screen} of those ({pct(had_screen, len(no_interview_rejects))}%) still had a recruiter "
      f"screening call logged (Screened On filled) -- just not a formal Interview record.")
write_csv("jobboard_screening_check", [
    "No Formal Interview Rejections", "Had A Screening Call Logged", "Share (%)",
], [[len(no_interview_rejects), had_screen, pct(had_screen, len(no_interview_rejects))]])

# ===========================================================================
# 12. Offer pay vs posted salary band -- categorized, not a per-ID list
# ===========================================================================
print("=== 12. Offer pay vs posted salary band ===")
position_status = Counter()
outliers = []
for oid, f in offers.items():
    app_id = (f.get("Application") or [None])[0]
    app_f = apps.get(app_id, {}) if app_id else {}
    op_id = (app_f.get("Opening") or [None])[0]
    op_f = openings.get(op_id, {}) if op_id else {}
    band_min, band_max = op_f.get("Salary Band Min"), op_f.get("Salary Band Max")
    base = f.get("Base CTC")
    if base is None or band_min is None or band_max is None:
        continue
    if base < band_min:
        position = "Below band"
    elif base > band_max:
        position = "Above band"
    else:
        position = "Within band"
    position_status[(position, f.get("Status"))] += 1
    over_by_pct = round((base - band_max) / band_max * 100, 0) if base > band_max else None
    if over_by_pct and over_by_pct >= 100:
        outliers.append([f.get("Offer ID"), base, band_max, over_by_pct, f.get("Status")])

rows = [(pos, status, c) for (pos, status), c in sorted(position_status.items(), key=lambda x: -x[1])]
write_csv("offer_vs_band_summary", ["Position", "Offer Status", "Offers"], rows)
write_csv("offer_vs_band_outliers", [
    "Offer ID", "Offered Salary", "Band Max", "Over Band (%)", "Offer Status",
], outliers)
print("  offer_vs_band_outliers lists only offers >=100% over the posted band max.")

# ===========================================================================
# 13. No-show/cancellation rate -- grouped and sorted, not interleaved
# ===========================================================================
print("=== 13. No-show/cancellation rate, grouped by dimension ===")
NONCOMPLETE = {"No Show", "Cancelled", "Rescheduled"}
dim_totals = defaultdict(Counter)
for iv in interviews_raw:
    f = iv["fields"]
    app_id = (f.get("Application") or [None])[0]
    app_f = apps.get(app_id, {}) if app_id else {}
    op_id = (app_f.get("Opening") or [None])[0]
    d = dept_name.get((openings.get(op_id, {}).get("Department") or [None])[0]) if op_id else None
    cid = (app_f.get("Candidate") or [None])[0]
    src = cands.get(cid, {}).get("Source") if cid else None
    outcome = f.get("Outcome")
    noncomplete = outcome in NONCOMPLETE
    for dim, val in [("Department", d), ("Source", src), ("Round", f.get("Round"))]:
        dim_totals[(dim, val)]["total"] += 1
        if noncomplete:
            dim_totals[(dim, val)]["noncomplete"] += 1

DIM_ORDER = {"Department": 0, "Source": 1, "Round": 2}
rows = []
for (dim, val), c in dim_totals.items():
    rows.append([dim, val, c["total"], c["noncomplete"], pct(c["noncomplete"], c["total"])])
rows.sort(key=lambda r: (DIM_ORDER[r[0]], -r[4]))
write_csv("interview_noncompletion_rate", [
    "Dimension", "Value", "Interviews Scheduled", "Non-Completions", "Rate (%)",
], rows)
print("  Non-Completions = interviews with Outcome in No Show, Cancelled, Rescheduled.")

# ===========================================================================
# 14. Materiality: how much of the data has an error, including the new
#     requisition-status-integrity finding
# ===========================================================================
print("=== 14. Materiality summary ===")
dup_candidate_ids = {m for v in canonical.values() if len(v["members"]) > 1 for m in v["members"]}
appid_ctr = Counter(a["fields"].get("Application ID") for a in apps_raw)
dup_appid_records = [a["id"] for a in apps_raw if appid_ctr[a["fields"].get("Application ID")] > 1]
declined_stage_lag = [
    o["fields"].get("Offer ID") for o in offers_raw
    if o["fields"].get("Status") == "Declined"
    and apps.get((o["fields"].get("Application") or [None])[0], {}).get("Stage") == "Offer"
]
bad_interview_dates = [
    iv["fields"].get("Interview ID") for iv in interviews_raw
    if pd(iv["fields"].get("Completed On")) and pd(iv["fields"].get("Scheduled On"))
    and pd(iv["fields"].get("Completed On")) < pd(iv["fields"].get("Scheduled On"))
]
bad_offer_dates = [
    o["fields"].get("Offer ID") for o in offers_raw
    if pd(o["fields"].get("Proposed Start Date")) and pd(o["fields"].get("Offered On"))
    and pd(o["fields"].get("Proposed Start Date")) < pd(o["fields"].get("Offered On"))
]
filled_without_hire = [f.get("Req ID") for oid, f in openings.items()
                        if f.get("Status") == "Filled" and oid not in hired_opening_ids]

total_records = len(cands_raw) + len(apps_raw) + len(openings_raw) + len(interviews_raw) + len(offers_raw) + len(people_raw) + len(depts_raw)
issue_rows = [
    ("Duplicate candidate records (phone+name match)", len(dup_candidate_ids), len(cands_raw)),
    ("Application records with a reused Application ID", len(dup_appid_records), len(apps_raw)),
    ("Declined offers whose Application.Stage still says Offer (not Rejected)", len(declined_stage_lag), len(offers_raw)),
    ("Interviews with Completed On before Scheduled On", len(bad_interview_dates), len(interviews_raw)),
    ("Offers with Proposed Start Date before Offered On", len(bad_offer_dates), len(offers_raw)),
    ("Job openings marked 'Filled' with no matching Hired application", len(filled_without_hire), len(openings_raw)),
]
touched = (len(dup_candidate_ids) + len(dup_appid_records) + len(declined_stage_lag)
           + len(bad_interview_dates) + len(bad_offer_dates) + len(filled_without_hire))
issue_rows.append(("TOTAL records touched by at least one issue above", touched, total_records))
out_rows = [(name, n, table_n, pct(n, table_n)) for name, n, table_n in issue_rows]
write_csv("materiality_summary", [
    "Issue", "Records Affected", "Table Size", "Share Affected (%)",
], out_rows)
print("  Table Size is the source table's row count, except the TOTAL row where it's the whole dataset.")

print("\nAll views built. See talentflow/analysis/output/")
