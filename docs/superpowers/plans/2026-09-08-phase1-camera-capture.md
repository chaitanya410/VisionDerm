# Phase 1 — Camera Capture Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live camera mode that coaches the user toward a usable frame, captures a still, and runs it through the existing analysis pipeline.

**Architecture:** A pure, DOM-free frame-quality analyzer is sampled at ~5 fps from a `<video>` element by a React hook. When the frame passes, the user captures a downscaled JPEG which is POSTed to the existing `/api/segment`. Results render through the existing `ImageCanvas`, which already draws lesion boxes client-side. No new backend inference; the only backend change is making the unused overlay PNG optional.

**Tech Stack:** React 19, TypeScript 5.7, Vite 7, Tailwind v4, Vitest + Testing Library (added in Task 1), FastAPI, pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-camera-skin-analysis-design.md`

## Global Constraints

- Python 3.14.7; `opencv-python-headless<5` (5.0.0.x alpha lacks `cv2.CascadeClassifier`).
- Backend tests must pass with **no model weights present**.
- **Images are never persisted** — no disk writes, no logging of image bytes.
- The word "cure" must not appear in any user-facing copy.
- `getUserMedia` requires a secure context: `localhost` in dev, HTTPS in production.
- Existing `/api/segment` behaviour must not break — `test_api.py` stays green.

---

### Task 1: Repository and frontend test infrastructure

No test runner exists in `frontend/` today, so TDD is impossible until this lands. This task also puts the project under version control.

**Files:**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/smoke.test.ts`
- Modify: `frontend/package.json`

**Interfaces:**
- Consumes: nothing
- Produces: `npm test` runs Vitest in jsdom; `@testing-library/react` available to later tasks.

- [ ] **Step 1: Initialize git and commit the current working tree**

```bash
cd "C:/Users/USER/Desktop/ACNE IMAGE SEGMENATION"
git init -b main
git add -A
git commit -m "chore: initial commit of working acne segmentation app"
```

- [ ] **Step 2: Commit the spec and this plan**

```bash
git add docs/superpowers
git commit -m "docs: add camera skin analysis spec and phase 1 plan"
```

- [ ] **Step 3: Install test dependencies**

```bash
cd frontend
npm install -D vitest@^3 jsdom@^26 @testing-library/react@^16 @testing-library/jest-dom@^6 @testing-library/user-event@^14
```

- [ ] **Step 4: Create `frontend/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

- [ ] **Step 5: Create `frontend/src/test/setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 6: Add scripts to `frontend/package.json`**

Add to the `"scripts"` object:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 7: Write a smoke test at `frontend/src/test/smoke.test.ts`**

```ts
import { describe, it, expect } from "vitest";

describe("test infrastructure", () => {
  it("runs in a DOM environment", () => {
    const el = document.createElement("div");
    el.textContent = "ok";
    expect(el.textContent).toBe("ok");
  });
});
```

- [ ] **Step 8: Run the tests**

Run: `cd frontend && npm test`
Expected: PASS, 1 test.

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/src/test
git commit -m "test: add vitest + testing-library infrastructure"
```

---

### Task 2: Make the unused overlay PNG optional

`overlay_png_base64` is declared at `frontend/src/api.ts:31` and consumed nowhere — `ImageCanvas.tsx:69` uses `mask_png_base64` only. The backend renders and base64-encodes roughly 978 KB per request that the client discards. The camera path makes this worse (one request per capture), so make it opt-in.

**Files:**
- Modify: `backend/app/schemas.py:39-41`
- Modify: `backend/app/routes/segment.py:29-91`
- Modify: `frontend/src/api.ts:31,63-84`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: nothing
- Produces: `/api/segment` accepts `include_overlay: bool` (default `True`, preserving current behaviour). `SegmentResponse.overlay_png_base64` becomes `str | None`. TS type becomes `string | null`, and `SegmentOptions` gains `includeOverlay: boolean`.

- [ ] **Step 1: Write the failing test in `backend/tests/test_api.py`**

```python
def test_segment_can_omit_overlay(synthetic_face):
    rgb, _ = synthetic_face
    files = {"image": ("face.png", _png_bytes(rgb), "image/png")}
    data = {"include_overlay": "false"}

    r = client.post("/api/segment", files=files, data=data)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["overlay_png_base64"] is None
    # The mask is still returned - the frontend renders from it.
    assert isinstance(body["mask_png_base64"], str)
    assert len(body["mask_png_base64"]) > 0


def test_segment_includes_overlay_by_default(synthetic_face):
    rgb, _ = synthetic_face
    files = {"image": ("face.png", _png_bytes(rgb), "image/png")}

    r = client.post("/api/segment", files=files)
    assert r.status_code == 200, r.text
    assert isinstance(r.json()["overlay_png_base64"], str)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_api.py::test_segment_can_omit_overlay -v`
Expected: FAIL — the response still contains a base64 string, not `None`.

- [ ] **Step 3: Widen the schema in `backend/app/schemas.py`**

Replace line 40:

```python
    overlay_png_base64: str | None = Field(
        None, description="Original + translucent lesion overlay, PNG. Null when include_overlay=false."
    )
```

- [ ] **Step 4: Add the parameter in `backend/app/routes/segment.py`**

Add to the signature after `draw_boxes`:

```python
    include_overlay: bool = Form(True),
```

Replace the `overlay_png_base64=` argument in the `SegmentResponse(...)` construction:

```python
        overlay_png_base64=(
            overlay_to_base64(rgb, result, draw_boxes=draw_boxes)
            if include_overlay
            else None
        ),
```

- [ ] **Step 5: Run the backend tests**

Run: `cd backend && ./.venv/Scripts/python.exe -m pytest -v`
Expected: PASS — 11 tests (9 existing + 2 new).

- [ ] **Step 6: Update the TypeScript client in `frontend/src/api.ts`**

Change line 31:

```ts
  overlay_png_base64: string | null;
```

Add to `SegmentOptions`:

```ts
  includeOverlay: boolean;
```

Add to the `FormData` in `segment()`, after the `draw_boxes` append:

```ts
  fd.append("include_overlay", String(opts.includeOverlay));
```

- [ ] **Step 7: Fix the one existing call site**

In `frontend/src/App.tsx`, inside `runSegment`'s options object, add:

```ts
            includeOverlay: false,
```

- [ ] **Step 8: Verify the frontend still type-checks and builds**

Run: `cd frontend && npm run build`
Expected: `tsc --noEmit` clean, `vite build` succeeds.

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas.py backend/app/routes/segment.py backend/tests/test_api.py frontend/src/api.ts frontend/src/App.tsx
git commit -m "perf: make overlay PNG opt-in, drop ~978KB of unused payload per request"
```

---

### Task 3: Frame quality analyzer

A pure function over raw pixels. No DOM types, so it is fully testable in isolation. This is the logic that produces "too dark" / "hold still" coaching.

**Files:**
- Create: `frontend/src/camera/frameQuality.ts`
- Test: `frontend/src/camera/frameQuality.test.ts`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `type QualityIssue = "OK" | "TOO_DARK" | "TOO_BRIGHT" | "TOO_BLURRY"`
  - `interface FramePixels { data: Uint8ClampedArray; width: number; height: number }`
  - `interface QualityVerdict { ok: boolean; issue: QualityIssue; message: string; brightness: number; sharpness: number }`
  - `function analyzeFrame(px: FramePixels): QualityVerdict`

- [ ] **Step 1: Write the failing tests in `frontend/src/camera/frameQuality.test.ts`**

```ts
import { describe, it, expect } from "vitest";
import { analyzeFrame, type FramePixels } from "./frameQuality";

function solid(value: number, w = 32, h = 32): FramePixels {
  const data = new Uint8ClampedArray(w * h * 4);
  for (let i = 0; i < data.length; i += 4) {
    data[i] = value;
    data[i + 1] = value;
    data[i + 2] = value;
    data[i + 3] = 255;
  }
  return { data, width: w, height: h };
}

function checkerboard(w = 32, h = 32): FramePixels {
  const data = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const v = (x + y) % 2 === 0 ? 40 : 210;
      const i = (y * w + x) * 4;
      data[i] = v;
      data[i + 1] = v;
      data[i + 2] = v;
      data[i + 3] = 255;
    }
  }
  return { data, width: w, height: h };
}

describe("analyzeFrame", () => {
  it("flags a very dark frame", () => {
    const v = analyzeFrame(solid(8));
    expect(v.issue).toBe("TOO_DARK");
    expect(v.ok).toBe(false);
    expect(v.message).toMatch(/light/i);
  });

  it("flags a blown-out frame", () => {
    const v = analyzeFrame(solid(250));
    expect(v.issue).toBe("TOO_BRIGHT");
    expect(v.ok).toBe(false);
  });

  it("flags a well-lit but flat frame as blurry", () => {
    const v = analyzeFrame(solid(128));
    expect(v.issue).toBe("TOO_BLURRY");
    expect(v.sharpness).toBeLessThan(1);
  });

  it("accepts a well-lit frame with strong detail", () => {
    const v = analyzeFrame(checkerboard());
    expect(v.issue).toBe("OK");
    expect(v.ok).toBe(true);
    expect(v.sharpness).toBeGreaterThan(60);
  });

  it("reports brightness as mean luma", () => {
    expect(analyzeFrame(solid(128)).brightness).toBeCloseTo(128, 0);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm test -- frameQuality`
Expected: FAIL — cannot resolve `./frameQuality`.

- [ ] **Step 3: Implement `frontend/src/camera/frameQuality.ts`**

```ts
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

/** Rec. 709 luma for one RGBA pixel run. */
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
```

- [ ] **Step 4: Run the tests**

Run: `cd frontend && npm test -- frameQuality`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/camera/frameQuality.ts frontend/src/camera/frameQuality.test.ts
git commit -m "feat: add pure frame-quality analyzer for camera coaching"
```

---

### Task 4: Camera stream hook

Owns `getUserMedia`, permission state, and teardown. The failure modes here are the ones users actually hit: denied permission, no camera, and insecure context.

**Files:**
- Create: `frontend/src/camera/useCamera.ts`
- Test: `frontend/src/camera/useCamera.test.ts`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `type CameraStatus = "idle" | "requesting" | "streaming" | "denied" | "unavailable" | "error"`
  - `function useCamera(): { videoRef: RefObject<HTMLVideoElement | null>; status: CameraStatus; error: string | null; start: () => Promise<void>; stop: () => void }`

- [ ] **Step 1: Write the failing tests in `frontend/src/camera/useCamera.test.ts`**

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useCamera } from "./useCamera";

const originalMediaDevices = navigator.mediaDevices;

function setMediaDevices(value: unknown) {
  Object.defineProperty(navigator, "mediaDevices", {
    value,
    configurable: true,
    writable: true,
  });
}

function fakeStream() {
  const track = { stop: vi.fn(), kind: "video" };
  return {
    getTracks: () => [track],
    _track: track,
  } as unknown as MediaStream & { _track: { stop: ReturnType<typeof vi.fn> } };
}

afterEach(() => {
  setMediaDevices(originalMediaDevices);
  vi.restoreAllMocks();
});

describe("useCamera", () => {
  beforeEach(() => {
    setMediaDevices({ getUserMedia: vi.fn() });
  });

  it("starts idle", () => {
    const { result } = renderHook(() => useCamera());
    expect(result.current.status).toBe("idle");
  });

  it("reaches streaming on success", async () => {
    const stream = fakeStream();
    (navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>)
      .mockResolvedValue(stream);

    const { result } = renderHook(() => useCamera());
    await act(async () => {
      await result.current.start();
    });

    await waitFor(() => expect(result.current.status).toBe("streaming"));
    expect(result.current.error).toBeNull();
  });

  it("reports denied when permission is refused", async () => {
    const err = new Error("denied");
    err.name = "NotAllowedError";
    (navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>)
      .mockRejectedValue(err);

    const { result } = renderHook(() => useCamera());
    await act(async () => {
      await result.current.start();
    });

    expect(result.current.status).toBe("denied");
    expect(result.current.error).toMatch(/permission/i);
  });

  it("reports unavailable when mediaDevices is missing", async () => {
    setMediaDevices(undefined);

    const { result } = renderHook(() => useCamera());
    await act(async () => {
      await result.current.start();
    });

    expect(result.current.status).toBe("unavailable");
    expect(result.current.error).toMatch(/https|secure/i);
  });

  it("stops every track on stop()", async () => {
    const stream = fakeStream();
    (navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>)
      .mockResolvedValue(stream);

    const { result } = renderHook(() => useCamera());
    await act(async () => {
      await result.current.start();
    });
    act(() => result.current.stop());

    expect(stream._track.stop).toHaveBeenCalled();
    expect(result.current.status).toBe("idle");
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm test -- useCamera`
Expected: FAIL — cannot resolve `./useCamera`.

- [ ] **Step 3: Implement `frontend/src/camera/useCamera.ts`**

```ts
import { useCallback, useEffect, useRef, useState } from "react";

export type CameraStatus =
  | "idle"
  | "requesting"
  | "streaming"
  | "denied"
  | "unavailable"
  | "error";

const CONSTRAINTS: MediaStreamConstraints = {
  video: {
    facingMode: "user",
    width: { ideal: 1280 },
    height: { ideal: 720 },
  },
  audio: false,
};

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [status, setStatus] = useState<CameraStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setStatus("idle");
    setError(null);
  }, []);

  const start = useCallback(async () => {
    // Absent on http:// origins other than localhost, and in old browsers.
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("unavailable");
      setError(
        "Camera needs a secure connection. Open this page over HTTPS or on localhost.",
      );
      return;
    }

    setStatus("requesting");
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia(CONSTRAINTS);
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {
          /* autoplay rejection is not fatal; the user can press play */
        });
      }
      setStatus("streaming");
    } catch (e) {
      const err = e as DOMException;
      if (err.name === "NotAllowedError" || err.name === "SecurityError") {
        setStatus("denied");
        setError("Camera permission was blocked. Allow it in your browser settings.");
      } else if (err.name === "NotFoundError" || err.name === "OverconstrainedError") {
        setStatus("unavailable");
        setError("No camera found on this device.");
      } else {
        setStatus("error");
        setError(err.message || "Could not start the camera.");
      }
    }
  }, []);

  // Release the device if the component unmounts while streaming.
  useEffect(() => stop, [stop]);

  return { videoRef, status, error, start, stop };
}
```

- [ ] **Step 4: Run the tests**

Run: `cd frontend && npm test -- useCamera`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/camera/useCamera.ts frontend/src/camera/useCamera.test.ts
git commit -m "feat: add useCamera hook with permission and teardown handling"
```

---

### Task 5: Frame capture helper

Turns the live `<video>` into a downscaled JPEG blob. Downscaling matters: a raw 1280×720 PNG is far larger than the backend needs, and `MAX_UPLOAD_BYTES` caps uploads at 12 MB (`backend/app/config.py`).

**Files:**
- Create: `frontend/src/camera/captureFrame.ts`
- Test: `frontend/src/camera/captureFrame.test.ts`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `function drawScaled(video: HTMLVideoElement, canvas: HTMLCanvasElement, maxEdge?: number): { width: number; height: number }`
  - `function captureFrame(video: HTMLVideoElement, maxEdge?: number): Promise<Blob>`

- [ ] **Step 1: Write the failing tests in `frontend/src/camera/captureFrame.test.ts`**

jsdom has no real canvas, so test the pure sizing arithmetic via `drawScaled` against a stubbed canvas.

```ts
import { describe, it, expect, vi } from "vitest";
import { drawScaled } from "./captureFrame";

function stubVideo(w: number, h: number) {
  return { videoWidth: w, videoHeight: h } as HTMLVideoElement;
}

function stubCanvas() {
  const ctx = { drawImage: vi.fn() };
  return {
    width: 0,
    height: 0,
    getContext: () => ctx,
    _ctx: ctx,
  } as unknown as HTMLCanvasElement & { _ctx: { drawImage: ReturnType<typeof vi.fn> } };
}

describe("drawScaled", () => {
  it("leaves small frames untouched", () => {
    const canvas = stubCanvas();
    const size = drawScaled(stubVideo(640, 480), canvas, 1280);
    expect(size).toEqual({ width: 640, height: 480 });
  });

  it("scales the long edge down to maxEdge, preserving aspect", () => {
    const canvas = stubCanvas();
    const size = drawScaled(stubVideo(1920, 1080), canvas, 1280);
    expect(size.width).toBe(1280);
    expect(size.height).toBe(720);
  });

  it("handles portrait frames", () => {
    const canvas = stubCanvas();
    const size = drawScaled(stubVideo(720, 1280), canvas, 640);
    expect(size.height).toBe(640);
    expect(size.width).toBe(360);
  });

  it("sizes the canvas and draws once", () => {
    const canvas = stubCanvas();
    drawScaled(stubVideo(1920, 1080), canvas, 1280);
    expect(canvas.width).toBe(1280);
    expect(canvas.height).toBe(720);
    expect(canvas._ctx.drawImage).toHaveBeenCalledTimes(1);
  });

  it("throws on a video with no dimensions yet", () => {
    expect(() => drawScaled(stubVideo(0, 0), stubCanvas())).toThrow(/not ready/i);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm test -- captureFrame`
Expected: FAIL — cannot resolve `./captureFrame`.

- [ ] **Step 3: Implement `frontend/src/camera/captureFrame.ts`**

```ts
const DEFAULT_MAX_EDGE = 1280;
const JPEG_QUALITY = 0.92;

/**
 * Draw the current video frame into `canvas`, scaled so the long edge is at
 * most `maxEdge`. Returns the resulting pixel size.
 */
export function drawScaled(
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement,
  maxEdge: number = DEFAULT_MAX_EDGE,
): { width: number; height: number } {
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  if (!vw || !vh) throw new Error("Camera frame is not ready yet.");

  const scale = Math.min(1, maxEdge / Math.max(vw, vh));
  const width = Math.round(vw * scale);
  const height = Math.round(vh * scale);

  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not get a 2D canvas context.");
  ctx.drawImage(video, 0, 0, width, height);

  return { width, height };
}

/** Capture the current frame as a JPEG blob, downscaled for upload. */
export function captureFrame(
  video: HTMLVideoElement,
  maxEdge: number = DEFAULT_MAX_EDGE,
): Promise<Blob> {
  const canvas = document.createElement("canvas");
  drawScaled(video, canvas, maxEdge);
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) =>
        blob ? resolve(blob) : reject(new Error("Could not encode the frame.")),
      "image/jpeg",
      JPEG_QUALITY,
    );
  });
}
```

- [ ] **Step 4: Run the tests**

Run: `cd frontend && npm test -- captureFrame`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/camera/captureFrame.ts frontend/src/camera/captureFrame.test.ts
git commit -m "feat: add downscaling frame capture helper"
```

---

### Task 6: CameraView component

Wires the hook, the analyzer, and the capture helper into a UI with live coaching.

**Files:**
- Create: `frontend/src/components/CameraView.tsx`
- Test: `frontend/src/components/CameraView.test.tsx`

**Interfaces:**
- Consumes: `useCamera` (Task 4), `analyzeFrame` / `FramePixels` (Task 3), `captureFrame` / `drawScaled` (Task 5)
- Produces: `function CameraView(props: { onCapture: (blob: Blob, filename: string) => void; busy: boolean }): JSX.Element`

- [ ] **Step 1: Write the failing tests in `frontend/src/components/CameraView.test.tsx`**

```tsx
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CameraView from "./CameraView";

function setMediaDevices(value: unknown) {
  Object.defineProperty(navigator, "mediaDevices", {
    value,
    configurable: true,
    writable: true,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("CameraView", () => {
  it("offers a start control before the camera is running", () => {
    setMediaDevices({ getUserMedia: vi.fn() });
    render(<CameraView onCapture={vi.fn()} busy={false} />);
    expect(screen.getByRole("button", { name: /start camera/i })).toBeInTheDocument();
  });

  it("explains the secure-context requirement when unavailable", async () => {
    setMediaDevices(undefined);
    render(<CameraView onCapture={vi.fn()} busy={false} />);

    await userEvent.click(screen.getByRole("button", { name: /start camera/i }));

    expect(await screen.findByText(/https|localhost/i)).toBeInTheDocument();
  });

  it("surfaces a blocked permission to the user", async () => {
    const err = new Error("no");
    err.name = "NotAllowedError";
    setMediaDevices({ getUserMedia: vi.fn().mockRejectedValue(err) });

    render(<CameraView onCapture={vi.fn()} busy={false} />);
    await userEvent.click(screen.getByRole("button", { name: /start camera/i }));

    expect(await screen.findByText(/permission/i)).toBeInTheDocument();
  });

  it("states that images are not stored", () => {
    setMediaDevices({ getUserMedia: vi.fn() });
    render(<CameraView onCapture={vi.fn()} busy={false} />);
    expect(screen.getByText(/never (stored|saved)/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm test -- CameraView`
Expected: FAIL — cannot resolve `./CameraView`.

- [ ] **Step 3: Implement `frontend/src/components/CameraView.tsx`**

```tsx
import { useCallback, useEffect, useRef, useState } from "react";
import { useCamera } from "../camera/useCamera";
import { analyzeFrame, type QualityVerdict } from "../camera/frameQuality";
import { captureFrame, drawScaled } from "../camera/captureFrame";

interface Props {
  onCapture: (blob: Blob, filename: string) => void;
  busy: boolean;
}

const SAMPLE_INTERVAL_MS = 200; // ~5 fps is plenty for coaching
const ANALYSIS_EDGE = 160; // analyze a small copy; the math is O(pixels)

export default function CameraView({ onCapture, busy }: Props) {
  const { videoRef, status, error, start, stop } = useCamera();
  const scratchRef = useRef<HTMLCanvasElement | null>(null);
  const [verdict, setVerdict] = useState<QualityVerdict | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "streaming") {
      setVerdict(null);
      return;
    }
    const id = setInterval(() => {
      const video = videoRef.current;
      if (!video) return;
      if (!scratchRef.current) scratchRef.current = document.createElement("canvas");
      const canvas = scratchRef.current;
      try {
        drawScaled(video, canvas, ANALYSIS_EDGE);
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        const px = ctx.getImageData(0, 0, canvas.width, canvas.height);
        setVerdict(analyzeFrame(px));
      } catch {
        /* frame not ready yet; the next tick retries */
      }
    }, SAMPLE_INTERVAL_MS);
    return () => clearInterval(id);
  }, [status, videoRef]);

  const handleCapture = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return;
    setCaptureError(null);
    try {
      const blob = await captureFrame(video);
      onCapture(blob, `camera-${Date.now()}.jpg`);
    } catch (e) {
      setCaptureError((e as Error).message);
    }
  }, [onCapture, videoRef]);

  const streaming = status === "streaming";

  return (
    <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="relative overflow-hidden rounded-lg bg-slate-950">
        <video
          ref={videoRef}
          playsInline
          muted
          className="h-auto w-full"
          data-testid="camera-video"
        />
        {streaming && verdict && (
          <p
            className={`absolute inset-x-0 bottom-0 px-3 py-2 text-center text-xs font-medium ${
              verdict.ok
                ? "bg-emerald-500/80 text-emerald-950"
                : "bg-amber-500/80 text-amber-950"
            }`}
          >
            {verdict.message}
          </p>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {!streaming ? (
          <button
            type="button"
            onClick={start}
            disabled={status === "requesting"}
            className="rounded-md bg-sky-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {status === "requesting" ? "Starting…" : "Start camera"}
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={handleCapture}
              disabled={busy || !verdict?.ok}
              title={verdict?.ok ? undefined : verdict?.message}
              className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {busy ? "Analysing…" : "Capture & analyse"}
            </button>
            <button
              type="button"
              onClick={stop}
              className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-300"
            >
              Stop camera
            </button>
          </>
        )}
      </div>

      {(error || captureError) && (
        <p className="text-xs text-rose-300">{error ?? captureError}</p>
      )}

      <p className="text-[11px] text-slate-500">
        Frames are analysed in your browser and the captured photo is processed in
        memory. Images are never stored.
      </p>
    </div>
  );
}
```

- [ ] **Step 4: Run the tests**

Run: `cd frontend && npm test -- CameraView`
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CameraView.tsx frontend/src/components/CameraView.test.tsx
git commit -m "feat: add CameraView with live frame-quality coaching"
```

---

### Task 7: Wire the camera into the app

Adds an input-mode switch so camera and upload share the existing analysis and rendering path. `App.tsx` is already 238 lines; keep this change small and push no new logic into it beyond mode state.

**Files:**
- Modify: `frontend/src/App.tsx` (line numbers below are from the pre-edit file and shift as you go — match on code, not position)
- Test: `frontend/src/App.test.tsx` (create)

**Interfaces:**
- Consumes: `CameraView` (Task 6), existing `runSegment`
- Produces: nothing downstream

- [ ] **Step 1: Write the failing test in `frontend/src/App.test.tsx`**

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

beforeEach(() => {
  Object.defineProperty(navigator, "mediaDevices", {
    value: { getUserMedia: vi.fn() },
    configurable: true,
    writable: true,
  });
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }),
  );
});

afterEach(() => vi.restoreAllMocks());

describe("App input modes", () => {
  it("shows the upload dropzone by default", () => {
    render(<App />);
    expect(screen.getByRole("tab", { name: /upload/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("switches to the camera panel", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("tab", { name: /camera/i }));
    expect(
      await screen.findByRole("button", { name: /start camera/i }),
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm test -- App`
Expected: FAIL — no element with role `tab`.

- [ ] **Step 3: Add mode state and the camera handler in `frontend/src/App.tsx`**

Add after the `Source` interface (line 19):

```ts
type InputMode = "upload" | "camera";
```

Add alongside the other `useState` calls (after line 38):

```ts
  const [mode, setMode] = useState<InputMode>("upload");
```

Add after `setSampleImage` (line 112):

```ts
  const setCameraCapture = useCallback((blob: Blob, filename: string) => {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    const url = URL.createObjectURL(blob);
    objectUrlRef.current = url;
    blobRef.current = blob;
    setResult(null);
    setError(null);
    setSource({ url, filename, origin: "upload" });
  }, []);
```

- [ ] **Step 4: Replace the Dropzone with a tabbed panel**

Step 3 shifted the line numbers, so match on the code, not a line number. Find this exact line inside the left `<aside>`:

```tsx
          <Dropzone onFile={setUploadFile} busy={busy} />
```

Replace it with:

```tsx
          <div>
            <div role="tablist" className="mb-3 flex gap-1 rounded-lg bg-slate-900 p-1">
              {(["upload", "camera"] as const).map((m) => (
                <button
                  key={m}
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => setMode(m)}
                  className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium capitalize ${
                    mode === m ? "bg-slate-700 text-slate-100" : "text-slate-400"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
            {mode === "upload" ? (
              <Dropzone onFile={setUploadFile} busy={busy} />
            ) : (
              <CameraView onCapture={setCameraCapture} busy={busy} />
            )}
          </div>
```

- [ ] **Step 5: Add the import at the top of `App.tsx`**

```ts
import CameraView from "./components/CameraView";
```

- [ ] **Step 6: Run the full frontend suite**

Run: `cd frontend && npm test`
Expected: PASS — all suites (smoke, frameQuality, useCamera, captureFrame, CameraView, App).

- [ ] **Step 7: Verify types and build**

Run: `cd frontend && npm run build`
Expected: `tsc --noEmit` clean, `vite build` succeeds.

- [ ] **Step 8: Verify the backend suite still passes**

Run: `cd backend && ./.venv/Scripts/python.exe -m pytest -v`
Expected: PASS, 11 tests.

- [ ] **Step 9: Manual verification**

Run `./run.ps1`, open `http://localhost:5173`, switch to the Camera tab, allow the camera, confirm the coaching banner reacts to covering the lens (TOO_DARK) and to shaking the camera (TOO_BLURRY), then capture and confirm lesion boxes render.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: add camera input mode alongside upload"
git tag phase-1-camera
```

---

## Notes for the executor

- **Resolved open question from the spec (§12.1):** Phase 1 uses **no face-detection model**. The brightness/sharpness heuristic needs no dependency, no WASM download, and no self-hosting on Spaces. The server-side Haar cascade in `classical.py` already gates faces during real analysis. Revisit MediaPipe only if user testing shows the coaching is insufficient.
- **Not in this phase:** the trained detector (Phase 2), condition screening (Phase 3), guidance and clinic finder (Phase 4). Do not add stubs for them.
- `frontend/dist/` and `backend/data/samples/` are gitignored; do not force-add them.
