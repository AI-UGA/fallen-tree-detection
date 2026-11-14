"""Privacy scan for published assets. Called by scripts/preflight.sh.

Prints one line per problem and nothing when clean. Checks tracked files under
docs/ and poster/:

- images (PNG, JPEG, WebP, TIFF) for GPS IFD, GeoTIFF tags or XMP location data
- text files for decimal latitude/longitude pairs in the Georgia range, the
  digit run 36665, and the site's road name
"""
from __future__ import annotations

import re
import subprocess
import sys

try:
    from PIL import Image
except ImportError:  # the image check needs Pillow; say so instead of passing silently
    print("Pillow is not installed; image metadata was not checked")
    sys.exit(0)

GEO_TAGS = {33550, 33922, 34264, 34735, 34736, 34737}
IMG = (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")
TEXT = (".html", ".md", ".json", ".geojson", ".csv", ".js", ".css", ".py", ".txt")
LATLON = re.compile(r"\b3[0-4]\.\d{4,}\b[^0-9\n]{1,8}-8[0-5]\.\d{4,}\b")
PATTERNS = [(re.compile(r"36665"), "digit run 36665"),
            (re.compile(r"new\s+york\s+r(oa)?d", re.I), "site road name"),
            (LATLON, "latitude/longitude pair")]

files = subprocess.run(["git", "ls-files", "docs", "poster"], capture_output=True, text=True).stdout.split()
for f in files:
    low = f.lower()
    if low.endswith(IMG):
        try:
            im = Image.open(f)
        except Exception as e:  # unreadable image is itself worth flagging
            print(f"{f}: cannot open ({e})")
            continue
        exif = im.getexif()
        if 34853 in exif:
            print(f"{f}: GPS metadata")
        tags = getattr(im, "tag_v2", {})
        if GEO_TAGS & set(tags):
            print(f"{f}: GeoTIFF tags")
        xmp = im.info.get("xmp") or im.info.get("XML:com.adobe.xmp") or b""
        if isinstance(xmp, str):
            xmp = xmp.encode()
        if re.search(rb"GPS(Latitude|Longitude)", xmp):
            print(f"{f}: XMP GPS data")
    elif low.endswith(TEXT):
        try:
            text = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for rx, label in PATTERNS:
            m = rx.search(text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                print(f"{f}:{line}: {label}")
