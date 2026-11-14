"""Spatial autocorrelation of wood volume density on the 300-quadrant grid.

Run from the repo root:  python poster/spatial_stats.py

Input: docs/assets/site.json (site_run_v3). Each quadrant is drawn as a unit square
on the anonymized row/col grid; no coordinates are used. Variable: wood volume per
hectare, (v_full + v_frag) / area_ha.

Weights: queen contiguity, row-standardized. Inference: 999 conditional permutations,
fixed seed. Outputs: poster/figures/spatial_stats.json (values + per-cell Gi* class).
"""
from pathlib import Path
import json

import numpy as np
import geopandas as gpd
from shapely.geometry import box
from libpysal.weights import Queen, fill_diagonal
from esda.moran import Moran
from esda.getisord import G_Local

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261114
PERM = 999

cells = json.loads((ROOT / "docs" / "assets" / "site.json").read_text())["cells"]
gdf = gpd.GeoDataFrame(
    {
        "row": [c["row"] for c in cells],
        "col": [c["col"] for c in cells],
        "dens": [(c["v_full"] + c["v_frag"]) / c["area_ha"] for c in cells],
    },
    geometry=[box(c["col"], -c["row"] - 1, c["col"] + 1, -c["row"]) for c in cells],
)
y = gdf["dens"].to_numpy()

w = Queen.from_dataframe(gdf, use_index=False, silence_warnings=True)
w.transform = "r"

np.random.seed(SEED)
mi = Moran(y, w, permutations=PERM)

# Gi*: binary queen weights with the cell itself included (self-weight 1), then
# row-standardized, as in the standard Getis-Ord Gi* hot spot analysis. Two-sided test.
w_star = fill_diagonal(Queen.from_dataframe(gdf, use_index=False, silence_warnings=True), 1.0)
w_star.transform = "r"
# esda draws Gi* permutations in numba, so np.random.seed does not control them;
# pass seed= with n_jobs=1 for a reproducible run.
# The first call in a process compiles the numba kernel and its seeded draw differs
# from every later call; run it once as a warm-up and discard it.
G_Local(y, w_star, transform="R", permutations=PERM, star=None, alternative="two-sided",
        seed=SEED, n_jobs=1)
gi = G_Local(y, w_star, transform="R", permutations=PERM, star=None, alternative="two-sided",
             seed=SEED, n_jobs=1)

z, p = gi.Zs, gi.p_sim


def classify(zi, pi):
    if pi <= 0.01:
        lvl = 99
    elif pi <= 0.05:
        lvl = 95
    elif pi <= 0.10:
        lvl = 90
    else:
        return "ns"
    return f"{'hot' if zi > 0 else 'cold'}{lvl}"


cls = [classify(zi, pi) for zi, pi in zip(z, p)]
counts = {k: cls.count(k) for k in ["hot99", "hot95", "hot90", "ns", "cold90", "cold95", "cold99"]}

area = np.array([c["area_ha"] for c in cells])
vol = np.array([c["v_full"] + c["v_frag"] for c in cells])
hot = np.array([c.startswith("hot") for c in cls])
cold = np.array([c.startswith("cold") for c in cls])

from esda import fdr
fdr_thr = float(fdr(p, 0.05))
seed_check = []
for s_ in (1, 2, 3):
    g_ = G_Local(y, w_star, transform="R", permutations=PERM, star=None, alternative="two-sided",
                 seed=s_, n_jobs=1)
    seed_check.append({"seed": s_, "hot": int(((g_.p_sim <= 0.10) & (g_.Zs > 0)).sum()),
                       "cold": int(((g_.p_sim <= 0.10) & (g_.Zs < 0)).sum())})

out = {
    "fdr05_threshold": round(fdr_thr, 4),
    "fdr05_hot": int(((p <= fdr_thr) & (z > 0)).sum()),
    "fdr05_cold": int(((p <= fdr_thr) & (z < 0)).sum()),
    "seed_check": seed_check,
    "moran_z_norm": round(float(mi.z_norm), 2),
    "n": int(w.n),
    "islands": list(map(int, w.islands)),
    "mean_neighbors": round(float(w.mean_neighbors), 2),
    "moran_I": round(float(mi.I), 3),
    "moran_EI": round(float(mi.EI), 4),
    "moran_z_sim": round(float(mi.z_sim), 2),
    "moran_p_sim": float(mi.p_sim),
    "gi_counts": counts,
    "hot_cells": int(hot.sum()),
    "hot_area_ha": round(float(area[hot].sum()), 1),
    "hot_area_share": round(float(area[hot].sum() / area.sum()), 3),
    "hot_volume_share": round(float(vol[hot].sum() / vol.sum()), 3),
    "cold_cells": int(cold.sum()),
    "cold_area_share": round(float(area[cold].sum() / area.sum()), 3),
    "cold_volume_share": round(float(vol[cold].sum() / vol.sum()), 3),
    "seed": SEED,
    "permutations": PERM,
    "cells": [{"row": int(r), "col": int(c), "gi_class": k, "gi_z": round(float(zz), 3), "p_sim": float(pp)}
              for r, c, k, zz, pp in zip(gdf["row"], gdf["col"], cls, z, p)],
}
(ROOT / "poster" / "figures" / "spatial_stats.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "cells"}, indent=1))
