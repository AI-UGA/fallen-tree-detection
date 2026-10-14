# Reproducing the results

## What can be reproduced without the imagery

The classification rules. `src/cwd/classify.py` re-derives every inventory
label from a measurement table and asserts the published per-class counts:

```bash
python -m cwd.classify /path/to/cwd_classified_site.csv
```

Expected output: 23,215 rows, agreement 1.0000, and these counts.

```
Full stem                              5,138
Fragment                              15,562
Excluded, below length threshold         695
Excluded, below width threshold        1,084
Excluded, insufficient elongation          1
Excluded, tile boundary contact          735
```

This is a real test, not a formality. The order of the threshold tests is
definitional: applying the length floor before the width floor gives the same
inventory count but a different split between the length and width
exclusions. The assertion is what establishes the order.

## What needs the imagery

The site-wide inventory. The 76 orthomosaic tiles are not released; see
`docs/DATA.md`.

## Pipeline order

1. Tile the orthomosaic into 2,500 x 2,500 px quadrants, four per tile.
2. Run the detector at the operating threshold, 0.225, converting each
   quadrant from RGB to BGR first with `cwd.inference.to_model_input`.
   `notebooks/02_detection.ipynb` does steps 1 to 5 in one pass.
3. Measure each instance with `volume_pipeline.measure_tree`, adding the
   tile-level fields (`source_tile`, `quadrant`, `centroid_easting`,
   `centroid_northing`, `mask_area_m2`, `touches_tile_edge`, `was_annotated`,
   `match_corr`).
4. Derive `width_corr_m` and `elongation`, then classify with
   `cwd.classify.classify_frame`.
5. Aggregate against the quadrant record for area and density.

## Practical notes

**Always name result files explicitly.** There are many CSVs under
`04. Results`. Selecting by modification time can pick up a YOLO `results.csv`
rather than the site run.

**Group by `source_tile` and `quadrant` together**, or by `qkey`. `quadrant`
takes only four values (`q00`, `q01`, `q10`, `q11`), so grouping on it alone
mixes tiles.

**Derive inventory membership from `klass`.** There is no `in_inventory`
column anywhere in this project.

**Coerce boolean columns read from CSV.** Depending on the writer they come
back as numpy bool or as the strings `'True'` and `'False'`, and a groupby on
the string form fails silently. `cwd.classify.coerce_bool` handles it.

**Handle empty frames in per-tile loops.** Seven of the 76 tiles produced no
detections. The quadrant record still has rows for them.

**Check colour order whenever an array goes into a model.** Rasterio and
matplotlib give RGB; Ultralytics expects BGR arrays. File paths are safe
because the library reads them itself. This cost one full site run.

**Never hardcode the project path.** Use `cwd.paths.find_root`, which searches
by content, since absolute Drive paths differ between accounts and shortcuts.
`find_root` ranks candidates by file count, so an empty duplicate folder never
wins over the populated one.

**Clear notebook outputs before committing.**

```bash
jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
```

A notebook committed with output embeds base64 images in git history
permanently and cannot be removed without rewriting history.

## Environment

See `requirements.txt`. Detectron2 must be built from source and the build
prints nothing for part of several minutes; interrupting it leaves an
unimportable package.

If running in Colab against Drive, mount first:

```python
import os
from google.colab import drive
if not os.path.ismount('/content/drive'):
    drive.mount('/content/drive')
```
