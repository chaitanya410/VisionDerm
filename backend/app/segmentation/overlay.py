"""Render helpers: build the translucent overlay PNG and encode masks to base64 PNG."""
from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from PIL import Image

from .base import SegmentationResult

_OVERLAY_RGB = (255, 60, 60)
_BOX_RGB = (255, 210, 60)


def _png_b64(arr: np.ndarray) -> str:
    """Encode an HxW (grayscale) or HxWx3 (RGB) uint8 array as base64 PNG."""
    mode = "L" if arr.ndim == 2 else "RGB"
    buf = io.BytesIO()
    Image.fromarray(arr, mode=mode).save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def mask_to_base64(mask: np.ndarray) -> str:
    return _png_b64(np.ascontiguousarray(mask.astype(np.uint8)))


def build_overlay(
    image_rgb: np.ndarray,
    result: SegmentationResult,
    *,
    alpha: float = 0.45,
    draw_boxes: bool = True,
) -> np.ndarray:
    """Original image with lesion pixels tinted red and optional bounding boxes."""
    out = np.ascontiguousarray(image_rgb[:, :, :3].astype(np.uint8)).copy()
    m = result.mask > 0
    if m.any():
        tint = np.zeros_like(out)
        tint[m] = _OVERLAY_RGB
        out[m] = cv2.addWeighted(out[m], 1.0 - alpha, tint[m], alpha, 0.0)

        contours, _ = cv2.findContours(
            (m.astype(np.uint8) * 255), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(out, contours, -1, _OVERLAY_RGB, 1)

    if draw_boxes:
        for lesion in result.lesions:
            x, y, w, h = lesion.bbox
            pad = 2
            cv2.rectangle(
                out,
                (max(0, x - pad), max(0, y - pad)),
                (x + w + pad, y + h + pad),
                _BOX_RGB,
                1,
            )
    return out


def overlay_to_base64(
    image_rgb: np.ndarray, result: SegmentationResult, **kwargs
) -> str:
    return _png_b64(build_overlay(image_rgb, result, **kwargs))
