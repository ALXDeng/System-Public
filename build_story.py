"""Build grid/heat-med-story.html: the editorial (NYT/Reuters-style) evidence map.

Reads the same data the cards page uses (DATA + EXTRA embedded in grid/heat-med-cards.html),
plus grid/lenses_data.json (guidance + FDA label lens) and guidance.json, slims it, and injects
it into grid/.heat-med-story.template.html at /*__DATA__*/.

    python3 build_story.py                 # plain-language version (default)
    python3 build_story.py specialist      # the earlier, specialist report
    python3 build_story.py public          # plain-language report
    python3 build_story.py app             # interactive clinical guidance app (v1)
    python3 build_story.py guide           # map-first redesign with patient lens
"""
import json, re, pathlib, sys

ROOT = pathlib.Path(__file__).parent
G = ROOT / "grid"

src = (G / "heat-med-cards.html").read_text().split("\n")
def grab(prefix):
    line = next(l for l in src if l.startswith(prefix))
    obj, _ = json.JSONDecoder().raw_decode(re.sub(r"^const \w+\s*=\s*", "", line))
    return obj

DATA = grab("const DATA")
EXTRA = grab("const EXTRA")
LENS = json.loads((G / "lenses_data.json").read_text())
GUIDE = json.loads((ROOT / "guidance.json").read_text())

# Slim the bridge examples: keep 2 drug and 2 heat examples per mechanism.
for r in DATA["rows"]:
    for c in r["cells"].values():
        for m in c.get("mechanisms") or []:
            m["drug_examples"] = (m.get("drug_examples") or [])[:2]
            m["heat_examples"] = (m.get("heat_examples") or [])[:2]
            for ex in m["drug_examples"] + m["heat_examples"]:
                ex.pop("pop", None)

lens_rows = {}
for r in LENS["rows"]:
    lens_rows[r["class"]] = {
        "pattern": r["pattern"],
        "finding": r["finding"],
        "research": {k: r["research"].get(k) for k in ("tier", "signal", "label", "n_direct_studies")},
        "guidance_n": r.get("guidance_n"),
        "guidance_actions": r.get("guidance_actions"),
        "guidance": r["guidance"],
        "label": [{k: x.get(k) for k in ("generic", "brand", "status", "n", "snippet", "storage", "dailymed")} for x in r["label"]],
    }

out = {
    "DATA": DATA,
    "EXTRA": EXTRA,
    "LENS": {
        "rows": lens_rows,
        "patterns": LENS["patterns"],
        "not_in_grid": LENS["not_in_grid"],
        "label_source": LENS["label_source"],
        "built": LENS["built"],
        "sources": LENS.get("sources", []),
        "scorecard": LENS.get("scorecard", []),
        "alignment": LENS.get("alignment_checks", []),
        "coded": LENS.get("coded", ["cdc", "nyc"]),
    },
    "GUIDE": {"sources": GUIDE["sources"], "general_actions": GUIDE["general_actions"]},
}

# NYC Heat Vulnerability Index by ZIP (ZCTA), 1-5 (probe_results/nyc_hvi_zcta.csv, DOHMH via NYC Open Data)
hp = ROOT / "probe_results" / "nyc_hvi_zcta.csv"
if hp.exists():
    import csv
    out["HVI"] = {r["zcta20"]: int(r["hvi"]) for r in csv.DictReader(hp.open())}

# PubMed counts for the wearables / storage context (probe_results/pubmed_wearable_counts.json).
wp = ROOT / "probe_results" / "pubmed_wearable_counts.json"
if wp.exists():
    W = json.loads(wp.read_text())
    out["PUBMED"] = {k.split(" ")[0]: {"label": k.split(" ", 1)[1], "count": v.get("count"), "ids": (v.get("ids") or [])[:3]}
                     for k, v in W.items() if isinstance(v, dict) and v.get("count") is not None}

VARIANT = "-" + sys.argv[1] if len(sys.argv) > 1 else ""
tpl = (G / f".heat-med-story{VARIANT}.template.html").read_text()
blob = "const D = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"
html = tpl.replace("/*__DATA__*/", blob)
(G / f"heat-med-story{VARIANT}.html").write_text(html)
print(f"wrote grid/heat-med-story{VARIANT}.html ({len(html)/1024:.0f} KB)")
