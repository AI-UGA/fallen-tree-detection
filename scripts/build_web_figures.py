"""Build the web images under docs/assets/img/ from the v3 paper figures.

Run from the repository root:  python scripts/build_web_figures.py

Sources are the coordinate-free figures in figures/ (never the *_coords*
files, which are not read here). Outputs are WebP with no EXIF, XMP or ICC
metadata, at most 1600 px wide:

- fig_site.webp     figure1 panel (a) only, the tile layout. Panel (b), the
                    orthomosaic, is cropped away and never published.
- fig_sizes.webp    figure4, size distributions
- fig_volume.webp   figure8, volume histogram
- fig_gallery.webp  figure5, example gallery
- fig_density.png   per-quadrant density, drawn from docs/assets/site.json
                    (300 quadrants of 127 m), replacing the per-tile version
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Rectangle
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "figures"
OUT = REPO / "docs" / "assets" / "img"
MAXW = 1600


def to_webp(img: Image.Image, name: str, quality: int = 82) -> None:
    img = img.convert("RGB")
    if img.width > MAXW:
        img = img.resize((MAXW, round(img.height * MAXW / img.width)), Image.LANCZOS)
    clean = Image.new("RGB", img.size)
    clean.paste(img)  # fresh image: no EXIF, XMP or ICC carried over
    clean.save(OUT / name, "WEBP", quality=quality, method=6)


def site_panel_a() -> None:
    im = Image.open(SRC / "figure1_site_nocoords.png")
    arr = np.asarray(im.convert("RGB"))
    white = (arr > 245).all(axis=2).all(axis=0)
    w = im.width
    gutter = next(x for x in range(int(w * 0.40), int(w * 0.60)) if white[x])
    # drop the "(a)" title line; the page caption carries that text
    to_webp(im.crop((0, 200, gutter, im.height)), "fig_site.webp")


def density_quadrants() -> None:
    site = json.loads((REPO / "docs" / "assets" / "site.json").read_text())
    cells = site["cells"]
    rows = np.array([c["row"] for c in cells])
    cols = np.array([c["col"] for c in cells])
    area = np.array([c["area_ha"] for c in cells])
    pha = np.array([c["n_full"] + c["n_frag"] for c in cells]) / area
    vha = np.array([c["v_full"] + c["v_frag"] for c in cells]) / area
    nrow, ncol = rows.max() + 1, cols.max() + 1
    plt.rcParams.update({"font.size": 11})
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), dpi=200)
    for ax, val, label in [(axes[0], pha, "pieces per hectare"), (axes[1], vha, "wood volume (m³/ha)")]:
        nz = np.sort(val[val > 0])
        b = [0] + [float(np.quantile(nz, q)) for q in np.linspace(0, 1, 6)[1:-1]] + [float(nz.max())]
        cmap = ListedColormap(plt.get_cmap("YlGn")(np.linspace(0.08, 1.0, len(b) - 1)))
        norm = BoundaryNorm(b, cmap.N)
        for i in range(len(cells)):
            ax.add_patch(Rectangle((cols[i], nrow - 1 - rows[i]), 1, 1,
                                   facecolor=cmap(norm(val[i])), edgecolor="white", lw=0.6))
        ax.set_xlim(0, ncol)
        ax.set_ylim(0, nrow)
        ax.set_aspect("equal")
        ax.axis("off")
        q = 500 / 127
        ax.plot([0.2, 0.2 + q], [0.5, 0.5], color="black", lw=3, solid_capstyle="butt")
        ax.text(0.2 + q / 2, 0.9, "500 m", ha="center", fontsize=10)
        ax.annotate("N", xy=(1.0, nrow - 1.0), xytext=(1.0, nrow - 3.6), ha="center",
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5), fontsize=11)
        sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
        cb = fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.02, ticks=b)
        cb.ax.set_yticklabels([f"{t:.0f}" for t in b])
        cb.outline.set_visible(False)
        cb.set_label(label + ", quantile classes")
    fig.tight_layout()
    fig.savefig(OUT / "fig_density.png", facecolor="white")
    plt.close(fig)
    Image.open(OUT / "fig_density.png").convert("RGB").save(OUT / "fig_density.png", optimize=True)


if __name__ == "__main__":
    site_panel_a()
    to_webp(Image.open(SRC / "figure4_size_distributions.png"), "fig_sizes.webp")
    to_webp(Image.open(SRC / "figure8_volume.png"), "fig_volume.webp")
    to_webp(Image.open(SRC / "figure5_gallery.png"), "fig_gallery.webp", quality=86)
    density_quadrants()
    for p in sorted(OUT.glob("fig_*")):
        im = Image.open(p)
        print(f"{p.name:20s} {im.size} {p.stat().st_size/1e3:.0f} kB exif={len(im.getexif())}")
