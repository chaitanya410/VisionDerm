import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

beforeEach(() => {
  Object.defineProperty(navigator, "mediaDevices", {
    value: { getUserMedia: vi.fn() },
    configurable: true,
    writable: true,
  });
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response("[]", {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
});

afterEach(() => vi.restoreAllMocks());

describe("App input modes", () => {
  it("shows the upload dropzone by default", () => {
    render(<App />);
    expect(screen.getByRole("tab", { name: /upload/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("switches to the camera panel", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("tab", { name: /camera/i }));
    expect(
      await screen.findByRole("button", { name: /start camera/i }),
    ).toBeInTheDocument();
  });
});
