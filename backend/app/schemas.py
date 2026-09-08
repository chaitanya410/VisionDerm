"""Pydantic models describing the /api/segment response contract."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ImageSize(BaseModel):
    width: int
    height: int


class Lesion(BaseModel):
    id: int
    bbox: list[int] = Field(..., description="[x, y, w, h] in pixels")
    area_px: int
    centroid: list[float] = Field(..., description="[x, y] in pixels")
    score: float = Field(..., description="0-1 confidence-like response strength")


class Severity(BaseModel):
    label: str = Field(..., description="Clear | Mild | Moderate | Severe")
    score: float = Field(..., description="0-1 combined severity index")
    note: str = "Heuristic estimate for demonstration only - not a medical diagnosis."


class SegmentParams(BaseModel):
    sensitivity: float
    min_area: int
    max_area: int


class SegmentResponse(BaseModel):
    engine: str = Field(..., description="classical | unet")
    image: ImageSize
    params: SegmentParams
    lesions: list[Lesion]
    count: int
    severity: Severity
    mask_png_base64: str = Field(..., description="Full-resolution binary mask, PNG")
    overlay_png_base64: str | None = Field(
        None,
        description=(
            "Original + translucent lesion overlay, PNG. "
            "Null when include_overlay=false."
        ),
    )
    elapsed_ms: float


class SampleInfo(BaseModel):
    id: str
    filename: str
    url: str
    source: str | None = None
    license: str | None = None
