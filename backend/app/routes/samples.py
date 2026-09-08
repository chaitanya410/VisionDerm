"""Sample-image gallery endpoints, backed by backend/data/samples/."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import SAMPLES_DIR
from ..schemas import SampleInfo

router = APIRouter()

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _credits() -> dict[str, dict]:
    path = SAMPLES_DIR / "credits.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {entry["filename"]: entry for entry in raw.get("images", [])}


def _list_files() -> list:
    if not SAMPLES_DIR.exists():
        return []
    return sorted(
        p for p in SAMPLES_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
    )


@router.get("/samples", response_model=list[SampleInfo])
async def list_samples() -> list[SampleInfo]:
    credits = _credits()
    out: list[SampleInfo] = []
    for p in _list_files():
        meta = credits.get(p.name, {})
        out.append(
            SampleInfo(
                id=p.stem,
                filename=p.name,
                url=f"/api/samples/{p.name}",
                source=meta.get("source"),
                license=meta.get("license"),
            )
        )
    return out


@router.get("/samples/{filename}")
async def get_sample(filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename.")
    path = SAMPLES_DIR / filename
    if not path.is_file() or path.suffix.lower() not in _IMAGE_EXTS:
        raise HTTPException(404, "Sample not found.")
    return FileResponse(path)
