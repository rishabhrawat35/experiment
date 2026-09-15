# TalentFlow (Acme Corp) — Data Quality Audit

**Scope:** all 8 tables pulled from the read-only Airtable base (`appYePRAI75PMbQNQ`), 892
records total, pulled 2026-08-27. Findings below are used to qualify the D1 verdicts and D2
roadmap in [talentflow-q3-roadmap.md](talentflow-q3-roadmap.md).

## Methodology — how I went looking

Not a spot-check: every check below ran against the full population of the relevant table(s),
not a sample. Three passes:

1. **Referential integrity** — every forward/reverse link field pair Airtable exposes (10
   relationship types across the 8 tables) checked for dangling or unsynced pointers.
2. **Semantic/business-logic consistency** — do fields that are supposed to move together
   actually agree (Application.Stage vs the linked Offer.Status; Recruiter/Interviewer/Hiring
   Manager department vs the Opening's department; interview date ordering).
3. **Plain-number soundness** — every rate cited elsewhere in this project is shown with its
   count and its total (never a bare percentage), was checked for right-censoring if
   time-based, and was re-run on both raw and duplicate-resolved candidate identities if
   source/channel-based. No statistical confidence ranges are used anywhere in this project —
   where a count is small enough that the number could easily look different with more data,
   that's said in plain words instead.

All numbers below are reproducible: `../analysis/build_all_views.py` computes them
deterministically (stdlib only, no model call inside it) and writes one CSV per view to
`../analysis/output/`. `../analysis/challenge_all_views.py` independently
re-derives the headline counts via SQL (a different execution engine from the dict/list
aggregation in the build script) and asserts they match — 8/8 checks pass as of this writing.

## What's wrong, and how much of it

**Top line: 34 of 892 pulled records (3.8%) are touched by at least one of the six issues
below.** The corruption is narrow and specific, not pervasive — but several of these issues sit
directly underneath both VP claims, so "only 3.8%" undersells the impact; materiality by
record count and materiality by decision-relevance are different questions.

| # | Issue | Records affected | % of relevant table | Severity |
|---|---|---|---|---|
| 1 | Duplicate candidate records (same phone + name, different email/record) | 12 (6 pairs) | 4.0% of 300 candidates | High — directly contaminates source-attribution claims |
| 2 | `Application ID` values reused across two unrelated records | 8 (4 IDs) | 2.3% of 350 applications | High — breaks any join on the business ID instead of the record ID |
| 3 | Declined offers whose Application.Stage still reads "Offer" not "Rejected" | 5 | 13.9% of 36 offers | High — directly underneath the offer-acceptance metric |
| 4 | Job openings marked "Filled" with no application that ever reached "Hired" | 2 | 25% of 8 filled openings | High — the requisition status field disagrees with what actually happened; directly explains Engineering's 0% hire rate |
| 5 | Interviews with Completed On before Scheduled On | 4 | 2.5% of 160 interviews | Medium — logically impossible, low volume |
| 6 | Offers with Proposed Start Date before Offered On | 3 | 8.3% of 36 offers | Medium — logically impossible, low volume |

### 1. Duplicate candidates — and it's not just noise, it contaminated a finding

Six pairs of candidate records share an identical phone number and full name but a different
email and Candidate ID — near-certain duplicates of the same physical person. Two of the six
pairs span **Job Board and Referral** for the same person, and in both cases the Job Board
application was rejected while the Referral application was the one that got hired. That means
40% of the raw "Referral hires" (2 of 5) are people who also have a Job Board record — the
initial "Job Board and Referral are tied at 26.9% of hires" reading was standing partly on
identity confusion. Re-run with the duplicates merged (first-touch attribution — credit the
source of whichever record was created first for that person):

| View | Job Board share of hires | Referral share of hires |
|---|---|---|
| Raw (as recorded) | 26.9% | 26.9% (tied) |
| Deduped, first-touch attribution | 33.3% | 16.7% |

Attribution methodology is a real, named choice, not a bug to resolve silently — see the
metric-spec section of the roadmap doc for why first-touch is the default here.

### 2. Application ID collisions

`APP-00001`, `APP-00005`, `APP-00007`, and `APP-00010` are each assigned to two completely
different application records — different candidates, different openings, different stages.
Anything that joins on the human-readable `Application ID` string instead of the Airtable
record `id` will silently merge unrelated rows. **Recommendation: never use the business ID as
a join key; the analysis code in this project uses the record `id` everywhere.**

### 3. Application.Stage lags Offer.Status — and it's systematic, not random

All 5 Declined offers (100% of that category) still show their linked Application at
`Stage = Offer` instead of `Rejected`. This isn't scattered noise — it's a consistent gap in
whatever process (manual or automated) is supposed to advance Stage when an Offer resolves.
`Applications.Status` (Active/Closed), by contrast, *does* track the Offer's resolution
correctly even when Stage doesn't — the 10 Offer-stage applications split cleanly into
5×(Active, Offer still Pending) and 5×(Closed, Offer Declined). So Status is the more reliable
"is this decided" signal today; Stage's specific Hired/Rejected bucket is what lags. The fix
isn't "add a sync job to patch a bug," it's that `Applications.Status` (and the Hired/Rejected
half of Stage) should be a computed rollup from Interviews/Offers events instead of two
independently-settable fields that can drift — see roadmap candidate A.

### 4. "Filled" requisitions that were never actually filled, per the application data

2 of the 8 Job Openings marked `Status = Filled` have **no Application that ever reached
`Stage = Hired`** for that opening: `REQ-2026-017` (Lead QA Engineer, Engineering) and
`REQ-2026-011` (Junior Technical Support Engineer, Customer Support). This is the direct
explanation for a pattern that would otherwise look unexplained: the department-level funnel
shows **Engineering at a 0% hire rate (0 of 30 applications)** — not because nothing worked out
for Engineering, but because the one role Engineering did fill has no record of who filled it.
Same class of problem as the Stage/Offer lag above — a status field that isn't backed by the
underlying event data — but on the Job Openings table instead of Applications.

### 5-6. Impossible date orderings

4 interviews have `Completed On` earlier than `Scheduled On`; 3 offers have `Proposed Start
Date` earlier than `Offered On`. Low volume (2.5% and 8.3% of their tables respectively) but
worth a basic form-level validation rule going forward — this is a one-line fix, not a project.

### What's clean

Every forward/reverse link field pair across all 8 tables (Interviews↔Interviewer,
Interviews↔Application, Applications↔Candidate, Applications↔Opening, Offers↔Application,
Openings↔Department, People↔Department, Openings↔Recruiter, Openings↔Hiring Manager — 10
relationship types) has **zero mismatches**, checked against every record. No dangling foreign
keys anywhere. No null Source/CTC/Years-Experience on Candidates. No negative or CTC-outlier
values. No Target-Close-before-Opened issues on Job Openings.

## The bigger structural finding: staffing assignment shows almost no department affinity

This surfaced while checking whether Interview links were synchronized (they are — see above).
What's actually unusual is who gets assigned to what:

| Relationship checked | Same department | Different department | Mismatch rate |
|---|---|---|---|
| Interview's Interviewer vs the Opening being interviewed for | 22 | 138 | 86% |
| Application's Recruiter vs the Opening's department | 80 | 270 | 77% |
| Job Opening's Hiring Manager vs the Opening's own department | 3 | 21 | 87.5% |
| Application's Recruiter vs that application's Interviewer, same application | 0 | 160 | 100% — never the same person |

Every person's Role is also perfectly single-purpose (a Recruiter never interviews, 0
exceptions) — combined with the department-random-looking assignment, this reads like People
were linked to Interviews/Applications/Openings independently of their Department field, which
is more consistent with a data-generation artifact than an organic org chart. **I can't resolve
which from the data alone — this is an open question for Acme, not a closed bug**, and it gates
how much weight any interviewer- or recruiter-level finding below can carry.

It does appear to matter operationally, though: same-department interviews average a higher
score (3.07 vs 2.77) and a much lower non-completion rate (4.5% vs 15.2% no-show/cancel/
reschedule) than cross-department ones — directionally consistent with the affinity break
having a real cost, though the same-department sample (n=22) is thin. (An earlier draft of
this line read 4.8%/17.4%, computed only over interviews that had a Score — but a No Show or
Cancelled interview usually has no score, so that undercounted the true group size. Fixed in
`build_all_views.py` and SQL-verified in `challenge_all_views.py`; the correct denominator is
every interview in the group, 22 and 138, not just the scored ones.)

## Interviewer calibration: one clear outlier

Six people carry all 160 interviews. Five of them give a normal mix of verdicts (roughly
25-45% Hire/Strong Hire) with average scores 2.9-3.3. The sixth, **Rakesh Sethi**, gave
**"Strong No Hire" on 26 of his 30 interviews (87%)**, average score 1.59 — the only
interviewer who never once recorded a Hire or Strong Hire. Critically, his verdict doesn't
predict the outcome: **9 of those 26 "Strong No Hire" candidates (35%) were still Hired or are
still active at Offer stage.** Either this is a genuinely miscalibrated panelist whose opinion
the rest of the process is (correctly) overriding, or his Score/Recommendation values were
seeded independently of the rest of the record in this export — I can't distinguish the two
from data alone, but either way his input is not currently informative and is worth Acme's
direct attention.

## Interview-journey structure: shorter and less sequential than the schema implies

Only 143 of 350 applications (41%) have any interview logged. Of those, 126 have exactly one
interview and 17 have exactly two — **nobody in this dataset has three or more**, despite the
`Round` field carrying five distinct values (Screen, Technical 1, Technical 2, Bar Raiser,
Hiring Manager) that imply a longer process exists conceptually. Where two rounds exist, the
pairing doesn't follow a consistent order — 63 applications have *only* a "Technical 1" round
logged with no Screen beforehand; other two-round applications skip straight from Screen to
Bar Raiser. Short, irregular journeys, not the clean multi-stage funnel the Round field's
value list suggests.

**58% of all Rejected applications (116/200) never had an interview at all** — they were
screened out on resume/comp/culture-fit grounds before reaching an interviewer. This matters
for reading Job Board's rejection volume specifically: most of it is a pre-interview filtering
question, not an interview-quality question (see roadmap doc).

## Ghosting / no-shows: the magnitude is real, the cause isn't recoverable

10 No Show + 7 Cancelled + 5 Rescheduled = 22 of 160 interviews (13.75%) didn't happen as
scheduled. But there's no field recording who caused it, and for those 22 records, `Feedback`,
`Completed On`, and `Score` are populated for only 4 — the rest are bare. I can report the rate
as an operational-efficiency signal; I cannot honestly attribute it to candidate-side ghosting
vs company-side rescheduling without a schema change Acme would need to make.

## Requisition aging — the largest operational finding in this audit

**10 of the 11 currently-Open requisitions (91%) are past their Target Close date**, overdue by
97 to 422 days (several exceed a year). This wasn't asked about by the VP and isn't part of
either headline claim, but by both volume and severity it's arguably the most material
operational problem visible in this data — see the roadmap doc for why it's now a build
candidate.

## Comp governance: offers outside the posted salary band

7 of 36 offers (19.4%) have a Base CTC outside the linked Job Opening's posted Salary Band — 4
above, 3 below. One Declined offer is 2.85M against a posted band of 400K-800K (3.5x the band
max) — either a serious data-entry error (wrong opening linked, wrong band, or wrong CTC) or a
real approved exception that should have its own record. Worth a quick manual check with Acme
before reading anything into the Decline itself.

## Senior/Lead candidates withdraw more often — two explanations tested, both ruled out

Senior and Lead candidates withdraw their own applications about 6 times more often than
Junior candidates do (6.2% vs 1.0%; Mid is 0%). Two obvious explanations were tested directly
against the data rather than assumed:

- **Comp mismatch?** No — withdrawn Senior candidates asked for a *smaller* raise on average
  (25.3% above their current pay) than Senior candidates who were ultimately hired (30.3%). If
  comp expectations were driving withdrawals, the withdrawn group should have asked for more,
  not less.
- **A process that drags on too long?** No — Lead-level hiring is the *fastest* of any level
  (median 14 days applied-to-closed, vs 20-24 days for every other level), yet Lead has one of
  the highest withdrawal rates. A slow process doesn't explain it either.

With only 13 withdrawals total across Senior and Lead combined, there isn't enough data in
this export to find the real cause. The most likely explanation — a competing offer from
elsewhere — isn't something this schema captures at all. Named here as an open question, not
forced into a story the data doesn't support.

## Confidence levels, summarized

Full detail with method per number is in [findings.md](../findings.md). As a
rule in this project: every rate is shown together with its count and total, never as a bare
percentage; anything based on fewer than 10 records is called out in words as a small sample,
not decision-grade; every source/channel claim was tested against both raw and
duplicate-resolved candidate identity. No statistical confidence ranges are used anywhere in
this project or its dashboard.
