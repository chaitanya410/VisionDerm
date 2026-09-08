import type { ViewMode } from "./ImageCanvas";

export interface ControlState {
  sensitivity: number;
  minArea: number;
  maxArea: number;
  engine: "auto" | "classical" | "unet";
  view: ViewMode;
  opacity: number;
  showBoxes: boolean;
}

interface Props {
  state: ControlState;
  onChange: (patch: Partial<ControlState>) => void;
  unetAvailable: boolean;
  busy: boolean;
}

const VIEWS: { key: ViewMode; label: string }[] = [
  { key: "overlay", label: "Overlay" },
  { key: "original", label: "Original" },
  { key: "mask", label: "Mask only" },
];

export default function Controls({ state, onChange, unetAvailable, busy }: Props) {
  return (
    <div className="space-y-5">
      <div>
        <div className="mb-1 flex justify-between text-xs text-slate-400">
          <label>Sensitivity</label>
          <span className="tabular-nums text-slate-300">{state.sensitivity.toFixed(1)}</span>
        </div>
        <input
          type="range"
          min={0.5}
          max={4}
          step={0.1}
          value={state.sensitivity}
          disabled={busy}
          onChange={(e) => onChange({ sensitivity: Number(e.target.value) })}
          className="w-full accent-sky-400"
        />
        <p className="mt-1 text-[11px] text-slate-500">
          Lower = detect more (looser), higher = detect fewer (stricter).
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label className="text-xs text-slate-400">
          Min lesion area (px²)
          <input
            type="number"
            min={1}
            max={2000}
            value={state.minArea}
            disabled={busy}
            onChange={(e) => onChange({ minArea: Number(e.target.value) })}
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-slate-200"
          />
        </label>
        <label className="text-xs text-slate-400">
          Max lesion area (px²)
          <input
            type="number"
            min={50}
            max={50000}
            value={state.maxArea}
            disabled={busy}
            onChange={(e) => onChange({ maxArea: Number(e.target.value) })}
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-slate-200"
          />
        </label>
      </div>

      <div>
        <label className="text-xs text-slate-400">Engine</label>
        <div className="mt-1 flex gap-2">
          {(["auto", "classical", "unet"] as const).map((e) => {
            const disabled = busy || (e === "unet" && !unetAvailable);
            return (
              <button
                key={e}
                disabled={disabled}
                onClick={() => onChange({ engine: e })}
                className={`flex-1 rounded-md border px-2 py-1 text-xs capitalize transition
                  ${
                    state.engine === e
                      ? "border-sky-400 bg-sky-400/15 text-sky-200"
                      : "border-slate-700 text-slate-300 hover:border-slate-500"
                  }
                  ${disabled ? "cursor-not-allowed opacity-40" : ""}`}
              >
                {e}
              </button>
            );
          })}
        </div>
        {!unetAvailable && (
          <p className="mt-1 text-[11px] text-slate-500">
            U-Net needs a trained checkpoint (see <code>backend/ml/</code>).
          </p>
        )}
      </div>

      <hr className="border-slate-800" />

      <div>
        <label className="text-xs text-slate-400">View</label>
        <div className="mt-1 flex gap-2">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              onClick={() => onChange({ view: v.key })}
              className={`flex-1 rounded-md border px-2 py-1 text-xs transition
                ${
                  state.view === v.key
                    ? "border-sky-400 bg-sky-400/15 text-sky-200"
                    : "border-slate-700 text-slate-300 hover:border-slate-500"
                }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-1 flex justify-between text-xs text-slate-400">
          <label>Overlay opacity</label>
          <span className="tabular-nums text-slate-300">
            {Math.round(state.opacity * 100)}%
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={state.opacity}
          onChange={(e) => onChange({ opacity: Number(e.target.value) })}
          className="w-full accent-sky-400"
        />
      </div>

      <label className="flex items-center gap-2 text-xs text-slate-300">
        <input
          type="checkbox"
          checked={state.showBoxes}
          onChange={(e) => onChange({ showBoxes: e.target.checked })}
          className="accent-sky-400"
        />
        Show bounding boxes
      </label>
    </div>
  );
}
