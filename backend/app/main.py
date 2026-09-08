"""FastAPI application entry point.

Run:  uvicorn app.main:app --reload   (from the backend/ directory)
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import CORS_ORIGINS, FRONTEND_DIST, UNET_CHECKPOINT
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


# Serve the built SPA when it exists, so one origin hosts both the API and the
# UI (this is how the app runs on Hugging Face Spaces). During local backend
# development there is no dist/ and Vite serves the UI instead, so these routes
# simply are not registered. Registered last so every /api route wins first.
if FRONTEND_DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        # Never let the catch-all answer for an unmatched API route - that would
        # turn a 404 into a 200 with an HTML body and mask real bugs.
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not Found")

        candidate = (FRONTEND_DIST / full_path).resolve()
        if (
            full_path
            and candidate.is_file()
            and candidate.is_relative_to(FRONTEND_DIST.resolve())
        ):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
