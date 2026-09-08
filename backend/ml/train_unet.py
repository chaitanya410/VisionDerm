"""Train a U-Net acne-lesion segmenter and save a checkpoint the API can load.

This is the OPTIONAL deep-learning path. The app runs fine without it (classical
engine). After training, `backend/models/unet.pt` is picked up automatically and
the API's engine badge switches to "U-Net".

Setup:
    python -m pip install -r requirements-ml.txt

Data: ACNE04 (academic use only) - https://github.com/xpwu95/LDL
    Download + extract so you have  <data>/images/*.jpg  and
    <data>/annotations/*.xml  (Pascal VOC), then:

    python ml/train_unet.py --data /path/to/acne04 --epochs 20 --img-size 512

    # or ACNE04v2 COCO json:
    python ml/train_unet.py --data /path/to/acne04v2 --coco /path/to/instances.json

The checkpoint stores: state_dict, encoder name, and normalization stats.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUT = BACKEND_DIR / "models" / "unet.pt"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--coco", type=Path, default=None)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--img-size", type=int, default=512)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--encoder", default="resnet34")
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    import segmentation_models_pytorch as smp
    import torch
    from torch.utils.data import DataLoader, Dataset
    from tqdm import tqdm

    from dataset import build_mask_for, iter_coco_pairs, iter_voc_pairs

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}")

    pairs = list(
        iter_coco_pairs(args.data, args.coco) if args.coco else iter_voc_pairs(args.data)
    )
    if not pairs:
        raise SystemExit(
            f"No (image, annotation) pairs found under {args.data}. "
            "Expected <data>/images and <data>/annotations (VOC) or pass --coco."
        )
    random.shuffle(pairs)
    n_val = max(1, int(len(pairs) * args.val_frac))
    train_pairs, val_pairs = pairs[n_val:], pairs[:n_val]
    print(f"{len(train_pairs)} train / {len(val_pairs)} val images")

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    try:
        import albumentations as A

        aug = A.Compose(
            [
                A.HorizontalFlip(p=0.5),
                A.RandomBrightnessContrast(p=0.3),
                A.ShiftScaleRotate(shift_limit=0.05, scale_limit=0.1, rotate_limit=15, p=0.5),
            ]
        )
    except Exception:  # noqa: BLE001
        aug = None

    import cv2

    class AcneDS(Dataset):
        def __init__(self, items, train: bool):
            self.items = items
            self.train = train

        def __len__(self) -> int:
            return len(self.items)

        def __getitem__(self, i):
            path, boxes = self.items[i]
            img = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)
            mask = build_mask_for(path, boxes)
            img = cv2.resize(img, (args.img_size, args.img_size))
            mask = cv2.resize(mask, (args.img_size, args.img_size), interpolation=cv2.INTER_NEAREST)
            if self.train and aug is not None:
                out = aug(image=img, mask=mask)
                img, mask = out["image"], out["mask"]
            x = ((img.astype(np.float32) / 255.0) - mean) / std
            x = torch.from_numpy(x.transpose(2, 0, 1)).float()
            y = torch.from_numpy((mask > 127).astype(np.float32))[None]
            return x, y

    train_dl = DataLoader(
        AcneDS(train_pairs, True), batch_size=args.batch_size, shuffle=True, num_workers=0
    )
    val_dl = DataLoader(
        AcneDS(val_pairs, False), batch_size=args.batch_size, shuffle=False, num_workers=0
    )

    model = smp.Unet(
        encoder_name=args.encoder, encoder_weights="imagenet", in_channels=3, classes=1
    ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    dice = smp.losses.DiceLoss(mode="binary")
    bce = torch.nn.BCEWithLogitsLoss()

    def loss_fn(logits, y):
        return 0.5 * dice(logits, y) + 0.5 * bce(logits, y)

    best_val = float("inf")
    OUT.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        tr = 0.0
        for x, y in tqdm(train_dl, desc=f"epoch {epoch}/{args.epochs}"):
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            tr += loss.item() * x.size(0)
        tr /= len(train_dl.dataset)

        model.eval()
        vl = 0.0
        with torch.no_grad():
            for x, y in val_dl:
                x, y = x.to(device), y.to(device)
                vl += loss_fn(model(x), y).item() * x.size(0)
        vl /= len(val_dl.dataset)
        print(f"  train {tr:.4f}  val {vl:.4f}")

        if vl < best_val:
            best_val = vl
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "encoder": args.encoder,
                    "mean": mean.tolist(),
                    "std": std.tolist(),
                    "img_size": args.img_size,
                    "val_loss": vl,
                },
                OUT,
            )
            print(f"  saved {OUT} (val {vl:.4f})")

    print(f"\nDone. Best val loss {best_val:.4f}. Restart the API to use the U-Net engine.")


if __name__ == "__main__":
    main()
