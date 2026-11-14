#!/usr/bin/env python3
"""Join the three lenses per drug class into grid/lenses_data.json and render grid/lenses.html.

  research  grid/grid_data.json        (System graph, built by build_grid.py)
  guidance  guidance.json              (CDC + NYC DOH, hand-coded 2026-11-14; CALOR pending; WHO not reviewed)
  label     probe_results/fda_labels.json  (openFDA label text, built by label_pull.py)

  python3 build_lenses.py
"""
import json
import os
from collections import Counter

CODED = ["cdc", "nyc", "az", "ukhsa", "canada", "ansm", "who"]
UNCLEAR = {"24334574"}  # oral glucose-lowering drugs, seasonal; direction of effect needs checking
HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(HERE, "grid")

# Hand-written pattern + one line per class. Patterns:
#   agree        guidance, label and research point the same way
#   overwarned   guidance and labels warn; measured heat evidence is null or thin
#   label_silent research links the class to heat harm; labels never mention heat
#   missed       research shows a heat risk that guidance omits or names for another reason
#   storage      a storage/handling problem; guidance and labels agree, the graph has nothing
FINDINGS = {
    "Antipsychotics": ("agree", "All three agree. Olanzapine, quetiapine and haloperidol labels warn about heat (clozapine's mentions heat stroke only as something to rule out in NMS), and all 7 guidance sources name the class. In 2003 France antipsychotic users had twice the odds of heat-wave death (OR 2.09); in the 2021 BC heat dome, dispensed antipsychotics raised death among people with schizophrenia, up to OR 4.05 for combinations (not in the graph). One UK study found no added heat-wave risk from psychotropics."),
    "Antidepressants": ("agree", "Mostly agree. Heat-wave death OR 1.71 (2003 France); starting an SSRI raised admission for dehydration or heat illness (1.17). One UK study found no added risk. 6 of 7 sources name the class. Tricyclic labels warn about hot weather; SSRI/SNRI labels mention hyperthermia only in serotonin syndrome."),
    "Anticholinergics": ("agree", "All 7 sources name them and labels lead with reduced sweating. Outside the graph, 25 studies address it: lab studies of atropine and sweating, heat-stroke case reports (e.g. oxybutynin), and the Layton Medicare study. The graph extracted only one, a null mortality study (OR 1.21, p = 0.31). OTC diphenhydramine labels say nothing about heat."),
    "Lithium": ("overwarned", "All 7 sources name lithium and Canada gives a hydration action; labels warn about dehydration. Yet the two temperature studies in the graph found no change in lithium levels. 15 studies exist in the literature (mostly case reports and class-wide psychotropic studies); the graph has drug findings from 3."),
    "Topiramate / zonisamide": ("agree", "Labels carry a strong heat warning (reduced sweating, heat stroke in children) and 6 of 7 guidance sources name it. Six case reports and pilot studies of reduced sweating exist outside the graph; the graph extracted none, so it shows only weak mechanism support."),
    "Diuretics": ("label_silent", "Measured repeatedly: heatstroke mortality (class-wide), diuretic hyponatraemia rising with outdoor temperature, renal decline in heat, and admissions after starting a diuretic. One UK diabetes study found no added risk. Yet furosemide and spironolactone labels warn only about dehydration, never heat."),
    "ACE inhibitors / ARBs": ("label_silent", "Class-wide heatstroke mortality (HR 2.17); starting an ACE inhibitor with a diuretic raised admission for dehydration or heat illness 2.79-fold, the highest of any class studied. No label mentions heat."),
    "Beta blockers": ("label_silent", "Guidance names reduced sweating and class-wide mortality data exist, but no label mentions heat. Heart rate is also blunted, which can hide heat strain from wearables."),
    "Calcium channel blockers": ("label_silent", "Seasonal BP swings and class-wide heatstroke mortality; labels are silent on heat and dehydration."),
    "NSAIDs": ("label_silent", "Strongest kidney-injury bridge in the graph (50 studies) and NSAIDs raised mild heat illness in military recruits. The heat-wave triple-whammy study was null. Labels warn about dehydration and kidney function, never heat."),
    "Benzodiazepines / sedatives": ("label_silent", "Evidence conflicts: severe sedative poisonings rise with temperature (Germany) and one 2003 study found higher risk, but another found lower risk and starting hypnotics or anxiolytics did not raise heat admissions. Named by 4 of 7 guidance sources; labels are silent."),
    "Insulin": ("missed", "Heat raises serious hypoglycaemia in older users (OR 1.38), and warmth speeds absorption of soluble insulin (three experiments; intermediate-acting insulin was unaffected). No guidance source mentions hypoglycaemia: US and Canada treat insulin as a storage problem. Labels cover storage only."),
    "SGLT2 inhibitors": ("missed", "Named by only 1 of 7 guidance sources (ANSM). Labels warn about volume depletion without naming heat. The literature is mixed: dehydration adverse events peak in July–August (Japan), but canagliflozin was well tolerated in hot-climate trial subsets. The graph extracted none of these."),
    "Metformin and sulfonylureas": ("missed", "Named by only 1 of 7 guidance sources (ANSM). Outside the graph, hotter days raised serious hypoglycaemia in glimepiride and glyburide users (not glipizide, US). Metformin labels warn about dehydration; sulfonylurea labels say nothing about heat."),
    "Opioids": ("missed", "Overdose rises in heat: ED visits (OR 1.079 per step, vetted), US overdose deaths (2026 national study) and severe opioid poisonings (Germany). Not every study agrees (BC deaths null; one study found cold, not heat). Five of 7 sources name opioids, none for overdose; only the fentanyl patch label warns about heat."),
    "Stimulants": ("missed", "Mixed. Heat raises overdose deaths from cocaine and psychostimulants (USA; NYC above 24 °C) and methylphenidate raised mild heat illness in recruits, but ADHD patients on stimulants had LOWER heat-illness risk in one database study. Guidance names raised body temperature; amphetamine labels mention hyperthermia only in serotonin syndrome."),
    "GLP-1 agonists": ("thin", "Named only by ANSM (France). Labels warn about kidney injury from volume depletion after vomiting or diarrhoea, but never mention heat. No heat study in the graph or the literature found; FDA adverse-event reports list 70 heat illness reports with GLP-1 drugs (raw count, not adjusted for use). Use is growing fast."),
    "Parkinson / dopaminergic": ("thin", "Named by ANSM and Health Canada. Levodopa, pramipexole and ropinirole labels mention hyperthermia only on abrupt withdrawal. Evidence is lab physiology (bromocriptine and sweat-gland adaptation) and case reports, including a hyperpyrexia syndrome in a heat wave."),
    "Cholinesterase inhibitors": ("thin", "Named by ANSM and Health Canada, for sweating and GI fluid loss. Rivastigmine patch labels warn against external heat; donepezil and galantamine labels are silent. The graph links the class only to falls."),
    "Combination: diuretic + ACEi/ARB (± NSAID)": ("missed", "Starting an ACE inhibitor with a diuretic carried the highest admission risk for dehydration or heat illness of any class studied (2.79-fold, not in the graph). Older inpatients on the full triple whammy in heat waves had no clear excess kidney injury (OR 1.02, small study). Only CDC and NYC mention the combination, without an action."),
    "Polypharmacy (several heat-sensitising drugs)": ("agree", "People on any medication had triple the odds of heat illness in Odisha, India (aOR 3.09); a US study of medication count was null. CDC, NYC, Arizona and WHO Europe all point to reviewing people on several such drugs, and WHO recommends at-risk registers that include medication use."),
    "Heat-labile emergency products": ("storage", "Guidance warns about hot cars and inhaler labels say canisters can burst above 49 °C. But epinephrine and fentanyl stayed within specification for a year in an ambulance (13.9–33.9 °C) and four resuscitation drugs survived 70 °C. Heat does change patch delivery: heating a nitroglycerin patch doubled plasma levels."),
}
PATTERNS = [
    ("missed", "Heat risk measured, guidance misses it", "Research shows harm in heat; guidance omits the class or names it for another reason."),
    ("label_silent", "Heat risk measured, labels silent", "Research links the class to heat harm; FDA labels never say heat."),
    ("overwarned", "Warned everywhere, measured weakly", "Guidance and labels lead with these; the heat studies that exist are null."),
    ("agree", "All three agree", "Guidance, labels and research point the same way."),
    ("thin", "Little evidence, little guidance", "Newer or overlooked classes: one or two guidance sources, no heat study."),
    ("storage", "Storage problem", "Guidance and labels agree; the research graph has nothing."),
]


def drug_status(d):
    if not d.get("n_labels"):
        return "none"
    if d["heat_warning"] >= 0.5:
        return "heat"
    if d["heat_patient"] >= 0.5:
        return "heat_patient"
    if d.get("burst_share", 0) >= 0.5 or d.get("heat_handling_share", 0) >= 0.5:
        return "handling"
    if d.get("hyperthermia_only", 0) >= 0.5:
        return "hyperthermia"
    if d["dehyd_warning"] >= 0.5:
        return "dehydration"
    return "silent"


def research_summary(row):
    best, lead = None, None
    order = {("direct", "risk"): 6, ("direct", "lower"): 5, ("direct", "null"): 4, ("bridged", 3): 3.3, ("bridged", 2): 3.2,
             ("bridged", 1): 3.1, ("partial", None): 2, ("gap", None): 1}
    for b, c in row["cells"].items():
        if c["tier"] == "none":
            continue
        key = (c["tier"], c.get("signal") if c["tier"] == "direct" else c.get("strength") if c["tier"] == "bridged" else None)
        sc = order.get(key, 0) + (0.05 if c.get("vetted", True) else 0)
        if c["tier"] == "direct" and c.get("direct") and all(d["pmid"] in UNCLEAR for d in c["direct"]):
            continue  # direction of effect unclear: do not let it count as direct evidence
        if best is None or sc > best[0]:
            best = (sc, key, b, c)
    _, key, bucket, cell = best
    studies = [s for c in row["cells"].values() for s in c.get("direct", []) if s["pmid"] not in UNCLEAR]
    for want in (lambda s: s["effect"] == "risk" and s["vetted"], lambda s: s["effect"] == "risk", lambda s: True):
        lead = next((s for s in studies if want(s)), None)
        if lead:
            break
    mech = next((m for m in cell.get("mechanisms", []) if m.get("primary")), None)
    tier = key[0]
    label = {"direct": {"risk": "Measured in heat: raises risk", "null": "Measured in heat: no clear effect", "lower": "Measured in heat: lower risk"}.get(key[1]),
             "bridged": f"Mechanism only ({ {1: 'weak', 2: 'moderate', 3: 'strong'}[key[1]] })" if tier == "bridged" else None,
             "partial": "Drug side only", "gap": "Nothing in the graph"}[tier]
    pmids = sorted({s["pmid"] for s in studies})
    return {"tier": tier, "signal": key[1] if tier == "direct" else None, "strength": key[1] if tier == "bridged" else None,
            "vetted": cell.get("vetted", True), "label": label, "bucket": bucket,
            "lead": {"pmid": lead["pmid"], "summary": lead["summary"], "vetted": lead["vetted"], "effect": lead["effect"]} if lead else None,
            "mechanism": {"name": mech["mechanism"], "drug": mech["drug_studies"], "heat": mech["heat_studies"]} if mech and tier != "direct" else None,
            "n_direct_studies": len(pmids)}


UMBRELLA = {"Antihypertensives (unspecified)": ["Diuretics", "ACE inhibitors / ARBs", "Beta blockers", "Calcium channel blockers"],
            "Psychotropics (unspecified)": ["Antipsychotics", "Antidepressants", "Benzodiazepines / sedatives", "Lithium"]}
PRIMARY = ("epidemiology", "seasonal", "experimental", "physiology", "case", "storage")


READ = json.load(open(os.path.join(HERE, "literature_read.json")))["studies"]


CLASS_EFFECT = {  # class-specific results inside multi-class studies (from the abstracts)
    "27378245": {"Topiramate / zonisamide": "null", "Benzodiazepines / sedatives": "null", "Parkinson / dopaminergic": "null"},
    "39433419": {"Insulin": "context"},
}


LIT_ALIAS = {"Polypharmacy (several heat-sensitising drugs)": "Any medication / polypharmacy"}
LIT_PMIDS = {"Combination: diuretic + ACEi/ARB (± NSAID)": {"27378245", "29116624", "27992525", "38831143"}}


def literature(lit, cls):
    out = []
    pm_extra = LIT_PMIDS.get(cls, set())
    alias = LIT_ALIAS.get(cls)
    for st in lit:
        if st["etype"] not in PRIMARY:
            continue
        direct = cls in st["classes"] or (alias in st["classes"] if alias else False) or st["pmid"] in pm_extra
        wide = [u for u, kids in UMBRELLA.items() if u in st["classes"] and cls in kids]
        if direct or wide:
            eff, fnd = READ.get(st["pmid"], ("harm_reported" if st["etype"] == "case" else ("graph" if st["drug_extracted"] else "unread"), ""))
            eff = CLASS_EFFECT.get(st["pmid"], {}).get(cls, eff)
            out.append({k: st[k] for k in ("pmid", "title", "year", "country", "etype", "graph", "drug_extracted", "note")} | {"class_wide": not direct, "effect": eff, "finding": fnd})
    out.sort(key=lambda x: (x["drug_extracted"], x["etype"] != "epidemiology", x["year"]), reverse=False)
    by = {}
    for x in out:
        by.setdefault(x["etype"], [0, 0]); by[x["etype"]][0] += 1; by[x["etype"]][1] += x["drug_extracted"]
    eff = Counter(x["effect"] for x in out)
    return {"n": len(out), "extracted": sum(x["drug_extracted"] for x in out), "by_type": by, "effects": dict(eff), "studies": out}


BEFORE_HOLD = {"Anticholinergics", "Antidepressants", "Antipsychotics", "Benzodiazepines / sedatives", "Beta blockers"}


def build_actions(grid):
    ex = json.load(open(os.path.join(HERE, "actions_extra.json")))
    rv = json.load(open(os.path.join(G, "review_fields.json")))["review"]
    spec = {r["class"]: r["specialties"] for r in grid["rows"]}
    items = []
    taken = {(c, a["bucket"], a["when"]) for c, lst in ex["classes"].items() for a in lst}
    for r in grid["rows"]:
        cls = r["class"]
        for b, c in r["cells"].items():
            if c["tier"] == "none" or not c.get("action"):
                continue
            when = {"Dose adjustment": "alert", "Closer monitoring": "alert", "Storage and stability": "before"}.get(b, "before" if cls in BEFORE_HOLD else "unwell")
            if (cls, b, when) in taken:
                continue
            risk_pm = [d["pmid"] for d in c.get("direct", []) if d["effect"] == "risk" and d["pmid"] not in UNCLEAR]
            basis = "study" if risk_pm else "mechanism" if c["tier"] == "bridged" else ("label" if "label" in (c.get("note") or "").lower() else "draft")
            trig, who, restart = (rv.get(cls, {}).get(b) or ["", "", ""])[:3]
            items.append({"class": cls, "bucket": b, "when": when, "text": c["action"], "who": who, "trigger": trig, "sources": [],
                          "pmids": risk_pm[:3], "basis": basis, "note": c.get("note", ""), "origin": "draft grid"})
            if restart:
                items.append({"class": cls, "bucket": b, "when": "after", "text": restart, "who": who, "trigger": "", "sources": [], "pmids": [],
                              "basis": "draft", "note": "", "origin": "draft grid"})
        for a in ex["classes"].get(cls, []):
            items.append({"class": cls, "trigger": "", "note": "", **a, "origin": "sourced"})
    for x in items:
        x["specialties"] = spec.get(x["class"], [])
    return {"timing": ex["timing"], "trigger_note": ex["trigger_note"], "all_classes": ex["all_classes"],
            "buckets": ["Dose adjustment", "Substitute or hold", "Closer monitoring", "Storage and stability", "Continue, don't stop", "Counsel and plan"],
            "items": items}


def main():
    grid = json.load(open(os.path.join(G, "grid_data.json")))
    guide = json.load(open(os.path.join(HERE, "guidance.json")))
    labels = json.load(open(os.path.join(HERE, "probe_results", "fda_labels.json")))
    pdp = os.path.join(HERE, "probe_results", "partd.json")
    partd = json.load(open(pdp)) if os.path.exists(pdp) else {"reach": {}, "prescribers": {}}
    lit_all = json.load(open(os.path.join(HERE, "probe_results", "literature.json")))
    lit = lit_all["studies"]
    rows = []
    for row in grid["rows"]:
        cls = row["class"]
        drugs = []
        for g, d in labels["drugs"].items():
            if d.get("class") != cls:
                continue
            st = d.get("storage", {})
            snip = (d.get("warn_snippets") or d.get("hyper_snippets") or d.get("dehyd_snippets") or st.get("burst_text") or st.get("heat_handling") or [""])[0]
            drugs.append({"generic": g, "status": drug_status(d), "n": d.get("n_labels", 0),
                          "heat_warning": d.get("heat_warning"), "heat_patient": d.get("heat_patient"),
                          "hyperthermia_only": d.get("hyperthermia_only"), "dehyd_warning": d.get("dehyd_warning"),
                          "burst": d.get("burst_share"), "handling": d.get("heat_handling_share"),
                          "terms": d.get("heat_terms", [])[:6], "snippet": snip[:420],
                          "storage": {"max_c": st.get("max_c"), "refrigerate": st.get("refrigerate"), "days": st.get("days_unrefrigerated")},
                          "dailymed": d.get("rep", {}).get("dailymed"), "brand": d.get("rep", {}).get("brand")})
        pat, line = FINDINGS[cls]
        rows.append({"class": cls, "examples": row["examples"], "specialties": row["specialties"],
                     "pattern": pat, "finding": line,
                     "research": research_summary(row),
                     "literature": literature(lit, cls),
                     "reach": {k: partd["reach"][cls][k] for k in ("national_benes", "national_benes_65", "ny_benes", "n_drugs")} | {"top": [d["generic"] for d in partd["reach"][cls]["drugs"][:4]]} if cls in partd["reach"] else None,
                     "prescribers": partd["prescribers"].get(cls),
                     "guidance": {k: guide["classes"][cls][k] for k in CODED},
                     "guidance_n": sum(guide["classes"][cls][k]["level"] in ("action", "mention") for k in CODED),
                     "guidance_actions": sum(guide["classes"][cls][k]["level"] == "action" for k in CODED),
                     "label": drugs})
    score = []
    for src in [x for x in guide["sources"] if x["id"] in CODED]:
        k = src["id"]
        lv = {c: guide["classes"][c][k]["level"] for c in guide["classes"]}
        checks = []
        for ch in guide["alignment_checks"]:
            r = ch["rule"]
            if "class" in r: ok = lv[r["class"]] in r["levels"]
            elif r.get("flag") == "overdose": ok = bool(guide["classes"]["Opioids"][k].get("overdose"))
            else: ok = any(v == "storage" for v in lv.values())
            checks.append(ok)
        score.append({"id": k, "short": src["short"], "jurisdiction": src.get("jurisdiction", ""), "year": src.get("year"),
                      "named": sum(v in ("action", "mention") for v in lv.values()), "actions": sum(v == "action" for v in lv.values()),
                      "of": len(lv), "checks": checks, "aligned": sum(checks)})
    prim = [x for x in lit if x["etype"] in PRIMARY]
    beyond = {}
    for c in ():
        xs = [x for x in prim if c in x["classes"]]
        beyond[c] = {"n": len(xs), "extracted": sum(x["drug_extracted"] for x in xs),
                     "studies": [{k: x[k] for k in ("pmid", "title", "year", "etype", "graph", "drug_extracted")} for x in xs]}
    from collections import Counter as _C
    lit_summary = {"candidates_note": "Hand-screened recall set + references of 5 reviews + papers citing 9 key studies; rule-screened, titles hand-reviewed",
                   "reviews": lit_all["reviews"], "primary": len(prim), "extracted": sum(x["drug_extracted"] for x in prim),
                   "any_finding": sum(x["graph"] in ("vetted", "api_only") for x in prim),
                   "graph_status": dict(_C(x["graph"] for x in prim)), "by_type": dict(_C(x["etype"] for x in prim)),
                   "extracted_by_type": dict(_C(x["etype"] for x in prim if x["drug_extracted"])), "beyond": beyond}
    wm = json.load(open(os.path.join(HERE, "wearables_matrix.json")))
    wc = {(c["class"], c["signal"]): c for c in json.load(open(os.path.join(HERE, "probe_results", "wearables.json")))["cells"]}
    pc = json.load(open(os.path.join(HERE, "probe_results", "pubmed_wearable_counts.json")))
    for row in wm["rows"]:
        for sig in wm["signals"]:
            c = wc.get((row["class"], sig), {})
            cell = row["cells"].setdefault(sig, {"effect": None, "level": "none", "pmids": [], "text": ""})
            cell.update({"graph": c.get("graph", 0), "graph_heat": c.get("graph_heat", 0), "pubmed_heat": c.get("pubmed_heat", 0),
                         "pubmed_heat_wearable": c.get("pubmed_heat_wearable", 0)})
    g = lambda k: next(v["count"] for kk, v in pc.items() if kk.startswith(k))
    wear = {"signals": wm["signals"], "rows": wm["rows"],
            "graph_drug_signal": sum(c["graph"] for c in wc.values()), "graph_drug_signal_heat": sum(c["graph_heat"] for c in wc.values()),
            "cells_with_wearable_heat": sum(1 for c in wc.values() if c["pubmed_heat_wearable"]), "cells_total": len(wc),
            "ladder": [
                {"label": "Wearables and heat stress", "n": g("W1"), "note": "Mostly healthy workers, soldiers, athletes"},
                {"label": "…in older adults", "n": g("W6"), "note": "Few test alerts; most describe exposure or sleep"},
                {"label": "…tested as heat-alert interventions", "n": g("W7"), "note": "All in workers or soldiers (e.g. 2B-Cool, PMID 36730025)"},
                {"label": "…in people taking any medication", "n": g("W3"), "note": "Where the evidence runs out"}],
            "why": [
                {"label": "Beta blockers and thermoregulation", "n": g("W4"), "note": "Why heart-rate alerts break"},
                {"label": "Core temperature estimated from heart rate", "n": g("W2"), "note": "Algorithms that assume a normal HR rise"},
                {"label": "Anticholinergics, sweating and heat", "n": g("W5"), "note": "Why sweat and skin signals break"}]}
    acts = build_actions(grid)
    out = {"built": "2026-11-14", "coded": CODED, "wearables": wear, "actions": acts,
           "partd_source": {"reach": partd.get("reach_source", ""), "prescribers": partd.get("prescriber_source", "")}, "literature": lit_summary, "scorecard": score, "alignment_checks": guide["alignment_checks"], "patterns": [dict(zip(("id", "title", "blurb"), p)) for p in PATTERNS],
           "sources": guide["sources"], "general_actions": guide["general_actions"], "not_in_grid": guide["not_in_grid"],
           "label_source": labels["source"] + ", pulled " + labels["pulled"], "rows": rows}
    with open(os.path.join(G, "lenses_data.json"), "w") as f:
        json.dump(out, f, indent=1)
    tpl = open(os.path.join(G, "lenses_template.html")).read()
    with open(os.path.join(G, "lenses.html"), "w") as f:
        f.write(tpl.replace("/*DATA*/null", json.dumps(out, separators=(",", ":")).replace("</", "<\\/")))
    for x in score: print(f"  {x['short']:14} named {x['named']}/{x['of']} actions {x['actions']} aligned {x['aligned']}/{len(x['checks'])} {x['year']}")
    from collections import Counter
    print(Counter(r["pattern"] for r in rows))
    for r in rows:
        print(f"{r['class']:30} {r['pattern']:12} {r['research']['label']:36} named={r['guidance_n']}/7 act={r['guidance_actions']} "
              + f"lit={r['literature']['n']}/{r['literature']['extracted']} ")


if __name__ == "__main__":
    main()
