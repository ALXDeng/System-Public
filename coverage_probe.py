#!/usr/bin/env python3
"""Coverage probe for Visualize Challenge 3 (heat-sensitive medications).

Asks the System Public Graph three questions:
  1. Which drug, heat and mechanism concepts exist?
  2. Direct tier: does any drug concept link straight to a heat concept?
  3. Bridged tier: do drugs and heat both link to the same mechanism?

Reads the key from SYSTEM_API_KEY. Standard library only.
Responses are cached in ./cache so reruns don't spend the daily quota.

Usage:
    source ~/.system_public_env && python3 coverage_probe.py
"""
import csv
import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://public-api.system.com"
KEY = os.environ.get("SYSTEM_API_KEY")
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
OUT = os.path.join(HERE, "probe_results")
REQUESTS_MADE = 0
FAILS = {}  # HTTP status -> count of requests that never got a definitive answer
THROTTLE = threading.Lock()
LAST = [0.0]
MIN_GAP = 0.12  # seconds between requests
WORKERS = 2

# Words that mark a variable name as a medication, for scanning heat findings.
DRUG_WORDS = [
    "diuretic", "furosemide", "thiazide", "beta-blocker", "beta blocker", "ace inhibitor",
    "angiotensin", "anticholinergic", "antipsychotic", "neuroleptic", "psychotropic", "lithium",
    "antidepressant", "ssri", "tricyclic", "insulin", "sglt2", "metformin", "nsaid",
    "anti-inflammatory", "antihistamine", "stimulant", "opioid", "anticonvulsant", "statin",
    "medication", "drug", "prescri", "polypharmacy", "antihypertensive", "sedative", "benzodiazepine",
]
HEAT_VARIABLE_TERMS = [
    "heat wave", "heat stroke", "heat-related illness", "heat-related hospitalization",
    "heat-related mortality", "heat exposure", "high ambient temperature",
]
COMBINED_QUERIES = [
    "medication use heat-related hospitalization", "diuretic heat wave", "antipsychotic heat stroke",
    "anticholinergic heat-related death", "beta blocker heat wave", "lithium heat", "insulin heat",
    "psychotropic medication heat wave mortality", "ACE inhibitor heat wave hospitalization",
    "SGLT2 inhibitor heat dehydration", "medication storage temperature degradation",
    "wearable skin temperature heat strain",
]

DRUGS = {
    "Diuretics": ["diuretic", "furosemide", "hydrochlorothiazide", "spironolactone"],
    "Beta blockers": ["beta blocker", "metoprolol", "propranolol"],
    "ACE inhibitors / ARBs": ["ACE inhibitor", "lisinopril", "angiotensin receptor blocker", "losartan"],
    "Anticholinergics": ["anticholinergic", "oxybutynin", "diphenhydramine", "antihistamine"],
    "Antipsychotics": ["antipsychotic", "olanzapine", "clozapine", "haloperidol", "quetiapine"],
    "Lithium": ["lithium"],
    "Antidepressants": ["selective serotonin reuptake inhibitor", "tricyclic antidepressant", "amitriptyline", "sertraline"],
    "Insulin": ["insulin"],
    "SGLT2 inhibitors": ["SGLT2 inhibitor", "empagliflozin", "dapagliflozin"],
    "Other diabetes": ["metformin", "sulfonylurea"],
    "NSAIDs": ["nonsteroidal anti-inflammatory drug", "ibuprofen"],
    "Stimulants": ["methylphenidate", "amphetamine"],
    "Anticonvulsants": ["topiramate"],
    "Opioids": ["opioid"],
    "Storage-sensitive": ["epinephrine", "salbutamol", "levothyroxine"],
}
HEAT = [
    "heat stroke", "heat illness", "heat exhaustion", "heat wave", "heat stress",
    "hyperthermia", "extreme heat", "ambient temperature", "high temperature",
    "temperature", "heat",
]
MECHANISMS = [
    "hyponatremia", "dehydration", "acute kidney injury", "hypohidrosis",
    "orthostatic hypotension", "hypotension", "syncope", "hypokalemia",
    "hyperkalemia", "hypoglycemia", "diabetic ketoacidosis", "rhabdomyolysis",
    "electrolyte imbalance", "fall", "hospitalization", "emergency department visit",
]


def get(path, params=None):
    """GET with on-disk cache. Returns (status, parsed_json_or_None)."""
    global REQUESTS_MADE
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    os.makedirs(CACHE, exist_ok=True)
    cpath = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            c = json.load(f)
        return c["status"], c["body"]
    req = urllib.request.Request(url, headers={"x-api-key": KEY, "accept": "application/json"})
    status, body = 0, None
    for attempt in range(6):
        with THROTTLE:  # one request at a time, spaced out: bursts get refused
            wait = MIN_GAP - (time.time() - LAST[0])
            if wait > 0:
                time.sleep(wait)
            LAST[0] = time.time()
            REQUESTS_MADE += 1
            if REQUESTS_MADE % 50 == 0:
                sys.stderr.write(f"  ...{REQUESTS_MADE} requests, failures so far: {dict(FAILS) or 'none'}\n")
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                status, body = r.status, json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            status = e.code
            try:
                body = json.loads(e.read().decode())
            except Exception:
                body = None
            if status in (403, 429, 500, 502, 503, 504) and attempt < 5:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                time.sleep(float(retry_after) if (retry_after or "").isdigit() else 3 * (attempt + 1))
                continue
            break
        except Exception as e:  # network hiccup or timeout
            status, body = 0, {"error": str(e)}
            if attempt < 5:
                time.sleep(3 * (attempt + 1))
                continue
            break
    if status in (200, 404):  # only cache definitive answers
        with open(cpath, "w") as f:
            json.dump({"status": status, "body": body}, f)
    else:
        FAILS[status] = FAILS.get(status, 0) + 1
    return status, body


def resolve(term):
    """Find the concept for a term. Exact label or alias match wins; else top hit, flagged fuzzy."""
    hits, failed = [], False
    for field in ("wikidata_label", "wikidata_aliases"):
        status, body = get("/v1/concepts", {"search": f"{field}:{term}", "limit": 25})
        if status != 200 or not body:
            failed = failed or status != 404
            continue
        for c in body.get("data", []):
            if c["system_id"] not in [h["system_id"] for h in hits]:
                hits.append(c)
    t = term.lower()
    for c in hits:
        if (c.get("wikidata_label") or "").lower() == t:
            return c, "exact", hits
    for c in hits:
        if t in [a.lower() for a in (c.get("wikidata_aliases") or [])]:
            return c, "alias", hits
    if hits:
        return hits[0], "fuzzy", hits
    return None, ("ERROR" if failed else "none"), hits


def rel_total(concept_id):
    status, body = get(f"/v1/concepts/{concept_id}/relationships", {"limit": 1, "include_total": "true"})
    return (body or {}).get("total") if status == 200 else None


def pair(a, b):
    """Look up the relationship between two concept ids, trying both orders."""
    for x, y in ((a, b), (b, a)):
        status, body = get("/v1/relationships/" + urllib.parse.quote(f"{x}|{y}", safe=""))
        if status == 200 and body:
            return body.get("num_studies") or 0, body.get("num_findings") or 0
    return 0, 0


def main():
    if not KEY:
        sys.exit("SYSTEM_API_KEY is not set. Run: source ~/.system_public_env")
    os.makedirs(OUT, exist_ok=True)

    status, body = get("/v1/concepts", {"search": "wikidata_label:lithium", "limit": 3})
    if status != 200:
        sys.exit(f"API check failed: HTTP {status} {json.dumps(body)[:300]}")

    # 1. Resolve concepts
    groups = [("drug", cls, t) for cls, terms in DRUGS.items() for t in terms]
    groups += [("heat", "Heat", t) for t in HEAT] + [("mechanism", "Mechanism", t) for t in MECHANISMS]
    with ThreadPoolExecutor(WORKERS) as ex:
        resolved = list(ex.map(lambda g: resolve(g[2]), groups))
    concepts = []
    for (kind, cls, term), (c, how, hits) in zip(groups, resolved):
        concepts.append({
            "kind": kind, "class": cls, "term": term, "match": how,
            "id": c["system_id"] if c else None,
            "label": (c.get("wikidata_label") or term) if c else None,
            "other_hits": [h.get("wikidata_label") for h in hits[:6]],
        })
    live = [c for c in concepts if c["id"]]
    with ThreadPoolExecutor(WORKERS) as ex:
        for c, n in zip(live, ex.map(lambda c: rel_total(c["id"]), live)):
            c["relationships"] = n

    print("\n=== 1. CONCEPTS ===")
    print(f"{'kind':10} {'term':40} {'match':6} {'rels':>6}  matched label")
    for c in concepts:
        print(f"{c['kind']:10} {c['term'][:40]:40} {c['match']:6} {str(c.get('relationships', '-')):>6}  {c['label'] or '-'}")
        if c["match"] in ("fuzzy", "none") and c["other_hits"]:
            print(f"{'':59}candidates: {', '.join(str(h) for h in c['other_hits'])}")

    drugs = [c for c in live if c["kind"] == "drug"]
    heat = [c for c in live if c["kind"] == "heat"]
    mech = [c for c in live if c["kind"] == "mechanism"]

    # 2 + 3. Pair lookups
    jobs = [(a, b) for a in drugs for b in heat] + [(a, b) for a in drugs for b in mech] + [(a, b) for a in heat for b in mech]
    with ThreadPoolExecutor(WORKERS) as ex:
        res = list(ex.map(lambda j: pair(j[0]["id"], j[1]["id"]), jobs))
    links = {(a["id"], b["id"]): r for (a, b), r in zip(jobs, res)}

    rows = []
    print("\n=== 2. DIRECT TIER: drug x heat (studies/findings) ===")
    found = False
    for d in drugs:
        hitlist = [(h["label"], *links[(d["id"], h["id"])]) for h in heat if links[(d["id"], h["id"])][0]]
        for lbl, s, f in hitlist:
            rows.append({"tier": "direct", "class": d["class"], "drug": d["label"], "partner": lbl, "studies": s, "findings": f})
        if hitlist:
            found = True
            print(f"  {d['class']:24} {d['label'][:30]:30} " + "; ".join(f"{l} {s}/{f}" for l, s, f in hitlist))
    if not found:
        print("  none")

    print("\n=== 3a. HEAT x MECHANISM (studies/findings) ===")
    heat_mech = {}
    for m in mech:
        hl = [(h["label"], *links[(h["id"], m["id"])]) for h in heat if links[(h["id"], m["id"])][0]]
        heat_mech[m["id"]] = sum(s for _, s, _ in hl)
        for lbl, s, f in hl:
            rows.append({"tier": "heat-mechanism", "class": "Heat", "drug": lbl, "partner": m["label"], "studies": s, "findings": f})
        print(f"  {m['label'][:30]:30} " + ("; ".join(f"{l} {s}/{f}" for l, s, f in hl) or "none"))

    print("\n=== 3b. BRIDGED TIER: drug x mechanism, where heat also reaches the mechanism ===")
    summary = {}
    for d in drugs:
        bl = []
        for m in mech:
            s, f = links[(d["id"], m["id"])]
            if s:
                bridged = heat_mech[m["id"]] > 0
                rows.append({"tier": "bridged" if bridged else "drug-mechanism-only", "class": d["class"],
                             "drug": d["label"], "partner": m["label"], "studies": s, "findings": f})
                bl.append(f"{m['label']} {s}/{f}" + ("" if bridged else " (no heat link)"))
                if bridged:
                    summary.setdefault(d["class"], [0, 0])[1] += s
        if bl:
            print(f"  {d['class']:24} {d['label'][:26]:26} " + "; ".join(bl))
    for r in rows:
        if r["tier"] == "direct":
            summary.setdefault(r["class"], [0, 0])[0] += r["studies"]

    print("\n=== SUMMARY BY DRUG CLASS (study counts, summed over concept pairs) ===")
    print(f"  {'class':26} {'direct':>7} {'bridged':>8}")
    for cls in DRUGS:
        d_, b_ = summary.get(cls, [0, 0])
        print(f"  {cls:26} {d_:>7} {b_:>8}")

    # 4. What does the graph link heat to at all?
    print("\n=== 4. TOP PARTNERS OF EACH HEAT CONCEPT (by studies) ===")
    for h in heat:
        status, body = get(f"/v1/concepts/{h['id']}/relationships", {"limit": 25, "sort": "num_studies:desc"})
        if status != 200 or not body:
            print(f"  {h['label']}: HTTP {status}")
            continue
        parts = []
        for r in body.get("data", []):
            s, t = r.get("source_concept") or {}, r.get("target_concept") or {}
            other = t if s.get("system_id") == h["id"] else s
            parts.append(f"{other.get('wikidata_label')} ({r.get('num_studies')})")
        print(f"  {h['label']} [{h.get('relationships')} rels]: " + ", ".join(parts))

    # 5. Ungrounded texture: variable names
    print("\n=== 5. VARIABLE NAME SEARCH (totals) ===")
    for term in ["heat wave", "heat stroke", "heat-related", "heat illness", "ambient temperature", "heat exposure"]:
        status, body = get("/v1/variables", {"search": f"name:{term}", "limit": 8, "include_total": "true"})
        if status == 200 and body:
            print(f"  {term}: total {body.get('total')} e.g. " + " | ".join(v.get("name", "") for v in body.get("data", [])))
        else:
            print(f"  {term}: HTTP {status}")

    # 6. Ranked variable search with a drug and heat in the same query
    print("\n=== 6. COMBINED VARIABLE SEARCHES (top names) ===")
    for q in COMBINED_QUERIES:
        status, body = get("/v1/variables", {"search": f"name:{q}", "limit": 6})
        names = [v.get("name", "") for v in (body or {}).get("data", [])] if status == 200 else [f"HTTP {status}"]
        print(f"  {q}:\n     " + "\n     ".join(n[:150] for n in names))

    # 7. Variable route: take heat variables, pull their findings, flag drug partners
    print("\n=== 7. HEAT VARIABLES -> FINDINGS -> DRUG PARTNERS ===")
    heat_vars = {}
    for term in HEAT_VARIABLE_TERMS:
        status, body = get("/v1/variables", {"search": f"name:{term}", "limit": 60})
        for v in (body or {}).get("data", []) if status == 200 else []:
            heat_vars[v["system_id"]] = v.get("name", "")
    ids = list(heat_vars)

    def assoc(vid):
        status, body = get(f"/v1/variables/{vid}/associations", {"limit": 100})
        return (body or {}).get("data", []) if status == 200 else []

    with ThreadPoolExecutor(WORKERS) as ex:
        all_assoc = list(ex.map(assoc, ids))
    seen, drug_hits, n_assoc = set(), [], 0
    for vid, alist in zip(ids, all_assoc):
        for a in alist:
            if a["system_id"] in seen:
                continue
            seen.add(a["system_id"])
            n_assoc += 1
            other = a.get("variable_2_name") if a.get("variable_1_id") == vid else a.get("variable_1_name")
            words = [w for w in DRUG_WORDS if w in (other or "").lower()]
            if words:
                drug_hits.append({
                    "heat_variable": heat_vars[vid], "partner": other, "matched": ",".join(words),
                    "statistic_type": a.get("statistic_type"), "value": a.get("statistic_value"),
                    "ci_lower": a.get("ci_lower"), "ci_upper": a.get("ci_upper"), "p_value": a.get("p_value"),
                    "pubmed_id": a.get("pubmed_id"), "association_id": a["system_id"],
                })
    print(f"  heat variables scanned: {len(ids)}; findings on them: {n_assoc}; with a medication partner: {len(drug_hits)}")
    print(f"  distinct studies among medication findings: {len({h['pubmed_id'] for h in drug_hits})}")
    for h in drug_hits[:60]:
        print(f"  - [{h['pubmed_id']}] {str(h['partner'])[:70]}  x  {h['heat_variable'][:70]}  ({h['statistic_type']} {h['value']})")
    if drug_hits:
        with open(os.path.join(OUT, "heat_drug_findings.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(drug_hits[0]))
            w.writeheader()
            w.writerows(drug_hits)

    print(f"\nRequests that never got an answer, by HTTP status (0 = timeout): {FAILS or 'none'}")
    with open(os.path.join(OUT, "concepts.json"), "w") as f:
        json.dump(concepts, f, indent=2)
    with open(os.path.join(OUT, "links.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tier", "class", "drug", "partner", "studies", "findings"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nNew API requests this run: {REQUESTS_MADE}. Results saved in {OUT}")


class Tee:
    """Copy everything printed to a log file, so the run can be read back later."""

    def __init__(self, path):
        self.term, self.log = sys.stdout, open(path, "w")

    def write(self, s):
        self.term.write(s)
        self.log.write(s)
        self.log.flush()

    def flush(self):
        self.term.flush()


if __name__ == "__main__":
    import traceback

    os.makedirs(OUT, exist_ok=True)
    sys.stdout = Tee(os.path.join(OUT, "probe_output.txt"))
    try:
        main()
    except SystemExit as e:
        print(f"STOPPED: {e}")
        raise
    except Exception:
        print("CRASHED:\n" + traceback.format_exc())
        raise
