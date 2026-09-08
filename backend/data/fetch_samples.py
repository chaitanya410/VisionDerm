"""Populate backend/data/samples/ with demo images.

Primary source: Wikimedia Commons (Creative Commons / public-domain photographs of
facial acne). Each download is recorded in credits.json with its source URL and
license.

Fallback: if a download fails (offline, blocked, 429), a synthetic face with
procedurally-placed reddish lesions is generated instead, so the demo, the sample
gallery, and the test-suite always have data to work with.

Usage:
    python data/fetch_samples.py            # top up to TARGET_COUNT images
    python data/fetch_samples.py --force    # wipe samples/ first
    python data/fetch_samples.py --synthetic-only
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
CREDITS_PATH = SAMPLES_DIR / "credits.json"
TARGET_COUNT = 12
USER_AGENT = (
    "AcneSegmentationDemo/1.0 (educational project; contact: local user) "
    "python-urllib"
)

# (Commons file name, human-readable license). Special:FilePath redirects to the
# actual media file; ?width= asks Commons to serve a resized JPEG/PNG.
COMMONS_FILES: list[tuple[str, str]] = [
    ("Acne vulgaris on a very oily skin.jpg", "CC BY-SA 4.0"),
    ("Teenager-with-acne.jpg", "CC BY-SA 3.0"),
    ("Pimples-human-boy.jpg", "CC BY-SA 4.0"),
    ("Pimples.jpg", "CC BY-SA 3.0"),
    ("Zits.jpg", "CC BY-SA 3.0"),
    ("Reddish zit.png", "CC BY-SA 4.0"),
    ("Botons d' djonnesse djonnete 20 ans.jpg", "CC BY-SA 4.0"),
    ("515 Acne formation.jpg", "CC BY 3.0"),
]


def _commons_url(filename: str, width: int = 1024) -> str:
    quoted = urllib.parse.quote(filename.replace(" ", "_"))
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quoted}?width={width}"


def _download(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


def _save_jpeg(data: bytes, dest: Path, max_side: int = 1024) -> None:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    if max(w, h) > max_side:
        s = max_side / max(w, h)
        img = img.resize((int(w * s), int(h * s)), Image.LANCZOS)
    img.save(dest, format="JPEG", quality=90)


def _synthetic_face(seed: int, size: int = 640) -> Image.Image:
    """A cartoonish skin-toned oval with random reddish papules. Enough structure
    for the classical pipeline and the tests to find lesions."""
    rng = np.random.default_rng(seed)
    canvas = np.full((size, size, 3), (28, 30, 36), dtype=np.uint8)  # dark background

    yy, xx = np.mgrid[0:size, 0:size]
    cy, cx = size * 0.52, size * 0.5
    ry, rx = size * 0.42, size * 0.33
    face = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0

    base = np.array([214, 170, 142]) + rng.normal(0, 5, 3)
    skin = np.clip(base + rng.normal(0, 6, (size, size, 3)), 60, 255)
    # soft vertical shading
    shade = np.linspace(1.06, 0.9, size)[:, None, None]
    skin = np.clip(skin * shade, 0, 255)
    canvas[face] = skin[face].astype(np.uint8)

    # eyes + brows so the skin gate has something non-skin to exclude
    for ex in (cx - rx * 0.42, cx + rx * 0.42):
        eye = ((yy - (cy - ry * 0.12)) ** 2 + (xx - ex) ** 2) <= (size * 0.03) ** 2
        canvas[eye] = (250, 250, 250)
        pupil = ((yy - (cy - ry * 0.12)) ** 2 + (xx - ex) ** 2) <= (size * 0.013) ** 2
        canvas[pupil] = (40, 30, 25)

    n_lesions = int(rng.integers(8, 34))
    for _ in range(n_lesions):
        for _try in range(20):
            ly = int(rng.uniform(cy - ry * 0.75, cy + ry * 0.85))
            lx = int(rng.uniform(cx - rx * 0.8, cx + rx * 0.8))
            if 0 <= ly < size and 0 <= lx < size and face[ly, lx]:
                break
        else:
            continue
        rad = int(rng.uniform(3, 8))
        blob = (yy - ly) ** 2 + (xx - lx) ** 2 <= rad**2
        redness = np.array([70, -35, -30]) * rng.uniform(0.5, 1.1)
        patch = np.clip(canvas[blob].astype(float) + redness, 0, 255)
        canvas[blob] = patch.astype(np.uint8)

    img = Image.fromarray(canvas, "RGB")
    return img


def load_credits() -> dict:
    if CREDITS_PATH.exists():
        try:
            return json.loads(CREDITS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"images": []}


def write_credits(entries: list[dict]) -> None:
    CREDITS_PATH.write_text(
        json.dumps(
            {
                "note": (
                    "Demo images. Commons photos are under the noted Creative "
                    "Commons / public-domain licenses; attribution is the file "
                    "page on Wikimedia Commons. Synthetic images are generated "
                    "locally and are unrestricted. This project is a technical "
                    "demonstration and is not a medical device."
                ),
                "images": entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="wipe samples/ first")
    ap.add_argument("--synthetic-only", action="store_true")
    ap.add_argument("--count", type=int, default=TARGET_COUNT)
    args = ap.parse_args()

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    if args.force:
        for p in SAMPLES_DIR.iterdir():
            if p.is_file():
                p.unlink()

    existing = {p.name for p in SAMPLES_DIR.iterdir() if p.is_file() and p.suffix != ".json"}
    entries: list[dict] = [e for e in load_credits()["images"] if e["filename"] in existing]
    have = len(existing)

    if not args.synthetic_only:
        for idx, (fname, lic) in enumerate(COMMONS_FILES, start=1):
            if have >= args.count:
                break
            dest = SAMPLES_DIR / f"commons_{idx:02d}.jpg"
            if dest.name in existing:
                continue
            url = _commons_url(fname)
            try:
                print(f"  downloading {fname} ...", flush=True)
                data = _download(url)
                _save_jpeg(data, dest)
                entries.append(
                    {
                        "filename": dest.name,
                        "title": fname,
                        "source": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(fname.replace(' ', '_'))}",
                        "download_url": url,
                        "license": lic,
                        "kind": "wikimedia-commons",
                    }
                )
                existing.add(dest.name)
                have += 1
            except Exception as exc:  # noqa: BLE001
                print(f"    ! failed ({exc.__class__.__name__}: {exc}); will use synthetic")

    # Top up with synthetic images.
    syn_idx = 1
    while have < args.count:
        dest = SAMPLES_DIR / f"synthetic_{syn_idx:02d}.jpg"
        if dest.name not in existing:
            _synthetic_face(seed=1000 + syn_idx).save(dest, format="JPEG", quality=90)
            entries.append(
                {
                    "filename": dest.name,
                    "title": f"Synthetic acne face #{syn_idx}",
                    "source": "generated locally by data/fetch_samples.py",
                    "download_url": None,
                    "license": "No rights reserved (synthetic)",
                    "kind": "synthetic",
                }
            )
            existing.add(dest.name)
            have += 1
        syn_idx += 1

    write_credits(entries)
    print(f"\nDone. {have} images in {SAMPLES_DIR}")
    print(f"Credits written to {CREDITS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
