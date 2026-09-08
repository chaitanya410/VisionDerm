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
