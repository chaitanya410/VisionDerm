import { describe, it, expect } from "vitest";

describe("test infrastructure", () => {
  it("runs in a DOM environment", () => {
    const el = document.createElement("div");
    el.textContent = "ok";
    expect(el.textContent).toBe("ok");
  });
});
