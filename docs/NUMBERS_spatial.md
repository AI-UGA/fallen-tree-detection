# Spatial statistics (draft, awaiting approval)

Status: approved by the author on 2026-11-14. On the poster: Moran's I 0.378, p = 0.001,
hot spots 14% of area holding 38% of wood.

Source: `docs/assets/site.json` (site_run_v3), 300 quadrants. Script:
`poster/spatial_stats.py`; full per-quadrant output in
`poster/figures/spatial_stats.json`.

## Method

- Variable: wood volume per hectare in each quadrant,
  (full stem volume + fragment volume) / quadrant area. Quadrants with no
  detections enter as 0 (54 quadrants). Clipped edge quadrants use their own
  smaller area.
- Geometry: each quadrant drawn as a unit square on the anonymized row/column
  grid. No coordinates are used.
- Weights: queen contiguity (shared edge or corner). 300 quadrants, no
  islands, mean 7.21 neighbors.
- Global Moran's I: queen weights, row-standardized, 999 conditional
  permutations, seed 20261114 (PySAL esda 2.10.0, libpysal 4.15.1).
- Getis-Ord Gi*: binary queen weights with each quadrant included in its own
  neighborhood (self-weight 1), then row-standardized; 999 conditional
  permutations, two-sided pseudo p-values, same seed. esda draws these
  permutations in numba, so the seed is passed to `G_Local(seed=...)` with
  one thread, after one discarded warm-up call (the first call in a process
  gives a different draw). Two runs give identical output.
- Gi* classes: hot or cold by the sign of z; confidence 99 / 95 / 90 percent
  for pseudo p of at most 0.01 / 0.05 / 0.10; otherwise not significant.

## Results

### Global Moran's I

| Quantity | Value |
|---|---|
| I | 0.378 |
| Expected I under randomness | -0.0033 |
| z (permutation) | 12.10 |
| Pseudo p (999 permutations) | 0.001, the smallest possible with 999 permutations |
| z (normal approximation) | 12.29 |

Reading: quadrants with high wood volume sit next to other high quadrants
far more than chance would produce. The clustering is real.

### Getis-Ord Gi*

| Class | Quadrants |
|---|---|
| Hot spot, 99 percent | 17 |
| Hot spot, 95 percent | 12 |
| Hot spot, 90 percent | 13 |
| Not significant | 202 |
| Cold spot, 90 percent | 12 |
| Cold spot, 95 percent | 23 |
| Cold spot, 99 percent | 21 |

| Summary | Hot spots (all levels) | Cold spots (all levels) |
|---|---|---|
| Quadrants | 42 | 56 |
| Area | 67.1 ha, 14.0 percent of imaged area | 18.8 percent of imaged area |
| Share of total wood volume | 38.2 percent | 1.6 percent |

## Caveats

- Multiple testing: Gi* tests 300 overlapping neighborhoods. With a false
  discovery rate of 0.05 (threshold p of at most 0.0055), 17 hot and 16 cold
  quadrants remain. The 90 and 95 percent classes are exploratory.
- Permutation noise: seeds 1, 2 and 3 give 43, 45 and 42 hot and 57, 56 and
  58 cold quadrants at the 90 percent level, against 42 and 56 for the chosen
  seed. Moran's I and its p-value do not change.
- Normal-theory p-values from the Gi* z-scores flag far fewer quadrants than
  the permutation test. Volume per quadrant is strongly skewed (54 zeros, a
  long upper tail), so the normal approximation is unreliable here and the
  permutation p-values are used.
- The variable is image-based volume, not field-validated (see NUMBERS.md),
  and the grid is the analysis unit, so results depend on the 127 m quadrant
  size (modifiable areal unit problem).

## Poster wording (approved)

- Takeaway caption for "Is the clustering real?": "**Yes. Wood volume is
  strongly clustered** (Moran's I 0.378, p = 0.001). Hot spots cover 14% of
  the area and hold 38% of the wood."
- Conclusions: "wood is spatially clustered in a few hot spots."

## Web map classes

Written by `scripts/build_web_layers.py` from `docs/assets/site.json`.
Quadrants with no wood form their own class; the rest are split into five
quantile classes (equal numbers of quadrants). Stem share uses fixed
20-point steps.

| Layer | Class breaks |
|---|---|
| Wood volume (m3/ha) | 0, 5.5, 19.1, 30.9, 55.5, 268.8 |
| Piece density (pieces/ha) | 0, 11.2, 32.9, 55.2, 84.3, 203.4 |
| Full stem share of volume (%) | 0, 20, 40, 60, 80, 100 |

## Permutation histogram on the website

The "How the test works" chart in `docs/index.html` is a static SVG drawn from
a separate numpy run, not from esda. Method: `vol_ha` for the 300 quadrants in
`docs/assets/data/quadrants.json`; queen contiguity built from grid row and
column (edge or corner neighbors); row-standardized weights; 999 random
permutations of the values with `numpy.random.default_rng(20261114)`.

| Quantity | Value |
|---|---|
| Recomputed Moran's I | 0.378 (0.3779) |
| Shuffled Moran's I, range | -0.089 to 0.135 |
| Shuffles at or above the real map | 0 of 999, so pseudo p = 0.001 |

The chart bins the shuffled values in steps of 0.01 from -0.1 to 0.4.
