# Hugging Face Spaces image: one container serving both the API and the UI.
#
# Stage 1 builds the React app; stage 2 runs FastAPI and serves the build from
# frontend/dist. The repo layout is mirrored inside the image because
# backend/app/config.py resolves FRONTEND_DIST relative to the backend package.

FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# requirements.txt (version floors), not requirements.lock.txt - that lock was
# resolved against Python 3.14 on Windows and does not transfer to this image.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend /build/dist ./frontend/dist

# Populate the sample gallery. Downloads CC-licensed photos from Wikimedia and
# falls back to locally generated synthetic images; a network failure here must
# not fail the build.
RUN cd backend && python data/fetch_samples.py || \
    echo "WARNING: sample fetch failed; gallery will be empty"

# Spaces expects a non-root user owning the app directory.
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--app-dir", "backend"]
