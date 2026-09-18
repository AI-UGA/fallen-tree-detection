"""Figure style, colours and save helpers for the manuscript figures.

Extracted from the canonical figure notebook so that every figure is generated
with one style definition rather than a copy per notebook. Figures are written
at 600 dpi in both PNG and TIFF, which is what the target journal requires.

The per-figure drawing code lives in notebooks/05_figures.ipynb, because most
figures need the orthomosaic tiles or the annotation file, neither of which is
released. See docs/FIGURES.md for what each figure needs and docs/DATA.md for
how to obtain the inputs.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

from .paths import figures_dir

# Column widths in inches for the target journal's two-column layout.
ONE_COL = 3.5
TWO_COL = 7.2

# Model colours, kept consistent across every figure that compares the two.
C_YOLO = "#1D9E75"
C_MRCNN = "#7F77DD"

# Class colours for inventory composition figures.
C_STEM = "#1D9E75"
C_FRAG = "#EF9F27"
C_EXCL = "#B4B2A9"

# Figure filename convention: figure<N>_<topic>, written as both png and tiff.
FILENAME_PATTERN = "figure{number}_{topic}"

RC_PARAMS = {
    "figure.dpi": 110,
    "savefig.dpi": 600,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.frameon": False,
}


def apply_style() -> None:
    """Install the manuscript figure style. Call once before drawing."""
    mpl.rcParams.update(RC_PARAMS)


def figure_name(number: int, topic: str) -> str:
    """Build a filename stem following the project convention."""
    return FILENAME_PATTERN.format(number=number, topic=topic)


def save(fig, name: str, outdir: str | Path | None = None, dpi: int = 600) -> list[Path]:
    """Write a figure as PNG and TIFF, returning the paths written."""
    directory = Path(outdir) if outdir is not None else figures_dir()
    directory.mkdir(parents=True, exist_ok=True)

    written = []
    for extension in ("png", "tiff"):
        path = directory / f"{name}.{extension}"
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
        written.append(path)

    return written


def new_figure(width: float = ONE_COL, height: float = 2.6, **kwargs):
    """Create a styled figure and axes at one of the journal column widths."""
    apply_style()
    return plt.subplots(figsize=(width, height), **kwargs)
