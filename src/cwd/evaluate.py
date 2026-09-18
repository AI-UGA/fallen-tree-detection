"""Unified detection scoring for both models.

WHY THIS MODULE EXISTS
The two detectors were originally scored by their own frameworks: YOLOv8s-seg
through Ultralytics, Mask R-CNN through Detectron2's COCOEvaluator. The two
evaluators do not agree, and the disagreement is large enough to invert a
conclusion. Scoring both models here, with pycocotools, against the identical
ground truth file and identical parameters, removed an apparent mask AP50
advantage for one model entirely.

Five differences between the original protocols were identified and are
reported in the manuscript's protocol audit:
  1. evaluation resolution mismatch between the two frameworks
  2. mask rasterisation path difference
  3. asymmetric ground-truth size filtering
  4. COCO's default detection cap of 100, far too low for dense forest scenes
  5. a systematic Ultralytics-to-pycocotools gap on mask AP50, while box AP50
     agrees to within 0.2 points

Any number reported from this module must state maxDets, the score threshold,
the mask resolution and whether a ground-truth size filter was applied.
Omitting them is what produced the superseded figures.
"""

from __future__ import annotations

import json
from pathlib import Path

from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

# Detection cap used for the published numbers. COCO's default of 100 truncates
# dense scenes: the validation split has a median of 68 instances per image and
# a maximum of 686.
MAXDETS = 700

# Score threshold used when generating predictions for scoring. Deliberately
# near zero so that average precision integrates over the full recall range.
# This is NOT the operating threshold; that is 0.225, in configs/thresholds.json.
SCORE_THRESHOLD = 0.001


def load_predictions(path: str | Path) -> list:
    """Read a COCO results list."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def score(
    gt_json: str | Path,
    predictions: list,
    iou_type: str,
    maxdets: int = MAXDETS,
    min_side: float | None = None,
) -> dict:
    """Score one prediction set against one ground truth file.

    iou_type is 'bbox' or 'segm'.

    min_side optionally drops ground-truth annotations whose shorter bbox side
    is below the given pixel count. This is included because one of the
    original protocols applied such a filter to only one model, which is
    artifact 3 above. Pass None to reproduce the published numbers.
    """
    coco = COCO(str(gt_json))

    if min_side is not None:
        keep = {
            index
            for index, ann in coco.anns.items()
            if min(ann["bbox"][2], ann["bbox"][3]) >= min_side
        }
        coco.anns = {i: a for i, a in coco.anns.items() if i in keep}
        coco.imgToAnns = {
            key: [a for a in value if a["id"] in keep]
            for key, value in coco.imgToAnns.items()
        }

    detections = coco.loadRes(list(predictions))
    evaluation = COCOeval(coco, detections, iou_type)
    evaluation.params.maxDets = [1, 10, maxdets]
    evaluation.evaluate()
    evaluation.accumulate()
    evaluation.summarize()

    stats = evaluation.stats * 100
    return {
        "AP": stats[0],
        "AP50": stats[1],
        "AP75": stats[2],
        "APs": stats[3],
        "APm": stats[4],
        "APl": stats[5],
    }


def score_both(
    gt_json: str | Path,
    prediction_paths: dict,
    maxdets: int = MAXDETS,
    min_side: float | None = None,
) -> dict:
    """Score several models on both IoU types.

    prediction_paths maps a model label to its COCO results file. Returns a
    dict keyed by (model, iou_type).
    """
    results = {}
    for label, path in prediction_paths.items():
        if not Path(path).exists():
            print(f"missing predictions for {label}, skipped")
            continue
        predictions = load_predictions(path)
        for iou_type in ("bbox", "segm"):
            results[(label, iou_type)] = score(
                gt_json, predictions, iou_type, maxdets, min_side
            )
    return results


# Published numbers on the 42-image validation split: pycocotools, maxDets 700,
# score 0.001, full-resolution masks, no ground-truth size filter. A run that
# does not reproduce these has changed something in the protocol.
PUBLISHED = {
    ("Mask R-CNN", "bbox"): {"AP50": 40.8, "AP": 19.1},
    ("Mask R-CNN", "segm"): {"AP50": 27.1, "AP": 6.9},
    ("YOLOv8s-seg", "bbox"): {"AP50": 43.0, "AP": 21.9},
    ("YOLOv8s-seg", "segm"): {"AP50": 24.9, "AP": 5.8},
}


def compare_to_published(results: dict, tolerance: float = 0.15) -> None:
    """Print each scored figure beside the published one."""
    print(f"\n{'model':<14}{'type':<7}{'AP50':>8}{'published':>11}{'delta':>8}")
    for key, expected in PUBLISHED.items():
        if key not in results:
            continue
        actual = results[key]["AP50"]
        delta = actual - expected["AP50"]
        mark = "" if abs(delta) <= tolerance else "   <-- differs"
        print(
            f"{key[0]:<14}{key[1]:<7}{actual:>8.1f}{expected['AP50']:>11.1f}"
            f"{delta:>+8.2f}{mark}"
        )
