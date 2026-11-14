#!/usr/bin/env python3
"""CMS Medicare Part D: how many people take each heat-sensitive class, and who prescribes it.

1. Reach: Part D Prescribers by Geography and Drug, 2023 (national + New York rows). Beneficiaries per generic
   drug, summed over brand rows (a person on two brands of one drug may count twice; small).
   Class totals sum drugs, so a person on two drugs in a class counts twice: read as "prescriptions reach", an upper bound.
2. Prescribers: Part D Prescribers by Provider and Drug, 2024, New York prescribers, top drugs per class by NY reach.
   Claims summed by prescriber type (Prscrbr_Type) -> share of claims.

Medicare Part D only: mostly people 65+, the group most at risk in heat. Cells under 11 are suppressed by CMS.

  python3 partd_pull.py  ->  probe_results/partd.json
"""
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache_cms")
GEO = "https://data.cms.gov/data-api/v1/dataset/3463648b-1971-478d-84ca-80cadc758153/data"   # 2023 by geography and drug
PD = "https://data.cms.gov/data-api/v1/dataset/9552739e-3d05-4c1b-8eff-ecabf391e2e5/data"    # 2024 by provider and drug

CLASSES = {
    "Diuretics": r"^(furosemide|bumetanide|torsemide|hydrochlorothiazide|chlorthalidone|indapamide|spironolactone|metolazone|eplerenone)$",
    "ACE inhibitors / ARBs": r"^(lisinopril|enalapril\w*|ramipril|benazepril\w*|quinapril\w*|fosinopril\w*|perindopril\w*|trandolapril|captopril|losartan potassium|valsartan|irbesartan|candesartan\w*|olmesartan\w*|telmisartan|sacubitril/valsartan)$",
    "Beta blockers": r"^(metoprolol \w+|atenolol|propranolol\w*|bisoprolol fumarate|carvedilol\w*|nebivolol\w*|labetalol\w*|nadolol)$",
    "Calcium channel blockers": r"^(amlodipine besylate|nifedipine|diltiazem\w*|verapamil\w*|felodipine)$",
    "Anticholinergics": r"^(oxybutynin\w*|tolterodine\w*|solifenacin\w*|trospium\w*|darifenacin\w*|fesoterodine\w*|benztropine\w*|hydroxyzine\w*|trihexyphenidyl\w*|promethazine\w*)$",
    "Antipsychotics": r"^(olanzapine|clozapine|haloperidol\w*|quetiapine\w*|risperidone|aripiprazole|ziprasidone\w*|lurasidone\w*|paliperidone\w*)$",
    "Lithium": r"^lithium carbonate$",
    "Antidepressants": r"^(sertraline\w*|escitalopram\w*|citalopram\w*|fluoxetine\w*|paroxetine\w*|venlafaxine\w*|duloxetine\w*|amitriptyline\w*|nortriptyline\w*|bupropion\w*|mirtazapine|trazodone\w*)$",
    "Benzodiazepines / sedatives": r"^(lorazepam|alprazolam|clonazepam|diazepam|temazepam|zolpidem\w*|eszopiclone)$",
    "Opioids": r"^(oxycodone\w*|hydrocodone/acetaminophen|oxycodone hcl/acetaminophen|morphine sulfate|tramadol\w*|fentanyl|methadone\w*|hydromorphone\w*|buprenorphine\w*)$",
    "Insulin": r"^insulin ",
    "SGLT2 inhibitors": r"^(empagliflozin|dapagliflozin\w*|canagliflozin|ertugliflozin\w*)$",
    "Metformin and sulfonylureas": r"^(metformin hcl|glipizide|glimepiride|glyburide\w*)$",
    "NSAIDs": r"^(meloxicam|ibuprofen|naproxen\w*|diclofenac\w*|celecoxib|nabumetone|etodolac)$",
    "Topiramate / zonisamide": r"^(topiramate|zonisamide)$",
    "Stimulants": r"^(methylphenidate\w*|dexmethylphenidate\w*|amphetamine\w*|dextroamphetamine\w*|lisdexamfetamine\w*|modafinil|armodafinil)",
    "GLP-1 agonists": r"^(semaglutide|liraglutide|dulaglutide|tirzepatide|exenatide\w*)$",
    "Parkinson / dopaminergic": r"^(carbidopa/levodopa\w*|pramipexole\w*|ropinirole\w*|rasagiline\w*|amantadine\w*)$",
    "Cholinesterase inhibitors": r"^(donepezil\w*|rivastigmine\w*|galantamine\w*)$",
    "Heat-labile emergency products": r"^(epinephrine|albuterol sulfate|nitroglycerin)$",
}
CRX = {k: re.compile(v, re.I) for k, v in CLASSES.items()}


def get(url, params):
    u = url + "?" + urllib.parse.urlencode(params)
    fn = os.path.join(CACHE, hashlib.sha1(u.encode()).hexdigest() + ".json")
    if os.path.exists(fn):
        return json.load(open(fn))
    for a in range(5):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "heat-med-research/1.0"}), timeout=120))
            break
        except Exception:
            time.sleep(3 + 4 * a)
    else:
        raise RuntimeError(u)
    os.makedirs(CACHE, exist_ok=True)
    json.dump(d, open(fn, "w"))
    time.sleep(0.3)
    return d


def all_rows(url, flt, cols=None):
    out, off = [], 0
    while True:
        p = {**flt, "size": 5000, "offset": off}
        if cols:
            p["column"] = cols
        d = get(url, p)
        out += d
        if len(d) < 5000:
            return out
        off += 5000


def num(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def main():
    nat = all_rows(GEO, {"filter[Prscrbr_Geo_Lvl]": "National"})
    ny = all_rows(GEO, {"filter[Prscrbr_Geo_Lvl]": "State", "filter[Prscrbr_Geo_Desc]": "New York"})
    print("national drug rows", len(nat), "| NY rows", len(ny))
    reach = {}
    for cls, rx in CRX.items():
        drugs = defaultdict(lambda: {"nat": 0, "ny": 0, "nat_65": 0})
        for r in nat:
            if rx.search(r["Gnrc_Name"].strip()):
                drugs[r["Gnrc_Name"]]["nat"] += num(r["Tot_Benes"]); drugs[r["Gnrc_Name"]]["nat_65"] += num(r["GE65_Tot_Benes"])
        for r in ny:
            if rx.search(r["Gnrc_Name"].strip()):
                drugs[r["Gnrc_Name"]]["ny"] += num(r["Tot_Benes"])
        top = sorted(drugs.items(), key=lambda kv: -kv[1]["ny"])
        reach[cls] = {"national_benes": sum(v["nat"] for v in drugs.values()), "national_benes_65": sum(v["nat_65"] for v in drugs.values()),
                      "ny_benes": sum(v["ny"] for v in drugs.values()),
                      "drugs": [{"generic": k, **v} for k, v in top[:8]], "n_drugs": len(drugs)}
        print(f"{cls:32} drugs={len(drugs):3} national={reach[cls]['national_benes']:>10,} NY={reach[cls]['ny_benes']:>9,}  top: {', '.join(k for k, _ in top[:3])}")
    spec = {}
    for cls, rv in reach.items():
        tot, n_rows = defaultdict(int), 0
        for d in rv["drugs"][:2]:
            rows = all_rows(PD, {"filter[Prscrbr_State_Abrvtn]": "NY", "filter[Gnrc_Name]": d["generic"]}, "Prscrbr_Type,Tot_Clms")
            n_rows += len(rows)
            for r in rows:
                tot[r["Prscrbr_Type"] or "Unknown"] += num(r["Tot_Clms"])
        T = sum(tot.values()) or 1
        top = sorted(tot.items(), key=lambda kv: -kv[1])
        spec[cls] = {"based_on": [d["generic"] for d in rv["drugs"][:2]], "prescriber_rows": n_rows, "claims": T,
                     "types": [{"type": k, "share": round(v / T, 3)} for k, v in top[:8]]}
        print(f"  {cls:30} " + "; ".join(f"{k} {v / T:.0%}" for k, v in top[:5]))
    json.dump({"built": time.strftime("%Y-%m-%d"), "reach_source": "CMS Part D Prescribers by Geography and Drug, 2023",
               "prescriber_source": "CMS Part D Prescribers by Provider and Drug, 2024, New York prescribers",
               "reach": reach, "prescribers": spec}, open(os.path.join(HERE, "probe_results", "partd.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
