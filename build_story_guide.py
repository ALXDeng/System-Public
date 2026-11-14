#!/usr/bin/env python3
"""Rebuild grid/heat-med-story-guide.html from its template with refreshed data and the NYC layer.

Reads the current injected block (`const D = {...};`) from the built page and refreshes:
  D.DATA         <- grid/grid_data.json        (22 rows; includes the cold-weather opioid correction)
  D.LENS.rows    <- grid/lenses_data.json rows  (keyed by class, same fields the guide reads)
  D.LENS.scorecard / alignment                  (current)
  D.EXTRA.drugs  <- adds generic names for the classes added on 2026-11-14 so notes can name them
Everything else in D (EXTRA.review, GUIDE, HVI, PUBMED) is kept as is.
Adds `const NYC = {...};` (neighbourhood names, PLACES rates, ZIP outlines) built by build_story_app.nyc_block().

  python3 build_story_guide.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_story_app import nyc_block, read_D  # noqa: E402

G = os.path.join(HERE, "grid")
OUT = os.path.join(G, "heat-med-story-guide.html")
TPL = os.path.join(G, ".heat-med-story-guide.template.html")
NEW_DRUGS = {
    "GLP-1 agonists": ["semaglutide", "liraglutide", "dulaglutide", "tirzepatide", "exenatide"],
    "Parkinson / dopaminergic": ["carbidopa/levodopa", "levodopa", "pramipexole", "ropinirole", "rasagiline"],
    "Cholinesterase inhibitors": ["donepezil", "rivastigmine", "galantamine"],
}
ROW_KEYS = ["pattern", "finding", "research", "guidance_n", "guidance_actions", "guidance", "label"]  # only fields the guide reads


def main():
    html = open(OUT).read()
    D = read_D(html)
    D["DATA"] = json.load(open(os.path.join(G, "grid_data.json")))
    L = json.load(open(os.path.join(G, "lenses_data.json")))
    D["LENS"]["rows"] = {r["class"]: {k: r.get(k) for k in ROW_KEYS} for r in L["rows"]}
    for k in ("scorecard", "patterns", "sources", "coded", "label_source", "not_in_grid", "built"):
        if k in L:
            D["LENS"][k] = L[k]
    D["LENS"]["alignment"] = L["alignment_checks"]
    for c, names in NEW_DRUGS.items():
        D["EXTRA"]["drugs"].setdefault(c, names)
    nyc = nyc_block()
    tpl = open(TPL).read()
    assert tpl.count("/*__DATA__*/") == 1
    data = ("const D = " + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";\nconst NYC = "
            + json.dumps(nyc, separators=(",", ":"), ensure_ascii=False) + ";").replace("</", "<\\/")
    open(OUT, "w").write(tpl.replace("/*__DATA__*/", data))
    print(f"DATA rows {len(D['DATA']['rows'])}, LENS rows {len(D['LENS']['rows'])}, NYC zips {len(nyc['zips'])}, page {os.path.getsize(OUT) // 1024} KB")


if __name__ == "__main__":
    main()
