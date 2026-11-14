# Data foundation strategy: heat × medication evidence map

Written 2026-11-14 (day two). It works from the challenge brief down to every dataset the deliverable needs. Every source below was probed today, and its status is stated. Nothing here is from memory unless it says so.

---

## 1. The brief, broken into requirements

| # | The brief asks for | Data needed | Where it comes from | Status |
|---|---|---|---|---|
| R1 | Evidence linking medications to heat-related outcomes, **from the System Public Graph** | Findings where a drug (class) meets a heat exposure or a heat outcome | Graph: Dataverse (vetted) + API (unvetted) | **Done**: 23 direct, 8 bridged, 1 partial, 4 gap cells |
| R2 | Organised into 4 action buckets | A mapping from evidence → action type (dose / hold / monitor / storage) | Hand curation, informed by labels and guidance | Done in draft; actions not yet sourced |
| R3 | **How strong** the evidence is, per bucket | A typed evidence rubric that ranks different kinds of evidence | Section 2 below | Partly done (tiers); **needs one rubric across evidence types** |
| R4 | **Which prescribers** are most involved | Real prescribing share by specialty per class | CMS Part D by Provider and Drug (`Prscrbr_Type`) | **Not done**. Specialties are currently assumed by hand |
| R5 | **What a prescriber might reasonably change**, before and during a heat wave | Sourced actions with timing | Labels (dosing, warnings), guidance, sick-day rules, Beers | Draft text; needs a source on every action |
| R6 | Compare against heat-health guidance **globally** | Coded guidance matrix: source × class × action | Agency pages and PDFs | **6 coded, 4 blocked** (section 4) |
| R7 | Highlight where guidance is **missing or out of step** | Joins R1/R3 against R6 | Derived | Done for US sources plus labels; extend to the global set |
| R8 | Wearables: what research exists, **where it runs out** | Evidence ladder with counts at each rung | Graph + PubMed + physiology literature | **Probed today** (section 6) |
| R9 | Optional: NYC heat exposure × prescriptions | ZCTA heat vulnerability + ZCTA prescribing + outcomes | NYC Open Data, NYC EHDP, CMS Part D, CDC PLACES | **All endpoints confirmed live** (section 7) |

The two biggest weak spots right now are **R3** (no single strength scale across evidence types) and **R4** (prescribers are assumed, not measured).

---

## 2. Evidence types: the core of the foundation

These sources hold different *kinds* of knowledge. Each answers a different question and deserves a different weight. Every evidence item gets typed, so the page never mixes a heat-wave cohort with a label sentence.

| Code | Evidence type | What it can show | Source | Status / volume |
|---|---|---|---|---|
| **E1** | Heat-exposure epidemiology | Drug users are harmed more in heat (heat waves, daily temperature, heatstroke cohorts) | Graph direct (type H) | 18 cells, ~20 papers |
| **E2** | Seasonal analogue | Effect differs summer vs winter (BP, potassium, hypoglycaemia) | Graph direct (type S) | 4 papers |
| **E3** | Experimental heat / PK | Heat changes drug absorption or delivery (patch, insulin site, pump) | Graph direct (type X) + PubMed | 4 papers |
| **E4** | Mechanism bridge | Drug → mechanism and heat → same mechanism, in separate studies | Graph | Done; counts per class × mechanism |
| **E5** | Physiology lab (new) | Drug alters thermoregulation under controlled heat (beta blockers: blunted HR/skin blood flow; anticholinergics: sweat suppression) | PubMed (MeSH) | **403** beta-blocker × thermoregulation papers; **69** anticholinergic × sweating × heat. Not yet pulled |
| **E6** | Pharmacovigilance (new) | Heat illness reported *with* the drug; seasonality | FAERS via openFDA `drug/event` | **3,850** reports (heat stroke, heat exhaustion, heat illness, anhidrosis, hypohidrosis). Clear summer peak: Jul 541, Aug 602 vs Feb 185 |
| **E7** | Regulatory label | What the manufacturer must warn about; storage limits | openFDA `drug/label` | **Done**: ~50 drugs, every manufacturer label |
| **E8** | Guidance / consensus | What agencies tell clinicians | Section 4 | 6 sources coded |
| **E9** | Case reports | Drug-associated heat stroke, mostly 1970s–2000s | PubMed seed (1,934 papers); the graph holds titles only | Seeded, not counted per class |

### One strength scale across types (proposal)

Grade each **cell** (class × bucket) on its best evidence, and keep the type visible next to the grade:

| Grade | Meaning | Qualifies |
|---|---|---|
| **A** | Measured in people in heat, with a significant effect | ≥1 vetted E1 study with CI excluding null, or ≥2 consistent E1/E2 studies |
| **B** | Measured, but limited | One unvetted E1; E2 or E3 only; or E1 null where power is low |
| **C** | Plausible by mechanism or signal | E4 strong/moderate, or E5 physiology, or an E6 disproportionality signal (ROR lower CI > 1) |
| **D** | Expert statement only | E7 label or E8 guidance with no study behind it |
| **0** | Nothing | — |

Separate flags, never folded into the grade: **direction** (raises / null / lower / unclear), **vetted** (Dataverse vs API-only), **hand-checked** (yes/no), **population** (older adults, workers, children).

---

## 3. Data model: one long table of typed evidence items

Everything joins on the **drug**, so build one crosswalk and one evidence table.

**`drug_xwalk.csv`**: one row per ingredient
`ingredient, rxcui, atc_code, fda_epc_class, our_class, graph_concept_ids, partd_generic_names`
(RxNorm/RxNav and the openFDA `openfda.rxcui` / `pharm_class_epc` fields supply most of this. This is what lets graph concepts, labels, FAERS, Part D and guidance line up without hand matching.)

**`evidence_items.csv`**: one row per piece of evidence
`item_id, class, ingredient?, bucket, evidence_type (E1–E9), source_id (pmid / set_id / guidance id / faers query), finding_text, statistic, value, ci_lo, ci_hi, p, direction, population, vetted, hand_checked, checked_by, url`

**`guidance_items.csv`**: one row per source × class
`source_id, jurisdiction, date, class, level (action / monitor / mention / storage / absent), action_text, bucket, names_specific_drugs (Y/N), cites_evidence (Y/N)`

**`actions.csv`**: what a prescriber might change
`class, bucket, when (before / during / sick day / after), action_text, source_ids, evidence_grade`

The page then reads only these four tables. `grid_data.json` becomes a build product of them.

---

## 4. Global guidance: inventory and early coding

### Status

| Source | Jurisdiction | Date | Status | Notes |
|---|---|---|---|---|
| CDC Heat & Medications, clinicians | US | 2025-09-18 | **Coded** | ~35 classes, mechanism only; actions are generic |
| NYC Health provider page | NYC | 2025 | **Coded** | Copies the CDC table; adds an AC/cooling checklist |
| Arizona (ADHS/SCORCH) provider sheet | US state | 2024-07 | **Coded** | Name list from CDC; adds insulin; generic actions |
| UKHSA "Supporting vulnerable people…: healthcare professionals" | England | 2024-12-19 | **Coded** | Mechanisms only, no class actions; "most medicines below 25 °C" |
| Health Canada, Extreme Heat Events: Technical Guide for Health Care Workers | Canada | 2011 | **Coded** (ch. 3–4) | **Only source with class-specific monitoring actions** (sodium on diuretics/SSRIs, lithium hydration, electrolytes on antipsychotics); insulin loses 14–18% potency at 32 °C over 28 days |
| ANSM "Liste des médicaments pouvant diminuer l'adaptation…" (with CRPV Toulouse) | France | 2024-07 | **Coded** | Most complete by mechanism; **only source naming SGLT2 inhibitors (gliflozines), GLP-1 agonists, statins**; warns about patches |
| ADAPT-HEAT / CALOR list | Germany | protocol 2026-05 | Pending | List not published until end of 2026 |
| WHO HHAP 2nd ed. / WHO Europe 2021 | Global / Europe | — | **Blocked** (403/404) | Needs a manual download |
| Heidelberg "Hitzetabelle" (dosing.de) | Germany | — | **Blocked** (table URL not found) | Linked from dosing.de home page; open by hand |
| NSW Health / Victoria | Australia | — | **Blocked** (403/404) | Needs manual access |
| AGS Beers Criteria 2023 | US (geriatrics) | 2023 | Not yet | Not heat guidance, but the source for "switch" actions (anticholinergics, TCAs) |
| UK sick-day guidance (Think Kidneys / NHS Scotland SADMANS) | UK | — | Not yet | Source for "hold" actions on ACEi/ARB, diuretics, metformin, SGLT2i, NSAIDs |

### Early coding across six sources (A = class action, M = mention, S = storage only, — = absent)

| Class | CDC | NYC | AZ | UKHSA | Canada | ANSM |
|---|---|---|---|---|---|---|
| Diuretics | A (fluids) | A | M | M | **A** (Na/electrolytes) | M |
| ACEi / ARB | M | M | M | M (antihypertensives) | **A** (hydration) | M |
| Beta blockers | M | M | M | M | — | M |
| CCB | M | M | M | — | **A** (hydration) | M (antihypertensives) |
| Anticholinergics | M | M | M | M | M | M |
| Antipsychotics | M | M | M | M | **A** (electrolytes) | M |
| Lithium | M | M | M | M | **A** (water, not ORS) | M |
| Antidepressants | M | M | M | — | **A** (Na, SSRIs) | M |
| Benzodiazepines | M | M | — | M | — | M |
| Opioids | M (sedation) | M | M | M (GI loss) | — | M (thermoregulation) |
| Insulin | S | S | M | — | S (potency) | M (elimination) |
| SGLT2i | — | — | — | — | — | **M** |
| Metformin / SU | — | — | — | — | — | **M** |
| NSAIDs | M | M | M | M | — | M (+ avoid after heat exposure, web page) |
| Topiramate / zonisamide | M | M | M | M (antiepileptics) | A (topiramate) | **M** (both) |
| Stimulants | M | M | M | — | M | M (illicit only) |
| Emergency products | S | S | — | — | — | — |

What it already shows:
- **No source gives a dose number.** Canada (2011, the oldest) is the only one with class-specific monitoring.
- **SGLT2 inhibitors and metformin/sulfonylureas are named only by France**, although the graph has moderate mechanism support.
- **No source mentions heat-related hypoglycaemia on insulin**, which is the graph's vetted direct finding (OR 1.38).
- **No source mentions opioid overdose rising with temperature**, which is the graph's strongest vetted direct signal.
- US sources copy one another (CDC → NYC → Arizona), so "3 US sources agree" is really one source.

---

## 5. Prescribers: measure them, don't assume

Use **CMS Part D Prescribers by Provider and Drug, 2024** (API confirmed; 1.78M NY rows, 28M national).
- For each class, sum `Tot_Clms` and `GE65_Tot_Clms` by `Prscrbr_Type`, nationally and for NY. Show the top specialties per class as a share.
- This replaces the hand-written specialty lists. It will probably surface nurse practitioners and primary care far more than the brief's list implies (the NY lithium sample already shows NPs and cardiology).
- Limits: Medicare Part D only (mostly ≥65, which is the heat-risk group anyway); cells under 11 are suppressed.

---

## 6. Wearables: where the evidence runs out

**The graph (Dataverse, vetted):** 3,383 physiological or wearable variables, 9,842 findings.
- heat × body signal (HR, skin/core temperature): **82 papers**
- drug × body signal: **204 papers** (mostly beta blockers or atropine on heart rate)
- wearable device validity: **220 papers**
- **heat × drug × signal: 0. heat × wearable device: 0.**

**PubMed (counts, 2026-11-14):**

| Rung | Query | Papers |
|---|---|---|
| 1 | Wearables × heat stress | 160 |
| 2 | Core temperature estimated from heart rate | 163 |
| 3 | Beta blockers × thermoregulation / heat | 403 |
| 4 | Anticholinergics × sweating × heat | 69 |
| 5 | Wearables × heat × older adults | 36 |
| 6 | Wearables × heat × alert intervention trials | 3 (all workers or soldiers, e.g. 2B-Cool, PMID 36730025) |
| 7 | **Wearables × heat × any medication** | **1** |

The story: the physiology of *why* drugs break wearable heat alerts is well studied (rungs 3–4). Algorithms to estimate heat strain exist and are validated in healthy young workers and soldiers (rungs 1–2, 6). Almost nothing tests them in older or medicated people (rungs 5, 7). A beta blocker blunts the heart-rate rise these algorithms rely on; an anticholinergic changes the skin-temperature and sweat response. Present it as a ladder, with the count dropping at each rung.

Queries are saved in `probe_results/pubmed_wearable_counts.json`; the graph probe is `wearable_probe.py`.

---

## 7. NYC extension: confirmed datasets

| Layer | Dataset | Geography | Status |
|---|---|---|---|
| Heat vulnerability | NYC Open Data HVI (`4mhf-duep`) | ZCTA, score 1–5 | Live API |
| Heat outcomes | NYC EHDP: heat-stress deaths (2074), ED visits (2075), hospitalisations (2076) | Neighbourhood (check: UHF or NTA, probably not ZCTA) | Live on GitHub `nychealth/EHDP-data` |
| AC access, older adults alone | EHDP indicators 2104, 2155, 2146, 2185 | Neighbourhood | Live |
| Surface temperature | EHDP 2141 | Neighbourhood | Live |
| Prescribing | CMS Part D by Provider and Drug × by Provider (`Prscrbr_Zip5`) joined on NPI | **Prescriber** ZIP, not patient | Live API |
| Resident burden proxy | CDC PLACES (ZCTA): diabetes, CHD, depression, BP-medication use | ZCTA, resident-based | Live API (`qnzd-25i4`) |

Caveat for the page: Part D places the **prescriber's** office, not where patients live. Clinics cluster in Manhattan. Use PLACES (resident-based) as the main burden layer, and Part D only to show *who* prescribes and *where clinics are* for outreach.

---

## 8. Quality controls

1. **Hand-check** every E1–E3 study shown (abstract vs extracted finding). Badge each one. About 30 papers.
2. **Double-code** the guidance matrix: two people code three sources independently, then report agreement.
3. **Validate the label matcher**: read 20 random labels by hand and report precision for "warns about heat".
4. **FAERS**: report the disproportionality ratio (ROR) with a CI against all FAERS reports, not raw counts. Flag confounding by indication (e.g. interferon beta appears because MS patients are heat-sensitive).
5. Keep the vetted/unvetted flag, and the evidence type, on every item through to the page.

---

## 9. Build order for the rest of today

| Order | Task | Time | Unblocks |
|---|---|---|---|
| 1 | Add UKHSA, Canada, ANSM, Arizona to `guidance.json`; rebuild the comparison page | 45 min | R6, R7 globally |
| 2 | Part D specialty shares per class (national + NY) | 45 min | R4 |
| 3 | FAERS disproportionality per class + monthly seasonality | 45 min | E6, grade C signals |
| 4 | Evidence table + A–D grade per cell | 60 min | R3 |
| 5 | Wearables ladder panel | 30 min | R8 |
| 6 | Source every action (labels, Canada, sick-day rules, Beers) | 45 min | R5 |
| 7 | NYC map (HVI × PLACES, Part D overlay) | 90 min, optional | R9 |
| — | Manual: download WHO, Heidelberg table, NSW; hand-check studies | Teammate, in parallel | — |

---

## 10. What is still missing (gap analysis, 2026-11-14 midday)

### Finding that changes the approach: "not in the graph" ≠ "not studied"
Checked the landmark papers against the graph:
- **Layton 2020, PMID 33301532** (Medicare, heat waves × medication classes × heat-related hospitalisation; the most relevant US study): 0 vetted findings. The API holds only 2 rows (heat wave → hospitalisation, RR 1.16 and 1.37), and **none of its per-drug-class results**.
- **Kalisch Ellett 2016, PMID 27378245** (sequence symmetry: medicine initiation → admission for dehydration or heat illness): not in the graph.
- **Systematic review 2024, PMID 39513185** (prescription and OTC drugs → core temperature under heat stress): not in the graph. This is the E5 synthesis.
- **Reviews to use as recall benchmarks:** PMID 42200961 (2026 scoping review: "Recognizing and Mitigating the Effects of Medication on Heat-Related Illness in Older Adults", the one cited in the brief's source list); PMID 41968235 (2026 narrative review of heat-vulnerability-increasing drugs); PMID 26073686 (Westaway 2015); PMID 9571303 (1998 review of hyperthermia and pharmacokinetics).

→ Add a **literature layer outside the graph**: the studies these reviews include, each typed E1–E9, with a flag `in_graph: vetted / api / title-only / absent`. Each cell then shows "graph evidence" and "literature evidence", and **"gap" splits into "never studied" and "studied, not extracted"**. That second category is itself a finding for System.

### Missing, by requirement

| Area | Missing piece | Why it matters | Source | Effort |
|---|---|---|---|---|
| Evidence | Literature layer from the 4–5 reviews above | Gap cells may be extraction gaps | PubMed + review reference lists | 2 h |
| Evidence | Study year and country for every shown study | "Out of step" needs evidence date vs guidance date; most evidence is France 2003 | PubMed esummary by PMID | 20 min |
| Evidence | Hand-check of the ~30 shown studies | 0 done; ~20% API error rate | Abstracts | 1–2 h, teammate |
| Evidence | Population tags (older adults / workers / children / pregnancy) | Children, pregnancy and outdoor workers are named in guidance, barely in evidence | From study population strings | 30 min |
| Strength | One A–D grade per cell (section 2) | The brief asks "how strong" per bucket | Derived | 1 h |
| Actions | **Heat-wave trigger definition**: what "ahead of" and "during" mean | No action is tied to a threshold yet | CDC HeatRisk levels; NWS/NYC heat advisory criteria; graph thresholds (e.g. AKI ED visits above 22.3 °C) | 45 min |
| Actions | A source for every action, plus restart criteria | All action text is a draft | Labels (dosing/warnings), Health Canada, UK sick-day rules, Beers 2023, STOPP | 1 h |
| Actions | Pharmacist and nurse roles | Pharmacists do storage and counselling; NPs prescribe a lot | Part D `Prscrbr_Type` | in Part D task |
| Prescribers | Measured specialty shares per class | Specialties are assumed today | CMS Part D 2024 | 45 min |
| Prioritisation | **How many people take each class** | Weighs which gaps matter most (a gap on a drug 10M people take beats one on a rare drug) | Part D `Tot_Benes` (national, ≥65); MEPS for all ages | 30 min |
| Guidance | WHO HHAP / WHO Europe, Heidelberg table, Australia | "Globally" currently means US + UK + Canada + France | Manual download | teammate |
| Guidance | Non-Western jurisdictions: India (city heat action plans), Japan, Hong Kong, Gulf states | The brief says "global"; heat burden is highest there | Agency sites | 1–2 h, may be thin |
| Guidance | **Health-system and professional-body guidance**, not only agencies | The brief names "health systems" | VA, NHS trusts/SPS, ASHP/APhA/RPS, ADA (insulin storage), APA (lithium) | 1 h |
| Guidance | Second coder on 3 sources | Coding reliability | Teammate | 30 min |
| Labels | Matcher precision check (20 labels by hand); storage parser bugs (albuterol, some tablets show no temperature) | Label claims go on the page | Existing pull | 30 min |
| Labels | Optional: EU SmPC vs US label for the same drugs | Shows whether regulators disagree | EMA EPAR | optional |
| Storage | Excursion data: what heat does to insulin, epinephrine, inhalers; hot-car temperatures; out-of-fridge days | Storage advice beyond "keep cool" | PubMed (313 stability × heat papers), label section 16, Health Canada (insulin 32 °C) | 1 h |
| Pharmacovigilance | FAERS disproportionality (ROR + CI) per class, and monthly seasonality per class | Raw counts reflect usage | openFDA `drug/event` | 45 min |
| Wearables | A paper list per rung, not just counts; magnitude of beta-blocker HR blunting in heat | Panel needs named examples | PMID 39513185 + rung queries | 45 min |
| NYC | Patient-residence prescribing (not public) → PLACES as the proxy; EHDP geography crosswalk (UHF/NTA ↔ ZCTA); cooling centres and pharmacies for outreach | Prescriber ZIP ≠ patient ZIP | PLACES, NYC Open Data | in map task |
| Validation | Clinician review of action wording; pharmacist review of storage | Required before anyone acts on it | Challenge owner (MD) on site | ask today |

---

## 11. Reframed scope (agreed 2026-11-14)

The brief's examples (insulin, diuretics, the six specialties, the four buckets) are starting points, not limits. Literal requirements we still meet: evidence strength per bucket, prescribers involved, actions, and the guidance comparison. On top of that:

1. **Action timeline × action type.** Every action gets a time tag: *before the season* (review, deprescribe, avoid starting or raising risky drugs, sick-day plan, storage kit) / *heat-alert day* (fluids, monitoring, check-ins) / *unwell in the heat* (hold, adjust) / *after* (restart, recheck). Two new buckets: **Continue, don't stop** (beta blockers, antipsychotics, dopaminergic drugs) and **Counsel and plan** (photosensitivity, symptoms, AC access, a named contact).
2. **Data-driven drug universe.** Classes = union of graph, FAERS, labels and six guidance sources, not only the 17 hand-picked ones. Add GLP-1 agonists, dopaminergic Parkinson drugs, cholinesterase inhibitors, corticosteroids, immunosuppressants, digoxin. Add **combination rows**: triple whammy (diuretic + ACEi/ARB + NSAID), anticholinergic burden, polypharmacy.
3. **Guidance scorecard** per source: coverage of risky classes, specificity (class actions vs mechanism), alignment with the evidence (names insulin hypoglycaemia, opioid overdose, SGLT2i?), recency.
4. **Wearables as a drug × sensor validity matrix**: which signal each class makes unreliable (beta blockers → heart rate; anticholinergics → skin temperature and sweat; diuretics → weight and hydration), filled from physiology literature, with the 1 medicated-wearables paper showing where evidence runs out.
5. **Health-system outreach list**: computable criteria (at-risk drug or combination + age ≥65 + no AC or living alone), sized nationally (Part D) and by NYC neighbourhood. Gives the NYC map a job.
6. **Outcome-first view**: heat stroke, kidney injury, low sodium, falls, hypoglycaemia, overdose, mental-health crises, lost drug potency.

Deferred: climate projections, equity analysis beyond NYC.

### Revised build order (supersedes section 9)

| Order | Task | Status |
|---|---|---|
| 1 | Code UKHSA, Health Canada, ANSM, Arizona into `guidance.json`; guidance scorecard; six-source matrix on the Crosscheck page | **Done** (Crosscheck page republished) |
| 2 | Literature layer from the review papers (studied vs extracted) + study year/country | Next |
| 3 | Wearables drug × sensor matrix | — |
| 4 | Timeline tags + the two new buckets on every action, each action sourced | — |
| 5 | New classes (GLP-1, Parkinson, cholinesterase inhibitors…) and combination rows through graph + labels + FAERS | — |
| 6 | Part D: specialty shares and number of people per class | — |
| 7 | One A–D grade per cell | — |
| 8 | Outreach list criteria + NYC map | optional |
| — | Teammate: hand-check studies; download WHO, Heidelberg, NSW; second coder; ask the challenge owner to review actions | parallel |

### Update: WHO Europe coded; Heidelberg and Australia dropped (2026-11-14)
- **WHO Europe, Heat–health action plans: guidance, 2nd ed. (2026, ISBN 9789289062930, CC BY-NC-SA 3.0 IGO)**, from a copy supplied by the team. Medicines are framed as a health-system task: pre-season medication review for diuretics, antihypertensives, anticholinergics, antipsychotics, antidepressants and lithium (p. 214); at-risk registers including medication use (pp. 90, 209); storage and supply checks (pp. 134, 212). Names 8 of 17 classes, no class actions, 3 of 8 evidence checks. Supports the outreach-list idea in section 11.
- Heidelberg table and Australian state guidance: dropped by team decision.
- Guidance matrix is now 7 sources: CDC, NYC, Arizona, UKHSA, Health Canada, ANSM, WHO Europe.

### Update: literature layer built (2026-11-14 afternoon)
- `lit_pull.py` → `probe_results/literature.{csv,json}`. Candidates: 57 hand-screened recall papers + reference lists of 5 reviews (PMIDs 42200961, 41968235, 39513185, 26073686, 9571303) + papers citing 9 key studies = 570; rule-screened and title-reviewed → 163 kept, **143 primary studies**.
- Graph status of the 143: **20 (14%) have a finding naming the drug**; 38 have any finding; 102 are study records with no findings; 3 absent.
- Pattern changes: anticholinergics (25 studies, 1 extracted) and topiramate/zonisamide (6, 0) moved from "warned everywhere, measured weakly" to "all three agree". Lithium stays (its two heat studies are null).
- **Error found by hand-check:** PMID 31205291 (overdose deaths) is about cold, not heat; the graph dropped the direction. Corrected in `build_grid.py`, `build_lenses.py`, `guidance.json` and `DATA_FINDINGS_FOR_DESIGN.md`. Opioids still show "raises risk" via vetted PMID 37897873 (ED visits).
- Not done: reading directions of effect from the unextracted abstracts; year/country only stored for literature studies.

### Update: directions read for unextracted studies (2026-11-14 afternoon)
- `literature_read.json`: 90 abstracts hand-read by one reader (59 epidemiology/seasonal/experimental/storage in full, 31 physiology conclusions); 33 case reports coded as "harm reported" without reading. Class-specific overrides for multi-class studies are in `CLASS_EFFECT` in `build_lenses.py`.
- New evidence the graph lacks: BC 2021 heat dome, antipsychotics → death in schizophrenia (combination OR 4.05, PMID 41044101); ACEi + diuretic initiation → dehydration/heat admission 2.79 (PMID 27378245); sulfonylureas (glimepiride, glyburide) → hypoglycaemia with heat (PMID 39433419); US overdose deaths rise with heat for opioids, cocaine, psychostimulants (PMID 41048198); NYC overdose deaths above 24 °C, cocaine-driven (PMID 20219056).
- Counter-evidence also now shown: psychotropics did not modify heat-wave risk in people with mental illness (39648665); medication use did not raise heat consultations in type 2 diabetics (28701216); ADHD stimulant users had lower heat-illness risk (39758443); canagliflozin well tolerated in hot climates (27600862); Layton Medicare study found risk all summer but no heat-wave interaction (33301532); emergency drugs stable in an EMS car for a year and at 70 °C (35717271, 8363680).
- Practice evidence for dose adjustment: Japanese doctors reduce antihypertensives in summer, most often diuretics (29939771).
- Still not done: second reader; full-text check of key numbers.

### Update: wearables drug × sensor matrix (2026-11-14 afternoon) — build step 3 done
- `wearables_pull.py` → `probe_results/wearables.json`: 10 classes × 8 signals. Graph (Dataverse): 2,803 drug→signal paper links, **0 measured in heat**. PubMed: drug × signal × heat studies exist for most pairs (lab physiology); drug × signal × heat × wearable: **1 of 80 pairs** (insulin + CGM, PMID 41464483, Italy, July 2023 heat wave stressed closed-loop pumps).
- `wearables_matrix.json`: hand-curated cells (effect, evidence level heat/lab/pharm, PMIDs). Key cells: beta blockers blunt the heat HR rise (1335440) so HR-based alerts and HR-derived core-temperature estimates under-read strain; anticholinergics suppress sweat (3606515, 3790405) so EDA/sweat sensors stay flat; diuretics lower body weight, confounding the weight-based fluid monitoring UKHSA suggests; stimulants raise core temperature without changing perceived effort (18408610); warm skin at insulin sites speeds absorption (22538141).
- On the Crosscheck page as "Wearables: which signals each drug makes unreliable": funnel 160 → 36 → 3 → 1, physiology counts, clickable matrix.
- Caveat: PubMed heat counts per cell are approximate (keyword queries); lab evidence is mostly healthy young volunteers.

### Update: action timeline built (2026-11-14 afternoon) — build step 4 done
- `actions_extra.json` (hand-curated, sources read this session only) + draft grid actions + `grid/review_fields.json` (trigger, owner, restart) → `actions` in `grid/lenses_data.json`.
- 76 class actions + 3 for every patient. Timing: 17 before the season, 28 heat-alert day, 6 unwell, 25 after (restart rules). Basis: 21 heat study, 9 label, 6 guidance, 6 mechanism, 34 draft (mostly restart rules).
- New buckets: "Continue, don't stop" (beta blockers, antipsychotics, antidepressants, benzodiazepines, plus all patients) and "Counsel and plan" (fluid plan, AC and check-in contact, naloxone, fentanyl patch heat, topiramate in children, stimulants in sport, beta blockers and wearable HR).
- Heat-alert trigger is a placeholder (local heat advisory or CDC HeatRisk orange+): **team to confirm the NYC threshold.**
- On the Crosscheck page as "Heat-season action plan", filterable by prescriber.

### Update: new classes and combination rows (2026-11-14 late afternoon) — build step 5 done
- `local_analysis.py` DRUGS gained GLP-1 agonists, Parkinson / dopaminergic, Cholinesterase inhibitors (rerun: 7 min). No direct heat findings in the graph for any; mechanism links only (GLP-1: AKI 7, glucose 44; Parkinson: hypotension 6; cholinesterase: hypotension 4).
- `build_grid.py` CLASSES gained those three plus two combination rows: "Combination: diuretic + ACEi/ARB (± NSAID)" and "Polypharmacy (several heat-sensitising drugs)". Map is now 22 rows. Note: `grid/heat-med-map.html` was regenerated locally with 22 rows but not republished.
- Labels: GLP-1 labels warn about AKI from volume depletion, never heat; levodopa/pramipexole/ropinirole mention hyperthermia only on withdrawal; rivastigmine patch labels warn against external heat.
- **Label matcher fix:** sentences with "differential diagnosis" / "important to consider the presence of other" are now dropped before matching (they list heat stroke as something to rule out in NMS). Effect: levodopa and **clozapine no longer count as heat warnings**; haloperidol still does (real warning). Antipsychotic finding text updated.
- New pattern "Little evidence, little guidance": GLP-1, Parkinson, cholinesterase inhibitors. Combination row → "guidance misses it"; polypharmacy → "all three agree".
- GLP-1 FAERS figure (70 heat-illness reports) is a raw count from the earlier probe, not disproportionality.
