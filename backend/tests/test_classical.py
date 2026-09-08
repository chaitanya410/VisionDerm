"""The classical pipeline should recover most of the known synthetic lesions
and respond monotonically to the sensitivity control."""
from __future__ import annotations

import numpy as np

from app.segmentation.classical import ClassicalEngine
from app.segmentation.overlay import build_overlay


def test_finds_known_lesions(synthetic_face):
    rgb, n_lesions = synthetic_face
    engine = ClassicalEngine()

    result = engine.segment(rgb, sensitivity=1.5, min_area=5, max_area=600)

    # Should find most of the 15 discs without wildly over-counting.
    assert n_lesions * 0.6 <= result.count <= n_lesions * 1.6
    assert result.mask.shape == rgb.shape[:2]
    assert result.mask.dtype == np.uint8
    assert set(np.unique(result.mask)).issubset({0, 255})
    assert result.severity_label in {"Clear", "Mild", "Moderate", "Severe"}
    for lesion in result.lesions:
        x, y, w, h = lesion.bbox
        assert w > 0 and h > 0
        assert 0 <= x < rgb.shape[1] and 0 <= y < rgb.shape[0]
        assert 0.0 <= lesion.score <= 1.0


def test_sensitivity_is_monotonic(synthetic_face):
    rgb, _ = synthetic_face
    engine = ClassicalEngine()

    low = engine.segment(rgb, sensitivity=0.8, min_area=5, max_area=600).count
    high = engine.segment(rgb, sensitivity=3.5, min_area=5, max_area=600).count

    # Higher k = stricter threshold = fewer (or equal) detections.
    assert high <= low


def test_blank_skin_is_clear():
    rgb = np.full((256, 256, 3), (205, 165, 140), dtype=np.uint8)
    result = ClassicalEngine().segment(rgb, sensitivity=2.0, min_area=8, max_area=1400)
    assert result.count <= 3  # a few noise blobs at most
    assert result.severity_label in {"Clear", "Mild"}


def test_overlay_render_shape(synthetic_face):
    rgb, _ = synthetic_face
    result = ClassicalEngine().segment(rgb, sensitivity=1.5, min_area=5, max_area=600)
    overlay = build_overlay(rgb, result, draw_boxes=True)
    assert overlay.shape == rgb.shape
    assert overlay.dtype == np.uint8
    # Overlay must differ from the original where lesions were tinted.
    assert not np.array_equal(overlay, rgb)
