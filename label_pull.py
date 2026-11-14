#!/usr/bin/env python3
"""Pull FDA drug labels (openFDA /drug/label, the DailyMed SPL text) for representative
drugs in each class and code what the label says about heat.

Per drug, across every manufacturer label returned (deduplicated by set_id):
  heat_warning   share of labels whose Warnings/Precautions/Boxed sections mention heat or
                 thermoregulation (hyperthermia, heat stroke, decreased sweating, hot weather,
                 external heat on the product ...)
  heat_patient   share whose patient-facing sections (Medication Guide, patient info) do
  heat_anywhere  share with a heat term in any clinical section (incl. adverse reactions)
  dehyd_warning  share whose warnings mention dehydration / volume depletion (no heat needed)
  storage        storage sentences and the temperatures in them, from the most recent label

No key needed (openFDA allows 240 requests/minute, 1,000/day without one). Responses are
cached in cache_fda/. Standard library only.

  python3 label_pull.py   ->  probe_results/fda_labels.json, probe_results/fda_labels.csv
"""
import csv
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache_fda")
OUT = os.path.join(HERE, "probe_results")
RX = "HUMAN PRESCRIPTION DRUG"
OTC = "HUMAN OTC DRUG"

# class (as in build_grid.CLASSES): [(generic name, product type, route filter or None)]
DRUGS = {
    "Diuretics": [("furosemide", RX, None), ("hydrochlorothiazide", RX, None), ("spironolactone", RX, None)],
    "ACE inhibitors / ARBs": [("lisinopril", RX, None), ("losartan potassium", RX, None), ("sacubitril and valsartan", RX, None)],
    "Beta blockers": [("metoprolol", RX, None), ("atenolol", RX, None), ("propranolol", RX, None)],
    "Calcium channel blockers": [("amlodipine", RX, None), ("diltiazem", RX, None), ("verapamil", RX, None)],
    "Anticholinergics": [("oxybutynin", RX, None), ("benztropine", RX, None), ("diphenhydramine", OTC, "ORAL")],
    "Antipsychotics": [("olanzapine", RX, None), ("quetiapine", RX, None), ("haloperidol", RX, None), ("clozapine", RX, None)],
    "Lithium": [("lithium carbonate", RX, None)],
    "Antidepressants": [("sertraline", RX, None), ("amitriptyline", RX, None), ("venlafaxine", RX, None)],
    "Benzodiazepines / sedatives": [("lorazepam", RX, None), ("diazepam", RX, None), ("zolpidem", RX, None)],
    "Opioids": [("fentanyl", RX, "TRANSDERMAL"), ("oxycodone", RX, None), ("methadone", RX, None)],
    "Insulin": [("insulin glargine", RX, None), ("insulin lispro", RX, None), ("insulin aspart", RX, None)],
    "SGLT2 inhibitors": [("empagliflozin", RX, None), ("dapagliflozin", RX, None)],
    "Metformin and sulfonylureas": [("metformin", RX, None), ("glipizide", RX, None), ("glyburide", RX, None)],
    "NSAIDs": [("ibuprofen", RX, None), ("naproxen", RX, None), ("diclofenac", RX, "ORAL")],
    "Topiramate / zonisamide": [("topiramate", RX, None), ("zonisamide", RX, None)],
    "Stimulants": [("methylphenidate", RX, None), ("amphetamine", RX, None)],
    "GLP-1 agonists": [("semaglutide", RX, None), ("liraglutide", RX, None), ("dulaglutide", RX, None), ("tirzepatide", RX, None)],
    "Parkinson / dopaminergic": [("carbidopa and levodopa", RX, None), ("pramipexole", RX, None), ("ropinirole", RX, None)],
    "Cholinesterase inhibitors": [("donepezil", RX, None), ("rivastigmine", RX, None), ("galantamine", RX, None)],
    "Heat-labile emergency products": [("epinephrine", RX, "INTRAMUSCULAR", r"auto-?injector"), ("albuterol", RX, "RESPIRATORY (INHALATION)", r"inhalation aerosol|metered"),
                                       ("nitroglycerin", RX, "SUBLINGUAL")],
}

WARN = ["boxed_warning", "warnings_and_cautions", "warnings", "precautions", "general_precautions"]
PATIENT = ["information_for_patients", "spl_patient_package_insert", "spl_medguide", "patient_medication_information"]
OTHER = ["adverse_reactions", "dosage_and_administration", "overdosage", "clinical_pharmacology", "geriatric_use",
         "pediatric_use", "drug_interactions", "use_in_specific_populations", "do_not_use", "stop_use", "ask_doctor"]
STORAGE = ["storage_and_handling", "how_supplied", "package_label_principal_display_panel"]

# Environmental heat: the label tells the reader that hot conditions are a hazard with this drug.
HEAT = re.compile(
    r"\b(heat[- ]?stroke|heat exhaustion|heat[- ]related|heat intolerance|heat prostration"
    r"|hot weather|hot environments?|hot climates?|high (?:ambient |environmental |outside )?temperatures?|extreme heat"
    r"|(?:exposure|exposed) to (?:extreme |excessive |high |direct )?heat|external heat|heat sources?|heating pads?|electric blankets?"
    r"|heat lamps?|sauna\w*|hot tubs?|heated water ?beds?|sunbath\w*|hot baths?"
    r"|oligohidrosis|anhidrosis|hypohidrosis|decreased sweating|reduced sweating|(?:inability|unable) to sweat|sweat(?:ing)? less"
    r"|body temperature regulation|(?:regulate|regulation of|reduce) (?:core |body )?(?:body )?temperature|thermoregulat\w*|overheat\w*)\b", re.I)
# Drug-induced hyperthermia (serotonin syndrome, NMS, overdose lists): a fever the drug causes, not a heat warning.
HYPER = re.compile(r"\b(hyperthermi\w*|hyperpyrexi\w*|(?:increased|elevated|high) (?:core |body )?temperature)\b", re.I)
DEHYD = re.compile(r"\b(dehydrat\w*|volume depletion|hypovolemi\w*|intravascular volume|fluid loss|excessive sweating)\b", re.I)
TEMP_SENT = re.compile(r"[^.]{0,250}?(°|º|degrees|refrigerat|room temperature|excursion|freez|\bheat\b|burst|puncture|incinerat)[^.]{0,250}", re.I)
DEG_C = re.compile(r"(\d{1,3})\s*(?:°|º|degrees?)\s*C\b", re.I)
BURST = re.compile(r"[^.]{0,200}(burst|explode|above 120 ?°? ?F|49 ?° ?C)[^.]{0,200}", re.I)
HANDLE = re.compile(r"(away from|protect\w* (?:\w+ )?from|avoid|not expose \w+ to|keep \w+ out of|do not (?:leave|store) \w+ (?:in|near))[^.]{0,40}\b(heat|hot|direct sunlight|car)\b", re.I)
DAYS_OUT = re.compile(r"(\d{1,3})\s*days?", re.I)


def fetch(generic, ptype, route):
    q = [f'openfda.generic_name:"{generic}"', f'openfda.product_type:"{ptype}"']
    if route:
        q.append(f'openfda.route:"{route}"')
    url = "https://api.fda.gov/drug/label.json?search=" + urllib.parse.quote("+AND+".join(q), safe=':+"()') + "&limit=50"
    key = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".json")
    if os.path.exists(key):
        with open(key) as f:
            return json.load(f)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "label-pull/1.0"}), timeout=60) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                data = {"results": []}
                break
            time.sleep(2 + attempt * 3)
        except Exception:
            time.sleep(2 + attempt * 3)
    else:
        raise RuntimeError("failed: " + url)
    os.makedirs(CACHE, exist_ok=True)
    with open(key, "w") as f:
        json.dump(data, f)
    time.sleep(0.3)
    return data


DIFFDX = re.compile(r"differential diagnosis|important to consider the presence of other", re.I)


def text(lbl, fields):
    # drop 'differential diagnosis' sentences: they list heat stroke as something to rule out, not as a warning
    t = " ".join(" ".join(lbl.get(k, [])) for k in fields)
    if not DIFFDX.search(t):
        return t
    return " ".join(x for x in re.split(r"(?<=\.)\s+", t) if not DIFFDX.search(x))


def snippets(t, rx, n=2, w=150):
    out, seen = [], set()
    for m in rx.finditer(t):
        term = m.group(0).lower()
        if term in seen:
            continue
        seen.add(term)
        s, e = max(0, m.start() - w), min(len(t), m.end() + w)
        out.append(("…" if s else "") + re.sub(r"\s+", " ", t[s:e]).strip() + ("…" if e < len(t) else ""))
        if len(out) == n:
            break
    return out


def matches_generic(lbl, generic):
    names = [n.lower() for n in lbl.get("openfda", {}).get("generic_name", [])]
    if " and " in generic:
        return any(generic in n for n in names)
    return any(generic in n and " and " not in n and "," not in n for n in names)


def storage_info(lbl):
    t = re.sub(r"\s+", " ", text(lbl, ["storage_and_handling", "how_supplied"]))
    t = re.sub(r"<[^>]+>", " ", t)
    allt = re.sub(r"\s+", " ", text(lbl, PATIENT + ["instructions_for_use", "storage_and_handling", "how_supplied"]))
    burst = [m.group(0).strip() for m in BURST.finditer(allt)]
    store_t = BURST.sub(" ", t)
    sents = [m.group(0).strip() for m in TEMP_SENT.finditer(store_t)]
    temps = sorted({int(x) for x in DEG_C.findall(store_t) if int(x) <= 60})
    days = sorted({int(d) for s in sents if re.search(r"room temperature|unrefrigerated|not refrigerated|30 ?°C|86 ?°F", s, re.I)
                   for d in DAYS_OUT.findall(s) if 1 <= int(d) <= 60})
    heat_handling = [m.group(0).strip() for m in re.finditer(r"[^.]{0,120}(?:away from|protect\w* (?:\w+ )?from|avoid|do not expose \w+ to|keep \w+ out of)[^.]{0,40}(?:heat|hot|sunlight|car)\b[^.]{0,120}", allt, re.I)]
    return {"sentences": sents[:6], "temps_c": temps, "max_c": max(temps) if temps else None, "days_unrefrigerated": days,
            "refrigerate": bool(re.search(r"refrigerat", t, re.I)) and not re.search(r"do not refrigerate", t, re.I) or bool(re.search(r"\b(?:2|36) ?°?\s*(?:C|F)?\s*(?:to|-|–)\s*(?:8|46) ?°", t)),
            "burst_warning": bool(burst), "burst_text": burst[:1], "heat_handling": heat_handling[:2],
            "excursion": bool(re.search(r"excursion", t, re.I))}


def main():
    os.makedirs(OUT, exist_ok=True)
    out, rows = {}, []
    for cls, drugs in DRUGS.items():
        for generic, ptype, route, *must in drugs:
            must = re.compile(must[0], re.I) if must else None
            res = fetch(generic, ptype, route).get("results", [])
            if must:
                res = [l for l in res if must.search(text(l, ["description", "dosage_forms_and_strengths", "how_supplied", "package_label_principal_display_panel"]))]
            labels, seen = [], set()
            for l in sorted(res, key=lambda l: l.get("effective_time", ""), reverse=True):
                if l.get("set_id") in seen or not matches_generic(l, generic):
                    continue
                seen.add(l.get("set_id"))
                labels.append(l)
            n = len(labels)
            if not n:
                print(f"{cls:30} {generic:26} NO LABELS")
                out[generic] = {"class": cls, "n_labels": 0}
                continue
            per = []
            for l in labels:
                w, p, o = text(l, WARN), text(l, PATIENT), text(l, OTHER)
                per.append({"warn": bool(HEAT.search(w)), "patient": bool(HEAT.search(p)), "any": bool(HEAT.search(w + p + o)),
                            "hyper_only": bool(HYPER.search(w)) and not HEAT.search(w + p),
                            "dehyd": bool(DEHYD.search(w)),
                            "burst": bool(BURST.search(text(l, PATIENT + ["instructions_for_use", "storage_and_handling", "how_supplied"]))),
                            "handle_heat": bool(HANDLE.search(text(l, PATIENT + ["instructions_for_use", "storage_and_handling", "how_supplied"]))),
                            "boxed_heat": bool(HEAT.search(text(l, ["boxed_warning"])))})
            share = {k: round(sum(x[k] for x in per) / n, 2) for k in per[0]}
            # representative label: most recent one carrying the modal heat_warning value
            modal = Counter(x["warn"] for x in per).most_common(1)[0][0]
            rep = next(l for l, x in zip(labels, per) if x["warn"] == modal)
            rw, rp, ro = text(rep, WARN), text(rep, PATIENT), text(rep, OTHER)
            st = storage_info(rep)
            heat_terms = sorted({m.group(0).lower() for m in HEAT.finditer(rw + " " + rp)})
            rec = {"class": cls, "generic": generic, "product_type": ptype, "route": route, "n_labels": n,
                   "heat_warning": share["warn"], "heat_patient": share["patient"], "heat_anywhere": share["any"],
                   "heat_boxed": share["boxed_heat"], "dehyd_warning": share["dehyd"], "hyperthermia_only": share["hyper_only"],
                   "burst_share": share["burst"], "heat_handling_share": share["handle_heat"],
                   "hyper_snippets": snippets(rw, HYPER, 1) if share["hyper_only"] >= 0.5 else [],
                   "heat_terms": heat_terms,
                   "warn_snippets": snippets(rw, HEAT) or snippets(rp, HEAT) or snippets(ro, HEAT),
                   "dehyd_snippets": [] if share["warn"] >= 0.5 else snippets(rw, DEHYD, 1),
                   "rep": {"set_id": rep.get("set_id"), "effective_time": rep.get("effective_time"),
                           "brand": (rep.get("openfda", {}).get("brand_name") or [""])[0],
                           "manufacturer": (rep.get("openfda", {}).get("manufacturer_name") or [""])[0],
                           "dailymed": f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={rep.get('set_id')}"},
                   "storage": st}
            out[generic] = rec
            rows.append({"class": cls, "generic": generic, "n_labels": n, "heat_warning": share["warn"], "heat_patient": share["patient"],
                         "heat_anywhere": share["any"], "heat_boxed": share["boxed_heat"], "dehyd_warning": share["dehyd"],
                         "hyperthermia_only": share["hyper_only"], "burst_share": share["burst"], "heat_handling_share": share["handle_heat"], "heat_terms": "; ".join(heat_terms), "max_storage_c": st["max_c"], "refrigerate": st["refrigerate"],
                         "burst_warning": st["burst_warning"], "days_unrefrigerated": " ".join(map(str, st["days_unrefrigerated"])),
                         "dailymed": rec["rep"]["dailymed"]})
            print(f"{cls:30} {generic:26} n={n:3}  heatWarn={share['warn']:.2f} patient={share['patient']:.2f} "
                  f"any={share['any']:.2f} hyperOnly={share['hyper_only']:.2f} dehyd={share['dehyd']:.2f}  ≤{st['max_c']}°C fridge={int(st['refrigerate'])} burst={share['burst']:.2f} handle={share['handle_heat']:.2f} days={st['days_unrefrigerated']}  {', '.join(heat_terms)[:50]}")
    with open(os.path.join(OUT, "fda_labels.json"), "w") as f:
        json.dump({"pulled": time.strftime("%Y-%m-%d"), "source": "openFDA drug label endpoint (DailyMed SPL)", "drugs": out}, f, indent=1)
    with open(os.path.join(OUT, "fda_labels.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)


if __name__ == "__main__":
    main()
