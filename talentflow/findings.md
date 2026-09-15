# TalentFlow — Findings

Every quantitative claim used anywhere in this project (the [data-quality audit](docs/talentflow-data-quality-audit.md),
the [Q3 roadmap](docs/talentflow-q3-roadmap.md), and the
[dashboard](artifacts/talentflow-analysis-dashboard.html)), with its exact value, the file that
produces it, and an honest confidence label.

**Confidence vocabulary** (matches the audit doc and roadmap — not a separate scale):
- **High** — exact count over the full population, usually SQL-reproduced independently by `analysis/challenge_all_views.py`.
- **Medium** — the count is exact but the sample is thin enough, or the reading contested enough, that it shouldn't be treated as more precise than it is.
- **Low** — directional only; too few records to support a decision.

Rows whose number is one of the 10 headline checks in `analysis/challenge_all_views.py` are marked
**SQL-verified** in Method — those carry the highest confidence tier available in this project.
Everything else (one-off computations against the raw JSON, not wired into the challenger) says so
plainly rather than borrowing that rigor.

Markdown chosen over CSV: several Value/Method cells below are long free text with embedded commas
and quotes that make CSV escaping unreadable in a diff, and every other doc in this project is
already Markdown — a `findings.csv` companion would just be the odd file out. See the bottom of
this file for the full rationale.

---

## VP Claim 1 — "Job boards bring 26.9% of our hires, biggest channel by a wide margin"

| Claim | Metric | Value | Method | Confidence |
|---|---|---|---|---|
| Job Board share of hires, as originally reported (before fixing duplicate candidate records) | Job Board share of hires, raw | 26.9% (7 of 26 hired applications) | Count of Hired-stage applications grouped by the linked candidate's Source field. `analysis/build_all_views.py` -> `analysis/output/q1_source_summary.csv`. SQL-verified in `analysis/challenge_all_views.py`. | High -- numerically exact, independently reproduced; see next row for why the headline reading is wrong |
| Referral share of hires, same method (before fixing duplicates) | Referral share of hires, raw | 26.9% (7 of 26) -- exactly tied with Job Board | Same method, segment = Referral. `analysis/output/q1_source_summary.csv`. SQL-verified. | High on the count; the tie itself is an artifact, see next row |
| Job Board share of hires after merging 6 duplicate candidate-record pairs (matched by phone number; credited to each person's earliest-created record) | Job Board share of hires, deduped | 33.3% (8 of 24 merged hires) -- clear leader, not a tie | `analysis/common.py` `canonical_persons()` groups candidates by normalized phone number. `analysis/build_all_views.py` -> `analysis/output/q1_source_summary.csv`, "after fixing duplicates" column. | High -- correct given the phone-matching rule; the rule itself (first-touch attribution) is a named assumption, not a measured fact |
| Job Board hire rate (applications hired / applications from that source) | Job Board conversion | 3.0% (7 of 236 applications) | `analysis/output/q1_source_summary.csv`. | High -- large sample (236), the number itself is solid |
| Referral hire rate, same method | Referral conversion | 53.8% (7 of 13 applications) | `analysis/output/q1_source_summary.csv`. | Medium on the exact figure -- only 13 applications; High on direction (Job Board converts worse than every other source, all >=9.7%) |
| Cross-check: hire rate for applications with Acme's real internal-employee-referrer field filled in, vs the self-reported "Referral" Source label | Referral signal comparison | 11.1% (3 of 27) with a real referrer link, vs 53.8% (7 of 13) self-reporting "Referral" as Source, vs 7.1% (23 of 323) with neither | The two "referral" signals live on different tables (`Applications.Referred By` vs `Candidates.Source`) and barely overlap -- only 3 of 13 Referral-source applications also carry a Referred-By link. `analysis/output/referral_signal_comparison.csv` and `analysis/output/referral_source_vs_referredby_crosstab.csv`. | Medium -- this materially tempers the 53.8% number; the real internal-referral lift looks much smaller once measured on Acme's own tracking field instead of the self-reported label |
| Pre- vs post-interview rejection split, Job Board specifically | Job Board rejection reasons | 58% of all rejections (116/200) happen with zero interviews logged company-wide; for Job Board, pre-interview rejections are led by Culture Fit (18), Comp Expectation (17), Skills Mismatch (16); post-interview rejections are led by Better Candidate (23), Skills Mismatch (19) | `analysis/output/rejection_reasons.csv`, joined against interview counts per application. | High -- counts are exact; reasons are recruiter-entered categorical judgments, not independently verifiable |
| Department x Source cross-tab (the two-dimension view requested directly) | Sales dept, Job Board vs LinkedIn | Sales: 50 Job Board applications, 0 hired; 8 LinkedIn applications, 3 hired (37.5%) -- the strongest department/source combination with a meaningful sample | `analysis/output/department_x_source.csv`. | High on the counts; LinkedIn's 37.5% is on a small base (n=8) and should be read as a lead worth watching, not a proven pattern |
| Operational: Job Board rejections with no formal Interview record that still had a recruiter screening call logged (`Applications.Screened On` filled) | Job Board "screened but not interviewed" | 64 of 84 (76.2%) -- "no formal interview" does not mean "no human contact" | `analysis/output/jobboard_screening_check.csv`, joined `Applications.Screened On` against the Interviews table. **SQL-verified** in `analysis/challenge_all_views.py`. | High |
| Technical 1 round is the single biggest post-screen filter -- bigger than Screen itself | Round-level rejection rate | Technical 1 rejects 65.2% (45 of 69 interviews held) of candidates who already passed Screen; Screen itself rejects 52.7% (39/74) | `analysis/output/round_summary.csv`. | High -- exact counts over the full 160-interview population; not one of the 10 checks the SQL challenger re-derives, so treat as solid-but-not-cross-engine-verified |

## VP Claim 2 — "Offer acceptance rate is ~72% and needs to move"

| Claim | Metric | Value | Method | Confidence |
|---|---|---|---|---|
| Acceptance rate, undecided offers counted as a "no" | Offer acceptance rate (Pending = fail) | 72.2% (26 of 36 offers) | `Offers.Status` distribution. `analysis/output/q2_offer_acceptance_two_ways.csv`. **SQL-verified**. | High on the count; the number itself is exactly what it says, but see next row for why it shouldn't be read as more precise than the sample allows |
| Acceptance rate, undecided offers left out of the count | Offer acceptance rate (Pending excluded) | 83.9% (26 of 31 offers) | Same source, Pending offers dropped. `analysis/output/q2_offer_acceptance_two_ways.csv`. **SQL-verified**. | High on the count; with only 36 offers total, this and the row above are both correct under their own definition -- neither is "more right" |
| Age of the 5 currently-Pending offers | Stale-offer age | 20 to 222 days old as of the latest data (2026-08-27); several exceed any plausible live decision window | `talentflow/data/offers.json`, Offered On vs dataset max date. | High |
| Monthly acceptance rate, most recent 3 months flagged as too immature to trust | Monthly offer volume | Offer volume per month ranges 1-8 across the whole dataset -- too few for any single month to be read as a trend | One-off computation from `talentflow/data/offers.json` (Offered On, grouped by month). Not a persisted pipeline CSV -- this fact is used only to justify the D3 metric spec's 3-month rolling window instead of monthly reporting, not shown as its own dashboard view. | Medium -- counts are exact, but volume per month is too small to support a trend conclusion either way |
| Notice-period vs offer outcome | Average notice period, Accepted vs Declined; bucketed accept rate | Accepted avg 47.3 days (n=26) vs Declined avg 30.0 days (n=5), of 36 offers with a linked Notice Period Days value. By bucket (Accepted+Declined only, n=31): 0-15 days = 57.1% accept (4/7); 16-30 days = 100% accept (9/9); 31-60 days = 80% accept (8/10); 61-90 days = 100% accept (5/5) | `talentflow/data/offers.json` joined to `applications.json` and `candidates.json` on the Notice Period Days field. One-off computation -- not wired into `analysis/build_all_views.py` or the SQL challenger. | Low -- n=36 offers total, smallest bucket n=7; pattern runs opposite to a naive "long notice = trapped, must accept" leverage story, not enough data to conclude a real leverage effect exists |

## Data quality

| Claim | Metric | Value | Method | Confidence |
|---|---|---|---|---|
| Candidate identity | Duplicate candidate records (identical phone + full name, different email/record) | 12 records / 6 people, 4.0% of 300 candidates; 2 of the 6 pairs span Job Board and Referral for the same person | `analysis/common.py` `canonical_persons()`. **SQL-verified**. | High |
| Join keys | Application ID values reused across two unrelated application records | 8 records / 4 IDs (APP-00001, 00005, 00007, 00010), 2.3% of 350 applications | `analysis/output/materiality_summary.csv`. **SQL-verified**. | High |
| Pipeline sync | Declined offers whose linked Application.Stage still reads "Offer" instead of "Rejected" | 5 of 5 Declined offers (100% of that category), 13.9% of all 36 offers | Join `Offers.Status='Declined'` to Applications via the Application link, compare to Stage. **SQL-verified**. | High |
| Requisition status integrity | Job openings marked "Filled" with no application that ever reached "Hired" | 2 of 8 Filled requisitions (25%) -- REQ-2026-017 (Engineering) and REQ-2026-011 (Customer Support); directly explains Engineering's 0% department hire rate | `analysis/output/requisition_status_integrity.csv`, cross-referencing Job Openings.Status against Applications.Stage via the Opening link. **SQL-verified**. | High |
| Impossible dates | Interviews with Completed On before Scheduled On | 4 of 160 interviews (2.5%) | `talentflow/data/interviews.json` date comparison. | High |
| Impossible dates | Offers with Proposed Start Date before Offered On | 3 of 36 offers (8.3%) | `talentflow/data/offers.json` date comparison. | High |
| Overall materiality | Total records touched by at least one issue above | 34 of 892 pulled records (3.8%) | `analysis/output/materiality_summary.csv` (sum of distinct affected records across the six issue types). | High |
| Link integrity | Every forward/reverse link field pair across all 8 tables (10 relationship types checked) | 0 mismatches across all of them -- record-ID pointers are 100% intact | Full-population check, not a sample, across every Airtable auto-maintained two-way link. | High |
| Staffing assignment | Interviewer's department vs the Opening's department | Match in 22 of 160 interviews (14%); mismatch in 138 (86%) | Join Interviews->Interviewer->People.Department against Interviews->Application->Opening->Department. | High |
| Staffing assignment | Application's Recruiter department vs the Opening's department | Match in 80 of 350 (23%); mismatch in 270 (77%) | Same method, Applications.Recruiter. | High |
| Staffing assignment | Job Opening's Hiring Manager department vs the Opening's own department | Match in 3 of 24 (12.5%); mismatch in 21 (87.5%) | Job Openings.Hiring Manager vs Job Openings.Department. | High |
| Staffing assignment | Application's Recruiter vs that application's Interviewer, same application | Same person: 0 of 160 (0%) | Cross-reference Applications.Recruiter against Interviews.Interviewer for the same Application record. | High |
| Staffing assignment, quality impact | Same-department vs cross-department interview: average score and non-completion rate | Same-dept (n=22): avg score 3.07, non-completion 4.5% (1/22). Cross-dept (n=138): avg score 2.77, non-completion 15.2% (21/138) | `analysis/output/affinity_quality_check.csv`, SQL-verified in `challenge_all_views.py`. (An earlier draft showed 4.8%/17.4%, computed only over interviews that had a Score -- but a No Show/Cancelled interview usually has no score, so that draft undercounted the true group size, 22 and 138. Fixed at the source in `build_all_views.py` and confirmed via an independent SQL query, not just a re-read.) | High -- exact counts, SQL-verified; the direction (cross-dept worse on both measures) is solid, the same-dept sample (n=22) is still small enough that the exact gap size shouldn't be over-read |
| Interviewer calibration | Rakesh Sethi's interview recommendations vs the other 5 interviewers | 28 of 30 interviews (93%) scored "No Hire" or "Strong No Hire" (average score 1.59, vs 2.9-3.34 for every other interviewer); 9 of those negative verdicts (32%) still ended in Hired or an active Offer | `analysis/output/interviewer_calibration.csv`; downstream Stage cross-referenced manually against his Interview records. | High on the counts; the interpretation (miscalibrated panelist vs seeding artifact) cannot be resolved from data alone |
| Interview structure | Applications with logged interviews, and round count | 143 of 350 applications (41%) have any interview logged; of those, 126 have exactly 1 and 17 have exactly 2 -- none have 3+, despite 5 named Round types existing in the schema | `talentflow/data/interviews.json` and `applications.json`, joined per application. | High |
| Interview structure | Round sequencing consistency | No canonical order followed -- e.g. 63 applications have only a "Technical 1" interview logged with no prior Screen round | `analysis/output/round_summary.csv` plus a manual sequence audit. | High |
| Ghosting attribution | No-show/cancelled/rescheduled interview rate | 13.75% (22 of 160) | `analysis/output/interview_noncompletion_rate.csv`. | High on the rate; not attributable to candidate vs company -- Feedback/Completed On/Score are populated for only 4 of the 22 non-completed records, so cause cannot be determined from this schema |
| Feedback text is templated, not written per interview | Distinct interview Feedback strings | Only 12 distinct Feedback strings appear across 142 non-empty interview records -- several repeat verbatim 3+ times | `talentflow/data/interviews.json`, distinct-value count over the Feedback field. One-off computation, not in `build_all_views.py`. | High on the count; this is the reason the "interviewer quality audit via feedback text" roadmap idea was ruled out as not buildable this cycle |
| Cross-department feedback text doesn't explain the cross-department quality gap | Unfamiliarity-language mentions and word count, cross- vs same-department feedback | 0 of 121 cross-department Feedback notes mention being unfamiliar with the role; average length is nearly identical either way (9.7 words cross-dept vs 10.1 words same-dept) | `talentflow/data/interviews.json` joined to `people.json` (interviewer department) and `job_openings.json` (opening department). One-off computation. | High on the counts; confirms the score/non-completion gap above is real but the feedback text itself doesn't explain why -- don't claim interviewers "admit" unfamiliarity, they don't, in this data |
| Rejection feedback coverage | Rejected applications with any interview Feedback linked at all | 73 of 200 Rejected applications (36.5%) have any linked interview Feedback | `talentflow/data/applications.json` joined to `interviews.json` on the Application link. One-off computation. | High on the count; this is why an automated rejection-reason taxonomy (beyond the existing 6 flat categories) isn't buildable from feedback text this cycle |

## Operational

| Claim | Metric | Value | Method | Confidence |
|---|---|---|---|---|
| Requisition aging | Open job requisitions past their Target Close date | 10 of 11 currently-Open requisitions (91%), overdue by 97 to 422 days | The 10/11 count is in `analysis/output/requisition_overview.csv`. The 97-422 day range is a one-off computation from `talentflow/data/job_openings.json` (Target Close vs 2026-08-27) -- not broken out by requisition in a persisted CSV, since the detailed per-req list isn't kept as a dashboard view. Re-verified directly: [97, 182, 214, 223, 231, 237, 334, 394, 406, 422]. | High |
| Comp governance | Offers with a Base CTC outside the linked Job Opening's posted Salary Band | 7 of 36 offers (19.4%) sit outside their band (4 above, 3 below); 2 of those sit more than double their band's maximum -- OFF-00016 (accepted, 161% over) and OFF-00006 (declined, 256% over) | `analysis/output/offer_vs_band_summary.csv` and `analysis/output/offer_vs_band_outliers.csv`, joined Offers->Application->Opening->Salary Band. | High on the counts; cannot tell from data alone whether the 2 extreme cases are data-entry errors or deliberate exceptions |
| Withdrawal pattern | Withdrawal rate by level, and two tested explanations | Senior 6.2% (10/162), Lead 6.2% (3/48), Junior 1.0% (1/96), Mid 0% (0/44). Comp-ask-gap hypothesis ruled out (withdrawn Senior candidates asked for LESS of a raise than hired ones: 25.3% vs 30.3%). Process-length hypothesis ruled out (Lead has the shortest median process of any level, 14 days, yet a high withdrawal rate) | `analysis/output/withdrawn_by_level.csv`. | High on the counts and on both hypotheses being ruled out; Low on identifying the true cause -- only 13 withdrawals exist across Senior+Lead, too few to isolate it from this data alone |

---

## Format decision

**Markdown, not CSV.** Several Value and Method cells here are long free text containing commas,
parentheses, and quoted sub-phrases (e.g. the referral cross-check row, the Rakesh Sethi row) -- in
CSV that requires careful quote-escaping that's easy to get wrong and unpleasant to diff-review;
in Markdown it's just prose in a cell. Every other deliverable in this project
(`talentflow-data-quality-audit.md`, `talentflow-q3-roadmap.md`) is already Markdown, so this
keeps the project's cross-links consistent instead of making findings.csv the one CSV artifact in
a Markdown project. Completeness and readability mattered more here than machine-parseability --
nothing downstream actually parses this file as structured data. `findings.csv` has been deleted;
this file is now the single source.
