import type { SampleInfo } from "../api";

interface Props {
  samples: SampleInfo[];
  activeUrl: string | null;
  onPick: (s: SampleInfo) => void;
  busy: boolean;
}

export default function SampleGallery({ samples, activeUrl, onPick, busy }: Props) {
  if (samples.length === 0) {
    return (
      <p className="text-xs text-slate-500">
        No sample images. Run <code className="text-slate-300">python data/fetch_samples.py</code>.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
      {samples.map((s) => {
        const active = activeUrl === s.url;
        return (
          <button
            key={s.id}
            onClick={() => onPick(s)}
            disabled={busy}
            title={s.license ? `${s.id} — ${s.license}` : s.id}
            className={`group relative aspect-square overflow-hidden rounded-lg border transition
              ${active ? "border-sky-400 ring-2 ring-sky-400/50" : "border-slate-700 hover:border-slate-500"}
              ${busy ? "opacity-50" : ""}`}
          >
            <img
              src={s.url}
              alt={s.id}
              loading="lazy"
              className="h-full w-full object-cover transition group-hover:scale-105"
            />
          </button>
        );
      })}
    </div>
  );
}
