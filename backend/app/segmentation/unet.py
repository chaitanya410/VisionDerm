"""Optional U-Net engine.

Activated only when BOTH are true:
  * `torch` and `segmentation-models-pytorch` are importable
    (pip install -r requirements-ml.txt)
  * a checkpoint exists at backend/models/unet.pt

Otherwise constructing UNetEngine raises and base.get_engine() falls back to the
classical pipeline. Train a checkpoint with `python ml/train_unet.py`.
"""
from __future__ import annotations

import numpy as np

from ..config import UNET_CHECKPOINT
from .base import LesionRegion, SegmentationResult


class UNetEngine:
    name = "unet"
    input_size = 512

    def __init__(self) -> None:
        if not UNET_CHECKPOINT.exists():
            raise FileNotFoundError(f"No checkpoint at {UNET_CHECKPOINT}")

        import segmentation_models_pytorch as smp  # noqa: F401
        import torch

        self._torch = torch
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        ckpt = torch.load(UNET_CHECKPOINT, map_location=self.device)
        encoder = ckpt.get("encoder", "resnet34")
        self.model = smp.Unet(
            encoder_name=encoder, encoder_weights=None, in_channels=3, classes=1
        )
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.to(self.device).eval()
        self.mean = np.array(ckpt.get("mean", [0.485, 0.456, 0.406]), dtype=np.float32)
        self.std = np.array(ckpt.get("std", [0.229, 0.224, 0.225]), dtype=np.float32)

    def segment(
        self,
        image_rgb: np.ndarray,
        *,
        sensitivity: float,
        min_area: int,
        max_area: int,
    ) -> SegmentationResult:
        import cv2
        from skimage.measure import label, regionprops

        torch = self._torch
        h, w = image_rgb.shape[:2]
        inp = cv2.resize(image_rgb[:, :, :3], (self.input_size, self.input_size))
        x = (inp.astype(np.float32) / 255.0 - self.mean) / self.std
        x = torch.from_numpy(x.transpose(2, 0, 1)[None]).float().to(self.device)

        with torch.no_grad():
            prob = torch.sigmoid(self.model(x))[0, 0].cpu().numpy()

        prob = cv2.resize(prob, (w, h))
        # sensitivity maps ~[0.5 .. 3.5] slider range onto a 0.2..0.8 prob cutoff
        cutoff = float(np.clip(0.2 + (sensitivity - 0.5) * 0.2, 0.2, 0.85))
        binary = (prob > cutoff).astype(np.uint8)

        lesions: list[LesionRegion] = []
        clean = np.zeros((h, w), dtype=np.uint8)
        lbl = label(binary)
        for region in regionprops(lbl, intensity_image=prob):
            area = int(region.area)
            if area < min_area or area > max_area:
                continue
            minr, minc, maxr, maxc = region.bbox
            cy, cx = region.centroid
            lesions.append(
                LesionRegion(
                    id=len(lesions) + 1,
                    bbox=(int(minc), int(minr), int(maxc - minc), int(maxr - minr)),
                    area_px=area,
                    centroid=(round(float(cx), 1), round(float(cy), 1)),
                    score=round(float(np.clip(region.mean_intensity, 0, 1)), 3),
                )
            )
            clean[lbl == region.label] = 255

        from .classical import _grade, _skin_mask

        label_txt, score = _grade(
            count=len(lesions),
            lesion_area=int((clean > 0).sum()),
            skin_area=int(_skin_mask(image_rgb).sum()),
        )
        return SegmentationResult(
            engine=self.name,
            mask=clean,
            lesions=lesions,
            severity_label=label_txt,
            severity_score=score,
        )
