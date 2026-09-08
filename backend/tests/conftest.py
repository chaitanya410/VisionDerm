"""Shared fixtures: a synthetic face with a known number of reddish lesions."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def synthetic_face():
    """Return (rgb_uint8, n_lesions). Skin-toned oval on a dark ground with
    `n_lesions` well-separated red discs of radius ~5 px."""
    rng = np.random.default_rng(42)
    size = 512
    img = np.full((size, size, 3), (25, 27, 33), dtype=np.uint8)

    yy, xx = np.mgrid[0:size, 0:size]
    cy, cx = size * 0.5, size * 0.5
    ry, rx = size * 0.42, size * 0.34
    face = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0
    skin = np.clip(np.array([210, 168, 140]) + rng.normal(0, 4, (size, size, 3)), 60, 255)
    img[face] = skin[face].astype(np.uint8)

    n_lesions = 15
    placed = 0
    centers: list[tuple[int, int]] = []
    while placed < n_lesions:
        ly = int(rng.uniform(cy - ry * 0.6, cy + ry * 0.7))
        lx = int(rng.uniform(cx - rx * 0.65, cx + rx * 0.65))
        if not face[ly, lx]:
            continue
        if any((ly - py) ** 2 + (lx - px) ** 2 < 34**2 for py, px in centers):
            continue
        centers.append((ly, lx))
        blob = (yy - ly) ** 2 + (xx - lx) ** 2 <= 5**2
        img[blob] = np.clip(img[blob].astype(int) + np.array([65, -30, -25]), 0, 255).astype(np.uint8)
        placed += 1

    return img, n_lesions
