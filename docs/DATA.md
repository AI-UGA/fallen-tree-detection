# Data availability

The study site is privately owned land. The imagery and all georeferenced
products are therefore **not** publicly released. This document states exactly
what is released, what is not, and how to request the rest.

This file is the repository's side of the paper's Data Availability Statement.
The two must agree.

## Released publicly

| Item | Where | Licence |
|---|---|---|
| Source code in this repository | GitHub | MIT |
| Model weights, Mask R-CNN and YOLOv8s-seg | Zenodo, DOI below | CC BY 4.0 |
| Annotation set, georeferencing removed | Zenodo, DOI below | CC BY 4.0 |
| A small number of example image crops | Zenodo, DOI below | CC BY 4.0 |

Zenodo DOI: `[to be inserted on submission]`

The annotation deposit carries the instance polygons with all georeferencing
stripped. It does not allow the site to be located.

## Not released

- The orthomosaic, and the 76 GeoTIFF tiles derived from it.
- Any georeferenced product, including the digital terrain, surface and canopy
  height models.
- Per-object measurement and inventory tables, because they carry UTM
  coordinates for every detected object in `centroid_easting` and
  `centroid_northing`.
- Precise site coordinates. The paper gives the county only.

## Requesting access

Requests for the full dataset should be directed to the corresponding author,
Roger C. Lowe III, Warnell School of Forestry and Natural Resources,
University of Georgia. Access decisions rest with the landowner and the
corresponding author, not with this repository.

## If you are releasing a derived file

Two checks, both of which have to pass:

1. Remove `centroid_easting` and `centroid_northing`. They are UTM coordinates
   (EPSG:26917, UTM zone 17N) of each object.
2. Check tile identifiers. Internal tile filenames follow the pattern
   `<sitename>_<date>_ortho-R-C`, where the site name component is a road
   name. Released filenames use the neutral form `tile-R-C` instead, because a
   road name plus a county plus an acquisition date is enough to locate a
   private parcel, which would defeat the purpose of withholding the
   coordinates.

`scripts/preflight.sh` checks for both of these, plus hardcoded Drive paths,
email addresses, credentials, oversized files, superseded numbers and notebook
outputs. Run it before every commit.

## Reproducing without the imagery

The measurement, classification and evaluation code runs on any COCO-format
predictions file, so the pipeline can be exercised on other imagery. What
cannot be reproduced without the tiles is the site-wide inventory itself.

`src/cwd/classify.py` is the exception: it re-derives every inventory label
from a released measurement table and checks the result against the published
per-class counts, so the classification rules can be verified independently of
the imagery. See `docs/REPRODUCE.md`.
