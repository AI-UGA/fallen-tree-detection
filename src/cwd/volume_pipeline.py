"""Per-object measurement and volume estimation for segmented woody debris.

Written by Joey Hattan. Unmodified in substance; the changes made for release
are listed below.

For each predicted instance mask this module extracts a centreline by
skeletonisation, samples perpendicular widths along it, and integrates a
sequence of conical frusta to obtain a volume. The 16 fields of
TreeMeasurement are the first 16 columns of the released measurement CSVs, in
order.

HOW THE PAPER ACTUALLY CALLED THIS
The site run does not use run_pipeline(). It calls measure_tree() directly,
once per instance, through a wrapper (measure_one) that adds the tile-level
fields the inventory needs: source_tile, quadrant, centroid_easting,
centroid_northing, mask_area_m2, touches_tile_edge, was_annotated and
match_corr. Those fields are georeferencing and provenance, not measurement,
which is why they are not produced here. run_pipeline() is retained as a
standalone entry point for a single predictions file.

CHANGES MADE FOR RELEASE
  - MIN_SCORE lowered from 0.5 to 0.225. The published operating point is
    0.225, chosen at the F1 maximum on the validation split. The old default
    was never exercised, because the site run bypasses run_pipeline(), but
    leaving it in a public file would misreport the threshold used.
  - Comments translated and expanded. No change to any computation.

Volumes are estimator output and have never been calibrated against field
measurement.
"""

from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from pycocotools import mask as coco_mask
from scipy import ndimage
from skimage.morphology import skeletonize

# Ground sample distance of the orthomosaic, metres per pixel. Confirmed
# identical across all 76 tiles.
METERS_PER_PIXEL = 0.0508

# Operating confidence threshold, the F1 maximum on the validation split at
# box IoU 0.5. See configs/thresholds.json.
MIN_SCORE = 0.225

# Spacing of perpendicular width samples along the centreline, in pixels.
WIDTH_SAMPLE_INTERVAL_PX = 10.0


@dataclass
class TreeMeasurement:
    """One measured object. Field order matches the released CSV columns."""

    tree_id: str
    image_id: str
    source_id: str
    confidence: float | None
    length_px: float
    length_m: float
    width_base_px: float
    width_top_px: float
    width_mean_px: float
    width_base_m: float
    width_top_m: float
    width_mean_m: float
    width_length_ratio: float
    volume_m3: float
    mask_area_px: int
    quality_flags: str


def load_predictions(path):
    """Read a COCO-format results file, which must be a JSON list."""
    with Path(path).open(encoding="utf-8") as file:
        predictions = json.load(file)

    if not isinstance(predictions, list):
        raise ValueError("Expected a COCO results JSON containing a list")
    return predictions


def decode_mask(prediction):
    """Decode an RLE mask and crop it to a small margin around the bbox.

    Cropping keeps the skeletonisation and width searches cheap. The two-pixel
    margin leaves room for the perpendicular search to step off the mask and
    detect an edge rather than running into the array boundary.
    """
    segmentation = prediction["segmentation"].copy()
    if isinstance(segmentation["counts"], str):
        segmentation["counts"] = segmentation["counts"].encode("ascii")

    mask = coco_mask.decode(segmentation).astype(bool)
    x, y, width, height = prediction["bbox"]
    x1 = max(0, math.floor(x) - 2)
    y1 = max(0, math.floor(y) - 2)
    x2 = min(mask.shape[1], math.ceil(x + width) + 2)
    y2 = min(mask.shape[0], math.ceil(y + height) + 2)

    return mask[y1:y2, x1:x2], (y1, x1), mask.shape


def largest_component(mask):
    """Keep only the largest connected component.

    A single predicted instance is sometimes split into several blobs, for
    example where foliage crosses a trunk. Measuring the union would inflate
    length. The discard is recorded as a quality flag rather than hidden.
    """
    labels, count = ndimage.label(mask, np.ones((3, 3)))
    if count <= 1:
        return mask, False

    areas = np.bincount(labels.ravel())
    areas[0] = 0
    return labels == areas.argmax(), True


def neighbors(point, points):
    """Yield skeleton neighbours of a point with their step lengths.

    Diagonal steps are suppressed when either orthogonal step is also present,
    so that a staircase in the skeleton is not shortcut and over-counted as a
    shorter diagonal path.
    """
    row, column = point
    for row_step in (-1, 0, 1):
        for column_step in (-1, 0, 1):
            if row_step == column_step == 0:
                continue

            neighbor = row + row_step, column + column_step
            if neighbor not in points:
                continue

            if row_step and column_step:
                horizontal = row, column + column_step
                vertical = row + row_step, column
                if horizontal in points or vertical in points:
                    continue

            step = math.sqrt(2) if row_step and column_step else 1.0
            yield neighbor, step


def shortest_paths(start, points):
    """Dijkstra over the skeleton graph from start."""
    distances = {start: 0.0}
    parents = {start: None}
    queue = [(0.0, start)]

    while queue:
        distance, point = heapq.heappop(queue)
        if distance != distances[point]:
            continue

        for neighbor, step in neighbors(point, points):
            new_distance = distance + step
            if new_distance < distances.get(neighbor, math.inf):
                distances[neighbor] = new_distance
                parents[neighbor] = point
                heapq.heappush(queue, (new_distance, neighbor))

    return distances, parents


def find_centerline(mask):
    """Return the longest path through the mask's skeleton, and a branch count.

    The longest path is found by the standard double sweep: walk to the
    farthest point from an arbitrary endpoint, then to the farthest point from
    there. Branch points are counted so that a forked skeleton, typically a
    trunk with limbs still attached, can be flagged.
    """
    points = {tuple(point) for point in np.argwhere(skeletonize(mask))}
    if not points:
        return [], 0
    if len(points) == 1:
        return list(points), 0

    degrees = {point: sum(1 for _ in neighbors(point, points)) for point in points}
    endpoints = [point for point, degree in degrees.items() if degree == 1]
    branch_count = sum(degree > 2 for degree in degrees.values())

    start = endpoints[0] if endpoints else next(iter(points))
    distances, _ = shortest_paths(start, points)
    first_end = max(distances, key=distances.get)
    distances, parents = shortest_paths(first_end, points)
    second_end = max(distances, key=distances.get)

    path = []
    point = second_end
    while point is not None:
        path.append(point)
        point = parents[point]

    return path[::-1], branch_count


def sample_centerline(centerline, interval_px=WIDTH_SAMPLE_INTERVAL_PX):
    """Thin the centreline to roughly one point per interval, keeping both ends."""
    if not centerline:
        return []

    sampled = [centerline[0]]
    distance_since_sample = 0.0

    for point_a, point_b in zip(centerline, centerline[1:]):
        distance_since_sample += math.dist(point_a, point_b)
        if distance_since_sample >= interval_px:
            sampled.append(point_b)
            distance_since_sample = 0.0

    if sampled[-1] != centerline[-1]:
        sampled.append(centerline[-1])

    return sampled


def perpendicular_width(mask, centerline, index, step=0.25):
    """Width of the mask measured perpendicular to the local centreline tangent.

    The tangent comes from the neighbouring sample points. The search walks
    outward in sub-pixel steps in both directions until it leaves the mask,
    and reports the distance to the midpoint of the last step, which centres
    the estimate on the true edge rather than biasing it outward.
    """
    point = centerline[index]

    before = centerline[max(0, index - 1)]
    after = centerline[min(len(centerline) - 1, index + 1)]

    tangent_row = after[0] - before[0]
    tangent_col = after[1] - before[1]
    norm = math.hypot(tangent_row, tangent_col)

    if norm == 0:
        return 0.0

    perp_row = -tangent_col / norm
    perp_col = tangent_row / norm

    def distance_to_edge(direction):
        distance = 0.0

        while True:
            next_distance = distance + step
            row = point[0] + direction * perp_row * next_distance
            col = point[1] + direction * perp_col * next_distance

            row_idx = int(round(row))
            col_idx = int(round(col))

            if (
                row_idx < 0
                or row_idx >= mask.shape[0]
                or col_idx < 0
                or col_idx >= mask.shape[1]
                or not mask[row_idx, col_idx]
            ):
                return max(0.0, next_distance - step / 2)

            distance = next_distance

    return distance_to_edge(1) + distance_to_edge(-1)


def width_profile(mask, centerline, interval_px=WIDTH_SAMPLE_INTERVAL_PX):
    """Perpendicular widths at the sampled centreline points.

    A short median filter removes single-sample spikes, which occur where the
    skeleton passes through a lump of attached foliage.
    """
    sampled_centerline = sample_centerline(centerline, interval_px)

    if not sampled_centerline:
        return [], np.array([])

    widths = np.array(
        [
            perpendicular_width(mask, sampled_centerline, index)
            for index in range(len(sampled_centerline))
        ],
        dtype=float,
    )

    if len(widths) >= 3:
        filter_size = min(5, len(widths))
        if filter_size % 2 == 0:
            filter_size -= 1
        widths = ndimage.median_filter(widths, size=filter_size)

    return sampled_centerline, widths


def centerline_length(centerline, widths):
    """Centreline length in pixels, extended by half a width at each end.

    Skeletonisation retracts from the mask boundary, so the raw path stops
    short of both ends of the stem. Adding half the end width at each end
    restores the missing amount.
    """
    length = sum(math.dist(a, b) for a, b in zip(centerline, centerline[1:]))
    if len(widths):
        length += (widths[0] + widths[-1]) / 2
    return float(length)


def summarize_widths(widths):
    """Return base, top and median widths in pixels.

    Base and top are medians over the outer 15 percent of samples, at least
    three, with the wider end reported as the base. Which physical end is the
    root cannot be determined from imagery alone.
    """
    if not len(widths):
        return 0.0, 0.0, 0.0

    end_count = min(max(3, math.ceil(len(widths) * 0.15)), len(widths))
    ends = np.median(widths[:end_count]), np.median(widths[-end_count:])
    return float(max(ends)), float(min(ends)), float(np.median(widths))


def estimate_volume(centerline, widths, meters_per_pixel):
    """Integrate conical frusta between consecutive width samples.

    Each segment contributes pi * L * (d1^2 + d1*d2 + d2^2) / 12, the volume of
    a frustum of a cone with end diameters d1 and d2. Widths are treated as
    diameters, which assumes a circular cross-section.
    """
    volume = 0.0

    for point_a, point_b, width_a, width_b in zip(
        centerline, centerline[1:], widths, widths[1:]
    ):
        length = math.dist(point_a, point_b) * meters_per_pixel
        diameter_a = width_a * meters_per_pixel
        diameter_b = width_b * meters_per_pixel

        volume += (
            math.pi
            * length
            * (diameter_a**2 + diameter_a * diameter_b + diameter_b**2)
            / 12
        )

    return float(volume)


def get_quality_flags(
    mask, centerline, widths, removed_components, branch_count, offset, image_shape
):
    """Semicolon-joined flags describing how reliable the measurement is.

    Values: ok, empty_mask, multiple_components_largest_used,
    branched_centerline, very_small_mask, no_centerline, no_width_estimate,
    touches_image_edge. Nothing is dropped on the basis of a flag; the flags
    are reported so that mask quality can be audited.
    """
    if not mask.any():
        return "empty_mask"

    flags = []
    if removed_components:
        flags.append("multiple_components_largest_used")
    if branch_count:
        flags.append("branched_centerline")
    if mask.sum() < 25:
        flags.append("very_small_mask")
    if not centerline:
        flags.append("no_centerline")
    elif not len(widths):
        flags.append("no_width_estimate")

    rows, columns = np.nonzero(mask)
    top, left = offset
    height, width = image_shape
    if (
        top + rows.min() == 0
        or left + columns.min() == 0
        or top + rows.max() == height - 1
        or left + columns.max() == width - 1
    ):
        flags.append("touches_image_edge")

    return ";".join(flags) if flags else "ok"


def measure_tree(prediction, tree_id, source_id, meters_per_pixel):
    """Measure one predicted instance.

    This is the function the site run calls, once per instance.
    """
    mask, offset, image_shape = decode_mask(prediction)
    mask, removed_components = largest_component(mask)
    centerline, branch_count = find_centerline(mask)
    sampled_centerline, widths = width_profile(mask, centerline)

    length_px = centerline_length(centerline, widths)
    base_px, top_px, mean_px = summarize_widths(widths)
    flags = get_quality_flags(
        mask,
        centerline,
        widths,
        removed_components,
        branch_count,
        offset,
        image_shape,
    )

    return TreeMeasurement(
        tree_id=tree_id,
        image_id=str(prediction["image_id"]),
        source_id=source_id,
        confidence=float(prediction["score"]),
        length_px=length_px,
        length_m=length_px * meters_per_pixel,
        width_base_px=base_px,
        width_top_px=top_px,
        width_mean_px=mean_px,
        width_base_m=base_px * meters_per_pixel,
        width_top_m=top_px * meters_per_pixel,
        width_mean_m=mean_px * meters_per_pixel,
        width_length_ratio=mean_px / length_px if length_px else 0.0,
        volume_m3=estimate_volume(sampled_centerline, widths, meters_per_pixel),
        mask_area_px=int(mask.sum()),
        quality_flags=flags,
    )


def save_csv(measurements, output_path):
    """Write measurements to CSV in dataclass field order."""
    fields = list(TreeMeasurement.__dataclass_fields__)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for measurement in measurements:
            row = asdict(measurement)
            writer.writerow(
                {
                    key: round(value, 6) if isinstance(value, float) else value
                    for key, value in row.items()
                }
            )


def run_pipeline(
    input_json,
    output_csv,
    meters_per_pixel=METERS_PER_PIXEL,
    min_score=MIN_SCORE,
    category_id=None,
    max_trees=None,
):
    """Measure every instance in one predictions file and write a CSV.

    Standalone entry point. The site run in the paper does not use this; see
    the module docstring.
    """
    if meters_per_pixel <= 0:
        raise ValueError("meters_per_pixel must be positive")
    if not 0 <= min_score <= 1:
        raise ValueError("min_score must be between 0 and 1")
    if max_trees is not None and max_trees <= 0:
        raise ValueError("max_trees must be positive")

    predictions = load_predictions(input_json)
    source_id = Path(input_json).stem
    image_counts = defaultdict(int)
    measurements = []

    for prediction in predictions:
        image_id = str(prediction["image_id"])
        tree_number = image_counts[image_id]
        image_counts[image_id] += 1

        if prediction["score"] < min_score:
            continue
        if category_id is not None and prediction["category_id"] != category_id:
            continue

        tree_id = f"{image_id}_tree_{tree_number:04d}"
        measurements.append(
            measure_tree(prediction, tree_id, source_id, meters_per_pixel)
        )

        if max_trees is not None and len(measurements) >= max_trees:
            break

    save_csv(measurements, output_csv)
    return measurements


def main():
    parser = argparse.ArgumentParser(
        description="Measure segmented woody debris and estimate volumes."
    )
    parser.add_argument("input_json")
    parser.add_argument("output_csv")
    parser.add_argument("--meters-per-pixel", type=float, default=METERS_PER_PIXEL)
    parser.add_argument("--min-score", type=float, default=MIN_SCORE)
    parser.add_argument("--category-id", type=int)
    parser.add_argument("--max-trees", type=int)
    args = parser.parse_args()

    measurements = run_pipeline(
        args.input_json,
        args.output_csv,
        args.meters_per_pixel,
        args.min_score,
        args.category_id,
        args.max_trees,
    )

    print(f"Wrote {len(measurements)} measurements to {args.output_csv}")


if __name__ == "__main__":
    main()
