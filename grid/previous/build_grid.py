#!/usr/bin/env python3
"""Build grid/grid_data.json for the evidence grid from local_analysis.py outputs.

Each cell = drug class x action bucket. The clinical action text and the
mechanisms that justify it are hand-written below (DRAFT, needs clinician
review). The evidence tier and the studies come from the graph.

Tiers
  direct   a graph finding links this drug (or its class) to a heat outcome
  bridged  drug -> mechanism AND heat -> same mechanism, both in the graph
  partial  drug -> mechanism in the graph, but no heat -> mechanism finding
  gap      the action is in labels/guidance, the graph has nothing for it
  none     no heat-specific action expected for this bucket
"""
import csv
import json
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from local_analysis import OFFTOPIC  # noqa: E402
import os
import sys
from collections import defaultdict

csv.field_size_limit(sys.maxsize)
HERE = os.path.dirname(os.path.abspath(__file__))
PR = os.path.join(HERE, "probe_results")
OUT = os.path.join(HERE, "grid")

BUCKETS = ["Dose adjustment", "Substitute or hold", "Closer monitoring", "Storage and stability"]
AKI, NA, DEH, BP, SWEAT, GLU, RHABDO, LEVELS = (
    "Acute kidney injury", "Hyponatremia / electrolytes", "Dehydration / volume", "Hypotension / falls",
    "Impaired sweating / thermoregulation", "Glucose", "Rhabdomyolysis", "Lithium toxicity / drug levels")

# Direct findings (from local_heat_drug_direct/modifier.csv), attached by hand to the cells they inform.
DIRECT = {
    "17698677": "Long-term antihypertensive use and death among heatstroke patients: HR 2.17 (1.17 to 4.05)",
    "36418530": "Starting irbesartan/HCTZ in the warm season vs the cold season: different blood-pressure response, 7.0 mmHg (4.7 to 9.3)",
    "37897873": "Each step up in daily temperature: more opioid overdoses, OR 1.079 (1.054 to 1.106); more ED visits for opioid use, OR 1.041",
    "15101888": "Heat applied over a fentanyl patch: plasma exposure (AUC) about 30% higher (experimental trial; heat on the skin, not ambient heat)",
    "31842287": "Taking any medication and heat illness: aOR 3.09 (1.15 to 8.29)",
    # API-only rows (not in the vetted Dataverse release)
    "29020197": "US Army soldiers: recent antipsychotic prescription and mild heat injury, HR 3.25 (1.33 to 7.9); heat stroke rows in the same study",
    "17513091": "Older adults, 2003 French heat wave: psychotropic use and admission for heat-related illness, OR 2.4 to 6.0 across models",
    "31205291": "Ambient temperature on the day and fatal opioid overdose: OR 1.3 (1.1 to 1.5)",
    "37897873a": "Each step up in daily temperature: more amphetamine overdoses, OR 1.15 (1.085 to 1.218); more ED visits, OR 1.072",
    "14622685": "Local heat over a fentanyl patch: higher peak serum fentanyl (Cmax)",
    "24334574": "Older adults on oral glucose-lowering drugs: severe hypoglycaemia admissions in the warm vs cool season (difference -17; direction needs checking)",
    "11434495": "Number of current medications and heat-related illness: OR 1.1 (0.8 to 1.5), no clear effect",
}
DIRECT.update({
    # added after the recall fixes (heat-context and drug-population routes), 2026-11-13
    "20104062a": "2003 French heat wave, people aged 70 to 100: antipsychotic use and death, OR 2.09 (1.89 to 2.35)",
    "20104062b": "2003 French heat wave, people aged 70 to 100: antidepressant use and death, OR 1.71 (1.57 to 1.86)",
    "20104062c": "2003 French heat wave, people aged 70 to 100: anxiolytic/hypnotic use and death, OR 0.85 (0.79 to 0.91), lower risk",
    "38060348": "Older insulin users, US and Taiwan: ambient heat and serious hypoglycaemia, OR 1.14 (1.08 to 1.20) per heat-index step; 1.38 (1.28 to 1.48) in the hottest category",
    "37369523": "British Columbia: 10 °C hotter 2-day maximum and opioid-related death, OR 1.15 (0.99 to 1.33); amphetamine-related, OR 1.11 (0.60 to 2.04)",
    "25163443": "Older lithium users: higher daily temperature and lithium dose-to-level ratio, coefficient -0.17, p = 0.08 (not significant)",
    "31782314": "2,493 patients, Sydney: preceding 5-day maximum temperature and serum lithium, r = -0.008 (no correlation)",
    "16911573": "Thiazide-induced hyponatraemia cases: air temperature and serum sodium, r = 0.2",
    "27160370": "Older inpatients during heat waves: drugs with anticholinergic effects and in-hospital death, OR 1.21 (p = 0.31); longer stay (p = 0.01)",
    "29116624": "Older inpatients during heat waves: diuretic + NSAID + ACEi/ARB together and in-hospital AKI, OR 1.02 (0.21 to 2.97), no clear effect",
    "28737683": "Sweden: outdoor temperature and reports of drug-induced hyponatraemia, OR 2.21",
    "28796021": "Older inpatients during a heat wave: psychotropic use and length of stay, HR 0.89 (0.69 to 1.14), no clear effect",
    "34338579": "Amlodipine-based therapy and seasonal blood-pressure swing: 4.33 mmHg difference between years of treatment",
    "37280056": "ACE-inhibitor users: serum potassium by season; ACEi prescriptions in cooler periods, RR 1.33 (1.12 to 1.59)",
    "7010077": "Insulin-treated patients at 35 °C vs 20 °C: faster insulin absorption from the injection site",
    "22538141": "Insulin pump users: local skin heating at mealtimes lowers the glucose curve (AUC difference -9.6 to -12.4)",
    "35564355": "Heat-exposed rice workers, Costa Rica: pain medication and eGFR change, -3.2 (-8.2 to 1.95), no clear effect",
})
UNVETTED = {"29020197", "17513091", "37897873a", "14622685", "24334574", "11434495",
            "20104062c", "27160370", "28737683", "34338579", "37280056", "7010077", "22538141", "35564355"}
NULL_DIRECT = {"11434495", "25163443", "31782314", "27160370", "29116624", "28796021", "35564355", "37369523"}
LOWER_DIRECT = {"20104062c"}
PMID_OF = {"37897873a": "37897873", "20104062a": "20104062", "20104062b": "20104062", "20104062c": "20104062"}
# Extra direct studies per cell, on top of the ones listed in CLASSES
EXTRA_DIRECT = {
    ("Antipsychotics", "Closer monitoring"): ["20104062a"],
    ("Antidepressants", "Closer monitoring"): ["20104062b"],
    ("Benzodiazepines / sedatives", "Closer monitoring"): ["20104062c"],
    ("Insulin", "Closer monitoring"): ["38060348"],
    ("Insulin", "Dose adjustment"): ["38060348", "7010077"],
    ("Insulin", "Storage and stability"): ["22538141"],
    ("Opioids", "Closer monitoring"): ["37369523"],
    ("Stimulants", "Closer monitoring"): ["37369523"],
    ("Lithium", "Dose adjustment"): ["25163443"],
    ("Lithium", "Closer monitoring"): ["25163443", "31782314"],
    ("Diuretics", "Closer monitoring"): ["16911573"],
    ("Anticholinergics", "Closer monitoring"): ["27160370"],
    ("NSAIDs", "Substitute or hold"): ["29116624", "35564355"],
    ("ACE inhibitors / ARBs", "Substitute or hold"): ["29116624"],
    ("Diuretics", "Substitute or hold"): ["29116624"],
    ("Calcium channel blockers", "Dose adjustment"): ["34338579"],
    ("ACE inhibitors / ARBs", "Closer monitoring"): ["37280056"],
}

# class: specialties, then per bucket: (action text, mechanisms, direct pmids, label/guidance note)
CLASSES = {
    "Diuretics": {
        "examples": "furosemide, hydrochlorothiazide, spironolactone",
        "specialties": ["Primary care", "Cardiology", "Nephrology", "Geriatrics"],
        "cells": {
            "Dose adjustment": ("Review the dose before and during a heat wave if intake is low or weight is falling.", [DEH, NA, AKI], ["36418530"], ""),
            "Substitute or hold": ("Sick-day rule: hold temporarily during vomiting, diarrhoea or poor fluid intake.", [DEH, AKI], [], "Sick-day guidance (e.g. UK 'SADMANS')"),
            "Closer monitoring": ("Check sodium, potassium and creatinine; daily weight; ask about dizziness.", [NA, AKI, BP], ["17698677"], ""),
            "Storage and stability": None,
        },
    },
    "ACE inhibitors / ARBs": {
        "examples": "lisinopril, ramipril, losartan, valsartan",
        "specialties": ["Primary care", "Cardiology", "Nephrology", "Geriatrics"],
        "cells": {
            "Dose adjustment": ("Consider a lower dose if blood pressure runs low through the summer.", [BP], ["36418530"], ""),
            "Substitute or hold": ("Sick-day rule: hold temporarily when dehydrated; avoid combining with an NSAID and a diuretic.", [AKI, DEH], [], "Sick-day guidance"),
            "Closer monitoring": ("Check creatinine and potassium; screen for orthostatic hypotension.", [AKI, NA, BP], ["17698677"], ""),
            "Storage and stability": None,
        },
    },
    "Beta blockers": {
        "examples": "metoprolol, atenolol, propranolol",
        "specialties": ["Primary care", "Cardiology", "Geriatrics"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": ("Do not stop abruptly. Reassess where the indication is weak.", [], [], "Label: rebound risk on abrupt withdrawal"),
            "Closer monitoring": ("Watch for dizziness and reduced exercise tolerance in the heat; heart-rate response is blunted.", [BP, SWEAT], ["17698677"], ""),
            "Storage and stability": None,
        },
    },
    "Calcium channel blockers": {
        "examples": "amlodipine, diltiazem, verapamil",
        "specialties": ["Primary care", "Cardiology", "Geriatrics"],
        "cells": {
            "Dose adjustment": ("Review the dose if symptomatic hypotension develops in hot weather.", [BP], [], ""),
            "Substitute or hold": None,
            "Closer monitoring": ("Ask about light-headedness, falls and ankle swelling.", [BP], ["17698677"], ""),
            "Storage and stability": None,
        },
    },
    "Anticholinergics": {
        "examples": "oxybutynin, diphenhydramine, benztropine",
        "specialties": ["Primary care", "Geriatrics", "Urology", "Psychiatry"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": ("Deprescribe or switch where possible, e.g. from oxybutynin to mirabegron.", [SWEAT], [], "Beers criteria; heat guidance (CDC, UKHSA)"),
            "Closer monitoring": ("Warn about reduced sweating; watch for confusion and hot, dry skin.", [SWEAT, BP], [], "Heat guidance names this class first"),
            "Storage and stability": None,
        },
    },
    "Antipsychotics": {
        "examples": "olanzapine, clozapine, haloperidol, quetiapine",
        "specialties": ["Psychiatry", "Primary care"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": ("Do not stop abruptly. Where a choice exists, prefer agents with low anticholinergic load.", [], [], "Label"),
            "Closer monitoring": ("Check temperature and hydration; watch for confusion, rigidity (NMS) and hypotension.", [SWEAT, BP, RHABDO], ["29020197", "17513091"], "Heat guidance (CDC, UKHSA)"),
            "Storage and stability": None,
        },
    },
    "Lithium": {
        "examples": "lithium carbonate",
        "specialties": ["Psychiatry", "Primary care", "Nephrology"],
        "cells": {
            "Dose adjustment": ("Levels can rise with dehydration; review the dose based on a level, not a fixed rule.", [LEVELS, DEH], [], "Label: narrow therapeutic index"),
            "Substitute or hold": ("Hold temporarily during vomiting or diarrhoea and seek a level.", [LEVELS], [], "Sick-day guidance"),
            "Closer monitoring": ("Check a serum lithium level and creatinine during prolonged heat; teach the signs of toxicity.", [LEVELS, AKI, NA], [], "Heat guidance (all sources)"),
            "Storage and stability": None,
        },
    },
    "Antidepressants": {
        "examples": "SSRIs, tricyclics (amitriptyline)",
        "specialties": ["Psychiatry", "Primary care", "Geriatrics"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": ("In older adults, prefer an SSRI over a tricyclic (anticholinergic).", [SWEAT], [], "Beers criteria"),
            "Closer monitoring": ("SSRIs: check sodium in older adults. Tricyclics: watch for overheating.", [NA, BP, SWEAT], ["17513091"], ""),
            "Storage and stability": None,
        },
    },
    "Benzodiazepines / sedatives": {
        "examples": "diazepam, lorazepam, zolpidem",
        "specialties": ["Psychiatry", "Primary care", "Geriatrics"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": ("Taper rather than stop. Review the need for long-term use.", [], [], "Beers criteria"),
            "Closer monitoring": ("Sedation dulls thirst and awareness of heat; watch for falls.", [BP], ["17513091"], ""),
            "Storage and stability": None,
        },
    },
    "Opioids": {
        "examples": "morphine, oxycodone, fentanyl patch, methadone",
        "specialties": ["Pain and palliative", "Primary care", "Addiction medicine"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": None,
            "Closer monitoring": ("Overdose risk rises with temperature: offer naloxone and add check-ins on hot days.", [BP, AKI], ["37897873", "31205291"], "Rarely named in heat guidance"),
            "Storage and stability": ("Fentanyl patch: keep heat sources and direct sun off the patch; a fever or heat raises absorption.", [], ["15101888", "14622685"], "FDA boxed warning on external heat"),
        },
    },
    "Insulin": {
        "examples": "all insulins",
        "specialties": ["Endocrinology", "Primary care"],
        "cells": {
            "Dose adjustment": ("Heat speeds absorption from the injection site; a dose reduction may be needed if lows occur.", [GLU], [], ""),
            "Substitute or hold": None,
            "Closer monitoring": ("Check glucose more often in hot weather.", [GLU, AKI], [], ""),
            "Storage and stability": ("Keep below about 30 °C and out of hot cars; use a cooling wallet when travelling.", [], [], "Label storage conditions"),
        },
    },
    "SGLT2 inhibitors": {
        "examples": "empagliflozin, dapagliflozin",
        "specialties": ["Endocrinology", "Cardiology", "Nephrology", "Primary care"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": ("Sick-day rule: hold when dehydrated or not eating (risk of volume depletion and euglycaemic DKA).", [DEH, AKI, GLU], [], "Label; sick-day guidance"),
            "Closer monitoring": ("Ask about fluid intake; check ketones if unwell.", [DEH, AKI, NA], [], ""),
            "Storage and stability": None,
        },
    },
    "Metformin and sulfonylureas": {
        "examples": "metformin, gliclazide, glyburide",
        "specialties": ["Endocrinology", "Primary care", "Geriatrics"],
        "cells": {
            "Dose adjustment": ("Sulfonylureas: consider a lower dose if intake falls and lows occur.", [GLU], [], ""),
            "Substitute or hold": ("Metformin: hold temporarily when dehydrated (AKI, lactic acidosis).", [AKI, DEH], [], "Sick-day guidance"),
            "Closer monitoring": ("Check glucose more often; watch kidney function.", [GLU, AKI], ["24334574"], ""),
            "Storage and stability": None,
        },
    },
    "NSAIDs": {
        "examples": "ibuprofen, naproxen, diclofenac",
        "specialties": ["Primary care", "Rheumatology", "Pharmacy"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": ("Avoid during heat waves when dehydrated, above all combined with a diuretic and an ACEi/ARB ('triple whammy').", [AKI, DEH], [], ""),
            "Closer monitoring": ("Check creatinine if NSAIDs continue during prolonged heat.", [AKI, NA], [], ""),
            "Storage and stability": None,
        },
    },
    "Topiramate / zonisamide": {
        "examples": "topiramate, zonisamide",
        "specialties": ["Neurology", "Pediatrics"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": None,
            "Closer monitoring": ("Reduced sweating (oligohidrosis), mainly in children: limit exertion in the heat and watch for fever.", [SWEAT], [], "Label warning"),
            "Storage and stability": None,
        },
    },
    "Stimulants": {
        "examples": "methylphenidate, amphetamine",
        "specialties": ["Psychiatry", "Pediatrics"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": None,
            "Closer monitoring": ("Watch for overheating on hot days, especially in sport; misuse and overdose rise with temperature.", [DEH, GLU], ["37897873a"], ""),
            "Storage and stability": None,
        },
    },
    "Heat-labile emergency products": {
        "examples": "epinephrine auto-injectors, salbutamol inhalers, nitroglycerin",
        "specialties": ["Primary care", "Pharmacy", "Pediatrics"],
        "cells": {
            "Dose adjustment": None,
            "Substitute or hold": None,
            "Closer monitoring": None,
            "Storage and stability": ("Keep out of hot cars and direct sun; replace after heat exposure, or if discoloured.", [], [], "Label storage conditions"),
        },
    },
}
# Graph class name used for drug->mechanism lookups
GRAPH_CLASS = {"Metformin and sulfonylureas": "Other diabetes drugs", "Topiramate / zonisamide": "Anticonvulsants",
               "Heat-labile emergency products": None}


def load(name):
    with open(os.path.join(PR, name)) as f:
        return list(csv.DictReader(f))


def excludes_null(r):
    try:
        lo, hi = float(r["ci_lower"]), float(r["ci_upper"])
    except (TypeError, ValueError):
        try:
            return float(r["p_value"]) < 0.05
        except (TypeError, ValueError):
            return False
    ratio = any(k in (r["statistic_type"] or "").lower() for k in ("ratio", "or", "rr", "hr"))
    null = 1.0 if ratio and lo > 0 else 0.0
    return lo > null or hi < null


def study_entry(r, side_a, side_b):
    return {"pmid": r["pubmed_id"], "a": side_a[:160], "b": side_b[:160], "stat": r["statistic_type"][:40],
            "value": r["value"], "ci": [r["ci_lower"], r["ci_upper"]], "p": r["p_value"],
            "trial": r["study_type"] == "Experimental Trial", "sig": excludes_null(r),
            "pop": (r["population"] or "")[:200]}


def pick(rows, key_a, key_b, n):
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: (not excludes_null(r), r["study_type"] != "Experimental Trial", not r["population"])):
        if r["pubmed_id"] in seen:
            continue
        seen.add(r["pubmed_id"])
        out.append(study_entry(r, r[key_a], r[key_b]))
        if len(out) == n:
            break
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    dm = defaultdict(list)
    for r in load("local_drug_mechanism_findings.csv"):
        dm[(r["classes"], r["mechanisms"])].append(r)
    dm_counts = {(r["class"], r["mechanism"]): int(r["drug_mech_studies"]) for r in load("local_drug_mechanism.csv")}
    hm = defaultdict(list)
    for r in load("local_heat_mechanism.csv"):
        for m in r["mechanisms"].split(" | "):
            hm[m].append(r)
    hm_counts = {m: len({r["study_id"] for r in rows}) for m, rows in hm.items()}
    direct_rows = {r["pubmed_id"]: r for r in load("local_heat_drug_direct.csv") + load("local_heat_drug_modifier.csv")}

    # API-only rows (api_pull.py): only for the mechanisms pulled there
    dv_dm_studies = defaultdict(set)
    for (c_, m_), lst in dm.items():
        dv_dm_studies[(c_, m_)] = {r["study_id"] for r in lst}
    dv_hm_studies = {m_: {r["study_id"] for r in lst} for m_, lst in hm.items()}
    api_dm, api_hm = defaultdict(list), defaultdict(list)
    api_path = os.path.join(PR, "api_findings.csv")
    for r in (load("api_findings.csv") if os.path.exists(api_path) else []):
        if r["in_dataverse"] == "True":
            continue
        mside = r["var1"] if r["var2"] == r["other_side"] else r["var2"]
        if r["kind"] == "drug-mechanism":
            if r["other_side"] != r["var1"] or OFFTOPIC.search(r["population"] or ""):
                continue  # drug must be the exposure (variable 1); skip animal / poisoning populations
            for c_ in r["classes"].split(" | "):
                for m_ in r["mechanisms"].split(" | "):
                    if r["study_id"] not in dv_dm_studies[(c_, m_)]:
                        api_dm[(c_, m_)].append({**r, "drug_side": r["other_side"], "mech_side": mside})
        elif r["kind"] == "heat-mechanism":
            for m_ in r["mechanisms"].split(" | "):
                if r["study_id"] not in dv_hm_studies.get(m_, set()):
                    api_hm[m_].append(r)
        if r["kind"] == "heat-drug":
            direct_rows.setdefault(r["pubmed_id"], {"var1": r["heat_side"], "var2": r["other_side"]})

    rows_out = []
    for cls, spec in CLASSES.items():
        gcls = GRAPH_CLASS.get(cls, cls)
        cells = {}
        for b in BUCKETS:
            c = spec["cells"].get(b)
            if not c:
                cells[b] = {"tier": "none"}
                continue
            action, mechs, direct, note = c
            direct = list(direct) + [k for k in EXTRA_DIRECT.get((cls, b), []) if k not in direct]
            mech_info = []
            for m in mechs:
                d_n = dm_counts.get((gcls, m), 0) if gcls else 0
                h_n = hm_counts.get(m, 0)
                ad = api_dm.get((gcls, m), []) if gcls else []
                ah = api_hm.get(m, [])
                d_u, h_u = len({r["study_id"] for r in ad}), len({r["study_id"] for r in ah})
                mech_info.append({"mechanism": m, "drug_studies": d_n, "heat_studies": h_n,
                                  "drug_unvetted": d_u, "heat_unvetted": h_u,
                                  "drug_examples": (pick(dm.get((gcls, m), []), "drug_side", "mech_side", 6) if d_n else [])
                                  + [dict(x, vetted=False) for x in pick(ad, "drug_side", "mech_side", 3)],
                                  "heat_examples": (pick(hm.get(m, []), "var1", "var2", 4) if h_n else [])
                                  + [dict(x, vetted=False) for x in pick(ah, "var1", "var2", 3)]})
            # Grade on the primary (first-listed) mechanism; the rest are supporting context.
            prim = mech_info[:1]
            for x in mech_info:
                x["primary"] = x is mech_info[0]
            def grade(use_api):
                d = lambda x: x["drug_studies"] + (x["drug_unvetted"] if use_api else 0)
                h = lambda x: x["heat_studies"] + (x["heat_unvetted"] if use_api else 0)
                dirs = [pm for pm in direct if use_api or pm not in UNVETTED]
                br = [x for x in prim if d(x) and h(x)]
                if dirs:
                    return "direct", None
                if br:
                    db, hb = d(br[0]), h(br[0])
                    return "bridged", 3 if db >= 30 and hb >= 10 else 2 if db >= 10 and hb >= 3 else 1
                if [x for x in prim if d(x)]:
                    return "partial", None
                return "gap", None
            tier, strength = grade(True)
            vetted = grade(False) == (tier, strength)
            dir_list = []
            for pm in direct:
                r = direct_rows.get(PMID_OF.get(pm, pm))
                dir_list.append({"pmid": PMID_OF.get(pm, pm), "summary": DIRECT[pm], "vetted": pm not in UNVETTED,
                                 "effect": "lower" if pm in LOWER_DIRECT else "null" if pm in NULL_DIRECT else "risk",
                                 **({"a": r["var1"][:160], "b": r["var2"][:160]} if r else {"a": "", "b": ""})})
            effects = {d["effect"] for d in dir_list}
            signal = None if tier != "direct" else ("risk" if "risk" in effects else "lower" if "lower" in effects else "null")
            cells[b] = {"tier": tier, "strength": strength, "vetted": vetted, "signal": signal, "action": action, "note": note,
                        "mechanisms": mech_info, "direct": dir_list}
        rows_out.append({"class": cls, "examples": spec["examples"], "specialties": spec["specialties"], "cells": cells})

    data = {"buckets": BUCKETS, "rows": rows_out, "general": [{"pmid": "31842287", "summary": DIRECT["31842287"], "vetted": True, "effect": "risk"},
                        {"pmid": "28737683", "summary": DIRECT["28737683"], "vetted": False, "effect": "risk"},
                        {"pmid": "28796021", "summary": DIRECT["28796021"], "vetted": True, "effect": "null"},
                        {"pmid": "11434495", "summary": DIRECT["11434495"], "vetted": False, "effect": "null"}],
            "source": "System Public Graph v1: Dataverse release doi:10.7910/DVN/7V6JDO (vetted) plus the live System API (unvetted rows, pulled 2026-11-13)",
            "built": "2026-11-13"}
    with open(os.path.join(OUT, "grid_data.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))
    from collections import Counter
    print(Counter(c["tier"] for r in rows_out for c in r["cells"].values()))
    for r in rows_out:
        print(f"{r['class']:32}", " ".join(f"{(c['tier'][:6] + str(c.get('strength') or '') + ({'null': '-0', 'lower': '-v'}.get(c.get('signal'), '')) + ('' if c.get('vetted', True) else '*')):10}" for c in r["cells"].values()))
    print(os.path.getsize(os.path.join(OUT, "grid_data.json")), "bytes")


if __name__ == "__main__":
    main()


def render_html():
    """Inline grid_data.json into template.html -> grid/heat-med-map.html"""
    with open(os.path.join(OUT, "template.html")) as f:
        tpl = f.read()
    with open(os.path.join(OUT, "grid_data.json")) as f:
        data = f.read().replace("</", "<\\/")
    with open(os.path.join(OUT, "heat-med-map.html"), "w") as f:
        f.write(tpl.replace("/*DATA*/null", data))


render_html()
