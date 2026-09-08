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
  } as unknown as HTMLCanvasElement & {
    _ctx: { drawImage: ReturnType<typeof vi.fn> };
  };
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
