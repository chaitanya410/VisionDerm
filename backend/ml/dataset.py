"""Turn ACNE04-style bounding-box annotations into segmentation masks.

ACNE04 (https://github.com/xpwu95/LDL, academic use only) ships facial images with
Pascal-VOC XML files listing one <object> box per lesion. There are no pixel
masks, so we synthesise a pseudo-mask by painting a filled disc inside each box
(radius = 0.42 * min(box_w, box_h)). Coarse, but enough to teach a U-Net "where
lesions are" for a demo.

Expected layout (pass the parent as --data):
    <data>/images/*.jpg
    <data>/annotations/*.xml        # same stem as the image

The ACNE04v2 COCO-style JSON annotations are also supported via `--coco path.json`.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np


def _disc_mask(h: int, w: int, boxes: list[tuple[int, int, int, int]]) -> np.ndarray:
    mask = np.zeros((h, w), dtype=np.uint8)
    for x0, y0, x1, y1 in boxes:
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        r = max(2, int(0.42 * min(x1 - x0, y1 - y0)))
        cv2.circle(mask, (cx, cy), r, 255, thickness=-1)
    return mask


def _boxes_from_voc(xml_path: Path) -> list[tuple[int, int, int, int]]:
    root = ET.parse(xml_path).getroot()
    boxes = []
    for obj in root.findall("object"):
        b = obj.find("bndbox")
        if b is None:
            continue
        boxes.append(
            (
                int(float(b.findtext("xmin", "0"))),
                int(float(b.findtext("ymin", "0"))),
                int(float(b.findtext("xmax", "0"))),
                int(float(b.findtext("ymax", "0"))),
            )
        )
    return boxes


def iter_voc_pairs(data_dir: Path):
    img_dir = data_dir / "images"
    ann_dir = data_dir / "annotations"
    for img in sorted(img_dir.glob("*.jp*g")):
        xml = ann_dir / f"{img.stem}.xml"
        if xml.exists():
            yield img, _boxes_from_voc(xml)


def iter_coco_pairs(data_dir: Path, coco_json: Path):
    coco = json.loads(coco_json.read_text(encoding="utf-8"))
    by_id = {im["id"]: im for im in coco["images"]}
    boxes_by_img: dict[int, list] = {}
    for ann in coco["annotations"]:
        x, y, w, h = ann["bbox"]
        boxes_by_img.setdefault(ann["image_id"], []).append(
            (int(x), int(y), int(x + w), int(y + h))
        )
    for img_id, meta in by_id.items():
        p = data_dir / "images" / meta["file_name"]
        if p.exists():
            yield p, boxes_by_img.get(img_id, [])


def build_mask_for(image_path: Path, boxes: list[tuple[int, int, int, int]]) -> np.ndarray:
    img = cv2.imread(str(image_path))
    h, w = img.shape[:2]
    return _disc_mask(h, w, boxes)
