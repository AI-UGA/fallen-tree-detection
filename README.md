# Coarse woody debris inventory from UAV imagery

Code for a site-wide coarse woody debris inventory of a Hurricane Helene
windthrow site in the Georgia Coastal Plain, built from UAV orthomosaic
imagery and instance segmentation.

The pipeline detects fallen woody material, extracts a centreline for each
instance, samples perpendicular widths along it, integrates conical frusta to
estimate volume, and classifies each object as a full stem, a fragment, or one
of four exclusion categories.

**The imagery and all georeferenced products are not released.** The study
site is privately owned land. See [docs/DATA.md](docs/DATA.md).

## Headline results

| Quantity | Value |
|---|---|
| Imaged area | 478.7345 ha |
| Total detections | 23,215 |
| Inventory objects | 20,700 |
| Inventory volume | 14,400.6 m3 |
| Inventory density | 30.08 m3/ha, 43.2 objects/ha |
| Full stems | 5,138 objects, 8,266.8 m3 |
| Fragments | 15,562 objects, 6,133.8 m3 |

Full stems are 24.8 percent of counted objects and 57.4 percent of volume.

These numbers come from the corrected site run of October 2026. An earlier run
passed RGB tiles to a model that expects BGR arrays; see
[CHANGELOG.md](CHANGELOG.md) and the inference note below.

Volumes are estimator output. They have never been calibrated against field
measurement. The object count is a floor rather than a ceiling, because recall
of 0.437 dominates any inflation from double counting.

Every number the code must reproduce is listed in
[docs/NUMBERS.md](docs/NUMBERS.md).

## Detection performance

42-image validation split, scored with pycocotools at maxDets 700, score
threshold 0.001, full-resolution masks, no ground-truth size filter.

| Model | Box AP50 | Box AP | Mask AP50 | Mask AP |
|---|---|---|---|---|
| Mask R-CNN | 40.8 | 19.1 | 27.1 | 6.9 |
| YOLOv8s-seg | 43.0 | 21.9 | 24.9 | 5.8 |

Both models were originally scored by their own frameworks, which do not
agree. Rescoring both through one evaluator removed an apparent mask AP50
advantage entirely. The five protocol differences behind that are documented
in [src/cwd/evaluate.py](src/cwd/evaluate.py).

YOLOv8s-seg is the inventory model, chosen on operational grounds rather than
an accuracy claim.

## Layout

```
configs/
  thresholds.json     classification rules, the single source of truth
  maskrcnn.yaml       Mask R-CNN architecture and solver
  yolov8s_seg.yaml    YOLOv8s-seg training arguments
src/cwd/
  paths.py            locate the data root by content, never by hardcoded path
  inference.py        convert raster tiles to the colour order the model expects
  volume_pipeline.py  per-object measurement and frustum volume
  classify.py         inventory and exclusion labels, with a self-test
  evaluate.py         unified pycocotools scoring for both models
  figures.py          figure style and save helpers
notebooks/
  02_detection.ipynb  site-wide inference, measurement and classification
docs/
  DATA.md             what is released, what is not, how to request access
  NUMBERS.md          every locked number the code must reproduce
  REPRODUCE.md        pipeline order and the traps that have cost time
  FIGURES.md          figure conventions and per-figure inputs
scripts/
  preflight.sh        pre-commit scan, seven failure classes
  fetch_data.py       download the Zenodo deposit
```

## Verifying the classification rules

This runs without the imagery. It re-derives every label from a released
measurement table and asserts the published per-class counts.

```bash
PYTHONPATH=src python -m cwd.classify path/to/cwd_classified_site.csv
```

Expected: 23,215 rows, agreement 1.0000, and the six counts in
[docs/NUMBERS.md](docs/NUMBERS.md).

The order of the threshold tests is definitional. Applying the length floor
before the width floor yields the same inventory count but a different split
between the length and width exclusions. The assertion is what pins the order
down.

## Inference input: colour order

Rasterio reads the GeoTIFF bands in RGB order. Ultralytics treats a numpy
array as BGR, the OpenCV convention, and converts it internally. An RGB array
passed straight to `model.predict` is therefore inferred with red and blue
swapped. On the validation split that lowers F1 from 0.481 to 0.427 at the
operating threshold. Convert first with `cwd.inference.to_model_input`. Passing
a file path instead of an array avoids the problem, because the library then
reads the file itself.

## Classification rules

Thresholds are in `configs/thresholds.json` and match Table 6 of the paper.

Tests apply in this order:

1. `width_corr_m` below 0.15 m, three pixels, excluded
2. `length_m` below 1.37 m, excluded
3. elongation below 3.0, excluded
4. touches a tile edge, excluded, because length on a truncated mask is
   unreliable
5. full stem if length is at least 6.78 m, elongation at least 12.0, and
   corrected width between 0.25 and 1.50 m
6. otherwise a fragment

Width comparisons use `width_corr_m`, which is `width_mean_m / 1.19`.
Predicted masks are about 19 percent wider than hand-annotated ones at the
median. The correction is applied to classification only, never to reported
volumes.

## Environment

PyTorch 2.11.0+cu128, Detectron2 0.6, Ultralytics 8.4.101, Python 3.12.13,
CUDA 12.8. See `requirements.txt`. Detectron2 has no PyPI release and must be
built from source.

## Citation

See [CITATION.cff](CITATION.cff). Code is MIT licensed; the data deposit is
CC BY 4.0. Requests for the full dataset go to the corresponding author.

## Authors

Dang Hoang, Rishab Subramaniyan, Owen Norman, Joey Hattan, Roger C. Lowe III.
AI@UGA and the Warnell School of Forestry and Natural Resources, University of
Georgia; Brown University.
