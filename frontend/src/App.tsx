import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getHealth,
  listSamples,
  segment,
  type SampleInfo,
  type SegmentResponse,
} from "./api";
import Dropzone from "./components/Dropzone";
import SampleGallery from "./components/SampleGallery";
import ImageCanvas from "./components/ImageCanvas";
import Controls, { type ControlState } from "./components/Controls";
import ResultsPanel from "./components/ResultsPanel";
import CameraView from "./components/CameraView";

interface Source {
  url: string; // for display (object URL or sample URL)
  filename: string;
  origin: "upload" | "sample";
}

type InputMode = "upload" | "camera";

const DEFAULT_CONTROLS: ControlState = {
  sensitivity: 2.5,
  minArea: 10,
  maxArea: 1600,
  engine: "auto",
  view: "overlay",
  opacity: 0.45,
  showBoxes: true,
};

export default function App() {
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [unetAvailable, setUnetAvailable] = useState(false);
  const [source, setSource] = useState<Source | null>(null);
  const [controls, setControls] = useState<ControlState>(DEFAULT_CONTROLS);
  const [result, setResult] = useState<SegmentResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<InputMode>("upload");

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const blobRef = useRef<Blob | null>(null); // bytes to POST for the current source
  const objectUrlRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    listSamples().then(setSamples).catch(() => setSamples([]));
    getHealth()
      .then((h) => setUnetAvailable(h.unet_checkpoint_present))
      .catch(() => setUnetAvailable(false));
  }, []);

  const runSegment = useCallback(
    async (blob: Blob, filename: string, c: ControlState) => {
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      setBusy(true);
      setError(null);
      try {
        const res = await segment(
          blob,
          filename,
          {
            sensitivity: c.sensitivity,
            minArea: c.minArea,
            maxArea: c.maxArea,
            engine: c.engine,
            drawBoxes: c.showBoxes,
            includeOverlay: false,
          },
          ac.signal,
        );
        setResult(res);
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          setError((e as Error).message || "Segmentation failed");
          setResult(null);
        }
      } finally {
        if (abortRef.current === ac) setBusy(false);
      }
    },
    [],
  );

  const setUploadFile = useCallback(
    (file: File) => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
      const url = URL.createObjectURL(file);
      objectUrlRef.current = url;
      blobRef.current = file;
      setResult(null);
      setSource({ url, filename: file.name, origin: "upload" });
    },
    [],
  );

  const setSampleImage = useCallback(async (s: SampleInfo) => {
    setResult(null);
    setError(null);
    try {
      const resp = await fetch(s.url);
      const blob = await resp.blob();
      blobRef.current = blob;
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
      setSource({ url: s.url, filename: s.filename, origin: "sample" });
    } catch {
      setError(`Could not load sample "${s.filename}"`);
    }
  }, []);

  const setCameraCapture = useCallback((blob: Blob, filename: string) => {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    const url = URL.createObjectURL(blob);
    objectUrlRef.current = url;
    blobRef.current = blob;
    setResult(null);
    setError(null);
    setSource({ url, filename, origin: "upload" });
  }, []);

  // Re-run whenever the source or a server-side parameter changes (debounced).
  const serverParamsKey = useMemo(
    () =>
      [
        source?.url,
        controls.sensitivity,
        controls.minArea,
        controls.maxArea,
        controls.engine,
        controls.showBoxes,
      ].join("|"),
    [source, controls.sensitivity, controls.minArea, controls.maxArea, controls.engine, controls.showBoxes],
  );

  useEffect(() => {
    if (!source || !blobRef.current) return;
    const t = setTimeout(() => {
      runSegment(blobRef.current!, source.filename, controls);
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serverParamsKey]);

  const patchControls = useCallback(
    (patch: Partial<ControlState>) => setControls((c) => ({ ...c, ...patch })),
    [],
  );

  const handleDownload = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (!blob) return;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      const stem = (source?.filename ?? "image").replace(/\.[^.]+$/, "");
      a.download = `${stem}_acne_segmentation.png`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    }, "image/png");
  }, [source]);

  return (
    <div className="mx-auto min-h-full max-w-7xl px-4 py-6">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-100">
            🔬 Acne Image Segmentation
          </h1>
          <p className="text-xs text-slate-400">
            Detects and outlines acne lesions, counts them, and estimates a
            severity band.
          </p>
        </div>
        <span className="rounded-md border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-[11px] text-amber-200">
          Demonstration only — not a medical device
        </span>
      </header>

      <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)_320px]">
        {/* Left: input */}
        <aside className="space-y-5">
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
          <div>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Sample images
            </h2>
            <SampleGallery
              samples={samples}
              activeUrl={source?.origin === "sample" ? source.url : null}
              onPick={setSampleImage}
              busy={busy}
            />
          </div>
        </aside>

        {/* Center: canvas */}
        <main className="space-y-3">
          <ImageCanvas
            canvasRef={canvasRef}
            originalUrl={source?.url ?? null}
            result={result}
            view={controls.view}
            opacity={controls.opacity}
            showBoxes={controls.showBoxes}
          />
          {busy && (
            <p className="text-center text-xs text-sky-300">Analysing image…</p>
          )}
        </main>

        {/* Right: controls + results */}
        <aside className="space-y-6">
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Controls
            </h2>
            <Controls
              state={controls}
              onChange={patchControls}
              unetAvailable={unetAvailable}
              busy={busy}
            />
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <ResultsPanel
              result={result}
              busy={busy}
              error={error}
              onDownload={handleDownload}
            />
          </div>
        </aside>
      </div>

      <footer className="mt-8 border-t border-slate-800 pt-4 text-[11px] leading-relaxed text-slate-500">
        Severity is a heuristic index derived from lesion count and involved skin
        area (GAGS-inspired), not a validated clinical grade. Sample photos are
        from Wikimedia Commons under their respective Creative Commons licenses,
        plus locally generated synthetic images. Do not use this tool for
        diagnosis or treatment decisions.
      </footer>
    </div>
  );
}
