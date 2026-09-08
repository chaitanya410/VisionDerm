"""Segmentation engines: a dependency-free classical pipeline plus an optional U-Net."""
from __future__ import annotations

from .base import SegmentationResult, get_engine

__all__ = ["SegmentationResult", "get_engine"]
