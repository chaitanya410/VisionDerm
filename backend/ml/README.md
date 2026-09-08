# Optional deep-learning engine (U-Net)

The app ships with a dependency-free **classical** segmentation engine and runs
without anything in this folder. This is the path to a learned model when you
want better accuracy.

## 1. Install the ML extras

```bash
python -m pip install -r ../requirements-ml.txt
```

## 2. Get data

[ACNE04](https://github.com/xpwu95/LDL) — **academic use only**. Extract so you have:

```
acne04/
  images/*.jpg
  annotations/*.xml        # Pascal VOC, one <object> box per lesion
```

`dataset.py` converts each bounding box into a filled-disc pseudo-mask (ACNE04
has no pixel labels). [ACNE04v2](https://github.com/AIpourlapeau/acne04v2) COCO
JSON is also supported via `--coco`.

## 3. Train

```bash
python train_unet.py --data /path/to/acne04 --epochs 20 --img-size 512
# GPU is used automatically if available; CPU works but is slow.
```

The best checkpoint is written to `../models/unet.pt` with its encoder name and
normalization stats.

## 4. Use it

Restart the API. `GET /api/health` will report `"default_engine": "unet"` and the
UI badge switches to **U-Net**. Force either engine per request with the
`engine=classical|unet|auto` form field on `POST /api/segment`.

## Notes

- Disc pseudo-masks cap achievable quality. For real segmentation, annotate a
  subset with polygons (e.g. Label Studio) and point `dataset.py` at those.
- This is a demonstration, not a medical device.
