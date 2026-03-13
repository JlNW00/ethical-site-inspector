import { describe, it, expect } from "vitest";

import { titleize, relativeTime } from "./format";

describe("titleize", () => {
  it('converts "cookie_consent" to "Cookie Consent"', () => {
    expect(titleize("cookie_consent")).toBe("Cookie Consent");
  });

  it('converts "checkout_flow" to "Checkout Flow"', () => {
    expect(titleize("checkout_flow")).toBe("Checkout Flow");
  });

  it('converts "single" to "Single"', () => {
    expect(titleize("single")).toBe("Single");
  });

  it("returns empty string for empty input", () => {
    expect(titleize("")).toBe("");
  });
});

describe("relativeTime", () => {
  it("returns a non-empty string for a valid ISO date", () => {
    const result = relativeTime("2025-06-15T12:30:00Z");
    expect(result).toBeTruthy();
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });
});
