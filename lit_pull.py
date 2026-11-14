#!/usr/bin/env python3
"""Literature layer: heat x medication studies found OUTSIDE the graph, and whether the graph has them.

1. Candidates = the 57 hand-screened papers in recall/relevant.txt
              + reference lists of key reviews (PubMed elink pubmed_pubmed_refs)
              + papers citing key primary studies (pubmed_pubmed_citedin)
2. Fetch title, abstract, year, publication types, MeSH, first affiliation (efetch XML).
3. Screen by rule: climate/ambient/body heat AND a medication; drop TCM 'heat', heat-shock proteins, hot flashes, lab heat-pain.
4. Type each study (epidemiology / seasonal / experimental / physiology / case report / storage / review) and tag drug classes.
5. Graph status per PMID: vetted findings (Dataverse) / API findings / study record without findings / absent.

  source ~/.system_public_env && python3 lit_pull.py  ->  probe_results/literature.csv, literature.json
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import api_pull  # noqa: E402  (get() with cache, rate limit, retries)

csv.field_size_limit(sys.maxsize)
EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CACHE = os.path.join(HERE, "cache_pubmed")
REVIEWS = {"42200961": "Scoping review 2026 (older adults, FDA labels)", "41968235": "Narrative review 2026 (heat-vulnerability drugs)",
           "39513185": "Systematic review 2024 (drugs and core temperature in heat)", "26073686": "Westaway 2015 review",
           "9571303": "1998 review (hyperthermia and pharmacokinetics)"}
# Hand review of titles, 2026-11-14
EXCLUDE = {"2759081", "2830109", "9459535", "8866876", "3218898", "23578306", "25512891", "15954131", "32546415",
           "27225859", "16281522", "41269585"}  # no drug x heat question (sauna hormones, plan evaluation, anaesthesia fever, etc.)
TYPE_FIX = {"2262461": "physiology", "10926160": "physiology", "1335440": "physiology", "2355819": "physiology", "6725067": "physiology",
            "14841388": "physiology", "3432054": "physiology", "27768523": "physiology", "8866876": "physiology", "34119011": "physiology",
            "7000239": "experimental", "26656500": "case", "4152488": "case", "32730241": "epidemiology", "39591627": "epidemiology",
            "31205291": "epidemiology", "26073686": "review", "24613712": "case", "26052028": "case", "7589027": "experimental", "6259250": "physiology",
            "7957149": "physiology", "8831332": "physiology", "3092610": "experimental"}
NOTE = {"31205291": "Cold, not heat, raised overdose deaths; graph lost the direction"}
CITED = ["33301532", "27378245", "20104062", "38060348", "37897873", "17698677", "29116624", "31205291", "17513091"]


def eu(path, params, key):
    fn = os.path.join(CACHE, key)
    if os.path.exists(fn):
        return open(fn, "rb").read()
    url = EU + path + "?" + urllib.parse.urlencode(params)
    for a in range(4):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "heat-med-research/1.0"}), timeout=60).read()
            break
        except Exception:
            time.sleep(2 + 3 * a)
    else:
        raise RuntimeError(url)
    os.makedirs(CACHE, exist_ok=True)
    open(fn, "wb").write(b)
    time.sleep(0.4)
    return b


def links(pmid, linkname):
    d = json.loads(eu("elink.fcgi", {"dbfrom": "pubmed", "db": "pubmed", "id": pmid, "linkname": linkname, "retmode": "json"}, f"link_{linkname}_{pmid}.json"))
    out = []
    for ls in d.get("linksets", []):
        for ld in ls.get("linksetdbs", []):
            out += ld.get("links", [])
    return out


def fetch(pmids):
    recs = {}
    for i in range(0, len(pmids), 150):
        batch = pmids[i:i + 150]
        x = eu("efetch.fcgi", {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}, f"efetch_{hash(tuple(batch)) & 0xffffffff:x}_{len(batch)}.xml")
        root = ET.fromstring(x)
        for a in root.iter("PubmedArticle"):
            pm = a.findtext(".//PMID")
            title = "".join(a.find(".//ArticleTitle").itertext()) if a.find(".//ArticleTitle") is not None else ""
            abst = " ".join("".join(t.itertext()) for t in a.findall(".//Abstract/AbstractText"))
            year = a.findtext(".//PubDate/Year") or (a.findtext(".//PubDate/MedlineDate") or "")[:4]
            ptypes = [p.text for p in a.findall(".//PublicationType")]
            mesh = [m.findtext("DescriptorName") for m in a.findall(".//MeshHeading")]
            aff = a.findtext(".//AffiliationInfo/Affiliation") or ""
            journal = a.findtext(".//Journal/ISOAbbreviation") or ""
            recs[pm] = {"pmid": pm, "title": title, "abstract": abst, "year": year, "ptypes": ptypes, "mesh": mesh, "aff": aff, "journal": journal}
    return recs


HEAT = re.compile(r"\b(heat ?waves?|heatwaves?|heat[- ]related|heat[- ]?stroke|heat exhaustion|heat illness|heat stress|heat strain|extreme heat|hot weather|hot (?:days?|season|climate|environment|summer)|"
                  r"high (?:ambient |environmental |outdoor )?temperatures?|ambient temperature|outdoor temperature|air temperature|daily (?:mean |maximum )?temperature|"
                  r"summer|warm season|season(?:al|ality)?|climat\w*|thermoregulat\w*|hyperthermi\w*|sweat\w*|anhidrosis|oligohidrosis|"
                  r"heat exposure|exposed to heat|local heat|skin heating|heating pad|sauna|elevated temperature|temperature excursion|storage temperature|core temperature|body temperature)\b", re.I)
NOT_HEAT = re.compile(r"heat shock|hsp\d|damp[- ]heat|clearing heat|heat[- ]clearing|yin[- ]deficiency|hot flash|hot flush|heat pain|thermal pain|heat hyperalgesia|"
                      r"heat[- ]killed|heat[- ]inactivat|radiofrequency|ablation|hyperthermic intraperitoneal|HIPEC|malignant hyperthermia|sterili[sz]", re.I)
DRUG = re.compile(r"\b(medication|medicine|drugs?|pharmac\w*|prescri\w*|polypharmacy|diuretic|furosemide|thiazide|hydrochlorothiazide|ace inhibitor|angiotensin|"
                  r"antihypertensive|beta[- ]?blocker|propranolol|metoprolol|atenolol|calcium channel|amlodipine|anticholinergic|oxybutynin|atropine|scopolamine|glycopyrr\w*|"
                  r"antipsychotic|neuroleptic|olanzapine|clozapine|haloperidol|quetiapine|lithium|antidepressant|ssri|tricyclic|psychotropic|benzodiazepine|hypnotic|anxiolytic|"
                  r"opioid|fentanyl|methadone|morphine|heroin|insulin|sglt2|gliflozin|empagliflozin|dapagliflozin|metformin|sulfonylurea|glucose-lowering|antidiabetic|"
                  r"nsaid|ibuprofen|diclofenac|naproxen|topiramate|zonisamide|stimulant|amphetamine|methylphenidate|cocaine|epinephrine|adrenaline|inhaler|salbutamol|albuterol|nitroglycerin|"
                  r"antihistamine|diphenhydramine|glp-1|semaglutide|levodopa|dopaminergic|cholinesterase|donepezil|digoxin|corticosteroid|immunosuppress\w*)\b", re.I)
CLASSES = [
    ("Diuretics", r"diuretic|furosemide|thiazide|hydrochlorothiazide|spironolactone|bumetanide|torasemide|loop diuretic"),
    ("ACE inhibitors / ARBs", r"ace inhibitor|angiotensin|enalapril|lisinopril|ramipril|losartan|valsartan|irbesartan|\bARBs?\b|\bACEIs?\b|renin"),
    ("Beta blockers", r"beta[- ]?blocker|beta[- ]adrenergic (?:blocker|antagonist)|propranolol|metoprolol|atenolol|bisoprolol"),
    ("Calcium channel blockers", r"calcium channel|amlodipine|nifedipine|diltiazem|verapamil"),
    ("Antihypertensives (unspecified)", r"antihypertensive|blood pressure[- ]lowering|cardiovascular (?:drug|medication)"),
    ("Anticholinergics", r"anticholinergic|antimuscarinic|oxybutynin|atropine|scopolamine|glycopyrr\w*|benztropine|diphenhydramine|antihistamine"),
    ("Antipsychotics", r"antipsychotic|neuroleptic|olanzapine|clozapine|haloperidol|quetiapine|risperidone|chlorpromazine|phenothiazine"),
    ("Lithium", r"lithium"),
    ("Antidepressants", r"antidepressant|ssri|serotonin reuptake|tricyclic|amitriptyline|sertraline|fluoxetine|venlafaxine"),
    ("Psychotropics (unspecified)", r"psychotropic|psychiatric (?:drug|medication)"),
    ("Benzodiazepines / sedatives", r"benzodiazepine|hypnotic|anxiolytic|sedative|zolpidem|diazepam|lorazepam"),
    ("Opioids", r"opioid|opiate|fentanyl|methadone|morphine|heroin|oxycodone|tramadol"),
    ("Insulin", r"insulin"),
    ("SGLT2 inhibitors", r"sglt2|gliflozin|empagliflozin|dapagliflozin|canagliflozin"),
    ("Metformin and sulfonylureas", r"metformin|sulfonylurea|glucose-lowering|antidiabet\w*|glimepiride|glipizide|hypoglyc\w* (?:drug|agent)|glibenclamide|glyburide|gliclazide"),
    ("NSAIDs", r"nsaid|non-?steroidal anti-?inflammatory|ibuprofen|diclofenac|naproxen|aspirin"),
    ("Topiramate / zonisamide", r"topiramate|zonisamide|antiepileptic|anticonvulsant"),
    ("Stimulants", r"stimulant|amphetamine|methylphenidate|cocaine|mdma|methamphetamine"),
    ("Heat-labile emergency products", r"epinephrine|adrenaline|auto-?injector|inhaler|salbutamol|albuterol|nitroglycerin|glyceryl trinitrate"),
    ("GLP-1 agonists", r"glp-1|semaglutide|liraglutide|dulaglutide|tirzepatide"),
    ("Parkinson / dopaminergic", r"levodopa|dopaminergic|parkinson|bromocriptine|pramipexole|ropinirole"),
    ("Cholinesterase inhibitors", r"cholinesterase inhibitor|donepezil|rivastigmine|galantamine"),
    ("Any medication / polypharmacy", r"polypharmacy|number of (?:medications|drugs)|any medication|medication use|prescription drugs?|multiple medications"),
]
CLASSES = [(n, re.compile(r"\b(?:" + p + r")", re.I)) for n, p in CLASSES]


def evidence_type(r):
    t = (r["title"] + " " + r["abstract"]).lower(); pt = " ".join(r["ptypes"]).lower()
    if "systematic review" in pt or "meta-analysis" in pt: return "review"
    if "review" in pt and "case reports" not in pt: return "review"
    if "case reports" in pt or re.search(r"\bcase report|\ba case of\b|\bwe (?:report|describe|present) (?:a|an|two|three)", t): return "case"
    if re.search(r"stabilit|potency|degradat|storage|stored at|temperature excursion|hot car", t): return "storage"
    if re.search(r"absorption|pharmacokinetic|plasma (?:level|concentration)|serum (?:level|concentration)|bioavailab|patch|injection site|local heat|skin heating|sauna", t) and re.search(r"healthy|volunteer|crossover|randomi[sz]ed|subjects|participants", t):
        return "experimental"
    if re.search(r"climatic chamber|environmental chamber|exercise in (?:the )?heat|heat stress test|passive heat|core temperature|sweat rate|thermoregulat|skin blood flow", t) and re.search(r"healthy|volunteer|subjects|participants|placebo", t):
        return "physiology"
    if re.search(r"\bseason|summer (?:vs|versus|and winter)|winter|month of", t) and not re.search(r"heat ?wave|heatwave|extreme heat|daily temperature|ambient temperature", t):
        return "seasonal"
    if re.search(r"heat ?waves?|heatwave|extreme heat|ambient temperature|daily (?:mean |maximum )?temperature|outdoor temperature|hot weather|heat[- ]related|heat illness|heat ?stroke|case-crossover|time-series|cohort|case-control|hospitali|emergency department|mortality|deaths?", t):
        return "epidemiology"
    return "other"


def country(r):
    a = r["aff"]
    m = re.search(r",\s*([A-Z][A-Za-z .'-]+?)\.?\s*(?:Electronic address.*)?$", a.strip())
    c = (m.group(1).strip() if m else "")
    c = re.sub(r"^(?:USA|United States of America|U\.S\.A)$", "USA", c)
    return c[:40]


def graph_status(pmids):
    dv_f, dv_s, names = Counter(), set(), defaultdict(list)
    for r in csv.DictReader(open(os.path.join(HERE, "dataverse", "system-public-graph-v1-studies.csv"))):
        if r["pubmed_id"] in pmids: dv_s.add(r["pubmed_id"])
    for r in csv.DictReader(open(os.path.join(HERE, "dataverse", "system-public-graph-v1-associations.csv"))):
        if r["pubmed_id"] in pmids:
            dv_f[r["pubmed_id"]] += 1; names[r["pubmed_id"]].append(r["variable_1_name"] + " || " + r["variable_2_name"])
    api_s, api_f = {}, Counter()
    if api_pull.KEY:
        pl = sorted(pmids)
        for i in range(0, len(pl), 50):
            s, b = api_pull.get("/v1/studies", {"filter": "pubmed_id:" + "||".join(pl[i:i + 50]), "limit": 100})
            for st in (b or {}).get("data", b if isinstance(b, list) else []) if s == 200 else []:
                api_s[st.get("study_id") or st.get("system_id")] = str(st.get("pubmed_id"))
        sids = sorted(api_s)
        for i in range(0, len(sids), 25):
            s, b = api_pull.get("/v1/associations", {"filter": "study_id:" + "||".join(sids[i:i + 25]), "limit": 5000})
            for a in (b or {}).get("data", b if isinstance(b, list) else []) if s == 200 else []:
                pk = str(a.get("pubmed_id") or api_s.get(a.get("study_id")))
                api_f[pk] += 1; names[pk].append((a.get("variable_1_name") or "") + " || " + (a.get("variable_2_name") or ""))
    out, drugx = {}, {}
    for p in pmids:
        drugx[p] = any(DRUG.search(n) for n in names.get(p, []))
        if dv_f[p]: out[p] = ("vetted", dv_f[p], api_f.get(p, 0))
        elif api_f.get(p): out[p] = ("api_only", 0, api_f[p])
        elif p in dv_s or p in set(api_s.values()): out[p] = ("record_only", 0, 0)
        else: out[p] = ("absent", 0, 0)
    return out, drugx, bool(api_pull.KEY)


def main():
    seeds = {}
    for line in open(os.path.join(HERE, "recall", "relevant.txt")):
        if line.strip():
            p, *t = line.split(); seeds[p] = "hand-screened recall set"
    for rv, lbl in REVIEWS.items():
        refs = links(rv, "pubmed_pubmed_refs")
        print(f"refs of {rv} ({lbl}): {len(refs)}")
        for p in refs: seeds.setdefault(p, f"cited by review {rv}")
    for c in CITED:
        cit = links(c, "pubmed_pubmed_citedin")
        print(f"papers citing {c}: {len(cit)}")
        for p in cit: seeds.setdefault(p, f"cites {c}")
    for c in CITED: seeds.setdefault(c, "key primary study")
    print("candidates:", len(seeds))
    recs = fetch(sorted(seeds))
    keep = []
    for p, r in recs.items():
        t = r["title"] + " " + r["abstract"]
        hand = seeds.get(p) == "hand-screened recall set"
        if not hand and (not HEAT.search(t) or not DRUG.search(t)): continue
        if NOT_HEAT.search(r["title"]) and not hand: continue
        if p in EXCLUDE: continue
        cls = [n for n, rx in CLASSES if rx.search(r["title"]) or rx.search(r["abstract"])]
        if not cls and not hand: continue
        r["classes"] = cls; r["etype"] = TYPE_FIX.get(p) or evidence_type(r); r["note"] = NOTE.get(p, ""); r["country"] = country(r); r["via"] = seeds[p]
        keep.append(r)
    status, drugx, used_api = graph_status({r["pmid"] for r in keep})
    for r in keep:
        r["graph"], r["dv_findings"], r["api_findings"] = status[r["pmid"]]
        r["drug_extracted"] = drugx[r["pmid"]]
    rows = [{k: (";".join(v) if isinstance(v, list) else v) for k, v in r.items() if k not in ("abstract", "mesh", "aff", "ptypes")} for r in keep]
    rows.sort(key=lambda r: (r["etype"], r["year"]))
    with open(os.path.join(HERE, "probe_results", "literature.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    json.dump({"built": time.strftime("%Y-%m-%d"), "api_checked": used_api, "reviews": REVIEWS, "cited": CITED,
               "studies": [{k: r[k] for k in ("pmid", "title", "year", "journal", "country", "classes", "etype", "graph", "dv_findings", "api_findings", "drug_extracted", "note", "via")} for r in keep]},
              open(os.path.join(HERE, "probe_results", "literature.json"), "w"), indent=1)
    print(f"kept {len(keep)} studies; api checked: {used_api}")
    print("by type:", Counter(r["etype"] for r in keep))
    print("graph status:", Counter(r["graph"] for r in keep))
    prim = [r for r in keep if r["etype"] not in ("review", "other")]
    print("primary studies:", len(prim), "| any finding:", sum(r["graph"] in ("vetted", "api_only") for r in prim), "| a finding naming a drug:", sum(r["drug_extracted"] for r in prim))
    print("graph status, primary studies (not review/other):", Counter(r["graph"] for r in keep if r["etype"] not in ("review", "other")))


if __name__ == "__main__":
    main()
