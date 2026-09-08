// Pure frame-quality heuristics. Deliberately DOM-free so they can be unit
// tested without a canvas: ImageData structurally satisfies FramePixels.

export type QualityIssue = "OK" | "TOO_DARK" | "TOO_BRIGHT" | "TOO_BLURRY";

export interface FramePixels {
  data: Uint8ClampedArray;
  width: number;
  height: number;
}

export interface QualityVerdict {
  ok: boolean;
  issue: QualityIssue;
  message: string;
  brightness: number; // mean luma, 0..255
  sharpness: number; // variance of the Laplacian
}

const MIN_BRIGHTNESS = 55;
const MAX_BRIGHTNESS = 215;
const MIN_SHARPNESS = 60;

const MESSAGES: Record<QualityIssue, string> = {
  OK: "Looks good — hold still and capture",
  TOO_DARK: "Too dark — find more light",
  TOO_BRIGHT: "Too bright — move away from direct light",
  TOO_BLURRY: "Blurry — hold still and move a little closer",
};

/** Rec. 709 luma for each RGBA pixel. */
function toLuma(px: FramePixels): Float32Array {
  const { data, width, height } = px;
  const out = new Float32Array(width * height);
  for (let i = 0, p = 0; p < out.length; i += 4, p++) {
    out[p] = 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2];
  }
  return out;
}

function mean(values: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < values.length; i++) sum += values[i];
  return values.length ? sum / values.length : 0;
}

/**
 * Variance of the 4-neighbour Laplacian — the standard cheap focus measure.
 * Flat regions give ~0; edges give large values.
 */
function laplacianVariance(luma: Float32Array, w: number, h: number): number {
  if (w < 3 || h < 3) return 0;
  const responses: number[] = [];
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const i = y * w + x;
      responses.push(
        luma[i - w] + luma[i + w] + luma[i - 1] + luma[i + 1] - 4 * luma[i],
      );
    }
  }
  const n = responses.length;
  if (!n) return 0;
  const m = responses.reduce((a, b) => a + b, 0) / n;
  return responses.reduce((a, b) => a + (b - m) ** 2, 0) / n;
}

export function analyzeFrame(px: FramePixels): QualityVerdict {
  const luma = toLuma(px);
  const brightness = mean(luma);
  const sharpness = laplacianVariance(luma, px.width, px.height);

  let issue: QualityIssue = "OK";
  if (brightness < MIN_BRIGHTNESS) issue = "TOO_DARK";
  else if (brightness > MAX_BRIGHTNESS) issue = "TOO_BRIGHT";
  else if (sharpness < MIN_SHARPNESS) issue = "TOO_BLURRY";

  return {
    ok: issue === "OK",
    issue,
    message: MESSAGES[issue],
    brightness,
    sharpness,
  };
}
