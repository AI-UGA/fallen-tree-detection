"""Coarse woody debris inventory from UAV imagery.

Modules:
    paths             locate the project data root by content
    volume_pipeline   per-object measurement and frustum volume
    classify          assign inventory and exclusion labels
    evaluate          unified pycocotools scoring of both detectors
    figures           manuscript figure generation
"""

__version__ = "1.0.0"
