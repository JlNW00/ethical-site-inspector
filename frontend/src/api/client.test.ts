import { describe, it, expect, vi, beforeEach } from "vitest";

import { api } from "./client";

describe("api.getReportUrl", () => {
  it("returns the correct URL format", () => {
    const url = api.getReportUrl("abc-123");
    expect(url).toContain("/api/audits/abc-123/report");
  });
});

describe("request() via api methods", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("handles a successful JSON response", async () => {
    const mockData = { id: "audit-1", target_url: "https://example.com", status: "completed" };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      }),
    );

    const result = await api.getAudit("audit-1");
    expect(result).toEqual(mockData);
    expect(fetch).toHaveBeenCalledOnce();

    const [url, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/api/audits/audit-1");
    expect(init.headers["Content-Type"]).toBe("application/json");
  });

  it("throws on a non-OK response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        text: () => Promise.resolve("Not Found"),
      }),
    );

    await expect(api.getAudit("bad-id")).rejects.toThrow("Not Found");
  });

  it("throws with default message when error body is empty", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        text: () => Promise.resolve(""),
      }),
    );

    await expect(api.getAudit("bad-id")).rejects.toThrow("Request failed");
  });

  it("api.createAudit sends correct payload", async () => {
    const mockAudit = { id: "new-1", status: "queued" };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockAudit),
      }),
    );

    const payload = {
      target_url: "https://example.com",
      scenarios: ["cookie_consent"],
      personas: ["default_user"],
    };

    const result = await api.createAudit(payload);
    expect(result).toEqual(mockAudit);
    expect(fetch).toHaveBeenCalledOnce();

    const [url, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/api/audits");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify(payload));
    expect(init.headers["Content-Type"]).toBe("application/json");
  });
});
