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
