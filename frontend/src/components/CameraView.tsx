import { useCallback, useEffect, useRef, useState } from "react";
import { useCamera } from "../camera/useCamera";
import { analyzeFrame, type QualityVerdict } from "../camera/frameQuality";
import { captureFrame, drawScaled } from "../camera/captureFrame";

interface Props {
  onCapture: (blob: Blob, filename: string) => void;
  busy: boolean;
}

const SAMPLE_INTERVAL_MS = 200; // ~5 fps is plenty for coaching
const ANALYSIS_EDGE = 160; // analyse a small copy; the math is O(pixels)

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
