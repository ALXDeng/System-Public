#!/usr/bin/env python3
"""Local version of the coverage probe, run on the Dataverse release of the
System Public Graph (doi:10.7910/DVN/7V6JDO). No API key, no rate limit.

Evidence tiers per drug class:
  direct   - a finding links a drug variable/concept to a heat variable/concept
  modifier - a single variable names both a drug and heat (e.g. "heat
             hospitalization among diuretic users"): effect-modification evidence
  bridged  - drug -> mechanism findings exist AND heat -> same mechanism exists
  gap      - none of the above

Usage:  python3 local_analysis.py
Inputs: ./dataverse/system-public-graph-v1-*.csv
Output: ./probe_results/local_*.{txt,csv,json}
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

csv.field_size_limit(sys.maxsize)
HERE = os.path.dirname(os.path.abspath(__file__))
DV = os.path.join(HERE, "dataverse")
OUT = os.path.join(HERE, "probe_results")


def dv(name):
    for ext in (".csv", ".tab"):
        p = os.path.join(DV, f"system-public-graph-v1-{name}{ext}")
        if os.path.exists(p):
            return p
    sys.exit(f"missing dataverse file: {name}")


# Drug classes: concept labels to ground on, plus regexes for free-text variable names.
DRUGS = {
    "Diuretics": (["diuretic", "loop diuretic", "thiazide", "furosemide", "hydrochlorothiazide", "spironolactone",
                   "bumetanide", "torasemide", "chlorthalidone", "indapamide"],
                  r"diuretic|furosemide|frusemide|thiazide|spironolactone|bumetanide|torsemide|torasemide|chlorthalidone|indapamide"),
    "Beta blockers": (["beta blocker", "metoprolol", "propranolol", "atenolol", "bisoprolol", "carvedilol"],
                      r"beta[- ]?blocker|β[- ]?blocker|metoprolol|propranolol|atenolol|bisoprolol|carvedilol"),
    "ACE inhibitors / ARBs": (["ACE inhibitor", "lisinopril", "enalapril", "ramipril", "angiotensin receptor blocker",
                               "angiotensin II receptor antagonist", "losartan", "valsartan"],
                              r"\bace[- ]?inhibitor|\bacei\b|\barbs?\b|angiotensin[- ]converting|angiotensin (ii )?receptor|lisinopril|enalapril|ramipril|losartan|valsartan|candesartan|\bras(i)? (blocker|inhibitor)"),
    "Calcium channel blockers": (["calcium channel blocker", "amlodipine", "diltiazem", "verapamil"],
                                 r"calcium[- ]channel[- ]blocker|\bccbs?\b|amlodipine|diltiazem|verapamil|nifedipine"),
    "Antihypertensives (any)": (["antihypertensive drug"], r"antihypertensive|blood pressure[- ]lowering (drug|medication)"),
    "Anticholinergics": (["anticholinergic", "oxybutynin", "diphenhydramine", "antihistamine", "benztropine"],
                         r"anticholinergic|antimuscarinic|\bdace\b|oxybutynin|diphenhydramine|antihistamin|benztropine|scopolamine|hydroxyzine"),
    "Antipsychotics": (["antipsychotic", "olanzapine", "clozapine", "haloperidol", "quetiapine", "risperidone"],
                       r"antipsychotic|neuroleptic|olanzapine|clozapine|haloperidol|quetiapine|risperidone|aripiprazole|chlorpromazine"),
    "Lithium": (["lithium carbonate", "lithium"], r"\blithium"),
    "Antidepressants": (["antidepressant", "selective serotonin reuptake inhibitor", "tricyclic antidepressant",
                         "amitriptyline", "sertraline", "fluoxetine"],
                        r"antidepressant|\bssris?\b|\bsnris?\b|serotonin reuptake|tricyclic|amitriptyline|nortriptyline|sertraline|fluoxetine|citalopram|paroxetine|venlafaxine"),
    "Benzodiazepines / sedatives": (["benzodiazepine", "sedative"],
                                    r"benzodiazepine|sedative|anxiolytic|hypnotic (drug|medication)|hypnotics|diazepam|lorazepam|alprazolam|zolpidem"),
    "Anticonvulsants": (["anticonvulsant", "topiramate", "zonisamide"], r"anticonvulsant|antiepileptic|topiramate|zonisamide"),
    "Stimulants": (["methylphenidate", "amphetamine", "stimulant"], r"stimulant medication|methylphenidate|amphetamine|adhd medication"),
    "Opioids": (["opioid"], r"\bopioid|morphine|oxycodone|fentanyl|methadone|buprenorphine"),
    "Insulin": ([],  # the "insulin" concept is mostly the hormone; ground on names only
                r"\binsulin (use|therapy|treatment|users?|injection|pump|absorption|disappearance|action|pharmacokinetic|requirement|dose|dosage|infusion)|insulin-treated|on insulin|(use|using) insulin|insulin-using"),
    "SGLT2 inhibitors": (["SGLT2 inhibitor", "empagliflozin", "dapagliflozin", "canagliflozin"],
                         r"sglt-?2|gliflozin|sodium[- ]glucose co-?transporter"),
    "Other diabetes drugs": (["metformin", "sulfonylurea", "glibenclamide"],
                             r"metformin|sulfonylurea|sulphonylurea|glibenclamide|glyburide|glipizide|gliclazide|antidiabetic|hypoglycemic agent|glucose-lowering"),
    "NSAIDs": (["nonsteroidal anti-inflammatory drug", "ibuprofen", "naproxen", "diclofenac"],
               r"nsaid|non-?steroidal anti-?inflammatory|ibuprofen|naproxen|diclofenac"),
    # added 2026-11-14 (reframed scope: data-driven drug list)
    "GLP-1 agonists": (["semaglutide", "liraglutide", "dulaglutide", "exenatide"],
                       r"glp-?1 (receptor )?agonist|glp-?1ras?\b|glucagon-like peptide-?1 (receptor )?agonist|semaglutide|liraglutide|dulaglutide|exenatide|tirzepatide"),
    "Parkinson / dopaminergic": (["levodopa", "pramipexole", "ropinirole", "dopamine agonist"],
                                 r"levodopa|l-dopa|carbidopa|dopamine agonist|pramipexole|ropinirole|rotigotine|antiparkinson|anti-parkinson|bromocriptine"),
    "Cholinesterase inhibitors": (["donepezil", "rivastigmine", "galantamine"],
                                  r"cholinesterase inhibitor|donepezil|rivastigmine|galantamine"),
    "Medication (unspecified)": ([], r"medication|polypharmacy|prescri|drug use|psychotropic|drug-induced|adverse drug"),
}
DRUG_RE = {k: re.compile(v[1], re.I) for k, v in DRUGS.items()}

HEAT_RE = re.compile(
    r"heat[- ]?waves?|heat[- ]?stroke|heat[- ]related|heat illness|heat exhaustion|extreme heat|heat stress|"
    r"heat exposure|exposure to heat|heat index|hot (days?|weather|season|nights?|temperatures?|spells?)|"
    r"ambient temperature|high (ambient |outdoor |air )?temperatures?|warm season|warm(er)? weather|"
    r"temperature (above|increase|rise)|summer temperature|apparent temperature|wet[- ]bulb|hyperthermia|"
    r"outdoor temperatures?|(daily|mean|maximum|max|average)( (daily|mean|maximum|max|average|outdoor|air|ambient))* temperatures?|"
    r"ambient heat|local (skin )?heat(ing)?|skin heating|heat application|heat dome|summer heat|hot (climate|environment)|"
    r"thermal stress|heat (warning|alert|event|episode)s?|excessive heat|temperature-related|hot spells?|warm spells?|heat",
    re.I)
# Things that match "heat"/"hyperthermia" but are not environmental heat.
HEAT_EXCLUDE = re.compile(
    r"malignant hyperthermia|heat shock|heat[- ]?(inactivat|treated|killed|map|capacity|flux|production|stable|labile|"
    r"pain|pain threshold|stimul|loss|pad|ing|er\b|ed\b|-ed)|hyperthermia \(4\d|hyperthermic intraperitoneal|"
    r"radiotherapy|chemotherapy|ablation|thermotherap|hipec|wheat|cheat|sheath|heath|theater|theatre|heated|heating|"
    r"heater|heartbeat|hyperalgesia|sensitivity to heat|heat (pain|detection|tolerance)|detection threshold|tolerance threshold|"
    r"heat[- ]prescription|heat storage|heat[- ]shock|damp[- ]heat|hot food|heat[- ]processed|"
    r"heat rigidified|heat devices|heat-induced thrombosis", re.I)
DRUG_EXCLUDE = re.compile(r"genotype|hypnotic state|under hypnosis|allele|polymorphism|gene\b|wastewater|sewage|influent|effluent|river|daily average of", re.I)
HEAT_STRONG = re.compile(r"heat[- ]?waves?|heat[- ]?stroke|heat[- ]related|heat illness|heat exhaustion|extreme heat|hot days?|"
                         r"ambient heat|skin heating|local (skin )?heat(ing)?|heat dome|summer heat", re.I)
# A study is heat-context when its population is described in these terms.
HEAT_CTX = re.compile(r"heat[- ]?waves?|heat[- ]?stroke|heat[- ]related|heat illness|heat exhaustion|extreme heat|heat dome|"
                      r"summer heat|ambient heat|hot (weather|days|season|summer|spells?)|high (ambient |outdoor )?temperatures?|"
                      r"heat exposure|exposed to heat", re.I)
# Populations that don't speak to therapeutic use in people (bridge counts only).
OFFTOPIC = re.compile(r"\b(rats?|mice|mouse|murine|rodents?|dogs?|canine|cats?|feline|pigs?|piglets?|porcine|swine|rabbits?|"
                      r"sheep|ovine|horses?|equine|cattle|bovine|cows?|calves|zebrafish|monkeys?|macaques?|primates|hamsters?|"
                      r"broilers?|chickens?|animals?|in vitro|cell lines?|cultured cells|poisoning|overdoses?|intoxicat\w*|"
                      r"self-poisoning|toxicology|suicide attempts?)\b", re.I)
PAREN_POP = re.compile(r"\((among|in|of|for)\b[^)]*\)", re.I)


def exposure_drug_classes(name):
    """Drug classes named as the exposure itself, not only inside an '(among ... )' population clause."""
    return drug_classes(PAREN_POP.sub("", name or ""))

HEAT_CONCEPTS = ["heat stroke", "heat illness", "heat exhaustion", "heat wave", "heat stress", "hyperthermia",
                 "extreme heat", "ambient temperature", "hot weather", "heat"]
MECHANISMS = {
    "Hyponatremia / electrolytes": ["hyponatremia", "hypokalemia", "hyperkalemia", "electrolyte imbalance", "hypernatremia"],
    "Dehydration / volume": ["dehydration", "hypovolemia"],
    "Acute kidney injury": ["acute kidney injury", "renal failure", "kidney failure"],
    "Impaired sweating / thermoregulation": ["hypohidrosis", "anhidrosis", "thermoregulation", "sweating", "perspiration"],
    "Hypotension / falls": ["orthostatic hypotension", "hypotension", "syncope", "falling", "fall"],
    "Glucose": ["hypoglycemia", "diabetic ketoacidosis", "hyperglycemia"],
    "Rhabdomyolysis": ["rhabdomyolysis"],
    "Lithium toxicity / drug levels": ["lithium toxicity", "drug toxicity"],
    "Hospitalisation / ED / death": ["hospitalization", "emergency department visit", "mortality", "death"],
}
MECH_RE = {
    "Hyponatremia / electrolytes": r"hyponatr|hypokal|hyperkal|hypernatr|electrolyte|serum sodium|potassium level",
    "Dehydration / volume": r"dehydrat|hypovol|fluid loss|volume depletion",
    "Acute kidney injury": r"acute kidney injury|\baki\b|renal failure|kidney failure|acute renal",
    "Impaired sweating / thermoregulation": r"hypohidrosis|anhidrosis|sweat|thermoregulat|core (body )?temperature|perspiration",
    "Hypotension / falls": r"hypotension|syncope|\bfalls?\b",
    "Glucose": r"hypoglyc|ketoacidosis|hyperglyc",
    "Rhabdomyolysis": r"rhabdomyolysis",
    "Lithium toxicity / drug levels": r"lithium (toxicity|level|intoxication)|drug toxicity",
    "Hospitalisation / ED / death": None,  # too generic for name matching
}
MECH_RE = {k: re.compile(v, re.I) for k, v in MECH_RE.items() if v}


LEVELS_KEY = "Lithium toxicity / drug levels"
GENERIC = {"Hospitalisation / ED / death"}  # every drug and heat touch this; not a mechanism


def is_heat_name(name):
    return bool(name and HEAT_RE.search(name) and not (HEAT_EXCLUDE.search(name) and not HEAT_STRONG.search(name)))


def drug_classes(name):
    if not name or DRUG_EXCLUDE.search(name):
        return []
    return [k for k, r in DRUG_RE.items() if r.search(name)]


def mech_classes(name):
    return [k for k, r in MECH_RE.items() if name and r.search(name)]


def main():
    os.makedirs(OUT, exist_ok=True)
    log = open(os.path.join(OUT, "local_output.txt"), "w")

    def p(*a):
        s = " ".join(str(x) for x in a)
        print(s)
        log.write(s + "\n")

    # 1. Concepts
    by_label, by_alias = {}, defaultdict(list)
    with open(dv("concepts")) as f:
        for r in csv.DictReader(f):
            by_label.setdefault(r["wikidata_label"].lower(), r)
            try:
                for a in json.loads(r["wikidata_aliases"] or "[]"):
                    by_alias[a.lower()].append(r)
            except ValueError:
                pass

    def resolve(term):
        t = term.lower()
        if t in by_label:
            return by_label[t], "exact"
        if by_alias.get(t):
            return by_alias[t][0], "alias"
        return None, "none"

    concept_kind = {}  # concept id -> (kind, class, label)
    p("=== 1. CONCEPTS (exact label or alias match in Dataverse concepts) ===")
    for kind, groups in (("drug", {k: v[0] for k, v in DRUGS.items()}), ("heat", {"Heat": HEAT_CONCEPTS}),
                         ("mechanism", MECHANISMS)):
        for cls, terms in groups.items():
            got = []
            for t in terms:
                c, how = resolve(t)
                if c:
                    concept_kind.setdefault(c["system_id"], (kind, cls, c["wikidata_label"]))
                    got.append(f"{c['wikidata_label']}" + ("" if how == "exact" else "*"))
            p(f"  {kind:9} {cls:38} {', '.join(got) or 'NONE'}")
    p("  (* = matched via alias)")

    # 2. Variables: classify heat / drug / mechanism, by name or by concept
    var = {}
    with open(dv("variables")) as f:
        for r in csv.DictReader(f):
            nm, cid = r["name"], r["concept_id"]
            ck = concept_kind.get(cid)
            heat = is_heat_name(nm) or (ck and ck[0] == "heat" and not HEAT_EXCLUDE.search(nm))
            drugs = set(drug_classes(nm))
            if ck and ck[0] == "drug" and not DRUG_EXCLUDE.search(nm):
                drugs.add(ck[1])
            mechs = set(mech_classes(nm))
            if ck and ck[0] == "mechanism":
                mechs.add(ck[1])
            if heat or drugs or mechs:
                var[r["system_id"]] = (nm, bool(heat), drugs, mechs)
    n_heat = sum(1 for v in var.values() if v[1])
    modifiers = {vid: v for vid, v in var.items() if v[1] and v[2]}
    p(f"\n=== 2. VARIABLES === heat: {n_heat}; drug: {sum(1 for v in var.values() if v[2])}; "
      f"mechanism: {sum(1 for v in var.values() if v[3])}; heat AND drug in one name: {len(modifiers)}")
    for vid, (nm, _, d, _) in list(modifiers.items())[:80]:
        p(f"  [{'/'.join(sorted(d))}] {nm[:150]}")

    heat_names = sorted(v[0] for v in var.values() if v[1])
    with open(os.path.join(OUT, "local_heat_variables.txt"), "w") as f:
        f.write("\n".join(heat_names))

    # 2b. Concept-level relationships (the graph's own pair counts)
    rel = defaultdict(lambda: [0, 0])
    with open(dv("relationships")) as f:
        for r in csv.DictReader(f):
            a, b = concept_kind.get(r["source_concept.system_id"]), concept_kind.get(r["target_concept.system_id"])
            if not a or not b or a[0] == b[0]:
                continue
            if a[0] != "drug" and b[0] == "drug":
                a, b = b, a
            key = (a[0], a[1], b[1], f"{a[2]} - {b[2]}")
            rel[key][0] += int(r["num_studies"] or 0)
            rel[key][1] += int(r["num_findings"] or 0)
    p("\n=== 2b. CONCEPT RELATIONSHIPS: drug x heat, drug x mechanism, heat x mechanism (studies/findings) ===")
    with open(os.path.join(OUT, "local_concept_pairs.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kind", "class", "partner_class", "pair", "studies", "findings"])
        for k, (s_, f_) in sorted(rel.items(), key=lambda x: (x[0][0], x[0][1], -x[1][0])):
            w.writerow([*k, s_, f_])
            if k[2] == "Heat" or k[1] == "Heat":
                p(f"  {k[3][:70]:70} {s_}/{f_}")

    # 2c. Study pre-pass: heat-context and off-topic populations
    heat_ctx, offtopic, pop_drug = set(), set(), {}
    with open(dv("studies")) as f:
        for r in csv.DictReader(f):
            pop = r["population_string"] or ""
            pdc = [c for c in exposure_drug_classes(pop) if c != "Medication (unspecified)"]
            if pdc:
                pop_drug[r["study_id"]] = pdc
            if HEAT_CTX.search(pop):
                heat_ctx.add(r["study_id"])
            if OFFTOPIC.search(pop):
                offtopic.add(r["study_id"])
    p(f"\n=== 2c. STUDIES === heat-context populations: {len(heat_ctx)}; off-topic populations: {len(offtopic)}")

    # 3. Studies (for type / population / doi)
    needed_studies = set()
    rows_ctx, rows_pop = [], []
    drug_mech_raw = defaultdict(set)  # old rule (any order, any population), for comparison
    drop = {"reversed": 0, "population clause": 0, "off-topic population": 0}
    rows_direct, rows_mod, rows_heat_mech = [], [], []
    drug_mech = defaultdict(set)    # (drug class, mech) -> studies
    heat_mech = defaultdict(set)    # mech -> studies
    drug_mech_rows = defaultdict(list)  # (drug class, mech) -> sample findings

    with open(dv("associations")) as f:
        for a in csv.DictReader(f):
            v1, v2 = var.get(a["variable_1_id"]), var.get(a["variable_2_id"])
            if not v1 and not v2:
                continue
            v1 = v1 or (a["variable_1_name"], False, set(), set())
            v2 = v2 or (a["variable_2_name"], False, set(), set())
            study = a["study_id"]
            rec = {
                "association_id": a["system_id"], "pubmed_id": a["pubmed_id"], "study_id": study,
                "var1": v1[0], "var2": v2[0], "statistic_type": a["statistic_type"],
                "value": a["statistic_value"], "ci_lower": a["ci_lower"], "ci_upper": a["ci_upper"],
                "p_value": a["p_value"],
            }
            # modifier: either variable names both drug and heat
            mod_cls = (v1[2] if v1[1] else set()) | (v2[2] if v2[1] else set())
            if mod_cls:
                rows_mod.append({**rec, "classes": " | ".join(sorted(mod_cls))})
                needed_studies.add(study)
            # direct: heat on one side, drug on the other
            for h, d in ((v1, v2), (v2, v1)):
                if h[1] and d[2] and not d[1]:
                    rows_direct.append({**rec, "classes": " | ".join(sorted(d[2])), "heat_side": h[0], "drug_side": d[0]})
                    needed_studies.add(study)
            # heat-context: drug finding inside a study whose population is a heat setting
            if study in heat_ctx and not (v1[1] or v2[1]):
                ctx_cls = set(exposure_drug_classes(v1[0])) | set(exposure_drug_classes(v2[0]))
                if ctx_cls:
                    rows_ctx.append({**rec, "classes": " | ".join(sorted(ctx_cls))})
                    needed_studies.add(study)
            # heat finding inside a population defined by a drug ("adults who use insulin")
            if (v1[1] or v2[1]) and study in pop_drug and not (v1[2] or v2[2]):
                rows_pop.append({**rec, "classes": " | ".join(pop_drug[study]),
                                 "heat_side": v1[0] if v1[1] else v2[0], "drug_side": "(population)"})
                needed_studies.add(study)
            # lithium levels name the drug inside the mechanism; count any finding whose outcome is the level
            if LEVELS_KEY in v2[3] and "Lithium" in v2[2] and not v1[1]:
                drug_mech[("Lithium", LEVELS_KEY)].add(study)
                lst = drug_mech_rows[("Lithium", LEVELS_KEY)]
                if len(lst) < 400:
                    lst.append({**rec, "classes": "Lithium", "mechanisms": LEVELS_KEY, "drug_side": v1[0], "mech_side": v2[0]})
                    needed_studies.add(study)
            # drug <-> mechanism, old rule kept for comparison
            for d, m in ((v1, v2), (v2, v1)):
                for dc in d[2]:
                    for mc in m[3]:
                        if d is not m:
                            drug_mech_raw[(dc, mc)].add(study)
            # drug <-> mechanism, new rule: drug is the exposure (variable 1), named outside a population
            # clause, mechanism is the outcome (variable 2), population is people on therapy
            if v1[2] and v2[3] and not v2[2]:
                named = set(drug_classes(v1[0]))
                grounded = v1[2] - named          # from concept_id, not visible in the name
                exp_cls = set(exposure_drug_classes(v1[0])) | grounded
                if not exp_cls:
                    drop["population clause"] += 1
                elif study in offtopic:
                    drop["off-topic population"] += 1
                else:
                    for dc in exp_cls:
                        for mc in v2[3]:
                            drug_mech[(dc, mc)].add(study)
                            lst = drug_mech_rows[(dc, mc)]
                            if len(lst) < 400:
                                lst.append({**rec, "classes": dc, "mechanisms": mc, "drug_side": v1[0], "mech_side": v2[0]})
                                needed_studies.add(study)
            elif v2[2] and v1[3] and not v1[2]:
                drop["reversed"] += 1
            # heat <-> mechanism
            for h, m in ((v1, v2), (v2, v1)):
                if h[1] and m[3] and not m[1]:
                    for mc in m[3]:
                        heat_mech[mc].add(study)
                    rows_heat_mech.append({**rec, "mechanisms": " | ".join(sorted(m[3]))})
                    needed_studies.add(study)

    studies = {}
    with open(dv("studies")) as f:
        for r in csv.DictReader(f):
            if r["study_id"] in needed_studies:
                studies[r["study_id"]] = r
    dm_rows = [r for lst in drug_mech_rows.values() for r in lst]
    for rows in (rows_direct, rows_mod, rows_heat_mech, dm_rows, rows_ctx, rows_pop):
        for r in rows:
            s = studies.get(r["study_id"], {})
            r.update(doi=s.get("doi", ""), study_type=s.get("study_type", ""), population=s.get("population_string", ""))

    # 4. Report
    def by_class(rows):
        out = defaultdict(lambda: [set(), 0])
        for r in rows:
            for c in r["classes"].split(" | "):
                out[c][0].add(r["study_id"])
                out[c][1] += 1
        return out

    dc, mc_ = by_class(rows_direct), by_class(rows_mod)
    p("\n=== 3. HEAT x MECHANISM (studies) ===")
    for m in MECHANISMS:
        p(f"  {m:40} {len(heat_mech.get(m, ()))}")

    p("\n=== 4. SUMMARY BY DRUG CLASS (distinct studies / findings) ===")
    p(f"  {'class':30} {'direct':>12} {'modifier':>12} {'bridged studies (via mechanisms)'}")
    summary = []
    for cls in DRUGS:
        br = {m: len(s) for (c, m), s in drug_mech.items() if c == cls and heat_mech.get(m) and m not in GENERIC}
        d_s, d_f = len(dc[cls][0]), dc[cls][1]
        m_s, m_f = len(mc_[cls][0]), mc_[cls][1]
        tier = "direct" if d_s or m_s else ("bridged" if br else "gap")
        summary.append({"class": cls, "tier": tier, "direct_studies": d_s, "direct_findings": d_f,
                        "modifier_studies": m_s, "modifier_findings": m_f,
                        "bridged": br, "bridged_studies": sum(br.values())})
        p(f"  {cls:30} {f'{d_s}/{d_f}':>12} {f'{m_s}/{m_f}':>12} "
          + ", ".join(f"{m.split(' /')[0]} {n}" for m, n in sorted(br.items(), key=lambda x: -x[1])))

    p(f"\n=== 4b. BRIDGE CLEAN-UP === rows dropped: {drop}")
    p(f"  {'class':30} {'mechanism':38} {'old':>5} {'new':>5}")
    for (c_, m_), s_ in sorted(drug_mech_raw.items()):
        if m_ in GENERIC:
            continue
        p(f"  {c_:30} {m_:38} {len(s_):5} {len(drug_mech.get((c_, m_), ())):5}")

    p(f"\n=== 4d. HEAT FINDINGS IN DRUG-DEFINED POPULATIONS === {len(rows_pop)} rows, {len({r['study_id'] for r in rows_pop})} studies")
    for r in rows_pop[:60]:
        p(f"  [{r['pubmed_id']}] ({r['classes']}) {r['var1'][:70]}  x  {r['var2'][:60]}  ({r['statistic_type'][:18]} {r['value']} [{r['ci_lower']}, {r['ci_upper']}]) | {r['population'][:70]}")
    p(f"\n=== 4c. HEAT-CONTEXT DRUG FINDINGS === {len(rows_ctx)} rows, {len({r['study_id'] for r in rows_ctx})} studies")
    for r in rows_ctx[:80]:
        p(f"  [{r['pubmed_id']}] ({r['classes']}) {r['var1'][:70]}  x  {r['var2'][:60]}  ({r['statistic_type'][:18]} {r['value']} [{r['ci_lower']}, {r['ci_upper']}]) | {r['population'][:70]}")

    p("\n=== 5. DIRECT + MODIFIER FINDINGS (first 120) ===")
    for r in (rows_mod + rows_direct)[:120]:
        p(f"  [{r['pubmed_id']}] ({r['classes']}) {r['var1'][:80]}  x  {r['var2'][:80]}  "
          f"({r['statistic_type']} {r['value']} [{r['ci_lower']}, {r['ci_upper']}])")

    fields = ["classes", "pubmed_id", "doi", "study_type", "var1", "var2", "statistic_type", "value",
              "ci_lower", "ci_upper", "p_value", "population", "association_id", "study_id"]
    for name, rows, extra in (("local_heat_drug_direct.csv", rows_direct, ["heat_side", "drug_side"]),
                              ("local_heat_drug_modifier.csv", rows_mod, []),
                              ("local_heat_context_drug.csv", rows_ctx, []),
                              ("local_heat_drug_population.csv", rows_pop, ["heat_side", "drug_side"]),
                              ("local_heat_mechanism.csv", rows_heat_mech, ["mechanisms"]),
                              ("local_drug_mechanism_findings.csv", dm_rows, ["mechanisms", "drug_side", "mech_side"])):
        fl = [x for x in fields if x != "classes" or name != "local_heat_mechanism.csv"] + extra
        with open(os.path.join(OUT, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fl, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    with open(os.path.join(OUT, "local_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(OUT, "local_drug_mechanism.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "mechanism", "drug_mech_studies", "heat_mech_studies"])
        for (c, m), s in sorted(drug_mech.items()):
            w.writerow([c, m, len(s), len(heat_mech.get(m, ()))])
    p(f"\nRows: direct {len(rows_direct)}, modifier {len(rows_mod)}, heat-mechanism {len(rows_heat_mech)}. "
      f"Saved in {OUT}")


if __name__ == "__main__":
    main()
