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
