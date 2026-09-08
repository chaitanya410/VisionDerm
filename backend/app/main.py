"""FastAPI application entry point.

Run:  uvicorn app.main:app --reload   (from the backend/ directory)
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, UNET_CHECKPOINT
from .routes import samples, segment

app = FastAPI(
    title="Acne Image Segmentation API",
    version="1.0.0",
    description=(
        "Segments acne lesions in facial photos and returns per-lesion masks, a "
        "count, a heuristic severity grade, and rendered overlays. "
        "Demonstration only - not a medical device."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(segment.router, prefix="/api", tags=["segmentation"])
app.include_router(samples.router, prefix="/api", tags=["samples"])


@app.get("/api/health", tags=["meta"])
async def health() -> dict:
    return {
        "status": "ok",
        "unet_checkpoint_present": UNET_CHECKPOINT.exists(),
        "default_engine": "unet" if UNET_CHECKPOINT.exists() else "classical",
    }
