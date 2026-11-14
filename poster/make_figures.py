"""Build every raster asset for the GIS Day poster at print size.

Run from the repo root:  python poster/make_figures.py

All numbers come from docs/assets/site.json (site_run_v3), which matches
docs/NUMBERS.md. Charts are drawn at their final printed size in inches at
300 dpi, so 1 pt in matplotlib is 1 pt on the printed sheet.
"""
from pathlib import Path
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Rectangle, FancyArrow
from PIL import Image, ImageDraw
import segno

ROOT = Path(__file__).resolve().parents[1]
POSTER = ROOT / "poster"
FIG = POSTER / "figures"
IMG = POSTER / "assets" / "img"
LOGOS = POSTER / "assets" / "logos"
FONTS = POSTER / "assets" / "fonts"
SRC_IMG = ROOT / "docs" / "assets" / "img"
SITE = json.loads((ROOT / "docs" / "assets" / "site.json").read_text())
DPI = 300

RED, BLACK, STEGEMAN, CREAMERY = "#BA0C2F", "#000000", "#9EA2A2", "#D6D2C4"
INK, MUTED = "#1a1a1a", "#4a4a4a"
FULL, FRAG = "#1d9e75", "#ef9f27"

for f in FONTS.glob("*.ttf"):
    font_manager.fontManager.addfont(str(f))
plt.rcParams.update({
    "font.family": "Merriweather Sans",
    "font.size": 28,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "svg.fonttype": "none",
})

for d in (FIG, IMG, LOGOS):
    d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- cells
cells = SITE["cells"]
area = np.array([c["area_ha"] for c in cells])
vol = np.array([c["v_full"] + c["v_frag"] for c in cells])
rows = np.array([c["row"] for c in cells])
cols = np.array([c["col"] for c in cells])
dens = vol / area

order = np.argsort(-dens)
cum_area = np.r_[0, np.cumsum(area[order])] / area.sum()
cum_vol = np.r_[0, np.cumsum(vol[order])] / vol.sum()
share_top10 = float(np.interp(0.10, cum_area, cum_vol))
area_half = float(np.interp(0.50, cum_vol, cum_area))
top10 = set(order[: int(np.searchsorted(cum_area[1:], 0.10, side="right")) + 1])
print(f"densest 10% of area holds {share_top10:.1%} of wood")
print(f"half the wood sits on {area_half:.1%} of area")
print(f"top-10% quadrants outlined: {len(top10)}")


# ---------------------------------------------------------------- hero map
def density_map(w_in=17.8):
    """Figure is cropped to the grid's data extent; keys sit in the grid's empty corners."""
    bounds = [0, 10, 20, 40, 60, 90, 130, 280]
    cmap = ListedColormap(plt.get_cmap("YlGn")(np.linspace(0.14, 1.0, len(bounds) - 1)))
    norm = BoundaryNorm(bounds, cmap.N)
    nrow, ncol = rows.max() + 1, cols.max() + 1
    h_in = w_in * nrow / ncol

    fig = plt.figure(figsize=(w_in, h_in), dpi=DPI)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    for i in range(len(cells)):
        x, y = cols[i], nrow - 1 - rows[i]
        ax.add_patch(Rectangle((x, y), 1, 1, facecolor=cmap(norm(dens[i])),
                               edgecolor="white", linewidth=2.2))
    for i in top10:  # densest 10 percent of area
        x, y = cols[i], nrow - 1 - rows[i]
        ax.add_patch(Rectangle((x + 0.08, y + 0.08), 0.84, 0.84, fill=False,
                               edgecolor=RED, linewidth=7, zorder=5))
    ax.set_xlim(0, ncol)
    ax.set_ylim(0, nrow)
    ax.axis("off")

    # scale bar, bottom-left gap: 500 m at 127 m per quadrant
    q = 500 / 127.0
    x0, y0 = 0.08, 0.35
    ax.add_patch(Rectangle((x0, y0), q / 2, 0.22, facecolor=INK, edgecolor=INK, lw=1.5))
    ax.add_patch(Rectangle((x0 + q / 2, y0), q / 2, 0.22, facecolor="white", edgecolor=INK, lw=1.5))
    ax.text(x0, y0 + 0.4, "0", ha="left", va="bottom", fontsize=28)
    ax.text(x0 + q, y0 + 0.4, "500 m", ha="right", va="bottom", fontsize=28)

    # north arrow, top-left gap
    ax.add_patch(FancyArrow(1.2, nrow - 4.2, 0, 1.9, width=0.18, head_width=0.75,
                            head_length=0.85, color=INK, length_includes_head=True))
    ax.text(1.2, nrow - 2.1, "N", ha="center", va="bottom", fontsize=44,
            fontfamily="Oswald", fontweight=500)

    # outline key, bottom-right gap
    lx, ly = 12.4, 0.3
    ax.add_patch(Rectangle((lx, ly), 0.88, 0.88, fill=False, edgecolor=RED, lw=7))
    ax.text(lx + 1.2, ly + 0.44, "Densest 10% of area", va="center", fontsize=28)

    # stepped colorbar inside the top-right gap, next to the grid
    cx0, cx1, cy0, cy1 = 18.4, 19.0, 10.9, 18.0
    cax = fig.add_axes([cx0 / ncol, cy0 / nrow, (cx1 - cx0) / ncol, (cy1 - cy0) / nrow])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax,
                      orientation="vertical", spacing="uniform")
    cb.set_ticks(bounds[:-1])
    cb.ax.set_yticklabels([str(b) for b in bounds[:-1]])
    cb.ax.tick_params(labelsize=28, length=8, width=1.5)
    cax.yaxis.set_ticks_position("right")
    cb.outline.set_visible(False)
    cax.text(0.5, 1.015, "130+", transform=cax.transAxes, ha="center", va="bottom", fontsize=28)
    cax.text(0.5, 1.085, "m³/ha", transform=cax.transAxes, ha="center", va="bottom",
             fontsize=32, fontweight=700)
    pos = np.interp(30.08, bounds, np.linspace(0, 1, len(bounds)))
    cax.annotate("mean\n30.1", xy=(1.0, pos), xycoords="axes fraction",
                 xytext=(3.9, pos), textcoords="axes fraction", ha="center", va="center",
                 fontsize=26, linespacing=1.1,
                 arrowprops=dict(arrowstyle="-|>", color=INK, lw=2, mutation_scale=30))
    fig.savefig(FIG / "density_map.png", dpi=DPI, facecolor="white")
    plt.close(fig)



# ---------------------------------------------------------------- shared map helpers
YLGN_BOUNDS = [0, 10, 20, 40, 60, 90, 130, 280]
YLGN = ListedColormap(plt.get_cmap("YlGn")(np.linspace(0.14, 1.0, len(YLGN_BOUNDS) - 1)))
YLGN_NORM = BoundaryNorm(YLGN_BOUNDS, YLGN.N)
NROW, NCOL = rows.max() + 1, cols.max() + 1


def _grid_axes(w_in):
    h_in = w_in * NROW / NCOL
    fig = plt.figure(figsize=(w_in, h_in), dpi=DPI)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0, NCOL)
    ax.set_ylim(0, NROW)
    ax.axis("off")
    return fig, ax


def _north_and_scale(ax, fs=28):
    q = 500 / 127.0
    x0, y0 = 0.08, 0.35
    ax.add_patch(Rectangle((x0, y0), q / 2, 0.22, facecolor=INK, edgecolor=INK, lw=1.5))
    ax.add_patch(Rectangle((x0 + q / 2, y0), q / 2, 0.22, facecolor="white", edgecolor=INK, lw=1.5))
    ax.text(x0, y0 + 0.4, "0", ha="left", va="bottom", fontsize=fs)
    ax.text(x0 + q, y0 + 0.4, "500 m", ha="right", va="bottom", fontsize=fs)
    ax.add_patch(FancyArrow(1.2, NROW - 4.2, 0, 1.9, width=0.18, head_width=0.75,
                            head_length=0.85, color=INK, length_includes_head=True))
    ax.text(1.2, NROW - 2.1, "N", ha="center", va="bottom", fontsize=fs + 12,
            fontfamily="Oswald", fontweight=500)


# ---------------------------------------------------------------- hotspot map
GI_COLORS = {"hot99": "#BA0C2F", "hot95": "#E06A80", "hot90": "#F4B8C3", "ns": "#EEECE6",
             "cold90": "#C6DBEF", "cold95": "#6BAED6", "cold99": "#2171B5"}


def hotspot_map(w_in=9.0):
    st = json.loads((FIG / "spatial_stats.json").read_text())
    cls = {(c["row"], c["col"]): c["gi_class"] for c in st["cells"]}
    fig, ax = _grid_axes(w_in)
    for (r, c), k in cls.items():
        ax.add_patch(Rectangle((c, NROW - 1 - r), 1, 1, facecolor=GI_COLORS[k],
                               edgecolor="white", linewidth=1.6))
    _north_and_scale(ax, fs=26)
    fig.savefig(FIG / "hotspot_map.png", dpi=DPI, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- zonal statistics tile
def zonal_tile(size_in=4.4):
    """A real 5 x 5 block of quadrants from the hero map, as the step 4 picture."""
    r0, c0, n = 13, 3, 5
    fig = plt.figure(figsize=(size_in, size_in), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    for i in range(len(cells)):
        r, c = rows[i], cols[i]
        if r0 <= r < r0 + n and c0 <= c < c0 + n:
            ax.add_patch(Rectangle((c - c0, r0 + n - 1 - r), 1, 1, facecolor=YLGN(YLGN_NORM(dens[i])),
                                   edgecolor="white", linewidth=5))
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.axis("off")
    fig.savefig(IMG / "step4_zonal.png", dpi=DPI, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- locator map
def locator(w_in=5.0):
    import geopandas as gpd
    geo = POSTER / "geo_src"
    states = gpd.read_file(geo / "tiger" / "cb_2023_us_state_20m.shp")
    ga = states[states.STUSPS == "GA"].to_crs(5070)
    phys = gpd.read_file(geo / "physio" / "physio.shp")
    phys = phys.set_crs(4269, allow_override=True) if phys.crs is None else phys
    cp = phys[phys.PROVINCE == "COASTAL PLAIN"].to_crs(5070)
    cp_ga = gpd.overlay(cp, ga[["geometry"]], how="intersection")
    minx, miny, maxx, maxy = ga.total_bounds
    h_in = w_in * (maxy - miny) / (maxx - minx)
    fig = plt.figure(figsize=(w_in, h_in), dpi=DPI)
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
    cp_ga.plot(ax=ax, color="#C9DDB5", linewidth=0)
    ga.boundary.plot(ax=ax, color=INK, linewidth=3)
    cx, cy = cp_ga.dissolve().representative_point().iloc[0].coords[0]
    ax.text(cx, cy - (maxy - miny) * 0.08, "Coastal\nPlain", ha="center", va="center",
            fontsize=30, fontweight=700, color=INK, linespacing=1.05)
    ax.text(minx + (maxx - minx) * 0.30, maxy - (maxy - miny) * 0.16, "GEORGIA", ha="center",
            va="center", fontsize=28, fontfamily="Oswald", fontweight=500, color=INK)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(FIG / "locator.png", dpi=DPI, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- concentration
def concentration(w_in=14.42, h_in=6.3):
    fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=DPI)
    fig.subplots_adjust(left=0.125, right=0.955, top=0.95, bottom=0.25)
    x, y = cum_area * 100, cum_vol * 100
    ax.plot([0, 100], [0, 100], ls=(0, (4, 4)), color=STEGEMAN, lw=2.5)
    ax.text(99, 13, "if wood were spread evenly", color=MUTED, fontsize=24,
            ha="right", va="top")
    ax.fill_between(x, y, x, color=RED, alpha=0.08, lw=0)
    ax.plot(x, y, color=RED, lw=5, solid_capstyle="round")
    pts = [(10, share_top10 * 100, f"Densest 10% of area: {share_top10:.0%} of wood", 30),
           (area_half * 100, 50, f"Half of all wood: {area_half:.0%} of area", 62)]
    for px, py, lab, ty in pts:
        ax.plot([px], [py], "o", ms=16, color=RED, mec="white", mew=3, zorder=6)
        ax.annotate(lab, xy=(px, py), xytext=(24, ty), fontsize=30, va="center", zorder=7,
                    bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none"),
                    arrowprops=dict(arrowstyle="-", color=INK, lw=1.8, shrinkB=10))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 102)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_yticks([0, 50, 100])
    ax.set_xticklabels([f"{t}%" for t in [0, 25, 50, 75, 100]], fontsize=26)
    ax.set_yticklabels([f"{t}%" for t in [0, 50, 100]], fontsize=26)
    ax.set_xlabel("Share of site area, densest quadrants first", fontsize=28, labelpad=10)
    ax.set_ylabel("Share of wood", fontsize=28, labelpad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_linewidth(1.5)
    ax.spines["bottom"].set_linewidth(1.5)
    ax.tick_params(length=8, width=1.5)
    ax.grid(axis="y", color=CREAMERY, lw=1.2)
    ax.set_axisbelow(True)
    fig.savefig(FIG / "concentration.png", dpi=DPI, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- photos
def photos():
    for name in ["step1_image", "step2_detect", "step4_classify"]:
        Image.open(SRC_IMG / f"{name}.jpg").convert("RGB").save(IMG / f"{name}.jpg", quality=94)
    # step 3 carries a burned-in label box at the bottom left; crop it out
    im = Image.open(SRC_IMG / "step3_measure.jpg").convert("RGB")
    if im.size == (1200, 1200):  # the docs copy is already cropped since the v3 update
        im = im.crop((100, 0, 1040, 940))
    im.save(IMG / "step3_measure.jpg", quality=94)

    # figure 1 panel (a), the tile layout, from the v3 TIFF. Panel (b), the
    # orthomosaic, is cropped away and never used. The "(a)" title line goes too.
    v3 = ROOT / "figures"
    f1 = v3 / "figure1_site_nocoords.tiff"
    if f1.exists():
        fig1 = Image.open(f1).convert("RGB")
        arr = np.asarray(fig1)
        white = (arr > 245).all(axis=2).all(axis=0)
        gutter = next(x for x in range(int(fig1.width * 0.40), int(fig1.width * 0.60)) if white[x])
        fig1.crop((0, 200, gutter, fig1.height)).save(IMG / "site_extent.png", optimize=True)

    # study site tile (upper-left crop keeps out the buildings in the corner)
    # The source tile path is local and never committed: internal tile filenames
    # carry the site name. Set POSTER_SITE_TILE to it, or keep an existing crop.
    tile = Path(os.environ.get("POSTER_SITE_TILE", "")) if os.environ.get("POSTER_SITE_TILE") else None
    if (IMG / "site_tile.jpg").exists() and tile is None:
        pass
    elif tile is not None and tile.exists():
        Image.open(tile).convert("RGB").crop((0, 0, 900, 900)).save(IMG / "site_tile.jpg", quality=94)
    else:
        Image.open(SRC_IMG / "step1_image.jpg").convert("RGB").save(IMG / "site_tile.jpg", quality=94)

    # gallery: the v3 paper figure (TIFF, 600 dpi), else the web copy. Panel
    # boxes were measured on the 1600 px layout and scale with the width.
    tif = v3 / "figure5_gallery.tiff"
    src = tif if tif.exists() else SRC_IMG / "fig_gallery.webp"
    g = Image.open(src).convert("RGB")
    k = g.width / 1600
    boxes_x = [(57, 415), (444, 802), (831, 1189), (1218, 1576)]
    boxes_y = [(23, 381), (409, 767)]
    for r, (y0, y1) in enumerate(boxes_y):
        for c, (x0, x1) in enumerate(boxes_x):
            # drop the burned-in length label at the top; keep the panel square
            box = tuple(round(v * k) for v in (x0 + 19, y0 + 34, x1 - 19, y1 - 3))
            g.crop(box).save(IMG / f"gallery_{r}{c}.jpg", quality=95)


# ---------------------------------------------------------------- logos
def clean_logo(src, dst, tol=14):
    """Make the flat, edge-connected background transparent. Logo pixels are untouched."""
    im = Image.open(src).convert("RGBA")
    rgb = im.convert("RGB")
    key = (255, 0, 255)
    w, h = rgb.size
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if rgb.getpixel(seed) != key:
            ImageDraw.floodfill(rgb, seed, key, thresh=tol)
    a = np.array(im)
    bg = np.array(Image.open(src).convert("RGB").getpixel((0, 0)), dtype=int)
    # edge-connected background, plus enclosed counters (inside O, R, A) of the same flat color
    mask = np.all(np.array(rgb) == key, axis=-1) | np.all(
        np.abs(a[..., :3].astype(int) - bg) <= 6, axis=-1)
    a[mask, 3] = 0
    out = Image.fromarray(a)
    out.crop(out.getbbox()).save(dst)


def logos():
    for name in ["uga", "ai_at_uga"]:
        src = LOGOS / f"{name}_source.png"
        if src.exists():
            clean_logo(src, LOGOS / f"{name}.png")
    # Warnell file already has a transparent background: only trim the empty margin
    for src in [LOGOS / "warnell_source.png", LOGOS / "warnell_source.webp"]:
        if src.exists():
            im = Image.open(src).convert("RGBA")
            im.crop(im.getchannel("A").getbbox()).save(LOGOS / "warnell.png")
            break


# ---------------------------------------------------------------- QR
def qr():
    segno.make("https://github.com/AI-UGA/fallen-tree-detection", error="m").save(
        str(FIG / "qr.svg"), scale=10, border=0, dark=BLACK)


if __name__ == "__main__":
    logos()
    photos()
    density_map()
    hotspot_map()
    zonal_tile()
    locator()
    qr()
    print("done")
