"""Prepare raster tiles for the segmentation model.

Rasterio reads GeoTIFF bands in RGB order, and so does matplotlib. Ultralytics
treats a numpy array passed to ``model.predict`` as BGR, the OpenCV convention,
and converts it to RGB internally, so arrays must be converted first.

Passing a file path instead of an array avoids the problem, because the
library then reads the file itself. Everything that hands an array to the
model should go through to_model_input().
"""

from __future__ import annotations

import numpy as np


def to_model_input(rgb: np.ndarray) -> np.ndarray:
    """Return a contiguous BGR copy of an H x W x 3 RGB array.

    Raises ValueError for anything that is not a three-channel image, so that
    a four-band raster (RGB plus alpha) cannot slip through with the alpha band
    read as a colour channel.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"expected an H x W x 3 RGB array, got shape {rgb.shape}")
    return np.ascontiguousarray(rgb[..., ::-1])


if __name__ == "__main__":
    probe = np.zeros((2, 2, 3), dtype=np.uint8)
    probe[..., 0] = 255  # pure red in RGB
    out = to_model_input(probe)
    assert out[0, 0, 2] == 255 and out[0, 0, 0] == 0, "red must land in the last channel"
    assert out.flags["C_CONTIGUOUS"]
    print("to_model_input ok")
