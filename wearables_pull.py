#!/usr/bin/env python3
"""Wearables layer: which body signals does each drug class change, and how much evidence is there?

Signals a consumer or clinical wearable can measure during heat:
  heart rate (PPG), heart rate variability, skin temperature, sweat / electrodermal activity,
  core temperature (ingestible or estimated from HR), body weight / hydration, glucose (CGM), blood pressure (cuff)

1. System graph (Dataverse, vetted): findings where a drug class is linked to a body signal (any setting).
2. PubMed counts per class x signal: (a) any setting, (b) in heat, (c) in heat with a wearable device.

  python3 wearables_pull.py  ->  probe_results/wearables.json
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

csv.field_size_limit(sys.maxsize)
HERE = os.path.dirname(os.path.abspath(__file__))
DV = os.path.join(HERE, "dataverse")
CACHE = os.path.join(HERE, "cache_pubmed")

SIGNALS = {
    "Heart rate": (r"\bheart rate\b(?! variability)|\bpulse rate\b|\btachycardia\b", '"heart rate"[tiab]'),
    "HR variability": (r"heart rate variability|\bHRV\b", '"heart rate variability"[tiab]'),
    "Skin temperature": (r"skin temperature|skin blood flow|cutaneous (?:blood flow|vasodilat\w*)", '("skin temperature"[tiab] OR "skin blood flow"[tiab])'),
    "Sweat / EDA": (r"\bsweat\w*|electrodermal|skin conductance|anhidrosis|hypohidrosis|oligohidrosis", '(sweat*[tiab] OR electrodermal[tiab] OR "skin conductance"[tiab] OR hypohidrosis[tiab] OR anhidrosis[tiab])'),
    "Core temperature": (r"core (?:body )?temperature|rectal temperature|esophageal temperature|body temperature", '("core temperature"[tiab] OR "rectal temperature"[tiab] OR "body temperature"[tiab])'),
    "Weight / hydration": (r"body weight change|weight loss|hydration|plasma volume|dehydration|hypohydration", '(hydration[tiab] OR dehydration[tiab] OR hypohydration[tiab] OR "plasma volume"[tiab])'),
    "Glucose (CGM)": (r"\bglucose\b|hypoglyc\w*", '(hypoglycemia[tiab] OR hypoglycaemia[tiab] OR "continuous glucose"[tiab])'),
    "Blood pressure": (r"blood pressure|hypotension", '("blood pressure"[tiab] OR hypotension[tiab])'),
}
CLASSES = {
    "Beta blockers": (r"beta[- ]?blocker|beta[- ]adrenergic (?:blocker|antagonist)|propranolol|metoprolol|atenolol|bisoprolol|carvedilol", '("Adrenergic beta-Antagonists"[MeSH] OR "beta blocker*"[tiab] OR propranolol[tiab] OR metoprolol[tiab] OR atenolol[tiab])'),
    "Anticholinergics": (r"anticholinergic|antimuscarinic|atropine|scopolamine|glycopyrr\w*|oxybutynin|benztropine", '("Cholinergic Antagonists"[MeSH] OR anticholinergic*[tiab] OR atropine[tiab] OR oxybutynin[tiab] OR glycopyrr*[tiab])'),
    "Diuretics": (r"diuretic|furosemide|thiazide|hydrochlorothiazide|spironolactone", '("Diuretics"[MeSH] OR diuretic*[tiab] OR furosemide[tiab] OR hydrochlorothiazide[tiab])'),
    "ACE inhibitors / ARBs": (r"ace inhibitor|angiotensin|enalapril|lisinopril|ramipril|losartan|valsartan", '("Angiotensin-Converting Enzyme Inhibitors"[MeSH] OR "Angiotensin Receptor Antagonists"[MeSH] OR lisinopril[tiab] OR losartan[tiab])'),
    "Calcium channel blockers": (r"calcium channel|amlodipine|nifedipine|diltiazem|verapamil", '("Calcium Channel Blockers"[MeSH] OR amlodipine[tiab] OR nifedipine[tiab])'),
    "Antipsychotics": (r"antipsychotic|neuroleptic|olanzapine|clozapine|haloperidol|quetiapine|risperidone", '("Antipsychotic Agents"[MeSH] OR antipsychotic*[tiab] OR olanzapine[tiab] OR clozapine[tiab])'),
    "Antidepressants": (r"antidepressant|ssri|serotonin reuptake|tricyclic|amitriptyline|sertraline|fluoxetine", '("Antidepressive Agents"[MeSH] OR antidepressant*[tiab] OR SSRI*[tiab])'),
    "Stimulants": (r"stimulant|amphetamine|methylphenidate|cocaine", '("Central Nervous System Stimulants"[MeSH] OR amphetamine*[tiab] OR methylphenidate[tiab])'),
    "Insulin and sulfonylureas": (r"insulin|sulfonylurea|glimepiride|glyburide|glibenclamide|gliclazide", '(insulin[tiab] OR sulfonylurea*[tiab])'),
    "Topiramate / zonisamide": (r"topiramate|zonisamide", '(topiramate[tiab] OR zonisamide[tiab])'),
}
HEAT_Q = '("Hot Temperature"[MeSH] OR "heat stress"[tiab] OR "hot environment"[tiab] OR "heat exposure"[tiab] OR heatwave*[tiab] OR "heat wave"[tiab] OR "exercise in the heat"[tiab] OR sauna[tiab])'
WEAR_Q = '("Wearable Electronic Devices"[MeSH] OR wearable*[tiab] OR smartwatch*[tiab] OR "wrist-worn"[tiab] OR photoplethysmograph*[tiab] OR "continuous glucose monitor*"[tiab])'


def count(q):
    key = os.path.join(CACHE, "count_" + str(abs(hash(q)) % 10**12) + ".json")
    if os.path.exists(key):
        return json.load(open(key))
    u = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=5&sort=relevance&term=" + urllib.parse.quote(q)
    for a in range(4):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "heat-med-research/1.0"}), timeout=40))["esearchresult"]
            break
        except Exception:
            time.sleep(2 + 3 * a)
    else:
        raise RuntimeError(q)
    out = {"count": int(d["count"]), "ids": d["idlist"]}
    os.makedirs(CACHE, exist_ok=True)
    json.dump(out, open(key, "w"))
    time.sleep(0.35)
    return out


def main():
    crx = {c: re.compile(p, re.I) for c, (p, _) in CLASSES.items()}
    srx = {s: re.compile(p, re.I) for s, (p, _) in SIGNALS.items()}
    heat = re.compile(r"\bheat\b|hot environment|sauna|thermal stress|hyperthermi", re.I)
    graph = defaultdict(set)
    graph_heat = defaultdict(set)
    for r in csv.DictReader(open(os.path.join(DV, "system-public-graph-v1-associations.csv"))):
        a, b = r["variable_1_name"], r["variable_2_name"]
        for c, cr in crx.items():
            side = a if cr.search(a) else b if cr.search(b) else None
            if side is None:
                continue
            other = b if side is a else a
            for s, sr in srx.items():
                if sr.search(other):
                    graph[(c, s)].add(r["pubmed_id"])
                    if heat.search(a + " " + b):
                        graph_heat[(c, s)].add(r["pubmed_id"])
    cells = []
    for c, (_, cq) in CLASSES.items():
        for s, (_, sq) in SIGNALS.items():
            any_ = count(f"{cq} AND {sq}")
            hot = count(f"{cq} AND {sq} AND {HEAT_Q}")
            wear = count(f"{cq} AND {sq} AND {HEAT_Q} AND {WEAR_Q}")
            cells.append({"class": c, "signal": s, "graph": len(graph[(c, s)]), "graph_heat": len(graph_heat[(c, s)]),
                          "pubmed_any": any_["count"], "pubmed_heat": hot["count"], "pubmed_heat_wearable": wear["count"],
                          "heat_examples": hot["ids"][:3], "wearable_examples": wear["ids"][:3]})
            print(f"{c:26} {s:18} graph={len(graph[(c, s)]):4} graph_heat={len(graph_heat[(c, s)]):2}  pubmed={any_['count']:6} heat={hot['count']:4} heat+wearable={wear['count']:2}")
    json.dump({"built": time.strftime("%Y-%m-%d"), "signals": list(SIGNALS), "classes": list(CLASSES), "cells": cells,
               "queries": {"heat": HEAT_Q, "wearable": WEAR_Q, "classes": {c: q for c, (_, q) in CLASSES.items()}, "signals": {s: q for s, (_, q) in SIGNALS.items()}}},
              open(os.path.join(HERE, "probe_results", "wearables.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
