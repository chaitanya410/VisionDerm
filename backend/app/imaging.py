"""Decode uploaded bytes to an RGB ndarray, with EXIF orientation + size clamping."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

from .config import MAX_IMAGE_SIDE


def decode_image(data: bytes, max_side: int = MAX_IMAGE_SIDE) -> np.ndarray:
    """Return a contiguous uint8 HxWx3 RGB array. Raises ValueError on bad input."""
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Could not decode image: {exc}") from exc

    w, h = img.size
    longest = max(w, h)
    if longest > max_side:
        scale = max_side / longest
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

    return np.ascontiguousarray(np.asarray(img, dtype=np.uint8))
