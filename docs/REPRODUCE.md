# Reproducing the results

## What can be reproduced without the imagery

The classification rules. `src/cwd/classify.py` re-derives every inventory
label from a measurement table and asserts the published per-class counts:

```bash
python -m cwd.classify /path/to/cwd_classified_site.csv
```

Expected output: 23,603 rows, agreement 1.0000, and these counts.

```
Full stem                              5,240
Fragment                              15,965
Excluded, below length threshold         855
Excluded, below width threshold          784
Excluded, insufficient elongation          8
Excluded, tile boundary contact          751
```

This is a real test, not a formality. The order of the threshold tests is
definitional: applying the length floor before the width floor gives the same
inventory count but splits the exclusions 1,178 / 461 instead of 855 / 784.
The assertion is what establishes the order.

## What needs the imagery

The site-wide inventory. The 76 orthomosaic tiles are not released; see
`docs/DATA.md`.

## Pipeline order

1. Tile the orthomosaic into 2,500 x 2,500 px quadrants, four per tile.
2. Run the detector at the operating threshold, 0.225.
3. Measure each instance with `volume_pipeline.measure_tree`, adding the
   tile-level fields (`source_tile`, `quadrant`, `centroid_easting`,
   `centroid_northing`, `mask_area_m2`, `touches_tile_edge`, `was_annotated`,
   `match_corr`).
4. Derive `width_corr_m` and `elongation`, then classify with
   `cwd.classify.classify_frame`.
5. Aggregate against the quadrant record for area and density.

## Traps that have already cost time

**Always name result files explicitly.** There are 162 CSVs under
`04. Results`. Sorting by modification time and taking the most recent picks
up a YOLO `results.csv` rather than the site run. This has happened.

**Group by `source_tile` and `quadrant` together**, or by `qkey`. `quadrant`
takes only four values (`q00`, `q01`, `q10`, `q11`), so grouping on it alone
mixes tiles.

**Derive inventory membership from `klass`.** There is no `in_inventory`
column anywhere in this project.

**Coerce boolean columns read from CSV.** Depending on the writer they come
back as numpy bool or as the strings `'True'` and `'False'`, and a groupby on
the string form fails silently. `cwd.classify.coerce_bool` handles it.

**Handle empty frames in per-tile loops.** Six of the 76 tiles produced no
detections. The quadrant record still has rows for them.

**Never hardcode the project path.** Use `cwd.paths.find_root`, which searches
by content. Absolute Drive paths broke repeatedly, and a Drive restore
incident left empty duplicate folders that also matched; `find_root` ranks
candidates by file count so the populated copy wins.

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
