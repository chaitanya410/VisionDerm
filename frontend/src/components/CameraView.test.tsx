import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CameraView from "./CameraView";

function setMediaDevices(value: unknown) {
  Object.defineProperty(navigator, "mediaDevices", {
    value,
    configurable: true,
    writable: true,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("CameraView", () => {
  it("offers a start control before the camera is running", () => {
    setMediaDevices({ getUserMedia: vi.fn() });
    render(<CameraView onCapture={vi.fn()} busy={false} />);
    expect(screen.getByRole("button", { name: /start camera/i })).toBeInTheDocument();
  });

  it("explains the secure-context requirement when unavailable", async () => {
    setMediaDevices(undefined);
    render(<CameraView onCapture={vi.fn()} busy={false} />);

    await userEvent.click(screen.getByRole("button", { name: /start camera/i }));

    expect(await screen.findByText(/https|localhost/i)).toBeInTheDocument();
  });

  it("surfaces a blocked permission to the user", async () => {
    const err = new Error("no");
    err.name = "NotAllowedError";
    setMediaDevices({ getUserMedia: vi.fn().mockRejectedValue(err) });

    render(<CameraView onCapture={vi.fn()} busy={false} />);
    await userEvent.click(screen.getByRole("button", { name: /start camera/i }));

    expect(await screen.findByText(/permission/i)).toBeInTheDocument();
  });

  it("states that images are not stored", () => {
    setMediaDevices({ getUserMedia: vi.fn() });
    render(<CameraView onCapture={vi.fn()} busy={false} />);
    expect(screen.getByText(/never (stored|saved)/i)).toBeInTheDocument();
  });
});
