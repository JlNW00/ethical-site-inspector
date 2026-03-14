import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import { ReportPage } from "./ReportPage";
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
    getReportUrl: (id: string) => `/api/audits/${id}/report`,
    getPdfUrl: (id: string) => `/api/audits/${id}/report/pdf`,
    getCompliancePdfUrl: (id: string) => `/api/audits/${id}/report/compliance-pdf`,
  },
}));

import { api } from "../api/client";

const mockGetAudit = api.getAudit as ReturnType<typeof vi.fn>;
const mockGetFindings = api.getFindings as ReturnType<typeof vi.fn>;

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
  video_urls: null,
  metrics: {
    finding_count: 6,
    observation_count: 12,
    site_host: "example.com",
    evidence_origin_label: "Nova AI",
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
    scenario_breakdown: [
      {
        scenario: "cookie_consent",
        headline: "Cookie banner analysis",
        risk_level: "high",
        finding_count: 3,
        dominant_patterns: ["manipulative_design"],
      },
      {
        scenario: "checkout_flow",
        headline: "Checkout flow analysis",
        risk_level: "moderate",
        finding_count: 3,
        dominant_patterns: ["deceptive_content"],
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
    screenshot_urls: [],
    button_labels: [],
    matched_buttons: [],
    matched_prices: [],
    supporting_evidence: [],
    checkbox_states: {},
    price_points: [],
    friction_indicators: [],
    activity_log: [],
    interacted_controls: [],
  },
  confidence: 0.85,
  trust_impact: 0.3,
  order_index: 1,
  created_at: "2026-03-13T10:00:00Z",
  regulatory_categories: ["FTC", "GDPR"],
  suppressed: false,
  ...overrides,
});

function renderReportPage(auditId = "audit-123", searchParams = "") {
  return render(
    <MemoryRouter initialEntries={[`/audits/${auditId}/report${searchParams}`]}>
      <Routes>
        <Route path="/audits/:auditId/report" element={<ReportPage />} />
        <Route path="/audits/:auditId/diff" element={<div data-testid="diff-page">Diff Page</div>} />
        <Route path="/audits/:auditId/run" element={<div data-testid="run-page">Run Page</div>} />
        <Route path="/history" element={<div data-testid="history-page">History Page</div>} />
        <Route path="/benchmarks/:benchmarkId" element={<div data-testid="benchmark-page">Benchmark Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ReportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    mockGetAudit.mockReturnValue(new Promise(() => {}));
    mockGetFindings.mockReturnValue(new Promise(() => {}));

    renderReportPage();

    expect(screen.getByText(/loading report data/i)).toBeInTheDocument();
  });

  it("renders error state when API fails", async () => {
    mockGetAudit.mockRejectedValue(new Error("Network error"));

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  it("renders report when data loads successfully", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [createMockFinding({ id: "f1" }), createMockFinding({ id: "f2" })];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Trust Audit Report")).toBeInTheDocument();
    });

    expect(screen.getByText(/Trust Score/i)).toBeInTheDocument();
    expect(screen.getByText(/75\s*\/\s*100/)).toBeInTheDocument();
  });

  it("shows failed audit state when audit.status is failed", async () => {
    const audit = createMockAudit({ id: "audit-123", status: "failed", summary: "Timeout error" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Audit Failed")).toBeInTheDocument();
    });

    expect(screen.getByText(/encountered an error/i)).toBeInTheDocument();
    expect(screen.getByText(/Timeout error/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Back to History/i })).toBeInTheDocument();
  });

  it("displays screenshot timeline when screenshots exist", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [
      createMockFinding({
        id: "f1",
        scenario: "cookie_consent",
        persona: "privacy_sensitive",
        evidence_payload: {
          screenshot_urls: ["/artifacts/screenshots/cookie_privacy_initial.png"],
        },
      }),
      createMockFinding({
        id: "f2",
        scenario: "checkout_flow",
        persona: "cost_sensitive",
        evidence_payload: {
          screenshot_urls: ["/artifacts/screenshots/checkout_cost_product_selected.png"],
        },
      }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Screenshot Timeline")).toBeInTheDocument();
    });

    // Check for step indicators
    expect(screen.getByText("Step 1")).toBeInTheDocument();
    expect(screen.getByText("Step 2")).toBeInTheDocument();
  });

  it("shows empty state when no screenshots available", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [createMockFinding({ id: "f1", evidence_payload: { screenshot_urls: [] } })];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Screenshot Timeline")).toBeInTheDocument();
    });

    expect(screen.getByText(/no screenshots available/i)).toBeInTheDocument();
  });

  it("has Download PDF button linking to correct URL", async () => {
    const audit = createMockAudit({ id: "audit-123" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      const pdfButton = screen.getByText(/Download PDF/i).closest("a");
      expect(pdfButton).toHaveAttribute("href", "/api/audits/audit-123/report/pdf");
      expect(pdfButton).toHaveAttribute("target", "_blank");
    });
  });

  it("has Compare Personas button linking to diff page", async () => {
    const audit = createMockAudit({ id: "audit-123" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      const compareButton = screen.getByText(/Compare Personas/i).closest("a");
      expect(compareButton).toHaveAttribute("href", "/audits/audit-123/diff");
    });
  });

  it("has Back to History link", async () => {
    const audit = createMockAudit({ id: "audit-123" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      const historyLink = screen.getByRole("link", { name: /Back to History/i });
      expect(historyLink).toHaveAttribute("href", "/history");
    });
  });

  it("displays findings grouped by scenario", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [
      createMockFinding({ id: "f1", scenario: "cookie_consent", title: "Cookie finding 1" }),
      createMockFinding({ id: "f2", scenario: "cookie_consent", title: "Cookie finding 2" }),
      createMockFinding({ id: "f3", scenario: "checkout_flow", title: "Checkout finding 1" }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Findings and evidence")).toBeInTheDocument();
    });

    // Find by text content in headings - use getAllByText since scenarios appear in multiple places
    const headings = screen.getAllByRole("heading");
    expect(headings.some((h) => h.textContent?.includes("Cookie Consent"))).toBe(true);
    expect(headings.some((h) => h.textContent?.includes("Checkout Flow"))).toBe(true);
  });

  it("displays correct trust score and risk level", async () => {
    const audit = createMockAudit({ id: "audit-123", trust_score: 85, risk_level: "low" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      // Look for trust score in hero-score-value which should be unique
      const heroScore = document.querySelector(".hero-score-value");
      expect(heroScore?.textContent).toContain("85");
    });

    // Check for low risk text
    const riskElements = screen.getAllByText(/low/i);
    expect(riskElements.length).toBeGreaterThan(0);
  });

  it("shows running status message when audit is not completed", async () => {
    const audit = createMockAudit({ id: "audit-123", status: "running" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText(/still running/i)).toBeInTheDocument();
    });
  });

  it("shows persona comparison section", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_personas: ["privacy_sensitive", "cost_sensitive"],
    });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Persona comparison")).toBeInTheDocument();
    });

    // Use getAllByText since persona names appear in multiple places (cards, headers, breadcrumbs)
    const privacyElements = screen.getAllByText(/Privacy Sensitive/i);
    const costElements = screen.getAllByText(/Cost Sensitive/i);
    expect(privacyElements.length).toBeGreaterThan(0);
    expect(costElements.length).toBeGreaterThan(0);
  });

  it("shows scenario breakdown section", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_scenarios: ["cookie_consent", "checkout_flow"],
    });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Scenario breakdown")).toBeInTheDocument();
    });

    // Use getAllByText since scenario names may appear in multiple places (breakdown and timeline)
    expect(screen.getAllByText(/Cookie Consent/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Checkout Flow/i).length).toBeGreaterThan(0);
  });

  it("displays Open HTML report button", async () => {
    const audit = createMockAudit({ id: "audit-123" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      const htmlButton = screen.getByText(/Open HTML report/i).closest("a");
      expect(htmlButton).toHaveAttribute("href", "/api/audits/audit-123/report");
      expect(htmlButton).toHaveAttribute("target", "_blank");
    });
  });

  it("displays target URL and mode badges", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      target_url: "https://booking.com",
      mode: "live",
    });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText(/booking.com/i)).toBeInTheDocument();
    });

    // The mode badge appears in the Layout header
    const modeBadges = screen.getAllByText(/live mode/i);
    expect(modeBadges.length).toBeGreaterThan(0);
  });

  it("handles findings with screenshot URLs from evidence_payload", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [
      createMockFinding({
        id: "f1",
        evidence_payload: {
          screenshot_urls: [
            "/artifacts/audit-123/cookie_consent_privacy_initial.png",
            "/artifacts/audit-123/cookie_consent_privacy_after_click.png",
          ],
        },
      }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Screenshot Timeline")).toBeInTheDocument();
    });

    // Should show images
    const images = screen.getAllByRole("img");
    expect(images.length).toBeGreaterThan(0);
  });

  it("shows Back to run log button", async () => {
    const audit = createMockAudit({ id: "audit-123" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      const runLogLink = screen.getByText(/Back to run log/i).closest("a");
      expect(runLogLink).toHaveAttribute("href", "/audits/audit-123/run");
    });
  });

  it("shows Back to Benchmark link when ?benchmark= param is present", async () => {
    const audit = createMockAudit({ id: "audit-123" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage("audit-123", "?benchmark=bench-456");

    await waitFor(() => {
      const benchmarkLink = screen.getByText(/Back to Benchmark/i).closest("a");
      expect(benchmarkLink).toHaveAttribute("href", "/benchmarks/bench-456");
    });
  });

  it("does not show Back to Benchmark link when no benchmark param", async () => {
    const audit = createMockAudit({ id: "audit-123" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Trust Audit Report")).toBeInTheDocument();
    });

    expect(screen.queryByText(/Back to Benchmark/i)).not.toBeInTheDocument();
  });

  it("displays executive summary with metrics", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      metrics: {
        evidence_origin_label: "Nova AI",
      },
    });
    const findings = [createMockFinding(), createMockFinding()];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Executive summary")).toBeInTheDocument();
    });

    expect(screen.getByText(/Finding count/i)).toBeInTheDocument();
    expect(screen.getByText(/Scenarios covered/i)).toBeInTheDocument();
    expect(screen.getByText(/Personas compared/i)).toBeInTheDocument();
  });

  it("expands screenshot on click", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [
      createMockFinding({
        id: "f1",
        evidence_payload: {
          screenshot_urls: ["/artifacts/screenshots/test.png"],
        },
      }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Screenshot Timeline")).toBeInTheDocument();
    });

    // Click on the screenshot thumbnail
    const screenshotButton = screen.getByLabelText(/View screenshot/i);
    fireEvent.click(screenshotButton);

    // Modal should appear
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    // Close button should be visible
    expect(screen.getByText("✕ Close")).toBeInTheDocument();
  });

  it("closes expanded image modal when clicking close button", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [
      createMockFinding({
        id: "f1",
        evidence_payload: {
          screenshot_urls: ["/artifacts/screenshots/test.png"],
        },
      }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Screenshot Timeline")).toBeInTheDocument();
    });

    // Open modal
    const screenshotButton = screen.getByLabelText(/View screenshot/i);
    fireEvent.click(screenshotButton);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    // Close modal
    const closeButton = screen.getByText("✕ Close");
    fireEvent.click(closeButton);

    // Modal should be closed
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("handles missing audit gracefully", async () => {
    mockGetAudit.mockRejectedValue(new Error("Audit not found"));

    renderReportPage("nonexistent-audit");

    await waitFor(() => {
      expect(screen.getByText(/Audit not found/i)).toBeInTheDocument();
    });
  });

  it("displays risk level badge with correct styling", async () => {
    const audit = createMockAudit({ id: "audit-123", risk_level: "critical" });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      // Check for critical risk text (may appear in multiple places)
      const riskElements = screen.getAllByText(/critical/i);
      expect(riskElements.length).toBeGreaterThan(0);
    });
  });

  it("groups findings by scenario and persona", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [
      createMockFinding({ id: "f1", scenario: "cookie_consent", persona: "privacy_sensitive", title: "Finding 1" }),
      createMockFinding({ id: "f2", scenario: "cookie_consent", persona: "privacy_sensitive", title: "Finding 2" }),
      createMockFinding({ id: "f3", scenario: "cookie_consent", persona: "cost_sensitive", title: "Finding 3" }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Findings and evidence")).toBeInTheDocument();
    });

    // Should show findings
    expect(screen.getByText("Finding 1")).toBeInTheDocument();
    expect(screen.getByText("Finding 2")).toBeInTheDocument();
    expect(screen.getByText("Finding 3")).toBeInTheDocument();
  });

  // Video Section Tests
  it("renders Session Recordings section when video_urls is present", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_scenarios: ["cookie_consent", "checkout_flow"],
      selected_personas: ["privacy_sensitive", "cost_sensitive"],
      video_urls: {
        cookie_consent_privacy_sensitive: "/artifacts/videos/cookie_privacy.webm",
        checkout_flow_cost_sensitive: "/artifacts/videos/checkout_cost.webm",
      },
    });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Session Recordings")).toBeInTheDocument();
    });

    // Scoped assertions within video section using data-testid
    const videoSection = screen.getByTestId("video-section");
    expect(within(videoSection).getByText("Cookie Consent")).toBeInTheDocument();
    expect(within(videoSection).getByText("Privacy Sensitive")).toBeInTheDocument();
    expect(within(videoSection).getByText("Checkout Flow")).toBeInTheDocument();
    expect(within(videoSection).getByText("Cost Sensitive")).toBeInTheDocument();
  });

  it("shows 'No recordings available' when video_urls is null", async () => {
    const audit = createMockAudit({ id: "audit-123", video_urls: null });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Session Recordings")).toBeInTheDocument();
    });

    // Scoped assertion within video section
    const videoSection = screen.getByTestId("video-section");
    expect(within(videoSection).getByText("No recordings available")).toBeInTheDocument();
  });

  it("shows 'No recordings available' when video_urls is empty", async () => {
    const audit = createMockAudit({ id: "audit-123", video_urls: {} });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Session Recordings")).toBeInTheDocument();
    });

    // Scoped assertion within video section
    const videoSection = screen.getByTestId("video-section");
    expect(within(videoSection).getByText("No recordings available")).toBeInTheDocument();
  });

  it("renders video elements with controls and preload attributes", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_scenarios: ["cookie_consent"],
      selected_personas: ["privacy_sensitive"],
      video_urls: {
        cookie_consent_privacy_sensitive: "/artifacts/videos/cookie_privacy.webm",
      },
    });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      const videoElement = document.querySelector("video");
      expect(videoElement).toBeInTheDocument();
    });

    // Check video element has required attributes
    const video = document.querySelector("video");
    expect(video).toHaveAttribute("controls");
    expect(video).toHaveAttribute("preload", "metadata");
  });

  it("handles video error state gracefully", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      video_urls: {
        cookie_consent_privacy_sensitive: "/broken/video.webm",
      },
    });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      const videoElement = document.querySelector("video");
      expect(videoElement).toBeInTheDocument();
    });

    // Simulate video error
    const video = document.querySelector("video");
    fireEvent.error(video!);

    await waitFor(() => {
      expect(screen.getByText("Video unavailable")).toBeInTheDocument();
    });
  });

  it("renders multiple video cards correctly", async () => {
    const audit = createMockAudit({
      id: "audit-123",
      selected_scenarios: ["cookie_consent", "checkout_flow"],
      selected_personas: ["privacy_sensitive", "cost_sensitive"],
      video_urls: {
        cookie_consent_privacy_sensitive: "/videos/1.webm",
        cookie_consent_cost_sensitive: "/videos/2.webm",
        checkout_flow_privacy_sensitive: "/videos/3.webm",
      },
    });

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings: [] });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Session Recordings")).toBeInTheDocument();
    });

    // Scoped assertions within video section using data-testid
    const videoSection = screen.getByTestId("video-section");
    // We have 3 videos: 2 cookie consent + 1 checkout flow, and 2 personas (privacy + cost)
    expect(within(videoSection).getAllByText("Cookie Consent")).toHaveLength(2); // Two cookie videos
    expect(within(videoSection).getByText("Checkout Flow")).toBeInTheDocument();
    expect(within(videoSection).getAllByText("Privacy Sensitive")).toHaveLength(2); // Two privacy videos
    expect(within(videoSection).getByText("Cost Sensitive")).toBeInTheDocument();

    // Check that videos exist
    const videos = document.querySelectorAll("video");
    expect(videos.length).toBe(3);
  });

  // Compliance PDF Button Tests
  it("shows Download Compliance Report button when findings have regulatory_categories", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [
      createMockFinding({ id: "f1", regulatory_categories: ["FTC", "GDPR"] }),
      createMockFinding({ id: "f2", regulatory_categories: ["GDPR"] }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Trust Audit Report")).toBeInTheDocument();
    });

    const complianceButton = screen.getByText(/Download Compliance Report/i).closest("a");
    expect(complianceButton).toBeInTheDocument();
    expect(complianceButton).toHaveAttribute("href", "/api/audits/audit-123/report/compliance-pdf");
    expect(complianceButton).toHaveAttribute("target", "_blank");
  });

  it("hides Download Compliance Report button when no regulatory findings exist", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [
      createMockFinding({ id: "f1", regulatory_categories: [] }),
      createMockFinding({ id: "f2", regulatory_categories: [] }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Trust Audit Report")).toBeInTheDocument();
    });

    expect(screen.queryByText(/Download Compliance Report/i)).not.toBeInTheDocument();
  });

  it("hides Download Compliance Report button when all suppressed findings have regulatory_categories", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [
      createMockFinding({ id: "f1", regulatory_categories: ["FTC"], suppressed: true }),
      createMockFinding({ id: "f2", regulatory_categories: ["GDPR"], suppressed: true }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Trust Audit Report")).toBeInTheDocument();
    });

    expect(screen.queryByText(/Download Compliance Report/i)).not.toBeInTheDocument();
  });

  it("shows Download Compliance Report button when at least one non-suppressed finding has regulatory_categories", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [
      createMockFinding({ id: "f1", regulatory_categories: ["FTC"], suppressed: true }),
      createMockFinding({ id: "f2", regulatory_categories: ["GDPR"], suppressed: false }),
    ];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Trust Audit Report")).toBeInTheDocument();
    });

    expect(screen.getByText(/Download Compliance Report/i)).toBeInTheDocument();
  });

  it("ensures existing Download PDF button still works alongside compliance button", async () => {
    const audit = createMockAudit({ id: "audit-123" });
    const findings = [createMockFinding({ id: "f1", regulatory_categories: ["FTC"] })];

    mockGetAudit.mockResolvedValue(audit);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-123", findings });

    renderReportPage();

    await waitFor(() => {
      expect(screen.getByText("Trust Audit Report")).toBeInTheDocument();
    });

    // Both buttons should be present
    const complianceButton = screen.getByText(/Download Compliance Report/i).closest("a");
    const pdfButton = screen.getByText(/Download PDF/i).closest("a");

    expect(complianceButton).toBeInTheDocument();
    expect(complianceButton).toHaveAttribute("href", "/api/audits/audit-123/report/compliance-pdf");
    expect(complianceButton).toHaveAttribute("target", "_blank");

    expect(pdfButton).toBeInTheDocument();
    expect(pdfButton).toHaveAttribute("href", "/api/audits/audit-123/report/pdf");
    expect(pdfButton).toHaveAttribute("target", "_blank");
  });
});
