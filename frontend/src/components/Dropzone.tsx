import { useCallback } from "react";
import { useDropzone } from "react-dropzone";

interface Props {
  onFile: (file: File) => void;
  busy: boolean;
}

export default function Dropzone({ onFile, busy }: Props) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted[0]) onFile(accepted[0]);
    },
    [onFile],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".jpg", ".jpeg", ".png", ".webp", ".bmp"] },
    multiple: false,
    disabled: busy,
  });

  return (
    <div
      {...getRootProps()}
      className={`cursor-pointer rounded-xl border-2 border-dashed px-4 py-8 text-center transition
        ${
          isDragActive
            ? "border-sky-400 bg-sky-400/10"
            : "border-slate-700 bg-slate-900/40 hover:border-slate-500"
        }
        ${busy ? "pointer-events-none opacity-50" : ""}`}
    >
      <input {...getInputProps()} />
      <div className="text-3xl">📤</div>
      <p className="mt-2 text-sm font-medium text-slate-200">
        Drop a face photo here
      </p>
      <p className="text-xs text-slate-400">or click to browse — JPG / PNG, max 12 MB</p>
    </div>
  );
}
