import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useCamera } from "./useCamera";

const originalMediaDevices = navigator.mediaDevices;

function setMediaDevices(value: unknown) {
  Object.defineProperty(navigator, "mediaDevices", {
    value,
    configurable: true,
    writable: true,
  });
}

function fakeStream() {
  const track = { stop: vi.fn(), kind: "video" };
  return {
    getTracks: () => [track],
    _track: track,
  } as unknown as MediaStream & { _track: { stop: ReturnType<typeof vi.fn> } };
}

afterEach(() => {
  setMediaDevices(originalMediaDevices);
  vi.restoreAllMocks();
});

describe("useCamera", () => {
  beforeEach(() => {
    setMediaDevices({ getUserMedia: vi.fn() });
  });

  it("starts idle", () => {
    const { result } = renderHook(() => useCamera());
    expect(result.current.status).toBe("idle");
  });

  it("reaches streaming on success", async () => {
    const stream = fakeStream();
    (navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>).mockResolvedValue(
      stream,
    );

    const { result } = renderHook(() => useCamera());
    await act(async () => {
      await result.current.start();
    });

    await waitFor(() => expect(result.current.status).toBe("streaming"));
    expect(result.current.error).toBeNull();
  });

  it("reports denied when permission is refused", async () => {
    const err = new Error("denied");
    err.name = "NotAllowedError";
    (navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>).mockRejectedValue(
      err,
    );

    const { result } = renderHook(() => useCamera());
    await act(async () => {
      await result.current.start();
    });

    expect(result.current.status).toBe("denied");
    expect(result.current.error).toMatch(/permission/i);
  });

  it("reports unavailable when mediaDevices is missing", async () => {
    setMediaDevices(undefined);

    const { result } = renderHook(() => useCamera());
    await act(async () => {
      await result.current.start();
    });

    expect(result.current.status).toBe("unavailable");
    expect(result.current.error).toMatch(/https|secure/i);
  });

  it("stops every track on stop()", async () => {
    const stream = fakeStream();
    (navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>).mockResolvedValue(
      stream,
    );

    const { result } = renderHook(() => useCamera());
    await act(async () => {
      await result.current.start();
    });
    act(() => result.current.stop());

    expect(stream._track.stop).toHaveBeenCalled();
    expect(result.current.status).toBe("idle");
  });
});
