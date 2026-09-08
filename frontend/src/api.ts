// Typed client for the FastAPI backend. Mirrors backend/app/schemas.py.

export interface Lesion {
  id: number;
  bbox: [number, number, number, number]; // x, y, w, h
  area_px: number;
  centroid: [number, number];
  score: number;
}

export interface Severity {
  label: "Clear" | "Mild" | "Moderate" | "Severe";
  score: number;
  note: string;
}

export interface SegmentParams {
  sensitivity: number;
  min_area: number;
  max_area: number;
}

export interface SegmentResponse {
  engine: "classical" | "unet";
  image: { width: number; height: number };
  params: SegmentParams;
  lesions: Lesion[];
  count: number;
  severity: Severity;
  mask_png_base64: string;
  overlay_png_base64: string | null;
  elapsed_ms: number;
}

export interface SampleInfo {
  id: string;
  filename: string;
  url: string;
  source: string | null;
  license: string | null;
}

export interface HealthInfo {
  status: string;
  unet_checkpoint_present: boolean;
  default_engine: "classical" | "unet";
}

const API = "/api";

export async function getHealth(): Promise<HealthInfo> {
  const r = await fetch(`${API}/health`);
  if (!r.ok) throw new Error(`health ${r.status}`);
  return r.json();
}

export async function listSamples(): Promise<SampleInfo[]> {
  const r = await fetch(`${API}/samples`);
  if (!r.ok) throw new Error(`samples ${r.status}`);
  return r.json();
}

export interface SegmentOptions {
  sensitivity: number;
  minArea: number;
  maxArea: number;
  engine: "auto" | "classical" | "unet";
  drawBoxes: boolean;
  /** Server-rendered overlay PNG. The UI renders from `lesions` + the mask,
   *  so this is normally false - it saves roughly 1 MB per request. */
  includeOverlay: boolean;
}

export async function segment(
  file: Blob,
  filename: string,
  opts: SegmentOptions,
  signal?: AbortSignal,
): Promise<SegmentResponse> {
  const fd = new FormData();
  fd.append("image", file, filename);
  fd.append("sensitivity", String(opts.sensitivity));
  fd.append("min_area", String(opts.minArea));
  fd.append("max_area", String(opts.maxArea));
  fd.append("engine", opts.engine);
  fd.append("draw_boxes", String(opts.drawBoxes));
  fd.append("include_overlay", String(opts.includeOverlay));

  const r = await fetch(`${API}/segment`, { method: "POST", body: fd, signal });
  if (!r.ok) {
    let detail = `${r.status}`;
    try {
      detail = (await r.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return r.json();
}

export function dataUrl(b64: string): string {
  return `data:image/png;base64,${b64}`;
}
