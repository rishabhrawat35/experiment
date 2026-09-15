# TalentFlow Q3 Roadmap — Acme Corp

- **Prepared by:** Rishabh Rawat (PM)
- **Data source:** Airtable base `appYePRAI75PMbQNQ`, 892 records across 8 tables
- **Data quality detail:** [talentflow-data-quality-audit.md](talentflow-data-quality-audit.md)
- **Every number's method + confidence:** [findings.md](../findings.md)
- **Interactive dashboard:** [../artifacts/talentflow-analysis-dashboard.html](../artifacts/talentflow-analysis-dashboard.html)
- **Code behind every number:** [../analysis/](../analysis/)

---

## D5 — One-Page Memo (Executive Summary)

**What we found**

| Claim | VP said | Data shows | The number that decides it |
|---|---|---|---|
| Job boards | 26.9% of hires, biggest channel, wide margin | Job Board is #1 at 33.3% of hires once duplicates are fixed, but converts worst of any channel | 3.0% hire rate (7/236 applications), worst of 5 channels |
| Offer acceptance | ~72%, needs to move | 72.2%-83.9% depending on how Pending is counted; sample too thin to pick a "real" number | n = 36 offers total |

**One problem the VP didn't ask about, bigger than either claim**

- 34 of 892 records (3.8%) have wrong information because a status field wasn't updated when it should have been. This includes the offer records the 72% number was built from — see D2 build #1.

> Note: 91% of open job requisitions (10 of 11) are also already past their target close date. This is already covered by D2 build #2, so it isn't a separate open problem — flagging it here only for visibility.

**What we're doing about it (6 eng-weeks, see D2)**

1. Data Accuracy Program: fix the fields every other number depends on.
2. Offer & Requisition Lifecycle Automation: stale-offer and overdue-req alerting.
3. Governed Recruiting Metrics Dashboard: acceptance rate (per D3) plus funnel drop-off, by department and level.

**What we're explicitly not building this cycle (see D2)**

- AI-assisted technical screening: real opportunity, not scoped yet.
- Cross-department interviewer quality audit via feedback text: data can't support it yet.
- Notice-period leverage study: directionally interesting, n too small to act on.

**What we'd look at next**

- Scope "smarter technical screening" with Eng, and define what it screens on before sizing it.
- Fix the feedback-capture process so text is real, not templated. That unlocks idea #7 and #8 from the pool below.
- Run a handful of structured exit conversations with withdrawn Senior/Lead candidates. It's the cheapest way to get at a cause that quant analysis already narrowed to two ruled-out hypotheses.
- Re-pull Referral attribution using `Applications.Referred By` (11.1%, n=27) instead of self-reported `Candidates.Source` (53.8%, n=13). The self-report field is the one that produced the "referral converts 8x better" story, and it's the less trustworthy of the two.

---

## D1 — Verdict on the VP's Two Claims

### Claim 1: "Job boards bring 26.9% of our hires, biggest channel by a wide margin"

**Verdict: Build something different. Don't scale Job Board spend; fix Job Board's screening instead.**

| Fact | Number | Source |
|---|---|---|
| Raw reading (as VP saw it) | 26.9% Job Board = 26.9% Referral, a tie | Pre-dedup count |
| Corrected reading | Job Board 33.3%, Referral 16.7% | Post-dedup, first-touch attribution |
| **The number that decides the verdict** | **Job Board hire rate = 3.0% (7/236), worst of every channel** | Referral 53.8%, Career Site 16.1%, Agency 11.4%, LinkedIn 9.7%, Campus 0% |

- Job Board is the biggest channel by hire *volume*. VP is right on that point.
- Leads on volume, not conversion: 236 applications to get 7 hires.
- Targeting problem, not a channel problem: Sales got 50 Job Board applications, 0 hires. Sales got 8 LinkedIn applications, 3 hires (37.5%) — best department/source pair with a real sample.
- 58% of all rejections (116/200) happen with zero interview logged.
- Of Job Board's pre-interview rejections, 76.2% (64/84) had a real recruiter screening call logged (`jobboard_screening_check.csv`, SQL-verified) — not captured in the Interviews table, but a real conversation happened.
- Reading: recruiters are making judgment calls on real conversations, not blind-rejecting resumes off Culture Fit/Comp Expectation labels.
- **Bottom line:** don't cut Job Board spend — top volume source, screening already works as designed.
- **Bottom line:** don't scale it blind either — 3.0% conversion is the worst in the portfolio.
- **Next step:** close the Application-Stage data gap so screening calls show up as logged interviews, then re-measure whether Job Board's funnel health is under-counted by a data gap or genuinely this weak.

### Claim 2: "Offer acceptance is ~72%, needs to move"

**Verdict: Don't build a "move the number" initiative this cycle. Build the measurement first (D3), because the current denominator is unstable.**

| Counting method | Result | Source |
|---|---|---|
| Pending counted as "no" | 72.2% (26/36) | |
| Pending excluded | 83.9% (26/31) | |
| **The number that decides the verdict** | **n = 36 offers total. An 11.7-point swing on one counting choice is bigger than any realistic intervention effect** | |

- 5 of the offers in question sat Pending 20-222 days with zero follow-up. Those aren't "still deciding," they're an ops failure counted as ambiguous signal.
- Historical monthly offer volume ranges 1-8/month, too thin for a monthly trend line to mean anything. That's why D3 specifies a rolling 3-month window, not monthly.
- **Bottom line:** VP's instinct is directionally reasonable — 72% isn't stable enough to set a target against.
- **Next step:** ship the governed metric spec (D3) and the stale-offer fix (D2 #2) before committing to any target.

---

## D2 — The 6 Engineer-Weeks

### Full ranking: all 8 ideas, one framework

**Decision rule:** rank by Impact x Confidence, gate by Effort fitting inside 6 weeks, gate again by whether current data quality actually supports the build. An idea that's high-impact but marked "not buildable against current data" in the Data Support column is disqualified this cycle regardless of score.

| # | Idea | Pool | Impact | Effort | Confidence | Data Support | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Data Accuracy Program (ID collisions, dedup detection, Stage/Status auto-derive, Filled-status validation, backfill of 34 broken records) | A | High: every other metric in this doc depends on it | Medium | High | Every sub-fix traces to a confirmed defect (34/892 records, 3.8%) | **BUILD** |
| 2 | Offer & Requisition Lifecycle Automation (stale-offer flag, req-overdue digest) | A | High: 91% of reqs (10/11) already breached target; all 5 currently-Pending offers are aged 20-222 days with no follow-up | Low-Medium | High | Both figures are exact counts, not samples | **BUILD** |
| 3 | Governed Recruiting Metrics Dashboard (acceptance rate + funnel drop-off by department/level) | A | High: VP is already asking about acceptance rate, but the same "one shaky number" problem applies to every stage of the funnel, not just offers | Low-Medium | High | Full acceptance-rate spec in D3; funnel/department/level views already built and verified in this analysis, this build makes them a live, ongoing dashboard instead of a one-off | **BUILD** |
| 6 | Smarter/agentic technical-round screening | B | High: Technical 1 rejects 65.2% (45/69) post-screen, the single biggest filter in the process, bigger than Screen itself (52.7%) | Unknown, scope undefined | Medium | Problem is real and quantified; solution shape is not defined | **NOT NOW**, needs a scoping conversation before it can be sized |
| 4 | Senior/Lead withdrawal qualitative follow-up | B | Medium: 13 withdrawals total, but withdrawal rate 6x Junior's | Low (recruiter/PM time, not eng) | Medium, two hypotheses already ruled out | Comp-mismatch ruled out (withdrawn asked for *less*, 25.3% vs 30.3%); slow-process ruled out (Lead has shortest median cycle, 14 days) | **NOT BUILD (this cycle)**, right next step, wrong list (no eng build required) |
| 5 | Notice-period-vs-acceptance leverage study | B | Low-Medium: pattern exists but thin | Low | Low | n=36 total, smallest bucket n=7; 0-15 day bucket accepts at 57.1% (4/7), which undercuts rather than supports a "leverage" story | **NOT BUILD**, insufficient signal to justify effort at any size |
| 7 | Cross-department interviewer quality audit via feedback text | B | Medium: cross-dept gap is real (lower scores, higher non-completion) | Medium | Low | Feedback field has only 12 distinct strings across 142 records, templated; 0/121 cross-dept entries show unfamiliarity language | **NOT BUILD**, data disqualifies the near-term form; fix capture process first |
| 8 | L2/L3 rejection disposition taxonomy | B | Medium: only 6 flat rejection categories today | Low (manual) / Medium (auto) | Low (auto) / Medium (manual) | Only 36.5% of rejections (73/200) have any linked feedback at all; what exists is templated | **NOT BUILD (auto version)**, manual-tagging version is a process change, not an eng build, can start independently |

### The 3 builds (6 engineer-weeks, in order)

| Order | Build | Size | The number that justifies it |
|---|---|---|---|
| 1 | **Data Accuracy Program**: auto-derive Stage/Status from Interview/Offer events, validate "Filled" requires a real Hired application, prevent Application ID collisions, one-time backfill/cleanup of the 34 already-broken records, phone-based duplicate-candidate flagging at intake (flag only, no auto-merge) | 2.5 weeks | 34 of 892 records (3.8%) already broken; 100% of Declined offers (5/5) still show Stage=Offer; 2/8 Filled openings have no Hired application |
| 2 | **Offer & Requisition Lifecycle Automation**: stale-offer auto-flag past a decision window, requisition-overdue alerts, one shared "aged past threshold, notify once" mechanism, 10 already-overdue reqs batched into a single day-one digest | 2 weeks | 91% of open reqs (10/11) past target close by 97-422 days; all 5 currently-Pending offers are aged 20-222 days with no follow-up |
| 3 | **Governed Recruiting Metrics Dashboard**: implements the D3 acceptance-rate spec exactly (all 3 reporting layers), plus makes the funnel drop-off, department, and level views in this analysis a live dashboard instead of a one-time report. Cheap to add: the underlying numbers are already computed by this project's analysis code, this build wires them up as a maintained, refreshing dashboard | 1.5 weeks | 11.7-point swing (72.2% vs 83.9%) on the same 36 offers depending on one counting choice; the current number can't be trusted to set a target. Same instability risk applies wherever else a rate is read off a small, ungoverned count |

**Total: 6 engineer-weeks.**

**Scope note:** build #2 fixes stuck offers and overdue requisitions. It does not mean these are the only broken stages. The technical interview round rejects 65.2% of candidates who already passed screening — the single biggest drop-off point in the whole process, bigger than screening itself. That problem is real and sized (see the ranking table above, idea #6), it's just not scoped yet, so it's on the not-build list this cycle, not silently ignored.

### One real risk on build #1

- Airtable can fix bad data fast once it's saved, but build #1 can't stop bad data from being entered in the first place.

### The 3 not-builds (this cycle)

| Idea | Why not |
|---|---|
| **Smarter/agentic technical-round screening** | Real problem (65.2% post-screen rejection, the biggest filter in the pipeline), but "AI screening" has no defined scope: what it screens on (resume? take-home? JD match?) isn't decided. Sizing this now would be a guess dressed as an estimate. Needs a scoping conversation with Eng first, not a blind 2-week slot. |
| **Cross-department interviewer quality audit (feedback-text mining)** | The quantitative gap is real: cross-dept interviews score lower and have higher non-completion. But the Feedback field can't support text-mining today: only 12 distinct strings across 142 non-empty records, 0/121 cross-dept entries show unfamiliarity language, cross-dept and same-dept feedback average the same word count (9.7 vs 10.1). Mining what we have would produce a confident, wrong conclusion. Fix feedback capture first, then revisit the audit once real free text exists. |
| **Notice-period-vs-acceptance leverage study** | Directionally the opposite of the "trapped candidate accepts" story (0-15 day bucket accepts *least*, 57.1%), but every bucket sits at single digits to low teens (n=36 total). Not enough volume for the study to change any decision this cycle, and no eng build is implied by the idea itself; it's an analysis task, not a roadmap item. |

**Also lost, for the record (good ideas, no room):**

| Idea | Why it lost, not why it's bad |
|---|---|
| Senior/Lead withdrawal qualitative follow-up | It's the right next step (two quant hypotheses already ruled out), but it's recruiter/PM time, not an engineering build, so it doesn't compete for the 6 eng-weeks. Recommend starting this in parallel, outside this budget. |
| L2/L3 rejection taxonomy, manual-tagging version | Same logic: a cheap process change, not an eng build. Can start now independent of this roadmap; the auto-extraction version waits on feedback-capture quality. |

---

## D3 — Metrics Spec: Offer Acceptance Rate

| Field | Definition |
|---|---|
| **Numerator** | Count of offers with status = Accepted, within the window |
| **Denominator** | Count of offers with status in {Accepted, Declined, Lapsed}, within the window |
| **Lapsed (new status, must be added)** | Offer status = Pending for > 45 days with no candidate response |
| **Excluded from numerator and denominator, shown separately** | Offers currently Pending and < 45 days old: "still deciding," not yet a rate input |
| **Time window** | Rolling 3 months, not calendar-month. Justification: historical monthly volume ranges 1-8 offers/month, so a single-month rate is noise, not signal |

### Edge cases

| Case | Rule |
|---|---|
| Multiple offers on one application | Not observed in current data. If it occurs: use whichever offer has a final decision (Accepted or Declined). Only if more than one is still Pending, use the newest one |
| Acme-rescinded offer | Not observed in current data. If it occurs, track in a separate status, don't count as Declined |
| Offer extended near the end of the reporting window | Don't mark Lapsed prematurely. The 45-day Pending clock must fully elapse inside or after the window before Lapsed applies |

### Reporting layers — not just one number

A single company-wide rate hides where the problem actually is. Report it at three levels, same formula each time, just filtered narrower:

| Layer | What it shows | Example |
|---|---|---|
| 1. Company-wide | The one headline number | "Acceptance rate: 72% (26 offers)" |
| 2. By department | Same formula, filtered to one department | "Engineering: 80% (5 offers)" |
| 3. By department + level | Same formula, filtered to one department AND one level (Junior/Mid/Senior/Lead) | "Engineering, Senior: 100% (2 offers)" |

- Layers 2 and 3 use the exact same numerator/denominator/window rules above — only the filter changes.
- This is what lets someone go from "the number moved" to "it moved because of X department" or "X level" without a separate analysis.

### Dashboard display rules

- Always show rate with n, e.g. "72% (26 offers)," never a bare percentage.
- If n < 20 in the 3-month window, auto-expand to a 2-quarter window and label the expansion.
- Still-deciding count (Pending < 45 days) shown as its own tile, never folded into the acceptance rate.
- Any breakdown (by department, by level, by source) with fewer than 10 offers is labeled small-sample directly on the tile, not in a footnote.

---

## D4 — What Would We Not Trust? (Systematic Data Audit)

### What's wrong, and how much of it

| # | Problem | Count | Base | % |
|---|---|---|---|---|
| 1 | Same person listed as two separate candidates (matched by phone number + name) | 12 records (6 pairs) | 300 candidates | 4.0% |
| 2 | One application ID number was reused for two unrelated applications | 8 records (4 IDs) | 350 applications | 2.3% |
| 3 | Candidate declined the offer, but their record still says the offer is open, not rejected | 5 | 36 offers | 13.9% of offers |
| 4 | Job is marked "filled," but no candidate record ever shows a hire for it | 2 | 8 filled openings | 25% of filled openings |
| 5 | Interview's "completed" date is earlier than its "scheduled" date | 4 | 160 interviews | 2.5% |
| 6 | Job's start date is earlier than the date the offer was made | 3 | 36 offers | 8.3% of offers |
| **Total (any of the above)** | **34 records touched** | **892 total records** | **3.8%** |

### How that changes the answers above

| Data issue | What it would have corrupted if unfixed | What we did about it |
|---|---|---|
| Duplicate candidates | Counting the same person twice under "Referral" is why Job Board and Referral looked tied for most hires in Claim 1 | We merged duplicate people (matched by phone + name) and counted each person under their first source only. With that fix, Job Board really is ahead: 33.3% vs 16.7% |
| Application ID reuse | Looking up records by the visible application ID number can quietly mix up two different people | Every lookup in this project uses Airtable's hidden internal ID instead, which is always unique |
| Declined-offer status lag | This makes the "rejected" count look smaller than it really is, and makes it look like more candidates are still active than actually are | We're fixing this in the Data Accuracy Program (D2, build #1). Going forward, the acceptance-rate calculation (D3) checks the offer's own record, not this outdated field |
| "Filled" with no matching hire | This makes Engineering look like it hired nobody (0 of 30 applications), not true. Its one filled role is just missing its "Hired" record | We added a check for this to D2's build #1. Until it's fixed, don't take department hire-rate comparisons at face value, Engineering's included |

### Signals that looked promising, and what checking them found

| Signal | Looked like | Data check | Verdict |
|---|---|---|---|
| Cross-department interviewer feedback text | Might explain why interviews across departments score lower | None of the 121 cross-department feedback notes mention being unfamiliar with the role. The notes are also the same length either way (9.7 words vs 10.1 words) | The score and no-show gap is real and confirmed by the numbers, but the feedback text doesn't explain why. Don't say interviewers "admit" they're out of their depth. They don't, in this data |
| Interview feedback notes in general | Looked like a good source for the real reasons behind rejections and screening decisions | Only 12 different sentences appear across 142 filled-in records. One of them repeats word-for-word 3 or more times. This looks copy-pasted, not written by a real person each time. Only 36.5% of rejections (73/200) have any feedback linked at all | Worth doing eventually, but not with this data. Needs checking against Acme's live system, where people type their own notes |
| Candidate-reported referral source ("referral converts 8x better") | Candidates who said they came from a referral got hired 53.8% of the time (7 of 13), versus 7-11% for everyone else. Looked like a big win for referrals | Acme also tracks the actual employee who referred someone, in a separate field. That field tells a different story: 11.1% hired (3 of 27) with a named referrer vs 7.1% (23 of 323) without one, barely different. The two fields only agree on 3 of the 13 self-reported cases | Don't trust the self-reported number. Use the actual-referrer field (`Applications.Referred By`) for any decision about the referral program, not the self-reported one (`Candidates.Source`) |
| Senior/Lead withdrawal, pay theory | Theory: candidates withdraw because the pay offered was too low | Candidates who withdrew actually asked for a smaller raise (25.3% on average) than the ones who got hired (30.3% on average), the opposite of what the pay theory predicts | Ruled out |
| Senior/Lead withdrawal, slow-process theory | Theory: candidates withdraw because hiring takes too long | Lead-level hiring is actually the fastest of any level (14 days, the shortest median), yet Lead has a high withdrawal rate | Ruled out |
| Notice period as leverage ("a long notice period lets candidates shop competing offers") | People who accepted offers had a longer notice period on average (47.3 days) than people who declined (30.0 days), which seemed to support the theory | Split by notice length: people with 0-15 days notice accepted least often (57.1%, 4 of 7). People with 16-90 days notice accepted 80-100% of the time. That's the opposite of "a long notice period traps you into accepting." Only 36 offers total, and the smallest group is just 7 people | Not solid enough to act on. Don't build a story around a group of 7 people |
| Offer pay vs. posted salary band | Could mean pay is routinely set outside the approved range | 29 of 36 offers (80.6%) fall inside the approved range. 7 fall outside (4 above, 3 below). 2 are extreme: 161% and 256% over the top of the range | Worth asking about those 2 extreme cases directly. This isn't a company-wide pattern, so no fix needs to be built |

### Structural data-quality problems, independent of any single metric

| Problem | Number | What it means for trust |
|---|---|---|
| How often the interviewer works in the same department as the job | 14% (22/160) | Interviewers, recruiters, and hiring managers are mostly assigned to jobs outside their own department. It looks close to random. Because of this, don't compare one department's hiring quality to another's using these fields — the mismatch itself could be the reason for any difference you see |
| How often the recruiter works in the same department as the job | 23% (80/350) | Same as above |
| How often the hiring manager works in the same department as the job | 12.5% (3/24) | Same as above |
| How often the recruiter and interviewer are the same person on one application | 0% (0/160) | Recruiter and interviewer are always two different people, by design, not a data-entry error |

### Bottom line for D1/D2/D3

- Every number behind Claim 1 and Claim 2 holds up, because we recalculated them after fixing duplicates and using unique internal IDs. The raw, unfixed numbers (the 26.9% tie, the unadjusted 72%) would not have held up.
- The acceptance-rate calculation (D3) checks the offer's own record, not the application's separate progress field — we confirmed that progress field is wrong on 100% of declined offers.
- D2's first build item exists because 34 of 892 records (3.8%) is the minimum we found here. A live, growing dataset would likely show more problems, not fewer.
