# Process log

Chronological record of what was done, why, and what came out. Newest entry at the bottom.
Each entry: date, what we did, what we decided, files touched, findings added (by F-number from `FINDINGS.md`).

## 2026-11-13 — Session 1: understand the challenge and the data

**Goal.** Understand Visualize Challenge 3 (medications and heat) and what the System Public Graph holds for it.

**Steps**
1. Read the challenge brief. Deliverable: a visual evidence map of heat-sensitive medications grouped by action
   (dose adjustment, substitution/holding, monitoring, storage), with evidence strength, prescribers involved, and
   gaps against published heat-health guidance.
2. Read the System Public docs (overview, data dictionary, API reference, limitations). The API needs a key we do not
   have, so we used the public Dataverse snapshot instead.
3. Downloaded the five files (1.1 GB) to `data/raw` and loaded them into SQLite (`scripts/load_sqlite.py`). → F1, F2
4. Listed heat-related concepts, found grounding too noisy to rely on, and switched to matching on variable names.
5. Wrote name patterns for heat (two tiers) and 24 medication classes (`scripts/heat_meds_lib.py`), scanned all
   findings (`scripts/heat_meds.py`), and read every direct match by hand. → F3, F4, F5, F6, F10
6. Counted what heat links to and what each drug class links to across eight hand-picked mechanisms
   (`scripts/pathways.py`). → F7, F8
7. Built `data-explainer.html` (dataset structure and coverage charts) from `scripts/build_explainer.py` and
   `scripts/explainer_template.html`.
8. Built `graph-explainer.html`, a node-and-edge diagram of one real path (diuretic → acute kidney injury ← heat).
   Its edge data is hand-copied from SQL output, not generated. → F9, F12
9. Ran a data-driven inventory of concepts on the drug side, the heat side and in between (`scripts/bridges.py`),
   written to `reference/`. Curated a keep/drop list of bridge concepts. → F11
10. Wrote this documentation set and `AGENTS.md`.

**Decisions**
- Work from the Dataverse CSV, not the API (no key; the CSV is also the recommended accuracy filter).
- Detect drug and heat ends by variable name; use concepts only for the middle node.
- Frame the project as a two-hop map (drug → effect ← heat) with the missing direct link shown as a gap.
- Keep `data/` out of git; keep small derived reference tables in `reference/`.

**Not done / carried forward**
- Detailed plan for the visual has not been made yet.
- No paper metadata (title, year, abstract) fetched.
- No guidance documents collected.
- Bridge curation not reviewed by anyone with clinical expertise.
- Nothing committed to git yet.

## 2026-11-13 — Session 1 (continued): brainstorm for the visual

**Goal.** Generate concept directions for the deliverable before detailed planning. No decision made yet.

**Ideas put to the user** (short names used in conversation)
1. *The Medicine Cabinet* — the viewer builds one patient's drug list and watches pathways converge on shared effects.
2. *The Body Map* — pathways drawn on a body: drugs enter one side, heat the other, meeting at organs.
3. *Guidance vs Evidence quadrant* — every drug class placed by evidence strength and guidance coverage.
4. *The Studies Nobody Ran* — missing direct links ranked by how much they matter.
5. *Heat-wave clock* — actions laid out before / during / after a heat alert, by specialty, as a printable card.
6. *Subway map* — drug lines, effect stations, unbuilt track for missing evidence.
7. *Evidence replay* — how the evidence accumulated over time (needs publication years fetched).

**Assistant's recommendation.** Combine 1 + 2 as the main interactive, 3 as the headline result, 5 as the take-away
artefact, 4 as the closing slide. Awaiting the user's reaction, plus time left, team skills, and judging format.

## 2026-11-14 — Session 1 (continued): hackathon stance, API key, API harvest

**User direction**
- Thin evidence is not a reason to leave things out. This is a hackathon proof of concept; the primary goal is to
  impress the judges; bold claims are fine as long as they are grounded. Added to `AGENTS.md` as "Hackathon stance".
- Keep a note of anything potentially inaccurate. Created `docs/CAVEATS.md` (C1–C14).
- User supplied an API key and asked for it to be stored and used. Stored in `.env` as `SYSTEM_API_KEY`;
  `.env` added to `.gitignore`. The key value is not written in any doc.
- Links supplied by the user (both the same URL, given as "documentation" and "data docs"):
  https://docs.system.com/system/public/v1.0-api-documentation

**Steps**
1. Tested all five list endpoints with the key. The API is about 3x the size of the CSV. → F13
2. Re-read the API documentation for filter/search/sort syntax; probed real behaviour (see `DATA.md`, "Live API"). → C12
3. Wrote `scripts/api_harvest.py`: name-search 31 heat terms, keep variables passing our heat patterns (4,282),
   pull every finding for each, tag each row by whether it is also in the CSV. → F13, F14, C9
4. Read all 47 API-only heat × medication rows by hand. → F14, F19
5. Checked four key papers against PubMed abstracts via NCBI efetch. → F15, F16, F17, F18, C10, C11, C14
6. Updated `AGENTS.md`, `DATA.md`, `MAPPINGS.md` (bucket table), `FINDINGS.md`.

**API quota used:** about 4,400 of 10,000 requests on 2026-11-14 (4,314 by the harvest; responses are cached in
`data/api/cache/`, so re-runs cost nothing).

**What changed in our understanding**
- The direct path is no longer near-empty for the classes the brief names: anticholinergics and antipsychotics have a
  strong heat-wave case-control result, insulin has an absorption result, and hyponatremia has a temperature result.
- Each of the brief's four action buckets now has at least one grounded direct finding.
- Single extracted rows can be mislabelled or wrong; the abstract is the arbiter.

**Carried forward**
- Brainstorm ideas are still open; no direction chosen.
- Drug → effect arms have not been harvested from the API (CSV only).
- Guidance documents, prescribing data and specialty mapping still to be collected.
- Nothing committed to git.

## 2026-11-14 — Session 2: recover the session, re-explore the data hands-on

**Context.** Session 1 ran on an API account and stopped on "credit balance is too low" before answering the user's
last request (a second brainstorm with new pillars). The user switched to a Pro account, where session 1 is not
listed. The transcript was found on disk and read; this session continues from it.

**User direction (carried over from the unanswered message, and from this session)**
- Core pillars: comprehensiveness, clarity, explainability, and trust. A story must be easy to tell while presenting.
- Think bigger than a visualization: a full application people can click through, with a chatbot, live refreshes, and
  the ability to query the actual papers and synthesize explanations on demand.
- Do not rely on the transcript alone: re-explore the data before brainstorming.

**Steps**
1. Re-read all docs, the scripts and the tail of the session 1 transcript.
2. Inspected the schema and sample rows; listed concept-level neighbours of the core heat concepts.
3. Read all 46 direct and the 228 proxy heat × medication rows in `data/derived/heat_med_findings.csv`, and the 47
   API-only rows in `data/api/heat_med_api.csv`.
4. Re-scanned all 1,999,877 findings with the library patterns (3 min), keeping every heat row (3,084) and every
   drug-class row (110,012) in a scratch file outside the repo. Read the heat arm of each pathway; counted drug arms
   by class × effect and by direction. → F24, F25
5. Profiled heat studies by place and population. → F27
6. Applied the drug patterns to study population strings of heat rows. → F21, F22, C19
7. Checked nine more abstracts through PubMed efetch. → F21, F23, F26, C15, C16, C17, C21
8. Confirmed the live API still answers with the stored key.
9. Updated `FINDINGS.md` (F21–F28), `CAVEATS.md` (C15–C21), `MAPPINGS.md` (bucket table, third route, direction),
   `DATA.md` (quirks 8–9).

**Decisions**
- Treat "drug in the population" as a third route to direct evidence.
- Bridge thickness must be direction-aware, not a raw study count.
- No scripts were added to the repo; the exploration script lives in the session scratchpad. Fold the population
  route and direction counts into `scripts/` when the build starts.

**API quota used:** 1 request to the System API. About 3 NCBI efetch calls (not counted against the quota).

**What changed in our understanding**
- Insulin now has a large, verified, direct heat finding (2M users), which makes the dose-adjustment bucket strong.
- Two rows we had as leads are mislabelled (hyponatremia OR 1.76; potassium RR 1.33). Both papers still say
  something usable, in different words.
- The wearable question has a clear answer from the graph: plenty of lab physiology, nothing with medications.

**Carried forward**
- Brainstorm round 2 presented to the user in chat (application concepts); no direction chosen yet.
- A chatbot inside the app needs a model the app can call. The API account has no credit; options are a funded API
  key or a published Claude artifact that can ask Claude itself. Not decided.
- Guidance documents, prescribing data and specialty mapping still to be collected.
- Nothing committed to git.
