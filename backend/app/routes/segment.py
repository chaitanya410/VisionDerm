"""POST /api/segment - run acne-lesion segmentation on an uploaded image."""
from __future__ import annotations

import time

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import (
    ALLOWED_CONTENT_TYPES,
    DEFAULT_MAX_AREA,
    DEFAULT_MIN_AREA,
    DEFAULT_SENSITIVITY,
    MAX_UPLOAD_BYTES,
)
from ..imaging import decode_image
from ..schemas import (
    ImageSize,
    Lesion,
    SegmentParams,
    SegmentResponse,
    Severity,
)
from ..segmentation import get_engine
from ..segmentation.overlay import mask_to_base64, overlay_to_base64

router = APIRouter()


@router.post("/segment", response_model=SegmentResponse)
async def segment(
    image: UploadFile = File(...),
    sensitivity: float = Form(DEFAULT_SENSITIVITY),
    min_area: int = Form(DEFAULT_MIN_AREA),
    max_area: int = Form(DEFAULT_MAX_AREA),
    engine: str = Form("auto"),
    draw_boxes: bool = Form(True),
) -> SegmentResponse:
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(415, f"Unsupported content type: {image.content_type}")

    data = await image.read()
    if not data:
        raise HTTPException(400, "Empty upload.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image too large (max 12 MB).")

    try:
        rgb = decode_image(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    sensitivity = float(min(max(sensitivity, 0.2), 5.0))
    min_area = int(min(max(min_area, 1), 5000))
    max_area = int(min(max(max_area, min_area + 1), 200_000))
    if engine not in ("auto", "classical", "unet"):
        engine = "auto"

    try:
        eng = get_engine(prefer=engine)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc

    started = time.perf_counter()
    result = eng.segment(
        rgb, sensitivity=sensitivity, min_area=min_area, max_area=max_area
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

    h, w = rgb.shape[:2]
    return SegmentResponse(
        engine=result.engine,
        image=ImageSize(width=w, height=h),
        params=SegmentParams(
            sensitivity=sensitivity, min_area=min_area, max_area=max_area
        ),
        lesions=[
            Lesion(
                id=l.id,
                bbox=list(l.bbox),
                area_px=l.area_px,
                centroid=list(l.centroid),
                score=l.score,
            )
            for l in result.lesions
        ],
        count=result.count,
        severity=Severity(label=result.severity_label, score=result.severity_score),
        mask_png_base64=mask_to_base64(result.mask),
        overlay_png_base64=overlay_to_base64(rgb, result, draw_boxes=draw_boxes),
        elapsed_ms=elapsed_ms,
    )
