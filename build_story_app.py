#!/usr/bin/env python3
"""Rebuild grid/heat-med-story-app.html from its template, adding the NYC neighbourhood layer.

The existing injected data block (`const D = {...};`) is read back from the current built page and kept as is.
A second block, `const NYC = {...};`, is added with one entry per NYC ZIP area:
  heat vulnerability (NYC DOHMH HVI, 1-5), neighbourhood + borough (EHDP UHF42 names),
  CDC PLACES 2023 adult prevalence (high BP x BP medication, diabetes, depression, coronary heart disease),
  and an SVG outline (MODZCTA TopoJSON from nychealth/EHDP-data, projected here; no map library needed).

  python3 build_story_app.py
"""
import csv
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
G, PR = os.path.join(HERE, "grid"), os.path.join(HERE, "probe_results")
OUT = os.path.join(G, "heat-med-story-app.html")
TPL = os.path.join(G, ".heat-med-story-app.template.html")
W = 600  # SVG viewBox width


def read_D(html):
    i = html.index("const D = ")
    obj, end = json.JSONDecoder().raw_decode(html, i + len("const D = "))
    return obj


def simplify(pts, tol):
    """Ramer-Douglas-Peucker on a closed ring (pixel units)."""
    if len(pts) < 5:
        return pts
    def rdp(p):
        if len(p) < 3:
            return p
        (x1, y1), (x2, y2) = p[0], p[-1]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1e-9
        i, dm = 0, -1
        for j in range(1, len(p) - 1):
            d = abs(dy * p[j][0] - dx * p[j][1] + x2 * y1 - y2 * x1) / L
            if d > dm:
                i, dm = j, d
        return rdp(p[:i + 1])[:-1] + rdp(p[i:]) if dm > tol else [p[0], p[-1]]
    m = len(pts) // 2
    return rdp(pts[:m + 1])[:-1] + rdp(pts[m:])


def topo_paths():
    t = json.load(open(os.path.join(PR, "MODZCTA.topo.json")))
    sx, sy = t["transform"]["scale"]; tx, ty = t["transform"]["translate"]
    arcs = []
    for a in t["arcs"]:
        x = y = 0; pts = []
        for dx, dy in a:
            x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    def ring(idx):
        pts = []
        for i in idx:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts += seg if not pts else seg[1:]
        return pts
    geoms = t["objects"]["collection"]["geometries"]
    allp = [p for a in arcs for p in a]
    lon0, lon1 = min(p[0] for p in allp), max(p[0] for p in allp)
    lat0, lat1 = min(p[1] for p in allp), max(p[1] for p in allp)
    kx = math.cos(math.radians((lat0 + lat1) / 2))
    k = W / ((lon1 - lon0) * kx)
    H = round((lat1 - lat0) * k)
    proj = lambda p: (round((p[0] - lon0) * kx * k), round((lat1 - p[1]) * k))  # whole pixels are enough at 600 px
    out = {}
    for g in geoms:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        d, best = [], (0, None)
        for poly in polys:
            for ri, r in enumerate(poly):
                pts, last = [], None
                for p in map(proj, ring(r)):
                    if p != last: pts.append(p); last = p
                if ri == 0 and len(pts) > 2:  # outer ring: keep the largest one's centroid for pins
                    a = cx = cy = 0
                    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
                        f = x1 * y2 - x2 * y1; a += f; cx += (x1 + x2) * f; cy += (y1 + y2) * f
                    if abs(a) > best[0] and a:
                        best = (abs(a), [round(cx / (3 * a)), round(cy / (3 * a))])
                pts = simplify(pts, 0.6)
                if len(pts) > 2:
                    d.append("M" + "L".join(f"{x},{y}" for x, y in pts) + "Z")
        out[str(g["properties"]["GEOCODE"])] = {"d": "".join(d), "c": best[1],
                                                "zips": [z.strip() for z in str(g["properties"]["GEONAME"]).split(",")]}
    return out, H


def nyc_block():
    lk = {r["zcta"]: r for r in csv.DictReader(open(os.path.join(PR, "nyc_zcta_lookup.csv")))}
    places = json.load(open(os.path.join(PR, "places_nyc_zcta.json")))["rows"]
    pv = {}
    for r in places:
        z = pv.setdefault(r["locationname"], {"adults": int(float(r.get("totalpop18plus") or 0))})
        z[r["measureid"]] = float(r["data_value"])
    paths, H = topo_paths()
    zips = {}
    for z, r in lk.items():
        if not r["hvi"]:
            continue
        p = pv.get(z, {})
        e = {"h": int(r["hvi"]), "n": r["neighbourhood"], "b": r["borough"], "o": r["modzcta_outline"]}
        if p:
            e.update({"a": p["adults"], "bp": round(p.get("BPHIGH", 0) * p.get("BPMED", 0) / 100, 1),
                      "dm": p.get("DIABETES"), "dep": p.get("DEPRESSION"), "chd": p.get("CHD")})
        zips[z] = e
    # 11249 sits inside outline 11211 and has no neighbourhood row: borrow 11211's
    if "11249" in zips and not zips["11249"]["n"] and "11211" in zips:
        zips["11249"]["n"], zips["11249"]["b"] = zips["11211"]["n"], zips["11211"]["b"]
    med = {}
    for m in ("bp", "dm", "dep"):
        v = sorted(e[m] for e in zips.values() if e.get(m) is not None)
        med[m] = v[len(v) // 2]
    return {"w": W, "h": H, "zips": zips, "outlines": {k: v["d"] for k, v in paths.items() if k != "99999"},
            "cent": {k: v["c"] for k, v in paths.items() if k != "99999" and v["c"]}, "median": med,
            "sources": {"hvi": "NYC DOHMH Heat Vulnerability Index (NYC Open Data 4mhf-duep, updated Sept 2024)",
                        "places": "CDC PLACES 2023 model-based estimates, adults, by ZIP area (ZCTA)",
                        "geo": "MODZCTA outlines and UHF42 neighbourhood names, NYC Health EHDP-data repository"}}


def main():
    html = open(OUT).read()
    D = read_D(html)
    nyc = nyc_block()
    tpl = open(TPL).read()
    data = ("const D = " + json.dumps(D, separators=(",", ":"), ensure_ascii=False) + ";\nconst NYC = "
            + json.dumps(nyc, separators=(",", ":"), ensure_ascii=False) + ";").replace("</", "<\\/")
    assert tpl.count("/*__DATA__*/") == 1
    open(OUT, "w").write(tpl.replace("/*__DATA__*/", data))
    print(f"zips {len(nyc['zips'])}, outlines {len(nyc['outlines'])}, svg {nyc['w']}x{nyc['h']}, medians {nyc['median']}, "
          f"NYC block {len(json.dumps(nyc)) // 1024} KB, page {os.path.getsize(OUT) // 1024} KB")


if __name__ == "__main__":
    main()
