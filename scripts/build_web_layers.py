"""Build the quadrant layers and downloads behind the web map.

Reads docs/assets/site.json (site_run_v3) and poster/figures/spatial_stats.json
(written by poster/spatial_stats.py) and writes, under docs/assets/data/:

- quadrants.json     one record per quadrant for the map, plus legend classes
- quadrants.csv      the same attributes as a flat table
- quadrants.geojson  unit squares in grid coordinates (x = column, y = row)

Only grid row and column are written. No coordinate of any kind is read or
carried through. The legend class breaks are also written to the
"Web map classes" section of docs/NUMBERS_spatial.md.

Usage, from the repository root:

    python scripts/build_web_layers.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
SITE = json.loads((REPO / "docs" / "assets" / "site.json").read_text())
STATS = json.loads((REPO / "poster" / "figures" / "spatial_stats.json").read_text())
OUT = REPO / "docs" / "assets" / "data"
QUAD_SIDE_M = 127  # 2,500 px at 0.0508 m

cells = SITE["cells"]
gi = {(c["row"], c["col"]): c for c in STATS["cells"]}

area = np.array([c["area_ha"] for c in cells])
vol = np.array([c["v_full"] + c["v_frag"] for c in cells])
pcs = np.array([c["n_full"] + c["n_frag"] for c in cells])
vha = vol / area
pha = pcs / area

# densest 10 percent of area, same rule as the poster's hero map
order = np.argsort(-vha)
cum_area = np.cumsum(area[order]) / area.sum()
top10 = set(order[: int(np.searchsorted(cum_area, 0.10, side="right")) + 1].tolist())

# rank 1 = densest wood volume per hectare; ties share the better rank
rank = {}
for r, i in enumerate(order):
    rank[i] = r + 1
for i in range(len(cells)):
    same = [j for j in range(len(cells)) if vha[j] == vha[i]]
    rank[i] = min(rank[j] for j in same)


def quantile_breaks(values, k=5):
    """Zero gets its own class; the non-zero values are split into k quantile classes."""
    nz = np.sort(values[values > 0])
    qs = [float(np.quantile(nz, q)) for q in np.linspace(0, 1, k + 1)]
    return [0.0] + [round(q, 1) for q in qs[1:-1]] + [round(float(nz.max()), 1)]


breaks = {
    "vol_ha": quantile_breaks(vha),
    "pieces_ha": quantile_breaks(pha),
    "stem_share": [0, 20, 40, 60, 80, 100],
}

records = []
for i, c in enumerate(cells):
    g = gi[(c["row"], c["col"])]
    v = float(vol[i])
    records.append({
        "id": f"R{c['row']}-C{c['col']}",
        "row": c["row"], "col": c["col"],
        "area_ha": round(c["area_ha"], 3),
        "pieces": int(pcs[i]),
        "full_stems": c["n_full"], "fragments": c["n_frag"],
        "volume_m3": round(v, 1),
        "volume_full_m3": round(c["v_full"], 1), "volume_frag_m3": round(c["v_frag"], 1),
        "vol_ha": round(float(vha[i]), 1),
        "pieces_ha": round(float(pha[i]), 1),
        "stem_share": round(100 * c["v_full"] / v) if v > 0 else None,
        "gi_class": g["gi_class"],
        "gi_z": g["gi_z"],
        "gi_p": round(g["p_sim"], 3),
        "rank": rank[i],
        "densest10": i in top10,
    })

OUT.mkdir(parents=True, exist_ok=True)
summary = {
    "n": len(records),
    "quad_side_m": QUAD_SIDE_M,
    "nrow": max(r["row"] for r in records) + 1,
    "ncol": max(r["col"] for r in records) + 1,
    "breaks": breaks,
    "moran_I": STATS["moran_I"],
    "moran_p_sim": STATS["moran_p_sim"],
    "hot_area_share": STATS["hot_area_share"],
    "hot_volume_share": STATS["hot_volume_share"],
    "permutations": STATS["permutations"],
}
(OUT / "quadrants.json").write_text(json.dumps({"summary": summary, "cells": records}, separators=(",", ":")))

fields = [k for k in records[0]]
with open(OUT / "quadrants.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in records:
        w.writerow(r)

features = []
for r in records:
    x, y = r["col"], r["row"]
    ring = [[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1], [x, y]]
    features.append({"type": "Feature", "properties": r,
                     "geometry": {"type": "Polygon", "coordinates": [ring]}})
(OUT / "quadrants.geojson").write_text(json.dumps({
    "type": "FeatureCollection",
    "name": "fallen_wood_quadrants_grid",
    "crs_note": "Grid coordinates only: x = column index, y = row index (row 0 at the north). One unit = one 127 m quadrant. Not georeferenced.",
    "features": features}, separators=(",", ":")))

# keep the legend classes on record next to the other spatial numbers
md = REPO / "docs" / "NUMBERS_spatial.md"
text = md.read_text(encoding="utf-8")
section = "## Web map classes\n"
block = (section + "\nWritten by `scripts/build_web_layers.py` from `docs/assets/site.json`.\n"
         "Quadrants with no wood form their own class; the rest are split into five\n"
         "quantile classes (equal numbers of quadrants). Stem share uses fixed\n"
         "20-point steps.\n\n| Layer | Class breaks |\n|---|---|\n"
         f"| Wood volume (m3/ha) | {', '.join(f'{b:g}' for b in breaks['vol_ha'])} |\n"
         f"| Piece density (pieces/ha) | {', '.join(f'{b:g}' for b in breaks['pieces_ha'])} |\n"
         f"| Full stem share of volume (%) | {', '.join(f'{b:g}' for b in breaks['stem_share'])} |\n")
text = re.sub(r"## Web map classes\n.*?(?=\n## |\Z)", "", text, flags=re.S).rstrip() + "\n\n" + block
md.write_text(text, encoding="utf-8")

print(json.dumps(summary, indent=1))
print("top10:", len(top10), "zero-volume quadrants:", int((vol == 0).sum()))
