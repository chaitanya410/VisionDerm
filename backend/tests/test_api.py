"""End-to-end API contract checks via FastAPI's TestClient."""
from __future__ import annotations

import base64
import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _png_bytes(rgb: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["default_engine"] in {"classical", "unet"}


def test_segment_contract(synthetic_face):
    rgb, _ = synthetic_face
    files = {"image": ("face.png", _png_bytes(rgb), "image/png")}
    data = {"sensitivity": "1.5", "min_area": "5", "max_area": "600"}

    r = client.post("/api/segment", files=files, data=data)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["engine"] in {"classical", "unet"}
    assert body["image"] == {"width": rgb.shape[1], "height": rgb.shape[0]}
    assert body["count"] == len(body["lesions"])
    assert body["count"] > 0
    assert body["severity"]["label"] in {"Clear", "Mild", "Moderate", "Severe"}
    assert body["params"]["sensitivity"] == pytest.approx(1.5)

    for key in ("mask_png_base64", "overlay_png_base64"):
        raw = base64.b64decode(body[key])
        img = Image.open(io.BytesIO(raw))
        assert img.size == (rgb.shape[1], rgb.shape[0])

    mask_img = Image.open(io.BytesIO(base64.b64decode(body["mask_png_base64"])))
    assert mask_img.mode == "L"


def test_rejects_non_image():
    files = {"image": ("x.txt", b"not an image", "text/plain")}
    r = client.post("/api/segment", files=files)
    assert r.status_code == 415


def test_rejects_corrupt_image():
    files = {"image": ("x.png", b"\x89PNG\r\n\x1a\n garbage", "image/png")}
    r = client.post("/api/segment", files=files)
    assert r.status_code == 422


def test_samples_endpoint():
    r = client.get("/api/samples")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_segment_can_omit_overlay(synthetic_face):
    rgb, _ = synthetic_face
    files = {"image": ("face.png", _png_bytes(rgb), "image/png")}
    data = {"include_overlay": "false"}

    r = client.post("/api/segment", files=files, data=data)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["overlay_png_base64"] is None
    # The mask is still returned - the frontend renders from it.
    assert isinstance(body["mask_png_base64"], str)
    assert len(body["mask_png_base64"]) > 0


def test_spa_root_serves_index_when_frontend_is_built():
    from app.config import FRONTEND_DIST

    if not FRONTEND_DIST.is_dir():
        pytest.skip("frontend/dist not present - run `npm run build`")

    r = client.get("/")
    assert r.status_code == 200
    assert "<!doctype html" in r.text.lower()


def test_unknown_api_path_still_404s():
    """The SPA catch-all must never swallow unmatched /api routes."""
    r = client.get("/api/definitely-not-a-route")
    assert r.status_code == 404


def test_segment_includes_overlay_by_default(synthetic_face):
    rgb, _ = synthetic_face
    files = {"image": ("face.png", _png_bytes(rgb), "image/png")}

    r = client.post("/api/segment", files=files)
    assert r.status_code == 200, r.text
    assert isinstance(r.json()["overlay_png_base64"], str)
