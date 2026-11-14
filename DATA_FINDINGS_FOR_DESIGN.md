# Data findings for the design session

**Project:** System Public Challenge, NYC, 13 to 14 November 2026. Challenge "Visualize 3".
**Question:** Which common medications make heat more dangerous, and what should prescribers and health systems do about it?
**Audience:** clinicians, pharmacists and public-health officials planning heat-wave counselling.
**Deliverable:** a visual evidence map of heat-sensitive medications. It is grouped by type of action and shows how strong the evidence is, which prescribers are involved, and where current guidance has gaps.

This brief holds the analysis results. The data work is done. The design job is to present these results clearly, not to change them.

- **Source of truth for every number:** `grid/grid_data.json`. The schema is at the end of this brief.
- **Current page:** https://claude.ai/artifact/CqsXxVwScVfLynPtSyrnkb. It is private; the owner shares it.
- **Current page source:** `grid/template.html`. `build_grid.py` injects the JSON into it and writes `grid/heat-med-map.html`.
- **Status of the design:** the owner dislikes how the current page looks but hasn't said why yet. Ask them before redesigning.

---

## 1. Headline findings (lead with these)

1. **The strongest signal is in psychiatric drugs.** In the 2003 French heat wave, older people taking antipsychotics had about twice the odds of dying (OR 2.09, 95% CI 1.89 to 2.35). For antidepressants the OR was 1.71 (1.57 to 1.86). Both findings are vetted.
2. **The classes guidance stresses most are the least proven.** Every guidance source flags **lithium** and **anticholinergics**. Lithium was studied twice, with no clear heat effect (p = 0.08; r = −0.008). Anticholinergics have one unvetted study, with no clear effect on death (OR 1.21, p = 0.31) but a longer hospital stay.
3. **Overdose and hypoglycaemia are under-recognised heat risks.**
   - Opioid overdose ED visits rise with daily temperature (OR 1.079 per step). **Correction 2026-11-14:** the "fatal opioid overdose OR 1.3" finding (PMID 31205291) is about **cold** weather, not heat; the graph dropped the direction. Overdose-death evidence for heat is null (PMID 37369523).
   - Amphetamine overdose rises too (OR 1.15, unvetted).
   - Older insulin users have more serious hypoglycaemia in heat (OR 1.38 in the hottest category).
   - Heat guidance rarely names opioids or amphetamines.
4. **The evidence that exists is about kidneys and sodium, while guidance worries most about sweating.**
   - Diuretics, ACE inhibitors/ARBs, NSAIDs and SGLT2 inhibitors have 50 to 90 studies each linking them to kidney injury or low sodium, and heat links to those mechanisms too.
   - Almost no study links any drug to reduced sweating: anticholinergics 0, antipsychotics 0.
5. **Direct evidence is rare and unevenly extracted.**
   - Of 57 known heat × medication papers, only 18 have any findings in the graph.
   - The rest, mostly 1970s to 2000s case reports of drug-related heat stroke, exist only as titles.

---

## 2. Data sources and scale

| Source | What it is | Size | Trust |
|---|---|---|---|
| **Dataverse release** (doi:10.7910/DVN/7V6JDO, CC-BY-NC 4.0) | The findings System has vetted | 2.0M findings, 1.77M variables, 844k studies | **Vetted** |
| **Live System API** | The full graph | 5.94M findings, 5.65M variables | System estimates **~20% of API-only rows are mis-extracted** |
| **PubMed** | Used only to find heat × medication papers (title or abstract) | 1,934 papers seeded | Used for finding papers, not as evidence |
| **Drug labels and heat guidance** (CDC, UKHSA, Beers criteria, FDA) | Where most actions come from | — | Outside the graph |

The API-only rows we pulled come to about 6,900. Every row is flagged `vetted` or not.

**Licence:** the graph data is CC-BY-NC 4.0, so the page footer must credit it and note non-commercial use.

---

## 3. Evidence types (the core visual encoding)

The page must make these types tell apart at a glance. They are different kinds of knowledge, not just different strengths.

| Tier | Meaning | Count of cells |
|---|---|---|
| **Direct: raises risk** | A study measured the drug (or its class) together with heat, and found a risk | 18 |
| **Direct: no clear effect** | Measured together with heat, with no significant effect (or a lower risk) | 5 |
| **Bridged** (strong / moderate / weak) | Indirect. The drug → mechanism link and the heat → same-mechanism link both exist, but in separate studies | 8 |
| **Partial** | Drug → mechanism exists, but nothing links heat to that mechanism | 1 |
| **Gap** | The action is in labels or guidance, and the graph has nothing for its mechanism | 4 |
| **No action** | No heat-specific action expected for this bucket | 32 |

**Bridge strength rubric.** Each cell is graded on its *main* mechanism only, the first one listed:
- **strong:** at least 30 drug studies and at least 10 heat studies;
- **moderate:** at least 10 drug studies and at least 3 heat studies;
- **weak:** both halves present, below those thresholds.

**Cross-cutting flags. Each one needs its own visual cue, independent of tier:**
- **Unvetted (†):** the cell's grade depends on API-only rows. This applies to 9 cells. The current page uses a dashed border.
- **Effect direction** of each direct study: raises risk / no clear effect / lower risk.
- **Sub-types of direct evidence (not yet shown on the page; a design opportunity):** today "Direct" lumps together:
  - **Heat-exposure epidemiology:** heat waves, daily temperature, heatstroke cohorts. This is the strongest kind.
  - **Seasonal analogues:** summer vs winter. Used for dose adjustment.
  - **Experimental local heat:** heat applied to a patch, injection site or pump. Relevant to storage and handling.
  - **Class-wide evidence:** "any antihypertensive" applied to diuretics, ACE inhibitors/ARBs, beta blockers and calcium channel blockers.

  Section 6 tags every direct study with its sub-type.
- **Source outside the graph:** a label or guidance note per cell, such as "FDA boxed warning" or "Beers criteria".

---

## 4. The grid: 17 drug classes × 4 actions

Actions: **Dose** = dose adjustment; **Hold/switch** = substitute or temporarily hold; **Monitor** = closer monitoring; **Storage** = storage and stability. † = the grade relies on unvetted API rows.

| Drug class | Dose | Hold/switch | Monitor | Storage |
|---|---|---|---|---|
| Diuretics | Direct | Direct, no clear effect | Direct | — |
| ACE inhibitors / ARBs | Direct | Direct, no clear effect | Direct | — |
| Beta blockers | — | Gap | Direct (class-wide) | — |
| Calcium channel blockers | Direct † (seasonal) | — | Direct (class-wide) | — |
| Anticholinergics | — | Bridged (weak) † | Direct, no clear effect † | — |
| Antipsychotics | — | Gap | Direct | — |
| Lithium | Direct, no clear effect | Partial | Direct, no clear effect | — |
| Antidepressants | — | Bridged (weak) | Direct | — |
| Benzodiazepines / sedatives | — | Gap | Direct † | — |
| Opioids | — | — | Direct | Direct (experimental) |
| Insulin | Direct | — | Direct | Direct † (experimental) |
| SGLT2 inhibitors | — | Bridged (moderate) † | Bridged (moderate) † | — |
| Metformin and sulfonylureas | Bridged (moderate) | Bridged (weak) | Direct † (seasonal) | — |
| NSAIDs | — | Direct, no clear effect | Bridged (strong) | — |
| Topiramate / zonisamide | — | — | Bridged (weak) | — |
| Stimulants | — | — | Direct | — |
| Heat-labile emergency products | — | — | — | Gap |

**Prescriber filter values:** Addiction medicine, Cardiology, Endocrinology, Geriatrics, Nephrology, Neurology, Pain and palliative, Pediatrics, Pharmacy, Primary care, Psychiatry, Rheumatology, Urology. Each class lists its specialties in `grid_data.json`.

---

## 5. Cell by cell: actions, evidence and mechanisms

Action wording is a **draft for clinician review**, and the page must say so. Mechanism counts read "drug-side studies / heat-side studies"; "+N" means extra unvetted studies.

### Diuretics: furosemide, hydrochlorothiazide, spironolactone
Primary care, Cardiology, Nephrology, Geriatrics
- **Dose (Direct):** Review the dose before and during a heat wave if intake is low or weight is falling.
  - Direct: 36418530 (seasonal).
  - Main mechanism, dehydration: 1+2 / 4+1. Supporting: low sodium 60+5 / 6+4; kidney injury 82 / 17+4.
- **Hold/switch (Direct, no clear effect):** Sick-day rule: hold temporarily during vomiting, diarrhoea or poor fluid intake.
  - Source: sick-day guidance (UK "SADMANS").
  - Direct: 29116624 (null).
- **Monitor (Direct):** Check sodium, potassium and creatinine; daily weight; ask about dizziness.
  - Direct: 17698677 (class-wide), 16911573.
  - Main mechanism, low sodium: 60+5 / 6+4.

### ACE inhibitors / ARBs: lisinopril, ramipril, losartan, valsartan
Primary care, Cardiology, Nephrology, Geriatrics
- **Dose (Direct):** Consider a lower dose if blood pressure runs low through the summer.
  - Direct: 36418530 (seasonal).
  - Main mechanism, low BP: 27 / 6+7.
- **Hold/switch (Direct, no clear effect):** Sick-day rule: hold when dehydrated; avoid combining with an NSAID and a diuretic.
  - Direct: 29116624 (null).
  - Main mechanism, kidney injury: 86 / 17+4.
- **Monitor (Direct):** Check creatinine and potassium; screen for orthostatic hypotension.
  - Direct: 17698677 (class-wide), 37280056 (seasonal, unvetted).

### Beta blockers: metoprolol, atenolol, propranolol
Primary care, Cardiology, Geriatrics
- **Hold/switch (Gap):** Do not stop abruptly; reassess where the indication is weak.
  - Source: label (rebound risk on withdrawal).
- **Monitor (Direct):** Watch for dizziness and reduced exercise tolerance in the heat; heart-rate response is blunted.
  - Direct: 17698677 (class-wide).
  - Low BP: 18 / 6+7. Sweating: 1+1 / 19+31.

### Calcium channel blockers: amlodipine, diltiazem, verapamil
Primary care, Cardiology, Geriatrics
- **Dose (Direct †):** Review the dose if symptomatic hypotension develops in hot weather.
  - Direct: 34338579 (seasonal, unvetted).
- **Monitor (Direct):** Ask about light-headedness, falls and ankle swelling.
  - Direct: 17698677 (class-wide).
  - Low BP: 17 / 6+7.

### Anticholinergics: oxybutynin, diphenhydramine, benztropine
Primary care, Geriatrics, Urology, Psychiatry
- **Hold/switch (Bridged, weak †):** Deprescribe or switch where possible, e.g. from oxybutynin to mirabegron.
  - Sources: Beers criteria; CDC and UKHSA heat guidance.
  - Sweating: 0+1 / 19+31. The single unvetted study is oxybutynin lotion reducing palm sweat.
- **Monitor (Direct, no clear effect †):** Warn about reduced sweating; watch for confusion and hot, dry skin.
  - Heat guidance names this class first.
  - Direct: 27160370 (null, unvetted).

### Antipsychotics: olanzapine, clozapine, haloperidol, quetiapine
Psychiatry, Primary care
- **Hold/switch (Gap):** Do not stop abruptly; where a choice exists, prefer agents with low anticholinergic load.
- **Monitor (Direct):** Check temperature and hydration; watch for confusion, rigidity (NMS) and hypotension.
  - Direct: 20104062 (vetted), 29020197 and 17513091 (unvetted).
  - Main mechanism, sweating: **0** / 19+31. Low BP: 13 / 6+7.

### Lithium: lithium carbonate
Psychiatry, Primary care, Nephrology
- **Dose (Direct, no clear effect):** Levels can rise with dehydration; review the dose based on a level, not a fixed rule.
  - Source: label (narrow therapeutic index).
  - Direct: 25163443 (null).
- **Hold/switch (Partial):** Hold temporarily during vomiting or diarrhoea and seek a level.
  - Lithium levels: 11+4 / **0**.
- **Monitor (Direct, no clear effect):** Check a serum lithium level and creatinine during prolonged heat; teach the signs of toxicity.
  - Direct: 25163443 and 31782314 (both null).

### Antidepressants: SSRIs, tricyclics (amitriptyline)
Psychiatry, Primary care, Geriatrics
- **Hold/switch (Bridged, weak):** In older adults, prefer an SSRI over a tricyclic.
  - Source: Beers criteria.
  - Sweating: 2 / 19+31.
- **Monitor (Direct):** SSRIs: check sodium in older adults. Tricyclics: watch for overheating.
  - Direct: 20104062 (vetted), 17513091 (unvetted).
  - Low sodium: 13+3 / 6+4.

### Benzodiazepines / sedatives: diazepam, lorazepam, zolpidem
Psychiatry, Primary care, Geriatrics
- **Hold/switch (Gap):** Taper rather than stop; review the need for long-term use.
  - Source: Beers criteria.
- **Monitor (Direct †):** Sedation dulls thirst and awareness of heat; watch for falls.
  - Direct: 17513091 (raises risk, unvetted); 20104062 anxiolytics row (**lower risk**, OR 0.85, unvetted).
  - The evidence conflicts.

### Opioids: morphine, oxycodone, fentanyl patch, methadone
Pain and palliative, Primary care, Addiction medicine
- **Monitor (Direct):** Overdose risk rises with temperature: offer naloxone and add check-ins on hot days.
  - Opioids are rarely named in heat guidance.
  - Direct: 37897873, 31205291 (vetted, risk); 37369523 (vetted, null).
- **Storage (Direct, experimental):** Keep heat sources and direct sun off a fentanyl patch; fever or heat raises absorption.
  - Source: FDA boxed warning.
  - Direct: 15101888 (vetted), 14622685 (unvetted).

### Insulin: all insulins
Endocrinology, Primary care
- **Dose (Direct):** Heat speeds absorption from the injection site; a dose reduction may be needed if lows occur.
  - Direct: 38060348 (vetted), 7010077 (experimental, unvetted).
  - Glucose: 135 / 3.
- **Monitor (Direct):** Check glucose more often in hot weather.
  - Direct: 38060348.
- **Storage (Direct †, experimental):** Keep below about 30 °C and out of hot cars; use a cooling wallet when travelling.
  - Source: label.
  - Direct: 22538141 (unvetted).

### SGLT2 inhibitors: empagliflozin, dapagliflozin
Endocrinology, Cardiology, Nephrology, Primary care
- **Hold/switch (Bridged, moderate †):** Sick-day rule: hold when dehydrated or not eating (risk of volume depletion and euglycaemic DKA).
  - Dehydration: 3+9 / 4+1. Kidney injury: 53 / 17+4.
- **Monitor (Bridged, moderate †):** Ask about fluid intake; check ketones if unwell.

### Metformin and sulfonylureas: metformin, gliclazide, glyburide
Endocrinology, Primary care, Geriatrics
- **Dose (Bridged, moderate):** Sulfonylureas: consider a lower dose if intake falls and lows occur.
  - Glucose: 130 / 3.
- **Hold/switch (Bridged, weak):** Metformin: hold temporarily when dehydrated (kidney injury, lactic acidosis).
  - Kidney injury: 9 / 17+4.
- **Monitor (Direct †, seasonal):** Check glucose more often; watch kidney function.
  - Direct: 24334574 (direction unclear, unvetted).

### NSAIDs: ibuprofen, naproxen, diclofenac
Primary care, Rheumatology, Pharmacy
- **Hold/switch (Direct, no clear effect):** Avoid during heat waves when dehydrated, above all combined with a diuretic and an ACE inhibitor/ARB ("triple whammy").
  - Direct: 29116624 (null), 35564355 (null, unvetted).
  - Kidney injury: 50 / 17+4.
- **Monitor (Bridged, strong):** Check creatinine if NSAIDs continue during prolonged heat.
  - Kidney injury: 50 / 17+4.

### Topiramate / zonisamide
Neurology, Pediatrics
- **Monitor (Bridged, weak):** Reduced sweating, mainly in children: limit exertion in heat and watch for fever.
  - Source: label warning.
  - Sweating: 1 / 19+31.

### Stimulants: methylphenidate, amphetamine
Psychiatry, Pediatrics
- **Monitor (Direct):** Watch for overheating on hot days, especially in sport; misuse and overdose rise with temperature.
  - Direct: 37897873 amphetamine rows (unvetted), 37369523 (null).

### Heat-labile emergency products: epinephrine auto-injectors, salbutamol inhalers, nitroglycerin
Primary care, Pharmacy, Pediatrics
- **Storage (Gap):** Keep out of hot cars and direct sun; replace after heat exposure or if discoloured.
  - Source: label storage conditions only.

---

## 6. Curated direct studies (all 23 + 4 general)

Effect: ↑ raises risk, 0 no clear effect, ↓ lower risk, ? unclear. Type: **H** = heat-exposure epidemiology, **S** = seasonal, **X** = experimental local heat, **C** = class-wide. Link pattern: `https://pubmed.ncbi.nlm.nih.gov/<PMID>/`

| PMID | Finding | Effect | Vetted | Type | Used in |
|---|---|---|---|---|---|
| 20104062 | 2003 French heat wave, ages 70 to 100: antipsychotics → death, OR 2.09 (1.89 to 2.35) | ↑ | Yes | H | Antipsychotics · Monitor |
| 20104062 | Same study: antidepressants → death, OR 1.71 (1.57 to 1.86) | ↑ | Yes | H | Antidepressants · Monitor |
| 20104062 | Same study: anxiolytics/hypnotics → death, OR 0.85 (0.79 to 0.91) | ↓ | No | H | Benzodiazepines · Monitor |
| 29020197 | US Army soldiers: recent antipsychotic prescription → mild heat injury, HR 3.25 (1.33 to 7.9) | ↑ | No | H | Antipsychotics · Monitor |
| 17513091 | Older adults, 2003 heat wave: psychotropic use → heat-related admission, OR 2.4 to 6.0 | ↑ | No | H | Antipsychotics, Antidepressants, Benzodiazepines · Monitor |
| 38060348 | Older insulin users, US and Taiwan: heat → serious hypoglycaemia, OR 1.14 (1.08 to 1.20) per step; 1.38 (1.28 to 1.48) hottest category | ↑ | Yes | H | Insulin · Dose, Monitor |
| 37897873 | California ED visits: daily temperature → opioid overdose, OR 1.079 (1.054 to 1.106); opioid-use ED visits, OR 1.041 | ↑ | Yes | H | Opioids · Monitor |
| 37897873 | Same study: amphetamine overdose, OR 1.15 (1.085 to 1.218) | ↑ | No | H | Stimulants · Monitor |
| 31205291 | **Corrected:** Connecticut and Rhode Island: **cold** (0 °C vs 11 °C, prior 7 days) → fatal opioid overdose, OR 1.3 (1.1 to 1.5). Not a heat effect; graph lost the direction | 0 for heat | Yes | H | Opioids · Monitor |
| 37369523 | British Columbia: 10 °C hotter → opioid death, OR 1.15 (0.99 to 1.33); amphetamine, OR 1.11 (0.60 to 2.04) | 0 | Yes | H | Opioids, Stimulants · Monitor |
| 17698677 | Heatstroke patients, Lyon: long-term antihypertensive → death, HR 2.17 (1.17 to 4.05) | ↑ | Yes | H, C | Diuretics, ACE/ARB, Beta blockers, CCB · Monitor |
| 16911573 | Thiazide-induced low sodium: air temperature ~ serum sodium, r = 0.2 | ↑ | Yes | H | Diuretics · Monitor |
| 29116624 | Older inpatients in heat waves: diuretic + NSAID + ACEi/ARB → kidney injury, OR 1.02 (0.21 to 2.97) | 0 | Yes | H | NSAIDs, ACE/ARB, Diuretics · Hold |
| 35564355 | Heat-exposed rice workers, Costa Rica: pain medication → eGFR change −3.2 (−8.2 to 1.95) | 0 | No | H | NSAIDs · Hold |
| 25163443 | Older lithium users: temperature → lithium dose-to-level ratio, β −0.17, p = 0.08 | 0 | Yes | H | Lithium · Dose, Monitor |
| 31782314 | 2,493 patients, Sydney: 5-day max temperature ~ serum lithium, r = −0.008 | 0 | Yes | H | Lithium · Monitor |
| 27160370 | Older inpatients in heat waves: anticholinergic drugs → death, OR 1.21 (p = 0.31); longer stay (p = 0.01) | 0 | No | H | Anticholinergics · Monitor |
| 36418530 | Irbesartan/HCTZ started in the warm vs cold season: BP response differs by 7.0 mmHg (4.7 to 9.3) | ↑ | Yes | S | Diuretics, ACE/ARB · Dose |
| 34338579 | Amlodipine-based therapy: seasonal BP swing 4.33 mmHg | ↑ | No | S | CCB · Dose |
| 37280056 | ACEi users: seasonal potassium; ACEi in cooler periods, RR 1.33 (1.12 to 1.59) | ↑ | No | S | ACE/ARB · Monitor |
| 24334574 | Oral glucose-lowering drugs: severe hypoglycaemia admissions, warm vs cool season (−17) | ? | No | S | Metformin/SU · Monitor |
| 15101888 | Heat on a fentanyl patch: plasma exposure (AUC) about 30% higher | ↑ | Yes | X | Opioids · Storage |
| 14622685 | Local heat on a fentanyl patch: higher peak serum fentanyl | ↑ | No | X | Opioids · Storage |
| 7010077 | Insulin at 35 °C vs 20 °C: faster absorption | ↑ | No | X | Insulin · Dose |
| 22538141 | Insulin pump with local skin heating: lower glucose curve (AUC −9.6 to −12.4) | ↑ | No | X | Insulin · Storage |
| **General** | | | | | (not tied to a class) |
| 31842287 | Odisha, India households: on any medication → heat illness, aOR 3.09 (1.15 to 8.29) | ↑ | Yes | H | — |
| 28737683 | Sweden: outdoor temperature → reports of drug-induced low sodium, OR 2.21 | ↑ | No | H | — |
| 28796021 | Older inpatients in a heat wave: psychotropics → length of stay, HR 0.89 (0.69 to 1.14) | 0 | Yes | H | — |
| 11434495 | Number of current medications → heat-related illness, OR 1.1 (0.8 to 1.5) | 0 | No | H | — |

---

## 7. The mechanism bridge (indirect evidence)

**Heat → mechanism** (studies; "+" = unvetted):

| Mechanism | Heat studies |
|---|---|
| Sweating / thermoregulation | 19 + 31 (mostly heat-chamber physiology in healthy volunteers) |
| Kidney injury | 17 + 4 |
| Low blood pressure / falls | 6 + 7 |
| Low sodium / electrolytes | 6 + 4 |
| Dehydration / volume | 4 + 1 |
| Glucose | 3 |
| Muscle breakdown | 2 + 1 |
| Lithium levels | 0 (but 2 direct temperature → lithium-level studies, both null) |

**Drug → mechanism.** Drug is the exposure, in people; studies:

| Class | Kidney injury | Low sodium | Low BP / falls | Glucose | Sweating | Dehydration |
|---|---|---|---|---|---|---|
| ACE inhibitors / ARBs | 86 | 33 | 27 | 4 | 1 | 0+1 |
| Diuretics | 82 | 60 | 17 | 2 | — | 1+2 |
| NSAIDs | 50 | 8 | 1 | — | 0+1 | 1 |
| SGLT2 inhibitors | 53 | 13 | 2 | 55 | — | 3+9 |
| Insulin | 3 | 2 | 3 | 135 | — | — |
| Metformin / sulfonylureas | 9 | 1 | 1 | 130 | — | 1 |
| Opioids | 12 | 1 | 35 | 3 | 0+2 | 1 |
| Antidepressants | 0 | 13 | 28 | 4 | 2 | — |
| Benzodiazepines | 0 | 1 | 28 | — | 0+1 | — |
| Beta blockers | 10 | 3 | 18 | 10 | 1 | — |
| Calcium channel blockers | 10 | 3 | 17 | 1 | — | — |
| Antipsychotics | 4 | 6 | 13 | 9 | **0** | 0 |
| Anticholinergics | 1 | 1 | 11 | — | **0+1** | — |
| Lithium | 3 | 1 | — | — | 1 | — (lithium levels 11+4) |
| Topiramate / zonisamide | — | 1 | 3 | — | 1 | — |

**The visual story here:** the kidney and sodium columns are full, and the sweating column is empty, yet sweating is the mechanism guidance cites for the classes it worries about most.

---

## 8. Coverage and quality numbers (for a methods or "how much to trust this" panel)

- **Recall check:** we took 57 relevant heat × medication papers from PubMed.
  - 18 have extracted findings in the graph; 13 of those are in scope.
  - **Our search finds 10 of the 13.** The 3 misses name no drug in any extracted finding.
- **Bridge clean-up:** 193 reversed findings (condition → prescription) and 31 animal or poisoning studies were removed. Counts fell 5 to 15%.
- **Error rate:** System estimates ~20% of API-only rows are mis-extracted. Those rows are always flagged.
- **Hand-checking:** none yet. Every study carries an "unchecked" badge until it has been checked against its abstract.
- **Variable search coverage:** 4,828 heat variables (API) and 1,907 (Dataverse), 30+ heat phrasings, 1,934 PubMed-seeded papers.
- **Concept layer:** only ACE inhibitor–"hot" and opioid–"hot" exist as concept pairs, 1 study each. It's not useful for this question.

---

## 9. Caveats that must be visible on the page

1. Action wording is a draft for clinician and pharmacist review, not a protocol.
2. Bridged means plausible by mechanism, not measured. Use language like "mechanism support", not "risk".
3. Unvetted rows (System estimates ~20% error) are always marked.
4. No study has been checked against its abstract yet.
5. Storage advice comes from drug labels; the graph has almost nothing on drug stability.
6. Absence of evidence is not evidence of safety. A "gap" or "no clear effect" cell is not a green light.

---

## 10. What the design must let a reader do

- **See the whole map at once:** 17 classes × 4 actions, summary before detail.
- **Tell evidence types apart without a legend lookup:** direct-risk vs direct-null vs bridged (3 strengths) vs partial vs gap vs no action.
- **See vetted vs unvetted at a glance.**
- **Ideally see the direct sub-type:** heat epidemiology / seasonal / experimental / class-wide.
- **See gaps as a finding,** not as empty space. The mismatch between what guidance stresses and what is measured is the headline.
- **Filter by prescriber specialty.**
- **Open any cell** to see the draft action, its source outside the graph, the direct studies (with effect, vetted flag and PubMed link) and the two halves of the bridge with example findings.
- **Read the 4 or 5 headline findings** before the grid.
- **Find the methods, rubric and caveats.**

Not built yet, and possible extras from the brief: a second grid comparing drug class against guidance source (CDC, UKHSA, WHO Europe, Health Canada, Australia), a wearables panel, and an NYC heat-exposure map. None of these has data prepared.

---

## 11. `grid/grid_data.json` schema

```text
{
  "buckets": ["Dose adjustment", "Substitute or hold", "Closer monitoring", "Storage and stability"],
  "rows": [{
    "class": "Diuretics",
    "examples": "furosemide, hydrochlorothiazide, spironolactone",
    "specialties": ["Primary care", ...],
    "cells": {
      "<bucket>": {
        "tier": "direct" | "bridged" | "partial" | "gap" | "none",
        "strength": 1 | 2 | 3 | null,           // bridged only: weak / moderate / strong
        "signal": "risk" | "null" | "lower" | null,   // direct only
        "vetted": true | false,                 // false = grade relies on API-only rows
        "action": "draft action text",
        "note": "source outside the graph, or empty",
        "direct": [{ "pmid", "summary", "vetted", "effect": "risk|null|lower", "a", "b" }],
        "mechanisms": [{
          "mechanism", "primary": bool,
          "drug_studies", "drug_unvetted", "heat_studies", "heat_unvetted",
          "drug_examples": [Study], "heat_examples": [Study]
        }]
      }
    }
  }],
  "general": [{ "pmid", "summary", "vetted", "effect" }],
  "source": "...", "built": "2026-11-13"
}
Study = { "pmid", "a", "b", "stat", "value", "ci": [lo, hi], "p", "trial": bool,
          "sig": bool /* CI excludes no effect, or p < 0.05 */, "pop", "vetted"?: false }
```

The direct sub-type (H/S/X/C in section 6) isn't in the JSON yet. If the design needs it, add a `type` field per entry in `DIRECT` in `build_grid.py` and rerun `python3 build_grid.py`. The data analysis doesn't need rerunning.

**Rebuild:** `python3 build_grid.py` regenerates `grid_data.json` and `heat-med-map.html` from the analysis outputs in `probe_results/`. The full pipeline is `python3 local_analysis.py`, then `source ~/.system_public_env && python3 api_pull.py`, then `python3 build_grid.py`.
