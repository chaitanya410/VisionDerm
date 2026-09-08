import { useEffect, type RefObject } from "react";
import type { SegmentResponse } from "../api";
import { dataUrl } from "../api";

export type ViewMode = "overlay" | "original" | "mask";

interface Props {
  canvasRef: RefObject<HTMLCanvasElement | null>;
  originalUrl: string | null;
  result: SegmentResponse | null;
  view: ViewMode;
  opacity: number; // 0..1
  showBoxes: boolean;
}

const LESION_RGB = [255, 60, 60] as const;
const BOX_STROKE = "rgba(255,210,60,0.95)";

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

export default function ImageCanvas({
  canvasRef,
  originalUrl,
  result,
  view,
  opacity,
  showBoxes,
}: Props) {
  useEffect(() => {
    let cancelled = false;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    async function render(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D) {
      if (!originalUrl) {
        canvas.width = 0;
        canvas.height = 0;
        return;
      }
      const base = await loadImage(originalUrl);
      if (cancelled) return;

      // Work in the processing resolution when we have a result, else native.
      const w = result?.image.width ?? base.naturalWidth;
      const h = result?.image.height ?? base.naturalHeight;
      canvas.width = w;
      canvas.height = h;

      ctx.clearRect(0, 0, w, h);

      if (view === "mask" && result) {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, w, h);
      } else {
        ctx.drawImage(base, 0, 0, w, h);
      }

      if (result && (view === "overlay" || view === "mask")) {
        const maskImg = await loadImage(dataUrl(result.mask_png_base64));
        if (cancelled) return;

        const off = document.createElement("canvas");
        off.width = w;
        off.height = h;
        const octx = off.getContext("2d")!;
        octx.drawImage(maskImg, 0, 0, w, h);
        const px = octx.getImageData(0, 0, w, h);
        const d = px.data;
        for (let i = 0; i < d.length; i += 4) {
          const on = d[i] > 127; // mask is white where lesions are
          d[i] = LESION_RGB[0];
          d[i + 1] = LESION_RGB[1];
          d[i + 2] = LESION_RGB[2];
          d[i + 3] = on ? 255 : 0;
        }
        octx.putImageData(px, 0, 0);

        ctx.globalAlpha = view === "mask" ? 1 : opacity;
        ctx.drawImage(off, 0, 0);
        ctx.globalAlpha = 1;
      }

      if (result && showBoxes && view !== "original") {
        ctx.lineWidth = Math.max(1, Math.round(w / 500));
        ctx.strokeStyle = BOX_STROKE;
        for (const l of result.lesions) {
          const [x, y, bw, bh] = l.bbox;
          ctx.strokeRect(x - 1, y - 1, bw + 2, bh + 2);
        }
      }
    }

    render(canvas, ctx).catch(() => {
      /* transient load errors are fine; next render retries */
    });
    return () => {
      cancelled = true;
    };
  }, [canvasRef, originalUrl, result, view, opacity, showBoxes]);

  return (
    <div className="flex min-h-[320px] items-center justify-center rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      {originalUrl ? (
        <canvas
          ref={canvasRef}
          className="max-h-[70vh] w-auto max-w-full rounded-lg shadow-lg shadow-black/40"
        />
      ) : (
        <p className="text-sm text-slate-500">
          Upload a photo or pick a sample to see the segmentation.
        </p>
      )}
    </div>
  );
}
