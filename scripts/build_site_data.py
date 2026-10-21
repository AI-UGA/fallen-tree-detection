"""Build the anonymized data file behind the project page.

Reads the classified site table and the quadrant record, and writes
docs/assets/site.json with:

- site totals (area, counts, volumes, densities),
- one record per 2,500 px quadrant on a neutral grid (tile row and column,
  quadrant row and column), with counts and volumes by class,
- a length histogram of counted pieces by class.

Nothing georeferenced is written. Tiles are named by grid position only
(``R-C``), never by their source filename, and no centroid, easting or
northing value is read or carried through.

Usage, from the repository root:

    python scripts/build_site_data.py                 # find the data root on Drive
    python scripts/build_site_data.py --site "<path to site_run_v3>"
    python scripts/build_site_data.py --out /content/site.json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

FULL, FRAG = "Full stem", "Fragment"
TILE_RE = re.compile(r"-(\d+)-(\d+)$")
QUAD_RE = re.compile(r"^q(\d)(\d)$")
LENGTH_BIN_M = 1.0
LENGTH_MAX_M = 30.0

# Only these columns are read. Coordinates never enter memory.
DET_COLS = ["source_tile", "quadrant", "klass", "volume_m3", "length_m", "width_mean_m"]
QUAD_COLS = ["source_tile", "quadrant", "area_ha"]


def locate_site(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    from cwd.paths import require_root  # searches by content, never by hardcoded path

    return Path(require_root()) / "04. Results" / "site_run_v3"


def grid_position(source_tile: str, quadrant: str) -> tuple[int, int, int, int]:
    t = TILE_RE.search(str(source_tile))
    q = QUAD_RE.match(str(quadrant))
    if not t or not q:
        raise ValueError(f"unexpected tile or quadrant name: {source_tile!r} {quadrant!r}")
    return int(t.group(1)), int(t.group(2)), int(q.group(1)), int(q.group(2))


def r(x: float, nd: int = 3) -> float:
    return float(round(float(x), nd))


EXCLUSION_KEYS = {
    "Excluded, below length threshold": "too_short",
    "Excluded, below width threshold": "too_narrow",
    "Excluded, insufficient elongation": "not_elongated",
    "Excluded, tile boundary contact": "tile_edge",
}


def class_stats(frame: pd.DataFrame) -> dict:
    """Per-piece summary for one class. Widths are measured mask widths."""
    if frame.empty:
        return {}
    return {
        "median_length_m": r(frame.length_m.median(), 2),
        "p90_length_m": r(frame.length_m.quantile(0.9), 2),
        "max_length_m": r(frame.length_m.max(), 2),
        "median_width_m": r(frame.width_mean_m.median(), 3),
        "median_volume_m3": r(frame.volume_m3.median(), 3),
        "mean_volume_m3": r(frame.volume_m3.mean(), 3),
    }


def build(site: Path) -> dict:
    det = pd.read_csv(site / "cwd_classified_site.csv", usecols=DET_COLS)
    quad_files = sorted(glob.glob(str(site / "per_tile" / "*.quads.csv")))
    if not quad_files:
        raise FileNotFoundError(f"no quadrant record under {site / 'per_tile'}")
    quads = pd.concat([pd.read_csv(f, usecols=QUAD_COLS) for f in quad_files], ignore_index=True)

    inv = det[det.klass.isin([FULL, FRAG])]
    excl = det[~det.klass.isin([FULL, FRAG])]
    area = float(quads.area_ha.sum())

    agg = (
        det.assign(
            n_full=(det.klass == FULL).astype(int),
            n_frag=(det.klass == FRAG).astype(int),
            v_full=det.volume_m3.where(det.klass == FULL, 0.0),
            v_frag=det.volume_m3.where(det.klass == FRAG, 0.0),
        )
        .groupby(["source_tile", "quadrant"])[["n_full", "n_frag", "v_full", "v_frag"]]
        .sum()
    )
    q = quads.merge(agg, left_on=["source_tile", "quadrant"], right_index=True, how="left").fillna(0)

    lost = len(inv) - int(q.n_full.sum() + q.n_frag.sum())
    if lost:
        raise ValueError(f"{lost} counted pieces fall outside the quadrant record")

    cells = []
    for row in q.itertuples(index=False):
        tr, tc, qr, qc = grid_position(row.source_tile, row.quadrant)
        cells.append({
            "tile": f"{tr}-{tc}",
            "q": f"{qr}{qc}",
            "row": tr * 2 + qr,
            "col": tc * 2 + qc,
            "area_ha": r(row.area_ha, 4),
            "n_full": int(row.n_full),
            "n_frag": int(row.n_frag),
            "v_full": r(row.v_full, 2),
            "v_frag": r(row.v_frag, 2),
        })
    cells.sort(key=lambda c: (c["row"], c["col"]))

    edges = np.arange(0, LENGTH_MAX_M + LENGTH_BIN_M, LENGTH_BIN_M)

    def hist(frame: pd.DataFrame) -> list[int]:
        clipped = frame.length_m.clip(upper=LENGTH_MAX_M - 1e-9)
        return np.histogram(clipped, bins=edges)[0].astype(int).tolist()

    from cwd.classify import load_thresholds  # single source of truth for the rules

    th = load_thresholds()

    out = {
        "summary": {
            "imaged_ha": r(area, 2),
            "quadrants": len(cells),
            "detections": int(len(det)),
            "pieces": int(len(inv)),
            "volume_m3": r(inv.volume_m3.sum(), 1),
            "density_m3_ha": r(inv.volume_m3.sum() / area, 2),
            "pieces_per_ha": r(len(inv) / area, 1),
            "full": {"n": int((inv.klass == FULL).sum()), "v": r(inv.volume_m3[inv.klass == FULL].sum(), 1),
                     **class_stats(inv[inv.klass == FULL])},
            "frag": {"n": int((inv.klass == FRAG).sum()), "v": r(inv.volume_m3[inv.klass == FRAG].sum(), 1),
                     **class_stats(inv[inv.klass == FRAG])},
            "excluded": {"n": int(len(excl)), "v": r(excl.volume_m3.sum(), 1),
                         "by_reason": {EXCLUSION_KEYS.get(k, "other"): int(v)
                                       for k, v in excl.klass.value_counts().items()}},
            "gsd_m": th["gsd_m_per_px"],
            "full_stem_min_length_m": th["full_stem"]["min_length_m"],
        },
        "length_hist": {
            "bin_m": LENGTH_BIN_M,
            "max_m": LENGTH_MAX_M,
            "full": hist(inv[inv.klass == FULL]),
            "frag": hist(inv[inv.klass == FRAG]),
        },
        "cells": cells,
    }
    return out


def check_anonymous(payload: dict) -> None:
    """Fail if anything other than neutral grid labels and numbers got through."""
    for c in payload["cells"]:
        if not re.fullmatch(r"\d+-\d+", c["tile"]) or not re.fullmatch(r"[01]{2}", c["q"]):
            raise ValueError(f"non-neutral tile label: {c['tile']!r} {c['q']!r}")
    text = json.dumps(payload).lower()
    for word in ("easting", "northing", "centroid", "ortho", "_20"):
        if word in text:
            raise ValueError(f"site data contains a forbidden term: {word}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", help="folder holding cwd_classified_site.csv and per_tile/")
    ap.add_argument("--out", default=str(REPO / "docs" / "assets" / "site.json"))
    args = ap.parse_args()

    site = locate_site(args.site)
    payload = build(site)
    check_anonymous(payload)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, separators=(",", ":")) + "\n")

    s = payload["summary"]
    print(f"site      {site}")
    print(f"area      {s['imaged_ha']:,.2f} ha in {s['quadrants']} quadrants")
    print(f"pieces    {s['pieces']:,}  ({s['full']['n']:,} full stems, {s['frag']['n']:,} fragments)")
    print(f"volume    {s['volume_m3']:,.1f} m3, {s['density_m3_ha']:.2f} m3/ha")
    print(f"written   {out}  ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
