# Handoff: System Public Challenge, Visualize 3

Written 2026-11-13 so work can continue on another laptop. Paste or point a new Claude session at this file.

## The event

- System Public Challenge, NYC, November 13 to 14, 2026.
- Challenge doc: https://docs.google.com/document/d/1PZon0PcNrHA3gYPsYsRGbOJk0SqUY9Nq70vCYNLwK6s/edit
- Chosen challenge: **Visualize 3. Which common medications make heat more dangerous, and what should prescribers and health systems do about it?**
- Challenge owner: Chethan Sarabu, MD, Cornell Tech.
- Deliverable: a visual evidence map of heat-sensitive medications grouped by type of action, showing evidence strength, the prescribers involved and gaps in current guidance. Audience: clinician, pharmacist or public health official planning heat-wave counseling.
- Action buckets named in the brief: dose adjustment, substitution or temporary holding, closer monitoring, storage and stability.
- Optional extras in the brief: wearables evidence, NYC map of heat exposure and prescriptions.
- Unknown: whether prizes are per challenge, per track or overall. Ask on site.

## System Public Graph: what we learned from the docs

Docs index: https://docs.system.com/system/llms.txt (append `.md` to any docs URL for markdown).

- Base URL `https://public-api.system.com`, header `x-api-key`, 10,000 requests per day.
- Five tables: relationships (concept pairs with `num_studies`, `num_findings`), associations (the findings: statistic type and value, CI, p-value, two variables, `pubmed_id`), variables, concepts (Wikidata grounded), studies (`doi`, `pubmed_id`, free-text `population`, `study_type`).
- Missing fields: country, sample size, direction of effect, study date. Dates need a PubMed lookup by `pubmed_id`.
- System says about 20% of API associations are extracted wrong. They recommend dropping any association not in the Dataverse CSV: https://doi.org/10.7910/DVN/7V6JDO (CC-BY-NC 4.0). The Dataverse set is narrower than the API.
- Findings are pairwise. "Drug X makes heat worse" is a three-way claim, so direct evidence is expected to be thin.
- Demo notebooks (landscaping, synthesis, hypothesis generation): https://docs.system.com/system/public/demo-examples

## What we learned by using the API

- **The API refuses bursts.** Eight parallel requests made most calls fail after the first dozen. Send one at a time.
- Concept search by exact Wikidata label works. Confirmed present with relationship counts: diuretic (348), furosemide (178), hydrochlorothiazide (122), spironolactone (139), beta blocker (418), propranolol (240), ACE inhibitor (582), losartan (129), anticholinergic (171).
- Everything else in the first full run came back empty because of the burst refusals. Those zeros are false. Do not trust them.
- Variable name search works and heat evidence is rich at the variable level. Examples returned:
  - "risk of death (among patients with nonexertional heatstroke during a heat wave)"
  - "ED visits for AKI during the warm season with ambient temperatures above 22.3 °C"
  - "heat-related hospitalization among older patients with chronic conditions"
  - "hospitalization for heat-related illness in children"
- Variable search looks ranked, not filtered: `total` is always 5,654,715 whatever the query.
- Working conclusion: go in through variable names, then pull each variable's associations. Concept pairs alone will miss a lot.

## Strategy

Three tiers of evidence per drug class, used as the visual encoding:

1. **Direct:** the graph links the drug to a heat outcome.
2. **Bridged:** the drug links to a mechanism (hyponatremia, dehydration, acute kidney injury, reduced sweating, lithium toxicity) and heat links to the same mechanism.
3. **Gap:** guidance names the drug and the graph has nothing.

Hero visual: a grid. Rows are drug classes, columns are the four action buckets, cells shaded by tier and strength, with a specialty filter. Clicking a cell shows the studies and one plain-language line on what a prescriber might change.

Second grid: drug class against guidance source (CDC, UKHSA, WHO Europe, Health Canada, Australia). Cell is a specific action, a mention, or absent. The mismatches between the grids are the headline findings.

Things that should set the entry apart:

- Hand-check every finding shown against its abstract and badge it, given the 20% error rate.
- Publish a simple strength rubric: number of studies, study type mix, whether the CI excludes null.
- Treat the storage bucket honestly. The graph likely has little on drug stability. Show it as a gap and fill from drug labels, marked as non-graph.
- Skip the NYC prescription map unless well ahead.

Order of work:

1. Finish the coverage probe (in progress, see below).
2. Pull associations, filter against the Dataverse CSV, add dates from PubMed.
3. Build the guidance matrix by hand. Can run in parallel with a teammate.
4. Build the grid, then verify the findings on it.
5. Day two: three headline mismatches, small wearables panel, demo rehearsal.

## State of the probe

- Script: `coverage_probe.py` in this folder. Standard library only, Python 3.
- Run 1: left no output. Probably interrupted; the script printed nothing until late.
- Run 2: finished, 533 requests, results invalid because of burst refusals (see above).
- Run 3: started on the first laptop with the fixed script (one request at a time, retries, failures labelled ERROR, progress every 50 requests). **Not confirmed finished when this file was written, and the fixed script had not been tested before that run.** Expected 15 to 25 minutes and about 3,300 requests.
- **Run 3 was going very slowly at handoff.** Several minutes in, the cache held only 28 responses (12 of them from earlier runs) and the log was still empty. So most requests were still failing and being retried even at one at a time. Cause not diagnosed. Candidates: a stricter per-minute limit than expected, the daily quota being counted differently than the docs say, or slow search endpoints. The `concepts.json` and `links.csv` in `probe_results/` are leftovers from the invalid run 2.
- First thing to do on the new laptop: run one request by hand and read the status code and time.

  ```bash
  source ~/.system_public_env && curl -s -o /dev/null -w "HTTP %{http_code} in %{time_total}s\n" -H "x-api-key: $SYSTEM_API_KEY" "https://public-api.system.com/v1/concepts?search=wikidata_label:lithium&limit=3"
  ```

  429 means rate limited (slow the script down: raise `MIN_GAP`). 403 means a key or quota problem (ask the System team on site). 200 but slow means cut the probe down to the variable route only (sections 5 to 7).
- If the API stays unusable, fall back to the Dataverse CSVs and do the same analysis locally.
- Output goes to `probe_results/probe_output.txt`. Extra files when complete: `concepts.json`, `links.csv`, `heat_drug_findings.csv`.
- Responses are cached in `cache/`. Copy that folder too and a rerun on the new laptop costs few new requests.
- Daily quota is per key, so both laptops draw on the same 10,000.

## Update, second laptop (2026-11-13): switched to the Dataverse release

The API key was not set up on this laptop, so the probe was not rerun. Instead the full Dataverse release was downloaded to `dataverse/` (5 CSVs, 1.1 GB, all SHA-256 checksums match `MANIFEST.json`). It holds 2.0M associations, 840k concept relationships, 1.77M variables, 844k studies and 46k concepts. These are the rows System vouches for, so no 20% error filter is needed and there's no rate limit.

- New script: `local_analysis.py`. Standard library only, about 2.5 minutes, no key: `python3 local_analysis.py`
- It replaces `coverage_probe.py` as the main analysis. The probe is still useful for spot checks once a key is set up. `probe_results/concepts.json` and `links.csv` are still the invalid run-2 leftovers. Ignore them.
- Outputs in `probe_results/`:
  - `local_output.txt`: full report
  - `local_summary.json`: one row per drug class with its tier
  - `local_heat_drug_direct.csv` and `local_heat_drug_modifier.csv`: direct evidence
  - `local_heat_mechanism.csv`: 235 heat × mechanism findings, the heat half of the bridge
  - `local_drug_mechanism.csv`: drug class × mechanism study counts
  - `local_concept_pairs.csv`: concept-level relationship counts
  - `local_heat_variables.txt`: the 1,365 variables classed as heat, for eyeballing the regex
- Filters added after reading the first pass. These rows were matching as "heat" or "drug" but are not climate heat × medication: heat-pain lab tests (hyperalgesia, detection and tolerance thresholds), drug residues in wastewater, ACE genotype, hypnosis, insulin as a hormone, heat-shock proteins, TCM "damp-heat" and "heat-prescription".

### Findings

**Direct evidence is almost absent, as expected.** Only 4 studies link a medication to a heat outcome:

| PMID | Finding | Bucket |
|---|---|---|
| 17698677 | Long-term antihypertensive use → mortality among heatstroke patients, HR 2.17 (1.17–4.05) | monitoring |
| 31842287 | "Persons under medication" → heat illness, aOR 3.09 (1.15–8.29) | monitoring (class unspecified) |
| 36418530 | Starting irbesartan/HCTZ or another antihypertensive in the warm vs cold season changes the BP response (difference 7.0 mmHg, 4.7–9.3) | **dose adjustment**: the only seasonal-dosing evidence |
| 37897873 | Daily ambient temperature → opioid overdose, OR 1.079 (1.054–1.106); ED visits for opioid use, OR 1.041 | monitoring |

There was one more, filtered out because it isn't ambient heat. Keep it by hand for the **storage/handling** bucket: PMID 15101888, where heat applied to a transdermal fentanyl patch raises plasma AUC by about 30%.

**Concept level:** in the relationships table the only drug × heat pairs are ACE inhibitor–"hot" and opioid–"hot", 1 study each.

**The bridge carries the map.** Heat reaches each mechanism in this many studies: AKI 15, impaired sweating/thermoregulation 20, hypotension/falls 5, dehydration 3, glucose 3, rhabdomyolysis 2, hyponatremia 1. Lithium toxicity: 0. Drug classes reach those mechanisms as follows (distinct studies):

- Diuretics: AKI 86, hyponatremia 74, hypotension 18
- ACE inhibitors/ARBs: AKI 96, hyponatremia 36, hypotension 30
- SGLT2 inhibitors: glucose 57, AKI 54, hyponatremia 13, dehydration 3
- NSAIDs: AKI 50
- Opioids: hypotension 38, AKI 17
- Antidepressants: hypotension 30, hyponatremia 14
- Benzodiazepines: hypotension 29
- Antipsychotics: hypotension 17, glucose 10; impaired sweating only 1
- Anticholinergics: hypotension 12; **impaired sweating 0**
- Lithium: AKI 3; **lithium toxicity not in the graph**
- Insulin and other diabetes drugs: glucose 102 / 143

### Headline mismatches emerging (check them against the guidance matrix)

1. **Anticholinergics and antipsychotics** are the classes every heat guidance names, for impaired sweating. The graph has almost no drug → sweating evidence (0 and 1 studies). This is a gap.
2. **Lithium** is flagged by all guidance. The graph has no lithium-toxicity concept and only 3 AKI studies. Fill it from drug labels and mark it as non-graph.
3. **Opioids** have the strongest direct heat signal (overdose rises with temperature), yet heat guidance rarely lists them.
4. **Dose adjustment** has a single study behind it (36418530, seasonal BP response). The rest of that bucket is bridge or label evidence.
5. **Storage**: nothing in the graph except the fentanyl patch study. Expected.

Caveats: bridged counts are drug → mechanism studies in any setting, not heat-specific. The mechanism groups are matched by regex on variable names, so the counts are indicative. Check the shown studies by hand.

### Evidence grid (built 2026-11-13)

- Live page (private until shared): https://claude.ai/artifact/CqsXxVwScVfLynPtSyrnkb
- To rebuild: `python3 local_analysis.py && python3 build_grid.py` writes `grid/grid_data.json` and `grid/heat-med-map.html`. Edit the layout in `grid/template.html`. Edit the drug classes, the action wording and the direct-study mapping in the `CLASSES` and `DIRECT` dicts in `build_grid.py`. Then republish the page to the same URL.
- Each cell is graded on its **main mechanism**, the first one listed. With supporting mechanisms counted, every class looked bridged and the sweating gap disappeared.
- The action wording is a draft and needs clinician review. All studies are badged "unchecked".
- Grid tiers: 8 direct, 17 bridged, 3 partial (all lithium), 8 gap (anticholinergics ×2, antipsychotic / beta-blocker / benzodiazepine "hold", stimulants monitoring, insulin and emergency-product storage).

### API pull (2026-11-13, after the key was set up)

- The API works: HTTP 200 in 0.1 to 0.9 s. Sequential requests 0.25 s apart caused no refusals. Run 3's stall was never reproduced.
- The API has **5,944,001 findings against 1,999,877 in Dataverse**, and 5.65M variables against 1.77M. At the concept level Dataverse is complete: 840k relationships against 626k in the API.
- A full dump isn't possible: `offset` beyond about 100k returns HTTP 504. But `search=name:<term>` with `limit=5000` returns **every** matching variable, and `filter=variable_1_id:a||b||...` batches 25 IDs per request.
- Script: `api_pull.py` (`source ~/.system_public_env && python3 api_pull.py`). It used 534 requests, none failed, all cached. It pulls every heat variable (3,372, of which 2,143 are not in Dataverse) and every variable for sweating/thermoregulation, lithium levels, dehydration and sodium (2,068). It then fetches all 9,214 associations touching them: 3,589 vetted, 5,625 API-only.
- Output: `probe_results/api_findings.csv`, each row flagged `in_dataverse`.
- `build_grid.py` merges these rows. API-only evidence is counted separately ("+N unvetted"), and a cell whose grade depends on it gets a dashed border. New direct studies (API-only) are curated by hand in `DIRECT`/`UNVETTED`: 29020197 (antipsychotics → heat injury, HR 3.25), 17513091 (psychotropics → heat admission, 2003 France), 31205291 (fatal opioid overdose), 37897873 amphetamine rows, 14622685 (fentanyl patch + heat), 24334574 (oral glucose-lowering drugs, direction unclear), 11434495 (number of medications, null).
- The drug side was **not** pulled from the API for AKI, hypotension or glucose. Dataverse is already rich there.
- Grid now: 13 direct (5 of them only via unvetted rows), 15 bridged, 3 partial (lithium), 5 gap.

### Weak-spot fixes (2026-11-13, evening)

**Recall test** (`recall/`): a PubMed title search for heat × medication gave 227 papers. 57 were screened as relevant. Only 18 have any findings extracted in the graph, so older case reports and reviews exist as titles only, a coverage limit of the graph itself. Of the 13 in scope (cocaine and self-harm excluded), the old search found 2. **It now finds 10 of 13.** The 3 still missed name no drug in any extracted finding.

Why the misses happened, and the fixes (in `local_analysis.py` and `api_pull.py`):
1. **The heat was in the study context, not in any variable.** For example, PMID 20104062 is "psychotropic use → death" during the 2003 heat wave, and its population string doesn't mention heat. Fix: a PubMed seed of 1,934 papers with heat and a medication in the title or abstract. 148 have findings, and their drug findings count as heat-context evidence (`heat-context-drug`).
2. **The drug was in the population** ("adults who use insulin") with a heat → outcome finding. Fix: the `heat-drug-population` route.
3. **Wording.** Added heat terms (outdoor/daily/mean/maximum temperature, ambient heat, local skin heating, heat dome…) and drug terms (DACE, drug-induced, anxiolytic, insulin absorption…). API heat variables went from 3,372 to 4,828.

**Bridge clean-up:** the drug must be the exposure (variable 1, 96% of rows) and the mechanism the outcome. Dropped 193 reversed rows (condition → prescription) and 31 rows from animal or poisoning populations. Most counts fell 5 to 15%; "Medication (unspecified)" → AKI fell 65 → 38. Lithium levels are special-cased, since the mechanism names the drug.

**Curated direct studies now in the grid** (`DIRECT`, `UNVETTED`, `NULL_DIRECT`, `EXTRA_DIRECT` in `build_grid.py`):
- 20104062 (vetted): 2003 heat wave, antipsychotics → death OR 2.09, antidepressants OR 1.71. Anxiolytics OR 0.85 (API-only).
- 38060348 (vetted): heat → serious hypoglycaemia in insulin users, OR 1.14 to 1.38.
- Lithium: 25163443 (p = 0.08) and 31782314 (r = 0). **Studied, no clear effect.** That replaces "never studied".
- 27160370 (API): anticholinergics in heat waves, death OR 1.21 p = 0.31, longer stay.
- 29116624 (vetted, null): triple whammy → AKI during heat waves, OR 1.02.
- Also 37369523, 16911573, 34338579, 37280056, 7010077, 22538141, 35564355, 28737683, 28796021.
- Direct cells now show the effect direction. Null direct results are outlined, not filled.

Grid now: 23 direct (5 rely on unvetted rows, 5 are "no clear effect"), 8 bridged, 1 partial, 4 gap.
API usage today: about 1,300 requests in all.

### Next steps (replaces the list at the bottom)

1. Hand-check the 4 direct studies and the strongest bridge studies per cell (PMIDs are in the CSVs). Badge each one.
2. Build the guidance matrix: CDC, UKHSA, WHO Europe, Health Canada, Australia.
3. Build the grid (drug class × action bucket, shaded by tier) from `local_summary.json` + `local_drug_mechanism.csv`.
4. Optional: once a key is set up, use the API (`coverage_probe.py`, sections 5 to 7) to see whether the full API graph adds direct findings beyond the Dataverse subset.

## Setup on the new laptop

The API key is not in this folder. It lives in `~/.system_public_env` on the first laptop. Recreate it:

```bash
read -s "k?Paste key: " && echo "export SYSTEM_API_KEY=$k" > ~/.system_public_env && chmod 600 ~/.system_public_env && unset k
```

Then run the probe from this folder:

```bash
source ~/.system_public_env && python3 coverage_probe.py
```

## Next steps for whoever picks this up

1. Read `probe_results/probe_output.txt`. Check the failure tally on the last lines. Any ERROR rows mean rerun.
2. From sections 2, 3 and 7 of the output, decide which drug classes have direct evidence and which rely on the bridge.
3. Open `heat_drug_findings.csv` and hand-check the PubMed IDs.
4. Start the guidance matrix.

## Guidance + label lenses (2026-11-14, morning)

- `guidance.json`: CDC clinician page (2025-09-18) and NYC DOH provider page, hand-coded per class (action / mention / storage / absent). NYC copies the CDC table. Neither gives a class-specific clinical action except sun protection for photosensitisers.
- ADAPT-HEAT / CALOR (PMC13305179) is a **protocol only**; the heat-PIM list is not published (study ends Dec 2026). WHO HHAP PDF returned 403: not reviewed.
- `label_pull.py` → `probe_results/fda_labels.{json,csv}`: openFDA labels for ~50 drugs, every manufacturer label. Splits environmental heat warnings from drug-induced hyperthermia (serotonin syndrome / NMS lists) and from dehydration-only warnings. Cached in `cache_fda/`.
- `build_lenses.py` → `grid/lenses_data.json` + `grid/lenses.html` (template `grid/lenses_template.html`). Per-class pattern and one-line finding are hand-written in `FINDINGS`.
- Patterns: 5 missed by guidance (insulin, SGLT2, metformin/SU, opioids, stimulants), 6 labels silent (diuretics, ACEi/ARB, beta blockers, CCB, NSAIDs, benzos), 3 over-warned vs evidence (anticholinergics, lithium, topiramate), 2 agree (antipsychotics, antidepressants), 1 storage.
- Not yet merged into the main map page.
