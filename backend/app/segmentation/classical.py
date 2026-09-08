"""Classical acne-lesion segmentation.

Pipeline (see project README for the rationale):
  1. Estimate the skin region (YCrCb + HSV gate) so hair/background/eyes are ignored.
  2. Work in CIE L*a*b*. Acne papules/pustules sit locally high on a* (redness)
     and often locally low on L* (a small shadowed bump).
  3. Build a "redness excess" map  = a* - large-median-blur(a*)   and a
     "darkness excess" map = large-median-blur(L*) - L*.
  4. response = normalized(redness_excess) + 0.5 * normalized(darkness_excess),
     restricted to the skin mask.
  5. Threshold at  mean + sensitivity * std  over skin pixels.
  6. Morphological open/close, then connected-component analysis with area and
     shape gates (drop wrinkles, specular highlights, large blotches).
  7. Grade severity from lesion count + fraction of skin area involved.

Pure NumPy + OpenCV + scikit-image. Deterministic. ~30-80 ms for a 1000px image.
"""
from __future__ import annotations

import os

import cv2
import numpy as np
from skimage.measure import label, regionprops

_FACE_CASCADE: "cv2.CascadeClassifier | None" = None


def _face_cascade() -> "cv2.CascadeClassifier | None":
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        clf = cv2.CascadeClassifier(path)
        _FACE_CASCADE = clf if not clf.empty() else cv2.CascadeClassifier()
    return None if _FACE_CASCADE.empty() else _FACE_CASCADE


def _face_region(image_rgb: np.ndarray) -> np.ndarray | None:
    """Boolean mask of the largest detected face, dilated to include the whole
    cheek/forehead area. Returns None if no face is found (pipeline then relies on
    the colour-based skin gate alone)."""
    clf = _face_cascade()
    if clf is None:
        return None
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    h, w = gray.shape
    faces = clf.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(max(40, w // 12),) * 2
    )
    if len(faces) == 0:
        return None
    x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
    # Ignore a tiny spurious hit, but still gate on a modest-sized face so that
    # background (foliage, clothing) in wide shots is excluded.
    if (fw * fh) < 0.03 * (w * h):
        return None
    # Expand: foreheads and jaws sit outside the Haar box.
    ex, ey = int(fw * 0.18), int(fh * 0.28)
    x0, y0 = max(0, x - ex), max(0, y - ey)
    x1, y1 = min(w, x + fw + ex), min(h, y + fh + ey)
    mask = np.zeros((h, w), dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask

from .base import LesionRegion, SegmentationResult


def _skin_mask(image_rgb: np.ndarray) -> np.ndarray:
    """Boolean skin estimate. Falls back to 'whole image' if the gate is too tight."""
    bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]

    skin = (
        (cr >= 133) & (cr <= 183)
        & (cb >= 77) & (cb <= 127)
        & (s >= 20) & (s <= 230)
        & ((h <= 25) | (h >= 160))
    )

    skin = skin.astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    skin = cv2.morphologyEx(skin, cv2.MORPH_CLOSE, kernel, iterations=2)
    skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, kernel, iterations=1)

    # Keep only the largest blob (the face), then fill it.
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(skin, connectivity=8)
    if n > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        skin = np.where(lbl == largest, 255, 0).astype(np.uint8)
        contours, _ = cv2.findContours(skin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        skin = np.zeros_like(skin)
        cv2.drawContours(skin, contours, -1, 255, thickness=cv2.FILLED)

    bool_mask = skin > 0
    if bool_mask.mean() < 0.06:  # gate failed (odd lighting / non-face) -> use all pixels
        bool_mask = np.ones(image_rgb.shape[:2], dtype=bool)
    return bool_mask


def _drop_small(mask: np.ndarray, min_size: int) -> np.ndarray:
    """Remove connected components with fewer than `min_size` pixels."""
    lbl = label(mask)
    if lbl.max() == 0:
        return mask
    counts = np.bincount(lbl.ravel())
    keep = np.where(counts >= min_size)[0]
    keep = keep[keep != 0]
    return np.isin(lbl, keep)


def _norm(x: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Robust 2-98 percentile normalization to [0,1] using only masked pixels."""
    vals = x[m]
    if vals.size == 0:
        return np.zeros_like(x, dtype=np.float32)
    lo, hi = np.percentile(vals, [2, 98])
    if hi - lo < 1e-6:
        return np.zeros_like(x, dtype=np.float32)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


class ClassicalEngine:
    name = "classical"

    def segment(
        self,
        image_rgb: np.ndarray,
        *,
        sensitivity: float,
        min_area: int,
        max_area: int,
    ) -> SegmentationResult:
        image_rgb = np.ascontiguousarray(image_rgb[:, :, :3])
        h, w = image_rgb.shape[:2]
        skin = _skin_mask(image_rgb)
        face = _face_region(image_rgb)
        if face is not None:
            skin &= face  # ignore hair, clothing, autumn leaves, background

        lab = cv2.cvtColor(cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2LAB)
        L = lab[:, :, 0].astype(np.float32)
        A = lab[:, :, 1].astype(np.float32)

        # Denoise first so single-pixel sensor noise never becomes a "lesion".
        A_s = cv2.bilateralFilter(A, d=5, sigmaColor=15, sigmaSpace=5)
        L_s = cv2.bilateralFilter(L, d=5, sigmaColor=15, sigmaSpace=5)

        # (a) Local top-hat on a* isolates small, rounded, redder-than-surroundings
        #     bumps *independently of* any broad regional flush - this is what
        #     catches inflamed papules sitting on an already-pink cheek.
        lesion_r = int(np.clip(min(h, w) / 45, 4, 22))
        se = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (2 * lesion_r + 1, 2 * lesion_r + 1)
        )
        redness_tophat = cv2.morphologyEx(A_s, cv2.MORPH_TOPHAT, se)

        # (b) Cheek-scale median background catches larger patchy lesions.
        k = max(11, (min(h, w) // 10) | 1)
        A_bg = cv2.medianBlur(A.astype(np.uint8), k).astype(np.float32)
        redness_excess = np.clip(A_s - A_bg, 0, None)   # CIE a* units

        # Reference skin colour (robust to lesions/shadow via the median).
        if skin.any():
            skin_a_med = float(np.median(A_s[skin]))
            skin_L_med = float(np.median(L_s[skin]))
        else:
            skin_a_med, skin_L_med = float(np.median(A_s)), float(np.median(L_s))

        # Beard stubble / hair / cast shadow is *dark* but not notably red - damp
        # the response wherever a pixel is much darker than typical skin.
        not_shadow = (L_s > 0.55 * skin_L_med).astype(np.float32)

        response = (
            _norm(redness_tophat, skin) + 0.6 * _norm(redness_excess, skin)
        ) * not_shadow
        response = cv2.GaussianBlur(response, (0, 0), sigmaX=1.6)
        response[~skin] = 0.0

        skin_vals = response[skin]
        mu = float(skin_vals.mean()) if skin_vals.size else 0.0
        sigma = float(skin_vals.std()) if skin_vals.size else 0.0
        thresh = mu + sensitivity * sigma

        # Absolute contrast floor: a genuine lesion is a few a* units redder than
        # its immediate surroundings on at least one scale.
        abs_floor = max(2.5, 7.0 - sensitivity)
        redder = np.maximum(redness_tophat, redness_excess)
        candidate = (response > thresh) & skin & (redder >= abs_floor)

        binary = candidate.astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        binary = _drop_small(binary > 0, min_size=max(min_area, 10))
        binary = binary.astype(np.uint8) * 255

        # Cap the number of accepted regions so a pathological frame can't return
        # a multi-thousand-entry payload; keep the strongest responses.
        max_lesions = 400

        raw: list[tuple[LesionRegion, int]] = []
        lbl = label(binary > 0)
        for region in regionprops(lbl, intensity_image=response):
            area = int(region.area)
            if area < min_area or area > max_area:
                continue
            # Shape gates: acne lesions are roundish and solid.
            if region.eccentricity > 0.92:
                continue
            if region.solidity < 0.5:
                continue
            minr, minc, maxr, maxc = region.bbox
            bh, bw = maxr - minr, maxc - minc
            if max(bh, bw) > 0 and min(bh, bw) / max(bh, bw) < 0.28:
                continue

            # Colour gate: the region must actually be redder than reference skin
            # and must not be shadow-dark (hair, deep crease).
            rr, cc = region.coords[:, 0], region.coords[:, 1]
            region_a = float(A_s[rr, cc].mean())
            region_L = float(L_s[rr, cc].mean())
            if region_a - skin_a_med < abs_floor * 0.6:
                continue
            if region_L < 0.5 * skin_L_med:
                continue

            cy, cx = region.centroid
            score = float(np.clip(region.intensity_mean, 0.0, 1.0))
            raw.append(
                (
                    LesionRegion(
                        id=0,
                        bbox=(int(minc), int(minr), int(bw), int(bh)),
                        area_px=area,
                        centroid=(round(float(cx), 1), round(float(cy), 1)),
                        score=round(score, 3),
                    ),
                    int(region.label),
                )
            )

        raw.sort(key=lambda t: t[0].score, reverse=True)
        raw = raw[:max_lesions]

        lesions: list[LesionRegion] = []
        clean = np.zeros((h, w), dtype=np.uint8)
        for new_id, (lesion, region_label) in enumerate(raw, start=1):
            lesion.id = new_id
            lesions.append(lesion)
            clean[lbl == region_label] = 255

        severity_label, severity_score = _grade(
            count=len(lesions),
            lesion_area=int((clean > 0).sum()),
            skin_area=int(skin.sum()),
        )

        return SegmentationResult(
            engine=self.name,
            mask=clean,
            lesions=lesions,
            severity_label=severity_label,
            severity_score=severity_score,
        )


def _grade(*, count: int, lesion_area: int, skin_area: int) -> tuple[str, float]:
    """GAGS-inspired heuristic band. Not a validated clinical score."""
    involvement = (lesion_area / skin_area) if skin_area > 0 else 0.0
    # Count dominates; involvement nudges it.
    idx = min(1.0, count / 45.0) * 0.75 + min(1.0, involvement / 0.05) * 0.25
    if count == 0:
        return "Clear", 0.0
    if count <= 5:
        return "Mild", round(max(idx, 0.15), 3)
    if count <= 20:
        return "Moderate", round(max(idx, 0.4), 3)
    return "Severe", round(max(idx, 0.75), 3)
