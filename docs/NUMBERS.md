# Locked numbers

Every figure here comes from the corrected site run of October 2026
(`site_run_v3`). If code does not reproduce these, the code is wrong, not the
numbers. The September run, which passed RGB tiles to a BGR-expecting model,
is superseded; see CHANGELOG.md.

## Site and imagery

| Quantity | Value |
|---|---|
| Imaged area | 478.7345 ha |
| Bounding box area | 655.7 ha (73.0 percent imaged) |
| Ground sample distance | 0.0508 m/px |
| Tiles | 76, of which 7 produced no detections |
| Quadrants | 300, each 2,500 x 2,500 px |
| CRS | EPSG:26917, UTM zone 17N |

Area always comes from the quadrant record, `per_tile/*.quads.csv`, grouped by
`was_annotated`. Never hardcode 152.9 or 325.8. The quadrant record covers all
300 quadrants including those with no detections, so it is the only complete
source. Clipped edge quadrants have smaller `area_ha`, which is why the six
clipped tiles do not corrupt the total.

## Detection, 42-image validation split

pycocotools, maxDets 700, score 0.001, full-resolution masks, no ground-truth
size filter.

| Model | Box AP50 | Box AP | Mask AP50 | Mask AP |
|---|---|---|---|---|
| Mask R-CNN | 40.8 | 19.1 | 27.1 | 6.9 |
| YOLOv8s-seg | 43.0 | 21.9 | 24.9 | 5.8 |

At maxDets 100: box AP50 34.9 and 35.3; mask AP50 24.6 and 22.3.

## Operating point

Threshold 0.225, the F1 maximum on the validation split at box IoU 0.5.
3,004 detections, 1,605 matched, precision 0.534, recall 0.437, F1 0.481.
Recall ceiling 0.611 at threshold 0.05.

## Inventory, site run

| Quantity | Value |
|---|---|
| Total detections | 23,215 |
| Total volume, detection basis | 14,879.3 m3 |
| Inventory objects | 20,700 |
| Inventory volume | 14,400.6 m3 |
| Inventory density | 30.08 m3/ha, 43.2 objects/ha |

Exclusions, by category:

| Category | Objects | Volume (m3) |
|---|---|---|
| Below length threshold | 695 | 24.6 |
| Below width threshold | 1,084 | 29.4 |
| Insufficient elongation | 1 | 0.3 |
| Tile boundary contact | 735 | 424.4 |
| Total | 2,515 | 478.7 |

Identities worth asserting: 14,879.3 - 478.7 = 14,400.6 exactly, and
3,668 + 17,032 = 20,700.

## Composition

| Class | Objects | Volume (m3) | m3/ha |
|---|---|---|---|
| Full stem | 5,138 | 8,266.8 | 17.27 |
| Fragment | 15,562 | 6,133.8 | 12.81 |

Full stems are 24.8 percent of counted objects and 57.4 percent of volume.

Length thresholds are fixed at the values in configs/thresholds.json. The
full stem cut of 6.78 m was the 75th percentile of length when the rule set
was fixed; in the corrected run that percentile is 6.70 m, and the cut was
deliberately not re-derived.

## Annotated versus unannotated quadrants

Inventory basis.

| Region | Area | Inventory objects | Volume (m3) | m3/ha |
|---|---|---|---|---|
| Unannotated | 152.929 ha | 3,668 | 2,528.3 | 16.5 |
| Annotated | 325.806 ha | 17,032 | 11,872.3 | 36.4 |

Per-tile inventory density: 0 to 185.2 objects/ha, median 36.2, mean 42.7;
volume up to 224.7 m3/ha.

## Annotation

209 images, 15,809 instances, splits 146 / 42 / 21. Validation carries 3,676
instances. 202 of 300 quadrants annotated, 98 not. 7 of the 209 images come
from outside the 76 tiles: they train the model but do not enter the
inventory. Dataset version 4, exported 28 July 2026. Mask R-CNN trained on an
earlier generation with 15,690 instances, 119 fewer, a 0.8 percent difference.

## Width bias

Predicted masks are 19 percent wider than annotated at the median over 1,605
matched objects. Lengths agree within 3 percent. Median per-object volume
factor 1.35; volume-weighted factor 1.17. The largest quartile holds 64
percent of volume at a weighted factor of 0.97.

WIDTH_BIAS = 1.19 is applied to CLASSIFICATION only, never to reported
volumes.

## Mask quality, site run

All detections. 16.8 percent multi-component, 11.5 percent branched
centerline. The two overlap: 74.6 percent are clean on both, and 69.3 percent
carry no quality flag of any kind. Median length 3.17 m for multi-component
masks against 4.69 m for the rest. On the validation run, 84.6 percent carried
no flag.

## Inference settings

imgsz 1600, conf 0.225, NMS IoU 0.6, max_det 700, retina_masks off. Tiles are
converted RGB to BGR before `model.predict`. Weights:
`04. Results/YOLOv8/best.pt` in the project data root.

## Environment

PyTorch 2.11.0+cu128, Detectron2 0.6, Ultralytics 8.4.101, Python 3.12.13,
CUDA 12.8. Training hardware A100.

Mask R-CNN: 7,000 iterations (metrics.json final logged iteration 6999), batch
4, LR 0.0005, warmup 1,000, steps 5,600 and 6,510, AMP off, gradient clip 1.0,
130 of 146 images, about 1 h 45 min, 0.897 s/iter, no seed.

YOLOv8s-seg: run yolov8s_seg_run3_v4_1600, 200 epochs, imgsz 1600, SGD LR 0.01
cosine, seed 0 deterministic, patience 50 not triggered, best epoch 151 by mask
AP50 = 0.373, about 0.85 h.
