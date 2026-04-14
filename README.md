# Fallen Tree AI-Driven Detection
AI@UGA | Spring 2026

## Overview
End-to-end computer vision pipeline using YOLOv8 and Mask R-CNN
to detect, count, and estimate volume of hurricane-damaged fallen
trees from 7,357 orthorectified drone images (62.7 GB).

Collaboration with Warnell School of Forestry and Natural Resources,
University of Georgia.

## Repository Structure
fallen-tree-detection/
├── data/
│   ├── raw/          # DO NOT COMMIT
│   ├── samples/      # sample images for testing
│   └── annotated/    # exported from Roboflow
├── src/
│   ├── detection/    # predict.py
│   ├── measurement/  # volume.py
│   ├── registration/ # dedup.py
│   └── pipeline/     # dataloader.py, reporter.py
├── notebooks/        # Jupyter EDA notebooks
├── docs/
├── run_pipeline.py
└── requirements.txt

## Setup
pip install -r requirements.txt

## Run Pipeline
python run_pipeline.py --input data/samples/ --output results/

## Dataset
7,357 orthorectified GeoTIFF images across 17 flight zones.
Captured April 26, 2025, at New York Road, Georgia.
Raw data stored separately - not in this repo.
