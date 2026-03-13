import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { ComparePage } from "./ComparePage";
import { api } from "../api/client";
import type { Audit, Finding } from "../api/types";

// Mock the API client
vi.mock("../api/client", () => ({
  api: {
    getAudit: vi.fn(),
    getFindings: vi.fn(),
  },
}));

// Mock react-router-dom's useSearchParams
const mockSearchParams = new globalThis.URLSearchParams();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useSearchParams: () => [mockSearchParams],
    Link: ({ children, to }: { children: React.ReactNode; to: string }) =>
      React.createElement("a", { href: to, "data-testid": "link" }, children),
  };
});

const mockAuditA: Audit = {
  id: "audit-a-123",
  target_url: "https://example.com",
  mode: "live",
  status: "completed",
  summary: "Test summary A",
  trust_score: 75,
  risk_level: "moderate",
  selected_scenarios: ["checkout_flow", "cookie_consent"],
  selected_personas: ["privacy_sensitive"],
  report_public_url: null,
  metrics: {
    finding_count: 8,
    observation_count: 12,
    site_host: "example.com",
    evidence_origin_label: "Nova AI + Rule Engine",
    persona_comparison: [
      {
        persona: "privacy_sensitive",
        headline: "Privacy focused user",
        finding_count: 8,
        friction_index: 0.3,
        average_steps: 5,
        price_delta: 0,
        notable_patterns: ["cookie_deception"],
      },
    ],
    scenario_breakdown: [
      {
        scenario: "checkout_flow",
        headline: "Checkout issues found",
        risk_level: "moderate",
        finding_count: 5,
        dominant_patterns: ["hidden_costs"],
      },
      {
        scenario: "cookie_consent",
        headline: "Cookie banner issues",
        risk_level: "low",
        finding_count: 3,
        dominant_patterns: ["asymmetric_choice"],
      },
    ],
  },
  created_at: "2026-03-10T10:00:00Z",
  updated_at: "2026-03-10T10:15:00Z",
  started_at: "2026-03-10T10:00:00Z",
  completed_at: "2026-03-10T10:15:00Z",
  events: [],
};

const mockAuditB: Audit = {
  id: "audit-b-456",
  target_url: "https://example.com",
  mode: "live",
  status: "completed",
  summary: "Test summary B",
  trust_score: 45,
  risk_level: "high",
  selected_scenarios: ["checkout_flow", "cookie_consent"],
  selected_personas: ["privacy_sensitive"],
  report_public_url: null,
  metrics: {
    finding_count: 15,
    observation_count: 22,
    site_host: "example.com",
    evidence_origin_label: "Nova AI + Rule Engine",
    persona_comparison: [
      {
        persona: "privacy_sensitive",
        headline: "Privacy focused user",
        finding_count: 15,
        friction_index: 0.7,
        average_steps: 8,
        price_delta: 12.99,
        notable_patterns: ["hidden_costs", "cookie_deception"],
      },
    ],
    scenario_breakdown: [
      {
        scenario: "checkout_flow",
        headline: "Checkout issues found",
        risk_level: "high",
        finding_count: 10,
        dominant_patterns: ["hidden_costs", "sneak_into_basket"],
      },
      {
        scenario: "cookie_consent",
        headline: "Cookie banner issues",
        risk_level: "moderate",
        finding_count: 5,
        dominant_patterns: ["asymmetric_choice", "confirmshaming"],
      },
    ],
  },
  created_at: "2026-03-11T10:00:00Z",
  updated_at: "2026-03-11T10:20:00Z",
  started_at: "2026-03-11T10:00:00Z",
  completed_at: "2026-03-11T10:20:00Z",
  events: [],
};

const mockFindingsA: Finding[] = [
  {
    id: "finding-1",
    scenario: "checkout_flow",
    persona: "privacy_sensitive",
    pattern_family: "hidden_costs",
    severity: "high",
    title: "Hidden fees detected",
    explanation: "Additional fees appeared at checkout",
    remediation: "Show all fees upfront",
    evidence_excerpt: "Price changed from $50 to $65",
    rule_reason: "price_mismatch",
    evidence_payload: {
      source: "rule_engine",
      site_host: "example.com",
      matched_prices: [{ label: "Subtotal", value: 50 }, { label: "Total", value: 65 }],
    },
    confidence: 0.85,
    trust_impact: -10,
    order_index: 1,
    created_at: "2026-03-10T10:10:00Z",
  },
];

const mockFindingsB: Finding[] = [
  {
    id: "finding-2",
    scenario: "checkout_flow",
    persona: "privacy_sensitive",
    pattern_family: "hidden_costs",
    severity: "critical",
    title: "Significant hidden fees",
    explanation: "Multiple hidden fees detected",
    remediation: "Display complete pricing",
    evidence_excerpt: "Price changed from $50 to $78",
    rule_reason: "price_mismatch",
    evidence_payload: {
      source: "rule_engine",
      site_host: "example.com",
      matched_prices: [{ label: "Subtotal", value: 50 }, { label: "Total", value: 78 }],
    },
    confidence: 0.92,
    trust_impact: -20,
    order_index: 1,
    created_at: "2026-03-11T10:10:00Z",
  },
  {
    id: "finding-3",
    scenario: "cookie_consent",
    persona: "privacy_sensitive",
    pattern_family: "confirmshaming",
    severity: "medium",
    title: "Confirmshaming detected",
    explanation: "Reject button uses shame language",
    remediation: "Use neutral language",
    evidence_excerpt: "Button says 'No, I hate savings'",
    rule_reason: "confirmshaming_language",
    evidence_payload: {
      source: "rule_engine",
      site_host: "example.com",
    },
    confidence: 0.78,
    trust_impact: -5,
    order_index: 2,
    created_at: "2026-03-11T10:15:00Z",
  },
];

function renderComparePage() {
  return render(
    <BrowserRouter>
      <ComparePage />
    </BrowserRouter>
  );
}

describe("ComparePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams.set("a", "audit-a-123");
    mockSearchParams.set("b", "audit-b-456");
  });

  it("renders loading state initially", () => {
    (api.getAudit as Mock).mockImplementation(() => new Promise(() => {}));
    (api.getFindings as Mock).mockImplementation(() => new Promise(() => {}));

    renderComparePage();

    expect(screen.getByText(/Loading comparison/i)).toBeInTheDocument();
  });

  it("shows error when audit IDs are missing", async () => {
    mockSearchParams.delete("a");
    mockSearchParams.delete("b");

    renderComparePage();

    await waitFor(() => {
      expect(screen.getByText(/Missing audit IDs/i)).toBeInTheDocument();
    });
  });

  it("displays both audit columns with trust scores", async () => {
    (api.getAudit as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve(mockAuditA);
      if (id === "audit-b-456") return Promise.resolve(mockAuditB);
      return Promise.reject(new Error("Unknown audit"));
    });
    (api.getFindings as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve({ audit_id: id, findings: mockFindingsA });
      if (id === "audit-b-456") return Promise.resolve({ audit_id: id, findings: mockFindingsB });
      return Promise.reject(new Error("Unknown audit"));
    });

    renderComparePage();

    await waitFor(() => {
      // Trust scores should be displayed - use getAllByText since they may appear in multiple places
      expect(screen.getAllByText(/75/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/45/).length).toBeGreaterThan(0);
    });
  });

  it("shows trust score delta", async () => {
    (api.getAudit as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve(mockAuditA);
      if (id === "audit-b-456") return Promise.resolve(mockAuditB);
      return Promise.reject(new Error("Unknown audit"));
    });
    (api.getFindings as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve({ audit_id: id, findings: mockFindingsA });
      if (id === "audit-b-456") return Promise.resolve({ audit_id: id, findings: mockFindingsB });
      return Promise.reject(new Error("Unknown audit"));
    });

    renderComparePage();

    await waitFor(() => {
      // Delta should be shown (45 - 75 = -30 points)
      expect(screen.getAllByText(/-30/).length).toBeGreaterThan(0);
    });
  });

  it("displays risk level comparison", async () => {
    (api.getAudit as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve(mockAuditA);
      if (id === "audit-b-456") return Promise.resolve(mockAuditB);
      return Promise.reject(new Error("Unknown audit"));
    });
    (api.getFindings as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve({ audit_id: id, findings: mockFindingsA });
      if (id === "audit-b-456") return Promise.resolve({ audit_id: id, findings: mockFindingsB });
      return Promise.reject(new Error("Unknown audit"));
    });

    renderComparePage();

    await waitFor(() => {
      // Risk levels appear in multiple places (badges, severity pills)
      expect(screen.getAllByText(/moderate/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/high/).length).toBeGreaterThan(0);
    });
  });

  it("shows finding count per scenario", async () => {
    (api.getAudit as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve(mockAuditA);
      if (id === "audit-b-456") return Promise.resolve(mockAuditB);
      return Promise.reject(new Error("Unknown audit"));
    });
    (api.getFindings as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve({ audit_id: id, findings: mockFindingsA });
      if (id === "audit-b-456") return Promise.resolve({ audit_id: id, findings: mockFindingsB });
      return Promise.reject(new Error("Unknown audit"));
    });

    renderComparePage();

    await waitFor(() => {
      // Scenario names appear in multiple places (scenario breakdown, timeline, etc.)
      expect(screen.getAllByText(/Checkout Flow/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Cookie Consent/i).length).toBeGreaterThan(0);
    });
  });

  it("displays links to individual reports", async () => {
    (api.getAudit as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve(mockAuditA);
      if (id === "audit-b-456") return Promise.resolve(mockAuditB);
      return Promise.reject(new Error("Unknown audit"));
    });
    (api.getFindings as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve({ audit_id: id, findings: mockFindingsA });
      if (id === "audit-b-456") return Promise.resolve({ audit_id: id, findings: mockFindingsB });
      return Promise.reject(new Error("Unknown audit"));
    });

    renderComparePage();

    await waitFor(() => {
      // Check for View Report links - use getAllByRole to find links by their text
      const viewReportLinks = screen.getAllByRole("link", { name: /View Report/i });
      expect(viewReportLinks.length).toBeGreaterThanOrEqual(2); // At least one per audit
      // Verify the links have correct hrefs
      expect(viewReportLinks[0]).toHaveAttribute("href", "/audits/audit-a-123/report");
    });
  });

  it("renders error state when API fails", async () => {
    (api.getAudit as Mock).mockRejectedValue(new Error("Network error"));
    (api.getFindings as Mock).mockRejectedValue(new Error("Network error"));

    renderComparePage();

    await waitFor(() => {
      // Component renders "Error: {error message}" in empty-state
      expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      expect(screen.getByText(/Network error/i)).toBeInTheDocument();
    });
  });

  it("shows key metric differences", async () => {
    (api.getAudit as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve(mockAuditA);
      if (id === "audit-b-456") return Promise.resolve(mockAuditB);
      return Promise.reject(new Error("Unknown audit"));
    });
    (api.getFindings as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve({ audit_id: id, findings: mockFindingsA });
      if (id === "audit-b-456") return Promise.resolve({ audit_id: id, findings: mockFindingsB });
      return Promise.reject(new Error("Unknown audit"));
    });

    renderComparePage();

    await waitFor(() => {
      // Finding count difference - finding arrays have 1 and 2 items, so delta is +1
      // Look for "+1" in the page (finding delta in hero pills or Key Differences section)
      expect(screen.getAllByText(/\+1/).length).toBeGreaterThan(0);
    });
  });

  it("displays target URL for both audits", async () => {
    (api.getAudit as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve(mockAuditA);
      if (id === "audit-b-456") return Promise.resolve(mockAuditB);
      return Promise.reject(new Error("Unknown audit"));
    });
    (api.getFindings as Mock).mockImplementation((id: string) => {
      if (id === "audit-a-123") return Promise.resolve({ audit_id: id, findings: mockFindingsA });
      if (id === "audit-b-456") return Promise.resolve({ audit_id: id, findings: mockFindingsB });
      return Promise.reject(new Error("Unknown audit"));
    });

    renderComparePage();

    await waitFor(() => {
      expect(screen.getAllByText(/example.com/i).length).toBeGreaterThanOrEqual(1);
    });
  });
});
