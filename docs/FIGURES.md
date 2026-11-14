# Figures

Style, colours and the save helper live in `src/cwd/figures.py`. Per-figure
drawing code lives in `notebooks/05_figures.ipynb`, because most figures need
either the orthomosaic tiles or the annotation file, neither of which is
released.

## Conventions

- Filenames follow `figure<N>_<topic>`, written as both PNG and TIFF at
  600 dpi.
- Column widths: 3.5 in single column, 7.2 in double column.
- Model colours are fixed across every figure: YOLOv8s-seg orange, Mask
  R-CNN green, annotations black (as in Figure 6).
- Class colours: full stem `#1D9E75`, fragment `#EF9F27`, excluded `#B4B2A9`.
- Colour never carries meaning on its own. Every distinction is also encoded
  by position, label or marker.

## Inputs each figure needs

| Figure | Needs | Released? |
|---|---|---|
| Study site footprint | tile extents | no |
| Pipeline diagram | none, drawn from scratch | yes |
| Instance size distribution | annotation file | yes, via Zenodo |
| Training curves | YOLO results.csv, Mask R-CNN metrics.json | no |
| Detection examples | tiles plus predictions | no |
| Box versus mask AP50 illustration | one tile crop plus annotation | no |
| Inventory composition | measurement table | no |
| Per-tile density (manuscript Figure 7) | measurement table plus quadrant record | no |
| Per-quadrant density (website, poster) | `docs/assets/site.json` | yes |

## Regenerating

Call `apply_style()` once, then `save(fig, figure_name(n, topic))`. Do not set
rcParams per figure; that is how two figures ended up with different fonts.

## Web images

`scripts/build_web_figures.py` writes the images under `docs/assets/img/`
from the coordinate-free v3 figures, as WebP with no metadata:
`fig_site.webp` (Figure 1, panel a only; the orthomosaic panel is never
published), `fig_sizes.webp` (Figure 4), `fig_volume.webp` (Figure 8),
`fig_gallery.webp` (Figure 5) and `fig_density.png`, which is drawn per
127 m (1.6 ha) quadrant from `docs/assets/site.json`. The manuscript's
Figure 7 shows the same data per tile (6.45 ha). Figure 2 is not used on the
website or poster, because its annotation and segmentation colours clash with
the full stem (green) and fragment (orange) colours.
