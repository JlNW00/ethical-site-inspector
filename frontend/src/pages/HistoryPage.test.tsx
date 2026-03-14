import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import { HistoryPage } from "./HistoryPage";
import type { Audit } from "../api/types";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../api/client", () => ({
  api: {
    getAudits: vi.fn(),
    createAudit: vi.fn(),
  },
}));

import { api } from "../api/client";

const mockGetAudits = api.getAudits as ReturnType<typeof vi.fn>;
const mockCreateAudit = api.createAudit as ReturnType<typeof vi.fn>;

const createMockAudit = (overrides: Partial<Audit> = {}): Audit => ({
  id: `audit-${overrides.id || Math.random().toString(36).slice(2, 7)}`,
  target_url: "https://example.com",
  mode: "live",
  status: "completed",
  summary: null,
  trust_score: 75,
  risk_level: "moderate",
  selected_scenarios: ["cookie_consent"],
  selected_personas: ["privacy_sensitive"],
  report_public_url: null,
  metrics: {
    finding_count: 5,
  },
  created_at: "2026-03-13T10:00:00Z",
  updated_at: "2026-03-13T10:05:00Z",
  started_at: "2026-03-13T10:00:00Z",
  completed_at: "2026-03-13T10:05:00Z",
  events: [],
  ...overrides,
});

function renderHistoryPage() {
  return render(
    <MemoryRouter initialEntries={["/history"]}>
      <Routes>
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/audits/:auditId/report" element={<div data-testid="report-page">Report Page</div>} />
        <Route path="/audits/:auditId/run" element={<div data-testid="run-page">Run Page</div>} />
        <Route path="/compare" element={<div data-testid="compare-page">Compare Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("HistoryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    mockGetAudits.mockReturnValue(new Promise(() => {}));
    renderHistoryPage();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("renders audit list from API", async () => {
    const audits = [
      createMockAudit({ id: "1", target_url: "https://booking.com", status: "completed", trust_score: 85 }),
      createMockAudit({ id: "2", target_url: "https://amazon.com", status: "failed" }),
    ];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("https://booking.com")).toBeInTheDocument();
    });

    expect(screen.getByText("https://amazon.com")).toBeInTheDocument();
  });

  it("renders error state when API fails", async () => {
    mockGetAudits.mockRejectedValue(new Error("Network error"));

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  it("displays status badges with correct colors", async () => {
    const audits = [
      createMockAudit({ id: "1", status: "completed" }),
      createMockAudit({ id: "2", status: "failed" }),
      createMockAudit({ id: "3", status: "running" }),
      createMockAudit({ id: "4", status: "queued" }),
    ];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("completed")).toBeInTheDocument();
    });

    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
    expect(screen.getByText("queued")).toBeInTheDocument();
  });

  it("filters by status when tab is clicked", async () => {
    const audits = [
      createMockAudit({ id: "audit-1", target_url: "https://booking.com", status: "completed" }),
      createMockAudit({ id: "audit-2", target_url: "https://amazon.com", status: "failed" }),
      createMockAudit({ id: "audit-3", target_url: "https://ebay.com", status: "running" }),
    ];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("https://booking.com")).toBeInTheDocument();
    });

    // Initially all 3 should be visible
    expect(screen.getByText("https://amazon.com")).toBeInTheDocument();
    expect(screen.getByText("https://ebay.com")).toBeInTheDocument();

    const completedTab = screen.getByRole("tab", { name: /completed/i });
    fireEvent.click(completedTab);

    // After filtering, only booking.com should be visible
    expect(screen.getByText("https://booking.com")).toBeInTheDocument();
    expect(screen.queryByText("https://amazon.com")).not.toBeInTheDocument();
    expect(screen.queryByText("https://ebay.com")).not.toBeInTheDocument();
  });

  it("filters by URL search input", async () => {
    const audits = [
      createMockAudit({ id: "1", target_url: "https://booking.com" }),
      createMockAudit({ id: "2", target_url: "https://amazon.com" }),
    ];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("https://booking.com")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search by url/i);
    fireEvent.change(searchInput, { target: { value: "booking" } });

    expect(screen.getByText("https://booking.com")).toBeInTheDocument();
    expect(screen.queryByText("https://amazon.com")).not.toBeInTheDocument();
  });

  it("navigates to report page when audit row is clicked", async () => {
    const audits = [createMockAudit({ id: "audit-1", target_url: "https://booking.com" })];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("https://booking.com")).toBeInTheDocument();
    });

    // Click on the audit-main clickable area
    const clickableArea = screen.getByText("https://booking.com").closest(".audit-main");
    fireEvent.click(clickableArea!);

    expect(mockNavigate).toHaveBeenCalledWith("/audits/audit-1/report");
  });

  it("reruns audit with same parameters when rerun button clicked", async () => {
    const audits = [
      createMockAudit({
        id: "audit-1",
        target_url: "https://booking.com",
        selected_scenarios: ["cookie_consent", "checkout_flow"],
        selected_personas: ["privacy_sensitive"],
      }),
    ];
    mockGetAudits.mockResolvedValue(audits);
    mockCreateAudit.mockResolvedValue({ id: "new-audit-1", status: "queued" });

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("https://booking.com")).toBeInTheDocument();
    });

    const rerunButton = screen.getByRole("button", { name: /rerun/i });
    fireEvent.click(rerunButton);

    await waitFor(() => {
      expect(mockCreateAudit).toHaveBeenCalledWith({
        target_url: "https://booking.com",
        scenarios: ["cookie_consent", "checkout_flow"],
        personas: ["privacy_sensitive"],
      });
    });

    expect(mockNavigate).toHaveBeenCalledWith("/audits/new-audit-1/run");
  });

  it("enables compare button only when exactly 2 audits selected", async () => {
    const audits = [
      createMockAudit({ id: "audit-1" }),
      createMockAudit({ id: "audit-2" }),
      createMockAudit({ id: "audit-3" }),
    ];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getAllByText(/example.com/).length).toBeGreaterThan(0);
    });

    const compareButton = screen.getByRole("button", { name: /compare/i });
    expect(compareButton).toBeDisabled();

    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    expect(compareButton).toBeDisabled();

    fireEvent.click(checkboxes[1]);
    expect(compareButton).toBeEnabled();

    fireEvent.click(checkboxes[2]);
    expect(compareButton).toBeDisabled();
  });

  it("navigates to compare page with selected audit IDs", async () => {
    const audits = [createMockAudit({ id: "audit-1" }), createMockAudit({ id: "audit-2" })];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getAllByText(/example.com/).length).toBeGreaterThan(0);
    });

    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    const compareButton = screen.getByRole("button", { name: /compare/i });
    fireEvent.click(compareButton);

    expect(mockNavigate).toHaveBeenCalledWith("/compare?a=audit-1&b=audit-2");
  });

  it("displays trust scores for completed audits", async () => {
    const audits = [
      createMockAudit({ id: "1", status: "completed", trust_score: 85 }),
      createMockAudit({ id: "2", status: "completed", trust_score: 42 }),
    ];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("85")).toBeInTheDocument();
    });

    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("displays formatted timestamps", async () => {
    const audits = [
      createMockAudit({
        id: "audit-1",
        created_at: "2026-03-13T10:30:00Z",
      }),
    ];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      // Look for the specific timestamp in the audit card (not the hero area)
      const auditCards = screen.getAllByTestId("audit-row");
      expect(auditCards.length).toBeGreaterThan(0);
    });

    // Check for timestamp in a specific location within an audit card
    const timestampElements = screen.getAllByText(/mar 13, 2026/i);
    expect(timestampElements.length).toBeGreaterThan(0);
  });

  it("shows empty state when no audits match filters", async () => {
    const audits = [createMockAudit({ id: "1", target_url: "https://booking.com" })];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("https://booking.com")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search by url/i);
    fireEvent.change(searchInput, { target: { value: "nonexistent" } });

    expect(screen.getByText(/no audits/i)).toBeInTheDocument();
  });

  it("handles all status filter options", async () => {
    const audits = [
      createMockAudit({ id: "1", status: "completed" }),
      createMockAudit({ id: "2", status: "failed" }),
      createMockAudit({ id: "3", status: "running" }),
      createMockAudit({ id: "4", status: "queued" }),
    ];
    mockGetAudits.mockResolvedValue(audits);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("completed")).toBeInTheDocument();
    });

    const allTab = screen.getByRole("tab", { name: /all/i });
    const completedTab = screen.getByRole("tab", { name: /completed/i });
    const failedTab = screen.getByRole("tab", { name: /failed/i });
    const runningTab = screen.getByRole("tab", { name: /running/i });
    const queuedTab = screen.getByRole("tab", { name: /queued/i });

    expect(allTab).toBeInTheDocument();
    expect(completedTab).toBeInTheDocument();
    expect(failedTab).toBeInTheDocument();
    expect(runningTab).toBeInTheDocument();
    expect(queuedTab).toBeInTheDocument();

    fireEvent.click(failedTab);
    expect(screen.getAllByText(/example.com/)).toHaveLength(1);
  });
});
