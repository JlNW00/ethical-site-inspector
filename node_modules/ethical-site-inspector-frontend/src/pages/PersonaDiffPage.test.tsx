import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import { PersonaDiffPage } from "./PersonaDiffPage";
import type { Audit, Finding } from "../api/types";

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
    getAudit: vi.fn(),
    getFindings: vi.fn(),
  },
}));

import { api } from "../api/client";

const mockGetAudit = api.getAudit as ReturnType<typeof vi.fn>;
const mockGetFindings = api.getFindings as ReturnType<typeof vi.fn>;

const createMockFinding = (overrides: Partial<Finding> = {}): Finding => ({
  id: `finding-${overrides.id || Math.random().toString(36).slice(2, 7)}`,
  scenario: "cookie_consent",
  persona: "privacy_sensitive",
  pattern_family: "manipulative_design",
  severity: "high",
  title: "Dark pattern detected",
  explanation: "Explanation of the finding",
  remediation: "How to fix this",
  evidence_excerpt: "Evidence text",
  rule_reason: "Why this matters",
  evidence_payload: {
    source: "classifier",
    source_label: "Nova AI evidence",
    site_host: "example.com",
    page_title: "Example Page",
    page_url: "https://example.com/page",
    matched_prices: [],
    button_labels: [],
    matched_buttons: [],
    supporting_evidence: [],
    price_points: [],
    friction_indicators: [],
    checkbox_states: {},
    activity_log: [],
  },
  confidence: 0.85,
  trust_impact: 0.3,
  order_index: 1,
  created_at: "2026-03-13T10:00:00Z",
  ...overrides,
});

const createMockAudit = (overrides: Partial<Audit> = {}): Audit => ({
  id: `audit-${overrides.id || Math.random().toString(36).slice(2, 7)}`,
  target_url: "https://example.com",
  mode: "live",
  status: "completed",
  summary: "Test summary",
  trust_score: 75,
  risk_level: "moderate",
  selected_scenarios: ["cookie_consent", "checkout_flow"],
  selected_personas: ["privacy_sensitive", "cost_sensitive"],
  report_public_url: null,
  metrics: {
    finding_count: 6,
    observation_count: 12,
    persona_comparison: [
      {
        persona: "privacy_sensitive",
        headline: "Privacy-focused journey",
        finding_count: 4,
        friction_index: 0.6,
        average_steps: 5,
        price_delta: 0,
        notable_patterns: ["manipulative_design", "obstruction"],
      },
      {
        persona: "cost_sensitive",
        headline: "Price-focused journey",
        finding_count: 2,
        friction_index: 0.3,
        average_steps: 4,
        price_delta: -15,
        notable_patterns: ["deceptive_content"],
      },
    ],
  },
  created_at: "2026-03-13T10:00:00Z",
  updated_at: "2026-03-13T10:05:00Z",
  started_at: "2026-03-13T10:00:00Z",
  completed_at: "2026-03-13T10:05:00Z",
  events: [],
  ...overrides,
});

function renderPersonaDiffPage(auditId = "audit-123") {
  return render(
    <MemoryRouter initialEntries={[`/audits/${auditId}/diff`]}>
      <Routes>
        <Route path="/audits/:auditId/diff" element={<PersonaDiffPage />} />
        <Route path="/audits/:auditId/report" element={<div data-testid="report-page">Report Page</div>} />
        <Route path="/history" element={<div data-testid="history-page">History Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PersonaDiffPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    mockGetAudit.mockReturnValue(new Promise(() => {}));
    mockGetFindings.mockReturnValue(new Promise(() => {}));

    renderPersonaDiffPage();

    expect(screen.getByText(/loading persona comparison/i)).toBeInTheDocument();
  });

  it("renders error state when API fails", async () => {
    mockGetAudit.mockRejectedValue(new Error("Network error"));

    renderPersonaDiffPage();

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  it("renders persona columns when data loads", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive", "cost_sensitive"],
    });
    const findings: Finding[] = [
      createMockFinding({ persona: "privacy_sensitive", severity: "high" }),
      createMockFinding({ persona: "cost_sensitive", severity: "medium" }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      // Use role selector to find the specific persona name heading
      const personaHeadings = screen.getAllByRole("heading", { name: /Privacy Sensitive/i });
      expect(personaHeadings.length).toBeGreaterThan(0);
    });

    expect(screen.getByText(/Cost Sensitive/i)).toBeInTheDocument();
  });

  it("displays persona-specific findings in columns", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive", "cost_sensitive"],
    });
    const findings = [
      createMockFinding({
        id: "f1",
        persona: "privacy_sensitive",
        title: "Privacy finding 1",
        severity: "high",
      }),
      createMockFinding({
        id: "f2",
        persona: "privacy_sensitive",
        title: "Privacy finding 2",
        severity: "medium",
      }),
      createMockFinding({
        id: "f3",
        persona: "cost_sensitive",
        title: "Cost finding 1",
        severity: "low",
      }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      expect(screen.getByText("Privacy finding 1")).toBeInTheDocument();
    });

    expect(screen.getByText("Privacy finding 2")).toBeInTheDocument();
    expect(screen.getByText("Cost finding 1")).toBeInTheDocument();
  });

  it("highlights differences between personas", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive", "cost_sensitive"],
    });
    const findings = [
      createMockFinding({
        id: "f1",
        persona: "privacy_sensitive",
        title: "Privacy specific finding",
        pattern_family: "manipulative_design",
      }),
      createMockFinding({
        id: "f2",
        persona: "cost_sensitive",
        title: "Cost specific finding",
        pattern_family: "deceptive_content",
      }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      expect(screen.getByText(/differences found/i)).toBeInTheDocument();
    });
  });

  it("shows price delta indicators when personas have different prices", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive", "cost_sensitive"],
      metrics: {
        persona_comparison: [
          {
            persona: "privacy_sensitive",
            headline: "Privacy journey",
            finding_count: 2,
            friction_index: 0.5,
            average_steps: 4,
            price_delta: 0,
            notable_patterns: [],
          },
          {
            persona: "cost_sensitive",
            headline: "Cost journey",
            finding_count: 3,
            friction_index: 0.4,
            average_steps: 5,
            price_delta: -25,
            notable_patterns: [],
          },
        ],
      },
    });
    const findings = [
      createMockFinding({
        persona: "privacy_sensitive",
        evidence_payload: {
          matched_prices: [{ label: "total", value: 100, raw: "$100.00" }],
        },
      }),
      createMockFinding({
        persona: "cost_sensitive",
        evidence_payload: {
          matched_prices: [{ label: "total", value: 75, raw: "$75.00" }],
        },
      }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      expect(screen.getByText(/\$25\.00/i)).toBeInTheDocument();
    });
  });

  it("navigates to report page when 'View Report' is clicked", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings: Finding[] = [];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      expect(screen.getByText(/back to report/i)).toBeInTheDocument();
    });

    const backButton = screen.getByText(/back to report/i).closest("a");
    expect(backButton).toHaveAttribute("href", "/audits/audit-123/report");
  });

  it("navigates to history page when 'Back to History' is clicked", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings: Finding[] = [];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      // Find the button link specifically using role
      const buttons = screen.getAllByRole("link", { name: /back to history/i });
      expect(buttons.length).toBeGreaterThan(0);
    });

    const historyLink = screen.getByRole("link", { name: /back to history/i });
    expect(historyLink).toHaveAttribute("href", "/history");
  });

  it("displays action paths for each persona", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive", "cost_sensitive"],
    });
    const findings: Finding[] = [
      createMockFinding({
        persona: "privacy_sensitive",
        evidence_payload: {
          interacted_controls: [
            "Clicked Accept Cookies",
            "Viewed Privacy Policy",
            "Closed Banner",
          ],
        },
      }),
      createMockFinding({
        persona: "cost_sensitive",
        evidence_payload: {
          interacted_controls: [
            "Clicked Accept Cookies",
            "Viewed Pricing",
            "Clicked Checkout",
          ],
        },
      }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      // Look for the section label specifically
      const sectionLabels = screen.getAllByText("Observed Path");
      expect(sectionLabels.length).toBeGreaterThan(0);
    });
  });

  it("displays UI controls found for each persona", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive"],
    });
    const findings: Finding[] = [
      createMockFinding({
        persona: "privacy_sensitive",
        evidence_payload: {
          matched_buttons: ["Accept All", "Reject All", "Customize"],
        },
      }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      // Use getAllByText since controls may appear multiple times
      const acceptAllElements = screen.getAllByText(/accept all/i);
      expect(acceptAllElements.length).toBeGreaterThan(0);
    });

    expect(screen.getByText(/reject all/i)).toBeInTheDocument();
    expect(screen.getByText(/customize/i)).toBeInTheDocument();
  });

  it("shows empty state when no findings for a persona", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive", "cost_sensitive"],
    });
    const findings = [
      createMockFinding({ persona: "privacy_sensitive", title: "Only privacy finding" }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      expect(screen.getByText(/Only privacy finding/i)).toBeInTheDocument();
    });

    expect(screen.getAllByText(/no findings/i).length).toBeGreaterThan(0);
  });

  it("displays scenario breakdown for each persona", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_scenarios: ["cookie_consent", "checkout_flow"],
      selected_personas: ["privacy_sensitive"],
    });
    const findings: Finding[] = [
      createMockFinding({ persona: "privacy_sensitive", scenario: "cookie_consent" }),
      createMockFinding({ persona: "privacy_sensitive", scenario: "checkout_flow" }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      // Scenario titles appear as heading level 5
      const cookieConsentHeadings = screen.getAllByRole("heading", { name: /Cookie Consent/i });
      expect(cookieConsentHeadings.length).toBeGreaterThan(0);
    });

    expect(screen.getByText(/Checkout Flow/i)).toBeInTheDocument();
  });

  it("displays trust score comparison", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      trust_score: 72,
      metrics: {
        persona_comparison: [
          {
            persona: "privacy_sensitive",
            headline: "Privacy journey",
            finding_count: 4,
            friction_index: 0.6,
            average_steps: 5,
            price_delta: 0,
            notable_patterns: ["obstruction"],
          },
          {
            persona: "cost_sensitive",
            headline: "Cost journey",
            finding_count: 2,
            friction_index: 0.3,
            average_steps: 4,
            price_delta: -15,
            notable_patterns: ["deceptive_content"],
          },
        ],
      },
    });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderPersonaDiffPage();

    await waitFor(() => {
      expect(screen.getByText(/72/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Trust Score/i)).toBeInTheDocument();
  });

  it("shows summary of key differences at top", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive", "cost_sensitive"],
      metrics: {
        persona_comparison: [
          {
            persona: "privacy_sensitive",
            headline: "Privacy journey",
            finding_count: 4,
            friction_index: 0.6,
            average_steps: 5,
            price_delta: 0,
            notable_patterns: ["manipulative_design"],
          },
          {
            persona: "cost_sensitive",
            headline: "Cost journey",
            finding_count: 2,
            friction_index: 0.3,
            average_steps: 4,
            price_delta: -15,
            notable_patterns: ["deceptive_content"],
          },
        ],
      },
    });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderPersonaDiffPage();

    await waitFor(() => {
      // Look for the "Key Differences" section header
      expect(screen.getByText(/key differences/i)).toBeInTheDocument();
    });
  });

  it("handles single persona gracefully", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive"],
    });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderPersonaDiffPage();

    await waitFor(() => {
      expect(screen.getByText(/Privacy Sensitive/i)).toBeInTheDocument();
    });

    expect(screen.queryByText(/Cost Sensitive/i)).not.toBeInTheDocument();
  });

  it("displays severity indicators in findings", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive"],
    });
    const findings = [
      createMockFinding({
        persona: "privacy_sensitive",
        severity: "critical",
        title: "Critical finding",
      }),
      createMockFinding({
        persona: "privacy_sensitive",
        severity: "low",
        title: "Low priority finding",
      }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderPersonaDiffPage();

    await waitFor(() => {
      expect(screen.getByText("critical")).toBeInTheDocument();
    });

    expect(screen.getByText("low")).toBeInTheDocument();
  });
});
