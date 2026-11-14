#!/usr/bin/env python3
"""Pull from the live System API the findings the Dataverse release leaves out.

The API holds ~5.9M associations; the Dataverse CSV holds the ~2.0M that System
vetted. We can't page the whole API (offsets past ~100k time out), so we pull
the slices the evidence map needs:

  1. every variable whose name matches a heat term       -> direct tier, heat half of bridge
  2. every variable for the thin mechanisms (sweating /  -> drug half of the bridge where
     thermoregulation, lithium levels, dehydration)        Dataverse showed gaps
  3. all associations touching those variables (OR filter, batched)
  4. study metadata for the rows

Each association is flagged in_dataverse (vetted) or not. System says ~20% of
API-only rows are mis-extracted, so the map shows them separately.

Usage: source ~/.system_public_env && python3 api_pull.py
Output: probe_results/api_*.csv, probe_results/api_output.txt
"""
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from local_analysis import dv, drug_classes, exposure_drug_classes, is_heat_name, mech_classes

csv.field_size_limit(sys.maxsize)
BASE = "https://public-api.system.com"
KEY = os.environ.get("SYSTEM_API_KEY")
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
OUT = os.path.join(HERE, "probe_results")
MIN_GAP = 0.25
STATS = {"requests": 0, "cached": 0, "failed": 0}
_last = [0.0]

HEAT_TERMS = [
    "heat wave", "heatwave", "heat stroke", "heatstroke", "heat-related", "heat related", "heat illness",
    "heat exhaustion", "extreme heat", "heat stress", "heat exposure", "exposure to heat", "heat index",
    "hot day", "hot weather", "hot season", "hot night", "hot temperature", "ambient temperature",
    "high temperature", "warm season", "warm weather", "summer temperature", "apparent temperature",
    "wet bulb", "WBGT", "hyperthermia", "temperature increase", "temperature rise", "heat",
    # added after the recall test (2026-11-13)
    "outdoor temperature", "daily temperature", "mean temperature", "maximum temperature", "average temperature",
    "ambient heat", "skin heating", "local heat", "heat application", "heat dome", "summer heat", "hot climate",
    "hot environment", "thermal stress", "heat warning", "heat alert", "heat event", "excessive heat",
    "temperature-related", "hot spell", "warm spell",
]
# PubMed seed: papers whose title/abstract is about environmental heat AND a medication.
# Their drug findings count as heat-context evidence even when no variable names heat.
PM_HEAT = ('("heat wave"[tiab] OR "heat waves"[tiab] OR heatwave*[tiab] OR "extreme heat"[tiab] OR "hot weather"[tiab] '
           'OR "high ambient temperature*"[tiab] OR "ambient temperature*"[tiab] OR "outdoor temperature*"[tiab] OR "heat-related"[tiab] '
           'OR "heat related"[tiab] OR "heat stroke"[tiab] OR heatstroke[tiab] OR "heat exposure"[tiab] OR "heat dome"[tiab] '
           'OR "summer heat"[tiab] OR "heat illness"[tiab] OR "heat stress"[tiab] OR "hot days"[tiab] OR "heat index"[tiab])')
PM_DRUG = ('(medication*[tiab] OR drug*[tiab] OR prescri*[tiab] OR polypharmacy[tiab] OR diuretic*[tiab] OR antipsychotic*[tiab] '
           'OR neuroleptic*[tiab] OR psychotropic*[tiab] OR lithium[tiab] OR anticholinergic*[tiab] OR antihypertensive*[tiab] '
           'OR "beta-blocker*"[tiab] OR "beta blocker*"[tiab] OR "ACE inhibitor*"[tiab] OR insulin[tiab] OR opioid*[tiab] '
           'OR antidepressant*[tiab] OR SSRI*[tiab] OR benzodiazepine*[tiab] OR SGLT2[tiab] OR metformin[tiab] OR NSAID*[tiab] '
           'OR "anti-inflammatory"[tiab] OR stimulant*[tiab] OR amphetamine*[tiab] OR topiramate[tiab] OR antiepileptic*[tiab])')
PM_QUERY = f"({PM_HEAT} AND {PM_DRUG} AND humans[mh]) OR ({PM_HEAT} AND {PM_DRUG} AND 2024:2026[dp] NOT animals[mh])"


def pubmed_seed():
    path = os.path.join(HERE, "recall", "pubmed_seed.json")
    if os.path.exists(path):
        with open(path) as f:
            c = json.load(f)
        if c.get("query") == PM_QUERY:
            return c["pmids"]
    u = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "term": PM_QUERY, "retmax": 10000, "retmode": "json"})
    ids = json.load(urllib.request.urlopen(u, timeout=90))["esearchresult"]["idlist"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"query": PM_QUERY, "pmids": ids}, f)
    return ids
MECH_TERMS = [
    "sweat", "sweating", "hypohidrosis", "anhidrosis", "oligohidrosis", "thermoregulation", "core temperature",
    "body temperature", "heat dissipation", "heat tolerance", "lithium level", "serum lithium",
    "lithium concentration", "lithium toxicity", "lithium intoxication", "dehydration", "volume depletion",
    "hyponatremia", "hyponatraemia",
]


def get(path, params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    cpath = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".json")
    if os.path.exists(cpath):
        STATS["cached"] += 1
        with open(cpath) as f:
            c = json.load(f)
        return c["status"], c["body"]
    req = urllib.request.Request(url, headers={"x-api-key": KEY, "accept": "application/json"})
    status, body = 0, None
    for attempt in range(4):
        wait = MIN_GAP - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        STATS["requests"] += 1
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                status, body = r.status, json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            status = e.code
            if status == 504:  # query too heavy; caller splits the batch
                break
            if status in (429, 500, 502, 503) and attempt < 3:
                ra = e.headers.get("Retry-After") if e.headers else None
                time.sleep(float(ra) if (ra or "").isdigit() else 5 * (attempt + 1))
                continue
            break
        except Exception:
            status = 0
            if attempt < 3:
                time.sleep(5 * (attempt + 1))
                continue
    if status == 200:
        os.makedirs(CACHE, exist_ok=True)
        with open(cpath, "w") as f:
            json.dump({"status": status, "body": body}, f)
    else:
        STATS["failed"] += 1
    if STATS["requests"] and STATS["requests"] % 50 == 0:
        sys.stderr.write(f"  ...{STATS['requests']} requests, {STATS['failed']} failed\n")
    return status, body


def search_variables(term):
    out, off = [], 0
    while True:
        s, b = get("/v1/variables", {"search": f"name:{term}", "limit": 5000, "offset": off})
        rows = (b or {}).get("data", []) if s == 200 else []
        out += rows
        if s != 200 or len(rows) < 5000:
            return out, s
        off += 5000


def assoc_for(ids, side):
    """Associations where variable_{side}_id is in ids. Splits the batch on timeout."""
    if not ids:
        return []
    rows, off = [], 0
    while True:
        s, b = get("/v1/associations", {"filter": f"variable_{side}_id:" + "||".join(ids), "limit": 5000, "offset": off})
        if s != 200:
            if len(ids) == 1:
                sys.stderr.write(f"  gave up on variable {ids[0]} (HTTP {s})\n")
                return rows
            h = len(ids) // 2
            return rows + assoc_for(ids[:h], side) + assoc_for(ids[h:], side)
        data = (b or {}).get("data", [])
        rows += data
        if len(data) < 5000:
            return rows
        off += 5000


def main():
    if not KEY:
        sys.exit("SYSTEM_API_KEY is not set. Run: source ~/.system_public_env")
    os.makedirs(OUT, exist_ok=True)
    log = open(os.path.join(OUT, "api_output.txt"), "w")

    def p(*a):
        s = " ".join(str(x) for x in a)
        print(s)
        log.write(s + "\n")
        log.flush()

    # 1-2. Variables
    heat_vars, mech_vars = {}, {}
    p("=== VARIABLE SEARCH (all matches per term) ===")
    for term in HEAT_TERMS:
        rows, s = search_variables(term)
        keep = [v for v in rows if is_heat_name(v.get("name", ""))]
        for v in keep:
            heat_vars[v["system_id"]] = v["name"]
        p(f"  heat  {term:22} {len(rows):6} returned, {len(keep):6} kept" + ("" if s == 200 else f"  HTTP {s}"))
    for term in MECH_TERMS:
        rows, s = search_variables(term)
        keep = [v for v in rows if mech_classes(v.get("name", "")) and not is_heat_name(v.get("name", ""))]
        for v in keep:
            mech_vars[v["system_id"]] = v["name"]
        p(f"  mech  {term:22} {len(rows):6} returned, {len(keep):6} kept" + ("" if s == 200 else f"  HTTP {s}"))

    dv_vars = set()
    with open(dv("variables")) as f:
        for r in csv.DictReader(f):
            dv_vars.add(r["system_id"])
    p(f"\n  heat variables: {len(heat_vars)} ({sum(1 for v in heat_vars if v not in dv_vars)} not in Dataverse)")
    p(f"  mechanism variables: {len(mech_vars)} ({sum(1 for v in mech_vars if v not in dv_vars)} not in Dataverse)")

    # 3. Associations, batched
    allv = list(heat_vars) + list(mech_vars)
    assoc = {}
    for i in range(0, len(allv), 25):
        batch = allv[i:i + 25]
        for side in (1, 2):
            for a in assoc_for(batch, side):
                assoc[a["system_id"]] = a
    p(f"  associations touching them: {len(assoc)}")

    # 3b. PubMed-seeded heat-context studies
    pmids = pubmed_seed()
    seed = {}
    for i in range(0, len(pmids), 50):
        s, b = get("/v1/studies", {"filter": "pubmed_id:" + "||".join(pmids[i:i + 50]), "limit": 100})
        for r in (b or {}).get("data", []) if s == 200 else []:
            seed[r.get("study_id") or r.get("system_id")] = r
    seed_ids = list(seed)
    n0 = len(assoc)
    for i in range(0, len(seed_ids), 25):
        rows_, off = [], 0
        while True:
            s, b = get("/v1/associations", {"filter": "study_id:" + "||".join(seed_ids[i:i + 25]), "limit": 5000, "offset": off})
            data = (b or {}).get("data", []) if s == 200 else []
            for a in data:
                assoc[a["system_id"]] = a
            if s != 200 or len(data) < 5000:
                break
            off += 5000
    with_assoc = {a.get("study_id") for a in assoc.values()} & set(seed_ids)
    p(f"  PubMed seed: {len(pmids)} papers, {len(seed)} in the API, {len(with_assoc)} with extracted findings; "
      f"{len(assoc) - n0} new associations")

    dv_assoc = set()
    with open(dv("associations")) as f:
        for r in csv.DictReader(f):
            if r["system_id"] in assoc:
                dv_assoc.add(r["system_id"])
    p(f"  of which in Dataverse: {len(dv_assoc)}; API only: {len(assoc) - len(dv_assoc)}")

    # 4. Studies
    sids = sorted({a.get("study_id") for a in assoc.values() if a.get("study_id")})
    studies, sidset = {}, set(sids)
    with open(dv("studies")) as f:
        for r in csv.DictReader(f):
            if r["study_id"] in sidset:
                studies[r["study_id"]] = r
    missing = [s for s in sids if s not in studies]
    for i in range(0, len(missing), 50):
        s, b = get("/v1/studies", {"filter": "study_id:" + "||".join(missing[i:i + 50]), "limit": 50})
        for r in (b or {}).get("data", []) if s == 200 else []:
            studies[r.get("study_id") or r.get("system_id")] = {
                "doi": r.get("doi", ""), "pubmed_id": r.get("pubmed_id", ""),
                "population_string": r.get("population") or r.get("population_string") or "",
                "study_type": r.get("study_type") or ""}
    p(f"  studies: {len(sids)} ({len(missing)} looked up in API)")

    # Write all rows with flags
    fields = ["association_id", "in_dataverse", "kind", "classes", "mechanisms", "pubmed_id", "doi", "study_type",
              "heat_side", "other_side", "var1", "var2", "statistic_type", "value", "ci_lower", "ci_upper", "p_value",
              "population", "study_id", "variable_1_id", "variable_2_id"]
    rows = []
    for a in assoc.values():
        v1, v2 = a.get("variable_1_id"), a.get("variable_2_id")
        n1, n2 = a.get("variable_1_name") or "", a.get("variable_2_name") or ""
        h1, h2 = v1 in heat_vars, v2 in heat_vars
        st = studies.get(a.get("study_id"), {})
        base = {"association_id": a["system_id"], "in_dataverse": a["system_id"] in dv_assoc,
                "pubmed_id": a.get("pubmed_id", ""), "doi": st.get("doi", ""), "study_type": st.get("study_type", ""),
                "var1": n1, "var2": n2, "statistic_type": a.get("statistic_type", ""),
                "value": a.get("statistic_value", ""), "ci_lower": a.get("ci_lower", ""),
                "ci_upper": a.get("ci_upper", ""), "p_value": a.get("p_value", ""),
                "population": st.get("population_string", ""), "study_id": a.get("study_id", ""),
                "variable_1_id": v1, "variable_2_id": v2}
        pop_dc = [c for c in exposure_drug_classes(st.get("population_string", "")) if c != "Medication (unspecified)"]
        h1 = h1 or is_heat_name(n1)
        h2 = h2 or is_heat_name(n2)
        if h1 or h2:
            heat_n, other = (n1, n2) if h1 else (n2, n1)
            dc = [] if is_heat_name(other) else drug_classes(other)
            mc = [] if is_heat_name(other) else mech_classes(other)
            if dc:
                kind = "heat-drug"
            elif pop_dc:  # heat finding inside a population defined by a drug ("adults who use insulin")
                kind, dc = "heat-drug-population", pop_dc
            else:
                kind = "heat-mechanism" if mc else "heat-other"
            rows.append({**base, "kind": kind, "classes": " | ".join(dc), "mechanisms": " | ".join(mc),
                         "heat_side": heat_n, "other_side": other})
        elif a.get("study_id") in seed and (exposure_drug_classes(n1) or exposure_drug_classes(n2)):
            dc = sorted(set(exposure_drug_classes(n1)) | set(exposure_drug_classes(n2)))
            rows.append({**base, "kind": "heat-context-drug", "classes": " | ".join(dc),
                         "mechanisms": " | ".join(mech_classes(n2)), "heat_side": "(study is about heat)",
                         "other_side": n1 if exposure_drug_classes(n1) else n2})
        else:
            mech_n, other = (n1, n2) if v1 in mech_vars else (n2, n1)
            dc = drug_classes(other)
            if dc:
                rows.append({**base, "kind": "drug-mechanism", "classes": " | ".join(dc),
                             "mechanisms": " | ".join(mech_classes(mech_n)), "heat_side": "", "other_side": other})
    with open(os.path.join(OUT, "api_findings.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    c = Counter((r["kind"], r["in_dataverse"]) for r in rows)
    p("\n=== ROWS BY KIND (vetted in Dataverse / API only) ===")
    for k in ("heat-drug", "heat-drug-population", "heat-context-drug", "heat-mechanism", "drug-mechanism", "heat-other"):
        p(f"  {k:22} {c[(k, True)]:6} / {c[(k, False)]:6}")
    p(f"\nRequests: {STATS['requests']} new, {STATS['cached']} from cache, {STATS['failed']} failed")


if __name__ == "__main__":
    main()
