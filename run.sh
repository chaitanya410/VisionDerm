#!/usr/bin/env bash
# Starts the FastAPI backend and the Vite frontend together (macOS / Linux).
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend="$root/backend"
frontend="$root/frontend"
venv_py="$backend/.venv/bin/python"

if [ ! -x "$venv_py" ]; then
  echo "Creating backend virtualenv..."
  python3 -m venv "$backend/.venv"
  "$venv_py" -m pip install --upgrade pip
  "$venv_py" -m pip install -r "$backend/requirements.txt"
fi

if ! ls "$backend"/data/samples/*.jpg >/dev/null 2>&1; then
  echo "Fetching sample images..."
  (cd "$backend" && "$venv_py" data/fetch_samples.py)
fi

if [ ! -d "$frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$frontend" && npm install)
fi

echo "Starting backend on http://localhost:8000 ..."
(cd "$backend" && "$venv_py" -m uvicorn app.main:app --reload --port 8000) &
be=$!
echo "Starting frontend on http://localhost:5173 ..."
(cd "$frontend" && npm run dev) &
fe=$!

trap 'kill $be $fe 2>/dev/null || true' EXIT INT TERM
echo
echo "Both running. Press Ctrl+C to stop."
wait
