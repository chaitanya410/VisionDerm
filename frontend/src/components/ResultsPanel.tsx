import type { SegmentResponse } from "../api";

interface Props {
  result: SegmentResponse | null;
  busy: boolean;
  error: string | null;
  onDownload: () => void;
}

const SEVERITY_STYLE: Record<string, string> = {
  Clear: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  Mild: "bg-lime-500/15 text-lime-300 border-lime-500/40",
  Moderate: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  Severe: "bg-rose-500/15 text-rose-300 border-rose-500/40",
};

export default function ResultsPanel({ result, busy, error, onDownload }: Props) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Results</h2>
        {result && (
          <span className="rounded-md border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-400">
            {result.engine === "unet" ? "U-Net" : "Classical"} · {result.elapsed_ms} ms
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
          {error}
        </div>
      )}

      {!result && !error && (
        <p className="text-xs text-slate-500">
          {busy ? "Analysing…" : "Run a segmentation to see lesion counts and severity."}
        </p>
      )}

      {result && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">
                Lesions
              </div>
              <div className="mt-1 text-3xl font-bold tabular-nums text-slate-100">
                {result.count}
              </div>
            </div>
            <div
              className={`rounded-xl border p-3 ${
                SEVERITY_STYLE[result.severity.label] ?? SEVERITY_STYLE.Clear
              }`}
            >
              <div className="text-[11px] uppercase tracking-wide opacity-70">
                Severity
              </div>
              <div className="mt-1 text-2xl font-bold">{result.severity.label}</div>
              <div className="text-[11px] opacity-70">
                index {result.severity.score.toFixed(2)}
              </div>
            </div>
          </div>

          <button
            onClick={onDownload}
            className="w-full rounded-lg border border-sky-500/50 bg-sky-500/15 px-3 py-2 text-sm font-medium text-sky-200 transition hover:bg-sky-500/25"
          >
            ⬇ Download annotated PNG
          </button>

          <div className="rounded-xl border border-slate-800">
            <div className="border-b border-slate-800 px-3 py-2 text-[11px] uppercase tracking-wide text-slate-500">
              Lesion detail ({result.lesions.length})
            </div>
            <div className="scroll-thin max-h-60 overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-slate-900 text-slate-500">
                  <tr>
                    <th className="px-3 py-1.5 font-medium">#</th>
                    <th className="px-3 py-1.5 font-medium">Centroid (x, y)</th>
                    <th className="px-3 py-1.5 font-medium">Area px²</th>
                    <th className="px-3 py-1.5 font-medium">Score</th>
                  </tr>
                </thead>
                <tbody className="text-slate-300">
                  {result.lesions.map((l) => (
                    <tr key={l.id} className="border-t border-slate-800/60">
                      <td className="px-3 py-1.5 tabular-nums">{l.id}</td>
                      <td className="px-3 py-1.5 tabular-nums">
                        {l.centroid[0].toFixed(0)}, {l.centroid[1].toFixed(0)}
                      </td>
                      <td className="px-3 py-1.5 tabular-nums">{l.area_px}</td>
                      <td className="px-3 py-1.5 tabular-nums">{l.score.toFixed(2)}</td>
                    </tr>
                  ))}
                  {result.lesions.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-3 py-3 text-center text-slate-500">
                        No lesions detected at this sensitivity.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <p className="text-[11px] leading-relaxed text-slate-500">{result.severity.note}</p>
        </>
      )}
    </div>
  );
}
