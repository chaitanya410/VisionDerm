"""Runtime configuration and shared paths."""
from __future__ import annotations

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
SAMPLES_DIR = DATA_DIR / "samples"
MODELS_DIR = BACKEND_DIR / "models"
UNET_CHECKPOINT = MODELS_DIR / "unet.pt"

# Built single-page app. Present in the Docker image and after `npm run build`;
# absent during ordinary backend-only development, where Vite serves the UI.
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

# Upload guard rails
MAX_UPLOAD_BYTES = 12 * 1024 * 1024  # 12 MB
MAX_IMAGE_SIDE = 1600  # images larger than this are downscaled before processing
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

# Default segmentation parameters (overridable per request from the UI)
DEFAULT_SENSITIVITY = 2.5   # threshold = mean + k * std  (higher k -> fewer detections)
DEFAULT_MIN_AREA = 10       # px^2
DEFAULT_MAX_AREA = 1600     # px^2

# CORS origins for the Vite dev server
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
