import csv, re, sys, collections
csv.field_size_limit(sys.maxsize)
DV = "dataverse/"
SIG = re.compile(r"wearable|smart ?watch|wrist[- ]worn|accelerometer|actigraph|photoplethysm|\bPPG\b|skin temperature|core (body )?temperature|rectal temperature|gastrointestinal temperature|physiological strain|thermal strain|heat strain|\bheart rate\b|heart rate variability|sweat rate|thermal sensation", re.I)
DEV = re.compile(r"wearable|smart ?watch|wrist[- ]worn|photoplethysm|\bPPG\b|sensor|device|estimated core", re.I)
HEAT = re.compile(r"\bheat\b|hot\b|thermal|warm (season|environment)|high (ambient )?temperature|heatwave|heat wave|hyperthermi|climatic chamber|°C environment", re.I)
DRUG = re.compile(r"beta[- ]?block|propranolol|metoprolol|atenolol|bisoprolol|anticholinerg|atropine|glycopyrr|oxybutynin|scopolamine|antipsychot|antidepress|ssri|diuretic|furosemide|amphetamine|methylphenidate|lithium|medication|drug", re.I)
sig = {}
for r in csv.DictReader(open(DV+"system-public-graph-v1-variables.csv")):
    if SIG.search(r["name"]): sig[r["system_id"]] = r["name"]
print("signal variables", len(sig))
rows = []
for r in csv.DictReader(open(DV+"system-public-graph-v1-associations.csv")):
    a, b = r["variable_1_id"], r["variable_2_id"]
    if a in sig or b in sig:
        rows.append(r)
print("associations touching signal vars", len(rows))
cat = collections.defaultdict(set); ex = collections.defaultdict(list)
for r in rows:
    t = r["variable_1_name"] + " || " + r["variable_2_name"]
    h, d, dev = bool(HEAT.search(t)), bool(DRUG.search(t)), bool(DEV.search(t))
    k = ("heat+drug" if h and d else "heat" if h else "drug" if d else "device" if dev else "other")
    if dev and k in ("heat","heat+drug"): k += "+device"
    cat[k].add(r["pubmed_id"])
    if len(ex[k]) < 12: ex[k].append((r["pubmed_id"], t[:170], r["statistic_type"], r["statistic_value"]))
for k in sorted(cat, key=lambda k: -len(cat[k])):
    print(f"\n## {k}: {len(cat[k])} papers")
    for e in ex[k]: print("  ", e)
