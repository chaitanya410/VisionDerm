"""Engine protocol + result container + engine selection with graceful fallback."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


@dataclass
class LesionRegion:
    id: int
    bbox: tuple[int, int, int, int]  # x, y, w, h
    area_px: int
    centroid: tuple[float, float]  # x, y
    score: float


@dataclass
class SegmentationResult:
    engine: str
    mask: np.ndarray  # uint8 {0,255}, same HxW as the (possibly downscaled) input
    lesions: list[LesionRegion] = field(default_factory=list)
    severity_label: str = "Clear"
    severity_score: float = 0.0

    @property
    def count(self) -> int:
        return len(self.lesions)


class SegmentationEngine(Protocol):
    name: str

    def segment(
        self,
        image_rgb: np.ndarray,
        *,
        sensitivity: float,
        min_area: int,
        max_area: int,
    ) -> SegmentationResult:
        ...


_UNET_ENGINE: SegmentationEngine | None = None
_CLASSICAL_ENGINE: SegmentationEngine | None = None


def get_engine(prefer: str = "auto") -> SegmentationEngine:
    """Return an engine.

    prefer="auto"      -> U-Net if a checkpoint + torch are available, else classical
    prefer="classical" -> always the classical pipeline
    prefer="unet"      -> U-Net, raising if unavailable
    """
    global _UNET_ENGINE, _CLASSICAL_ENGINE

    if prefer in ("auto", "unet"):
        if _UNET_ENGINE is None:
            try:
                from .unet import UNetEngine

                _UNET_ENGINE = UNetEngine()
            except Exception:  # noqa: BLE001 - any import/checkpoint problem -> fallback
                _UNET_ENGINE = None
        if _UNET_ENGINE is not None:
            return _UNET_ENGINE
        if prefer == "unet":
            raise RuntimeError(
                "U-Net engine unavailable. Install requirements-ml.txt and place a "
                "checkpoint at backend/models/unet.pt."
            )

    if _CLASSICAL_ENGINE is None:
        from .classical import ClassicalEngine

        _CLASSICAL_ENGINE = ClassicalEngine()
    return _CLASSICAL_ENGINE
