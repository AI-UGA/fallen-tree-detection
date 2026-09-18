# Locked numbers

Every figure here comes from the released site run. If code does not reproduce
these, the code is wrong, not the numbers.

## Site and imagery

| Quantity | Value |
|---|---|
| Imaged area | 478.7345 ha |
| Bounding box area | 655.7 ha (73.0 percent imaged) |
| Ground sample distance | 0.0508 m/px |
| Tiles | 76, of which 6 produced no detections |
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

Superseded, do not reuse: 42.8/38.5, 35.8/25.4, and the ratio 1.52. These came
from scoring each model with its own framework's evaluator.

## Operating point

Threshold 0.225, the F1 maximum on the validation split at box IoU 0.5.
3,004 detections, 1,605 matched, precision 0.534, recall 0.437, F1 0.481.
Recall ceiling 0.611 at threshold 0.05.

## Inventory, site run

| Quantity | Value |
|---|---|
| Total detections | 23,603 |
| Total volume, detection basis | 14,801.8 m3 |
| Inventory objects | 21,205 |
| Inventory volume | 14,237.0 m3 |
| Inventory density | 29.74 m3/ha, 44.3 objects/ha |

Exclusions, by category:

| Category | Objects | Volume (m3) |
|---|---|---|
| Below length threshold | 855 | 34.8 |
| Below width threshold | 784 | 26.2 |
| Insufficient elongation | 8 | 3.7 |
| Tile boundary contact | 751 | 500.1 |
| Total | 2,398 | 564.8 |

Identities worth asserting: 14,801.8 - 564.8 = 14,237.0 exactly, and
3,883 + 17,322 = 21,205.

## Composition

| Class | Objects | Volume (m3) | m3/ha |
|---|---|---|---|
| Full stem | 5,240 | 8,041.1 | 16.80 |
| Fragment | 15,965 | 6,195.9 | 12.94 |

Full stems are 24.7 percent of counted objects and 56.5 percent of volume.

## Annotated versus unannotated quadrants

Inventory basis. These replaced an earlier pair of figures, 17.1 and 37.4,
which were correct on the detection basis but did not sum to the paper's
headline volume.

| Region | Area | Inventory objects | Volume (m3) | m3/ha |
|---|---|---|---|---|
| Unannotated | 152.929 ha | 3,883 | 2,489.8 | 16.3 |
| Annotated | 325.806 ha | 17,322 | 11,747.2 | 36.1 |

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

18.1 percent multi-component, 12.5 percent branched centreline, 67.6 percent
clean on both. On the validation run, 84.6 percent carried no flag.

## Environment

PyTorch 2.11.0+cu128, Detectron2 0.6, Ultralytics 8.4.101, Python 3.12.13,
CUDA 12.8. Training hardware A100.

Mask R-CNN: 7,000 iterations (metrics.json final logged iteration 6999), batch
4, LR 0.0005, warmup 1,000, steps 5,600 and 6,510, AMP off, gradient clip 1.0,
130 of 146 images, about 1 h 45 min, 0.897 s/iter, no seed.

YOLOv8s-seg: run yolov8s_seg_run3_v4_1600, 200 epochs, imgsz 1600, SGD LR 0.01
cosine, seed 0 deterministic, patience 50 not triggered, best epoch 151 by mask
AP50 = 0.373, about 0.85 h.

Epoch 151 is correct. A competing figure of epoch 89 came from a custom
fitness formula applied to the same results.csv afterwards, not from
Ultralytics. Patience 50 not firing corroborates 151, since 151 + 50 > 200.

## Run name mapping

Internal run names drifted during development. This table is the authority.

| Internal name | Name used in the paper | Status |
|---|---|---|
| Run 2.0 | baseline | superseded, T4, trained on an earlier dataset |
| Run 2.1 | not reported | superseded, T4, 8,000 iterations |
| Run 3.0 | Mask R-CNN | reported, A100, 7,000 iterations, DataV4 |
| yolov8s_seg_run3_v4_1600 | YOLOv8s-seg | reported, the inventory model |

A run once labelled "run4" was in fact Run 3.0.

## Superseded values that must not reappear

42.8, 38.5, 35.8, 25.4, ratio 1.52, 17.1 and 37.4 as inventory densities,
22.2 m3/ha, 19.0 m3/ha, "upper bound" applied to 29.7, MIN_SIDE=8 as a
default, 1024 as the reported evaluation resolution, and the earlier project
name containing the word "Detection" where the paper says inventory.

`scripts/preflight.sh` greps for these.
