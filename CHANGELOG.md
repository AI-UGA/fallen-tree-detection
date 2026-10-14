# Changelog

## October 2026: colour-order fix and corrected site run

**What was wrong.** The September site run read each orthomosaic tile with
rasterio, which returns RGB, and passed the array directly to
`model.predict`. Ultralytics treats an array as BGR, so every quadrant was
inferred with red and blue swapped. Model evaluation was not affected: the
validation predictions were generated from image files, which the library
reads itself.

**How it was found.** While drawing mask overlays, re-running the model on
three quadrants matched only about 80 percent of the stored detections. Feeding
both colour orders to the 42-image validation split gave F1 0.481 for correct
input and 0.427 for swapped input.

**What changed.** The site run was repeated with the quadrant converted to BGR
before inference (`cwd.inference.to_model_input`). Everything else is
identical: weights, imgsz 1600, conf 0.225, NMS IoU 0.6, max_det 700, the
quadrant grid, the annotated-quadrant matching (202 of 300, same areas to the
third decimal) and the classification thresholds, which were held fixed rather
than re-derived.

| Quantity | September (superseded) | October (current) |
|---|---|---|
| Detections | 23,603 | 23,215 |
| Inventory objects | 21,205 | 20,700 |
| Inventory volume | 14,237.0 m3 | 14,400.6 m3 |
| Inventory density | 29.74 m3/ha | 30.08 m3/ha |
| Unannotated / annotated quadrants | 16.3 / 36.1 m3/ha | 16.5 / 36.4 m3/ha |
| Full stems | 5,240 | 5,138 |
| Fragments | 15,965 | 15,562 |

Inventory volume moved by 1.1 percent and no conclusion of the paper changes.
Expected counts in `src/cwd/classify.py`, `docs/NUMBERS.md` and
`docs/REPRODUCE.md` now refer to the corrected run.

Also in this change: the elongation fallback in `classify_frame` now uses the
bias-corrected width, matching the site run. It is only reached when a table
has no `elongation` column.
