# Figures

Style, colours and the save helper live in `src/cwd/figures.py`. Per-figure
drawing code lives in `notebooks/05_figures.ipynb`, because most figures need
either the orthomosaic tiles or the annotation file, neither of which is
released.

## Conventions

- Filenames follow `figure<N>_<topic>`, written as both PNG and TIFF at
  600 dpi.
- Column widths: 3.5 in single column, 7.2 in double column.
- Model colours are fixed across every figure: YOLOv8s-seg `#1D9E75`,
  Mask R-CNN `#7F77DD`.
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
| Per-tile density | measurement table plus quadrant record | no |

## Regenerating

Call `apply_style()` once, then `save(fig, figure_name(n, topic))`. Do not set
rcParams per figure; that is how two figures ended up with different fonts.
