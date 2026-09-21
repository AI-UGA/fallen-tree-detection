"""Classify measured objects into the coarse woody debris inventory.

Every measured object is assigned exactly one label. Two labels are counted in
the inventory ('Full stem', 'Fragment'); the other four are exclusions that are
reported but not counted.

The thresholds live in configs/thresholds.json and are the single source of
truth. They must match Table 6 of the manuscript exactly.

THE ORDER OF THE TESTS IS PART OF THE DEFINITION.
The width floor is applied before the length floor. Reversing the two produces
the same inventory count but a different split between the two exclusion
categories (1,178 / 461 instead of 855 / 784), because objects failing both
floors are attributed to whichever test runs first. The ordering used here was
confirmed by reproducing the published per-class counts exactly; see
verify_against_csv() below.

Width comparisons use width_corr_m, not width_mean_m. Predicted masks are
about 19 percent wider than hand-annotated ones at the median, so
width_corr_m = width_mean_m / WIDTH_BIAS. The correction is applied to
CLASSIFICATION ONLY and never to reported volumes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# Label strings, exactly as they appear in the released CSV.
FULL_STEM = "Full stem"
FRAGMENT = "Fragment"
EXCL_LENGTH = "Excluded, below length threshold"
EXCL_WIDTH = "Excluded, below width threshold"
EXCL_ELONGATION = "Excluded, insufficient elongation"
EXCL_BOUNDARY = "Excluded, tile boundary contact"

# The two labels that make up the inventory.
INVENTORY_CLASSES = (FULL_STEM, FRAGMENT)

ALL_CLASSES = (
    FULL_STEM,
    FRAGMENT,
    EXCL_LENGTH,
    EXCL_WIDTH,
    EXCL_ELONGATION,
    EXCL_BOUNDARY,
)

DEFAULT_THRESHOLDS_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "thresholds.json"
)


def load_thresholds(path: str | Path | None = None) -> dict:
    """Read the threshold configuration released with this code."""
    path = Path(path) if path is not None else DEFAULT_THRESHOLDS_PATH
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def apply_width_bias(width_mean_m, width_bias: float):
    """Convert a predicted mask width to a bias-corrected width.

    Applied for classification only. Reported volumes use the uncorrected
    widths, because the volume-weighted bias factor is close to one and the
    correction is not calibrated against field measurement.
    """
    return width_mean_m / width_bias


def elongation(length_m, width_mean_m):
    """Length over mean width. Undefined widths propagate as NaN."""
    return length_m / width_mean_m.replace(0, float("nan"))


def classify_row(
    length_m: float,
    width_corr_m: float,
    elongation_value: float,
    touches_tile_edge: bool,
    thresholds: dict,
) -> str:
    """Return the label for one object.

    Test order, which is definitional:
      1. width floor
      2. length floor
      3. elongation floor
      4. tile boundary contact
      5. full stem criteria, all three of which must hold
      6. otherwise a fragment
    """
    floors = thresholds["floors"]
    stem = thresholds["full_stem"]

    if width_corr_m < floors["width_m"]:
        return EXCL_WIDTH
    if length_m < floors["length_m"]:
        return EXCL_LENGTH
    if elongation_value < floors["elongation"]:
        return EXCL_ELONGATION

    # Objects cut by a tile edge are measured on a truncated mask, so their
    # length and volume are unreliable. They are excluded after the floors,
    # which is why touches_tile_edge is True for more rows (810) than carry
    # this label (751): the other 59 already failed a floor.
    if touches_tile_edge:
        return EXCL_BOUNDARY

    if (
        length_m >= stem["min_length_m"]
        and elongation_value >= stem["min_elongation"]
        and stem["min_width_m"] <= width_corr_m <= stem["max_width_m"]
    ):
        return FULL_STEM

    return FRAGMENT


def coerce_bool(series: pd.Series) -> pd.Series:
    """Normalise a boolean column read from CSV.

    Depending on the writer, a boolean column comes back as numpy bool or as
    the strings 'True' and 'False'. Grouping on the raw column silently
    produces wrong results in the string case.
    """
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().eq("true")


def classify_frame(
    frame: pd.DataFrame,
    thresholds: dict | None = None,
    width_column: str = "width_corr_m",
) -> pd.Series:
    """Return a Series of labels aligned to frame's index.

    Required columns: length_m, touches_tile_edge, the width column, and
    either elongation or width_mean_m from which it can be derived.
    """
    thresholds = thresholds or load_thresholds()

    missing = {"length_m", "touches_tile_edge"} - set(frame.columns)
    if missing:
        raise KeyError(f"missing required columns: {sorted(missing)}")

    widths = frame[width_column]
    if width_column == "width_mean_m":
        widths = apply_width_bias(widths, thresholds["width_bias"])

    if "elongation" in frame.columns:
        elongations = frame["elongation"]
    elif "width_mean_m" in frame.columns:
        elongations = elongation(frame["length_m"], frame["width_mean_m"])
    else:
        raise KeyError("need either an elongation or a width_mean_m column")

    edges = coerce_bool(frame["touches_tile_edge"])

    return pd.Series(
        [
            classify_row(length, width, elong, edge, thresholds)
            for length, width, elong, edge in zip(
                frame["length_m"], widths, elongations, edges
            )
        ],
        index=frame.index,
        name="klass",
    )


def inventory_only(frame: pd.DataFrame, klass_column: str = "klass") -> pd.DataFrame:
    """Rows counted in the inventory.

    There is no in_inventory column anywhere in this project. Inventory
    membership is always derived from the label.
    """
    return frame[frame[klass_column].isin(INVENTORY_CLASSES)]


# Per-class counts of the released site run. These are published numbers; if
# this module stops reproducing them, this module is wrong, not the numbers.
EXPECTED_COUNTS = {
    FRAGMENT: 15965,
    FULL_STEM: 5240,
    EXCL_LENGTH: 855,
    EXCL_WIDTH: 784,
    EXCL_BOUNDARY: 751,
    EXCL_ELONGATION: 8,
}
EXPECTED_TOTAL = 23603
EXPECTED_INVENTORY = 21205


def verify_against_csv(csv_path: str | Path, thresholds: dict | None = None) -> dict:
    """Re-derive every label from the released CSV and compare.

    Returns a summary dict and raises AssertionError on any mismatch. This is
    the test that establishes the rules above, including their order, as the
    ones that produced the published inventory.
    """
    frame = pd.read_csv(csv_path)
    predicted = classify_frame(frame, thresholds)

    agreement = float((predicted == frame["klass"]).mean())
    counts = predicted.value_counts().to_dict()

    assert len(frame) == EXPECTED_TOTAL, f"expected {EXPECTED_TOTAL} rows, got {len(frame)}"
    assert agreement == 1.0, f"labels disagree on {(1 - agreement) * len(frame):.0f} rows"

    for label, expected in EXPECTED_COUNTS.items():
        actual = counts.get(label, 0)
        assert actual == expected, f"{label}: expected {expected}, got {actual}"

    inventory = sum(EXPECTED_COUNTS[label] for label in INVENTORY_CLASSES)
    assert inventory == EXPECTED_INVENTORY

    return {"rows": len(frame), "agreement": agreement, "counts": counts}


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: python -m cwd.classify <cwd_classified_site.csv>")
        raise SystemExit(2)

    summary = verify_against_csv(sys.argv[1])
    print(f"rows {summary['rows']:,}  agreement {summary['agreement']:.4f}")
    for label in ALL_CLASSES:
        print(f"  {label:<36} {summary['counts'].get(label, 0):>7,}")
