import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import { BenchmarkPage } from "./BenchmarkPage";
import type { Benchmark, Audit, Finding } from "../api/types";

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
    getBenchmark: vi.fn(),
    getAudit: vi.fn(),
    getFindings: vi.fn(),
    getReportUrl: (id: string) => `/api/audits/${id}/report`,
  },
}));

import { api } from "../api/client";

const mockGetBenchmark = api.getBenchmark as ReturnType<typeof vi.fn>;
const mockGetAudit = api.getAudit as ReturnType<typeof vi.fn>;
const mockGetFindings = api.getFindings as ReturnType<typeof vi.fn>;

const createMockBenchmark = (overrides: Partial<Benchmark> = {}): Benchmark => ({
  id: `benchmark-${overrides.id || Math.random().toString(36).slice(2, 7)}`,
  status: "completed",
  urls: ["https://example.com", "https://test.com"],
  audit_ids: ["audit-1", "audit-2"],
  trust_scores: {
    "https://example.com": 75,
    "https://test.com": 45,
  },
  created_at: "2026-03-13T10:00:00Z",
  updated_at: "2026-03-13T10:05:00Z",
  ...overrides,
});

const createMockAudit = (overrides: Partial<Audit> = {}): Audit => ({
  id: overrides.id || `audit-${Math.random().toString(36).slice(2, 7)}`,
  target_url: "https://example.com",
  mode: "mock",
  status: "completed",
  summary: null,
  trust_score: 75,
  risk_level: "moderate",
  selected_scenarios: ["cookie_consent", "checkout_flow"],
  selected_personas: ["privacy_sensitive", "cost_sensitive"],
  report_public_url: null,
  video_urls: null,
  metrics: {
    finding_count: 5,
    observation_count: 10,
    site_host: "example.com",
    evidence_origin_label: "Mock",
    persona_comparison: [],
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
        finding_count: 2,
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
  scenario: overrides.scenario || "cookie_consent",
  persona: "privacy_sensitive",
  pattern_family: "manipulative_design",
  severity: "high",
  title: "Dark pattern detected",
  explanation: "Explanation of the finding",
  remediation: "How to fix this",
  evidence_excerpt: "Evidence text",
  rule_reason: "Why this matters",
  evidence_payload: {},
  confidence: 0.85,
  trust_impact: 0.3,
  order_index: 1,
  created_at: "2026-03-13T10:00:00Z",
  regulatory_categories: ["FTC"],
  suppressed: false,
  ...overrides,
});

function renderBenchmarkPage(benchmarkId = "benchmark-123") {
  return render(
    <MemoryRouter initialEntries={[`/benchmarks/${benchmarkId}`]}>
      <Routes>
        <Route path="/benchmarks/:benchmarkId" element={<BenchmarkPage />} />
        <Route path="/audits/:auditId/report" element={<div data-testid="report-page">Report Page</div>} />
        <Route path="/history" element={<div data-testid="history-page">History Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("BenchmarkPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders loading state initially", () => {
    mockGetBenchmark.mockReturnValue(new Promise(() => {}));

    renderBenchmarkPage();

    expect(screen.getByText(/loading benchmark/i)).toBeInTheDocument();
  });

  it("renders error state when API fails", async () => {
    mockGetBenchmark.mockRejectedValue(new Error("Network error"));

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  it("renders error when invalid benchmarkId causes 404", async () => {
    mockGetBenchmark.mockRejectedValue(new Error("Benchmark not found"));

    renderBenchmarkPage("invalid-id");

    await waitFor(() => {
      expect(screen.getByText(/benchmark not found/i)).toBeInTheDocument();
    });
  });

  it("polls every 1.5s while benchmark status is running", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    
    const runningBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "running",
      trust_scores: null,
    });
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      trust_scores: {
        "https://example.com": 75,
        "https://test.com": 45,
      },
    });

    mockGetBenchmark
      .mockResolvedValueOnce(runningBenchmark)
      .mockResolvedValueOnce(runningBenchmark)
      .mockResolvedValueOnce(completedBenchmark);

    mockGetAudit.mockResolvedValue(createMockAudit());
    mockGetFindings.mockResolvedValue({ audit_id: "", findings: [] });

    renderBenchmarkPage();

    // Initial call
    await waitFor(() => {
      expect(mockGetBenchmark).toHaveBeenCalledTimes(1);
    });

    // After 1.5s, should poll again
    vi.advanceTimersByTime(1500);
    await waitFor(() => {
      expect(mockGetBenchmark).toHaveBeenCalledTimes(2);
    });

    // After another 1.5s, should poll again
    vi.advanceTimersByTime(1500);
    await waitFor(() => {
      expect(mockGetBenchmark).toHaveBeenCalledTimes(3);
    });

    // No more polling after completed
    vi.advanceTimersByTime(1500);
    await waitFor(() => {
      expect(mockGetBenchmark).toHaveBeenCalledTimes(3);
    });
  });

  it("stops polling when benchmark status is completed", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
    });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit.mockResolvedValue(createMockAudit());
    mockGetFindings.mockResolvedValue({ audit_id: "", findings: [] });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/comparing 2 urls/i)).toBeInTheDocument();
    });

    // Should not poll again after initial load
    expect(mockGetBenchmark).toHaveBeenCalledTimes(1);
  });

  it("stops polling when benchmark status is failed", async () => {
    const failedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "failed",
    });

    mockGetBenchmark.mockResolvedValue(failedBenchmark);

    renderBenchmarkPage();

    await waitFor(() => {
      // Look for the status pill specifically by class name, not the error state title
      expect(screen.getByText((content, element) => {
        return !!(element?.classList?.contains("signal-pill") && element?.classList?.contains("status-failed") && content === "failed");
      })).toBeInTheDocument();
    });

    // Should not poll again
    expect(mockGetBenchmark).toHaveBeenCalledTimes(1);
  });

  it("shows per-URL progress while benchmark is running", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    
    const runningBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "running",
      audit_ids: ["audit-1", "audit-2"],
    });

    const audit1 = createMockAudit({
      id: "audit-1",
      target_url: "https://example.com",
      status: "running",
      events: [
        { id: 1, phase: "browser", status: "running", message: "Running cookie consent", progress: 50, details: {}, created_at: "2026-03-13T10:00:00Z" },
      ],
    });

    const audit2 = createMockAudit({
      id: "audit-2",
      target_url: "https://test.com",
      status: "running",
      events: [
        { id: 2, phase: "browser", status: "running", message: "Running checkout flow", progress: 30, details: {}, created_at: "2026-03-13T10:00:00Z" },
      ],
    });

    mockGetBenchmark.mockResolvedValue(runningBenchmark);
    mockGetAudit.mockResolvedValueOnce(audit1).mockResolvedValueOnce(audit2);

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/example.com/i)).toBeInTheDocument();
    });

    // Should show progress for running audits
    expect(screen.getByText(/50%/i)).toBeInTheDocument();
    expect(screen.getByText(/30%/i)).toBeInTheDocument();
  });

  it("renders trust score comparison ranked highest first when completed", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      urls: ["https://low-score.com", "https://high-score.com", "https://medium-score.com"],
      audit_ids: ["audit-low", "audit-high", "audit-medium"],
      trust_scores: {
        "https://low-score.com": 35,
        "https://high-score.com": 85,
        "https://medium-score.com": 60,
      },
    });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);

    const highAudit = createMockAudit({
      id: "audit-high",
      target_url: "https://high-score.com",
      trust_score: 85,
      risk_level: "low",
    });

    const mediumAudit = createMockAudit({
      id: "audit-medium",
      target_url: "https://medium-score.com",
      trust_score: 60,
      risk_level: "moderate",
    });

    const lowAudit = createMockAudit({
      id: "audit-low",
      target_url: "https://low-score.com",
      trust_score: 35,
      risk_level: "high",
    });

    mockGetAudit
      .mockResolvedValueOnce(highAudit)
      .mockResolvedValueOnce(mediumAudit)
      .mockResolvedValueOnce(lowAudit);

    mockGetFindings.mockResolvedValue({ audit_id: "", findings: [] });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/trust score comparison/i)).toBeInTheDocument();
    });

    // Check that trust scores are displayed
    const scoreElements = screen.getAllByText(/\d+%/);
    expect(scoreElements.length).toBeGreaterThanOrEqual(3);

    // First should be highest (85%)
    expect(scoreElements[0].textContent).toContain("85%");

    // Delta indicator should show 50 point spread (85 - 35)
    const deltaValue = screen.getByTestId("delta-value");
    expect(deltaValue.textContent).toBe("50");
    expect(screen.getByText(/point spread/i)).toBeInTheDocument();
  });

  it("shows scenario breakdown grid with correct finding counts", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      urls: ["https://site-a.com", "https://site-b.com"],
      audit_ids: ["audit-a", "audit-b"],
    });

    const auditA = createMockAudit({
      id: "audit-a",
      target_url: "https://site-a.com",
      selected_scenarios: ["cookie_consent", "checkout_flow", "newsletter_signup"],
      metrics: {
        finding_count: 5,
        observation_count: 10,
        site_host: "site-a.com",
        evidence_origin_label: "Mock",
        persona_comparison: [],
        scenario_breakdown: [
          { scenario: "cookie_consent", headline: "Cookie", risk_level: "high", finding_count: 3, dominant_patterns: [] },
          { scenario: "checkout_flow", headline: "Checkout", risk_level: "moderate", finding_count: 2, dominant_patterns: [] },
          { scenario: "newsletter_signup", headline: "Newsletter", risk_level: "low", finding_count: 0, dominant_patterns: [] },
        ],
      },
    });

    const auditB = createMockAudit({
      id: "audit-b",
      target_url: "https://site-b.com",
      selected_scenarios: ["cookie_consent", "checkout_flow", "newsletter_signup"],
      metrics: {
        finding_count: 4,
        observation_count: 8,
        site_host: "site-b.com",
        evidence_origin_label: "Mock",
        persona_comparison: [],
        scenario_breakdown: [
          { scenario: "cookie_consent", headline: "Cookie", risk_level: "medium", finding_count: 1, dominant_patterns: [] },
          { scenario: "checkout_flow", headline: "Checkout", risk_level: "low", finding_count: 0, dominant_patterns: [] },
          { scenario: "newsletter_signup", headline: "Newsletter", risk_level: "low", finding_count: 3, dominant_patterns: [] },
        ],
      },
    });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit.mockResolvedValueOnce(auditA).mockResolvedValueOnce(auditB);
    mockGetFindings.mockResolvedValue({ audit_id: "", findings: [] });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/scenario breakdown/i)).toBeInTheDocument();
    });

    // Grid should show finding counts per scenario per URL
    const scenarioGrid = screen.getByTestId("scenario-grid");

    // Check that finding counts are displayed (use getAllByText for values that appear multiple times)
    expect(within(scenarioGrid).getAllByText("3").length).toBeGreaterThan(0); // site-a cookie_consent
    expect(within(scenarioGrid).getAllByText("2").length).toBeGreaterThan(0); // site-a checkout_flow
    expect(within(scenarioGrid).getAllByText("0").length).toBeGreaterThan(0); // multiple cells with 0
  });

  it("renders unified summary with highest/lowest scoring URLs named", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      urls: ["https://low.com", "https://high.com"],
      audit_ids: ["audit-low", "audit-high"],
      trust_scores: {
        "https://low.com": 30,
        "https://high.com": 80,
      },
    });

    const highAudit = createMockAudit({
      id: "audit-high",
      target_url: "https://high.com",
      trust_score: 80,
      risk_level: "low",
    });

    const lowAudit = createMockAudit({
      id: "audit-low",
      target_url: "https://low.com",
      trust_score: 30,
      risk_level: "high",
    });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit.mockResolvedValueOnce(highAudit).mockResolvedValueOnce(lowAudit);

    const findings = [
      createMockFinding({ pattern_family: "manipulative_design" }),
      createMockFinding({ pattern_family: "obstruction" }),
    ];
    mockGetFindings.mockResolvedValue({ audit_id: "audit-low", findings });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/unified summary/i)).toBeInTheDocument();
    });

    // Summary should name highest and lowest scoring URLs (use summary section to scope)
    const summarySection = screen.getByTestId("summary-section");
    expect(within(summarySection).getByText(/high.com/i)).toBeInTheDocument();
    expect(within(summarySection).getByText(/low.com/i)).toBeInTheDocument();
  });

  it("mentions common dark patterns in unified summary", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      urls: ["https://site-a.com", "https://site-b.com"],
      audit_ids: ["audit-a", "audit-b"],
      trust_scores: {
        "https://site-a.com": 70,
        "https://site-b.com": 50,
      },
    });

    const auditA = createMockAudit({
      id: "audit-a",
      target_url: "https://site-a.com",
      trust_score: 70,
    });

    const auditB = createMockAudit({
      id: "audit-b",
      target_url: "https://site-b.com",
      trust_score: 50,
    });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit.mockResolvedValueOnce(auditA).mockResolvedValueOnce(auditB);

    // Add findings with pattern families
    const findingsA = [
      createMockFinding({ id: "f1", pattern_family: "manipulative_design" }),
      createMockFinding({ id: "f2", pattern_family: "manipulative_design" }),
    ];
    const findingsB = [
      createMockFinding({ id: "f3", pattern_family: "obstruction" }),
    ];

    mockGetFindings.mockResolvedValueOnce({ audit_id: "audit-a", findings: findingsA });
    mockGetFindings.mockResolvedValueOnce({ audit_id: "audit-b", findings: findingsB });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/unified summary/i)).toBeInTheDocument();
    });

    // Summary should mention pattern families - titleized format
    const summarySection = screen.getByTestId("summary-section");
    expect(within(summarySection).getByText("Manipulative Design")).toBeInTheDocument();
  });

  it("shows overall risk word in unified summary", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      urls: ["https://site-a.com"],
      audit_ids: ["audit-a"],
      trust_scores: {
        "https://site-a.com": 40,
      },
    });

    const auditA = createMockAudit({
      id: "audit-a",
      target_url: "https://site-a.com",
      trust_score: 40,
      risk_level: "high",
    });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit.mockResolvedValueOnce(auditA);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-a", findings: [] });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/unified summary/i)).toBeInTheDocument();
    });

    // Should show risk word (high, moderate, low, critical) - look for "High" as titleized
    const summarySection = screen.getByTestId("summary-section");
    expect(within(summarySection).getByText("High")).toBeInTheDocument();
  });

  it("has View Report links that navigate to individual audit ReportPages", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      urls: ["https://site-a.com"],
      audit_ids: ["audit-a"],
    });

    const auditA = createMockAudit({
      id: "audit-a",
      target_url: "https://site-a.com",
      trust_score: 70,
    });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit.mockResolvedValueOnce(auditA);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-a", findings: [] });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/view report/i)).toBeInTheDocument();
    });

    const viewReportLink = screen.getByRole("link", { name: /view report/i });
    expect(viewReportLink).toHaveAttribute("href", "/audits/audit-a/report?benchmark=benchmark-123");
  });

  it("passes benchmarkId as query param in View Report link", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      urls: ["https://site-a.com"],
      audit_ids: ["audit-a"],
    });

    const auditA = createMockAudit({
      id: "audit-a",
      target_url: "https://site-a.com",
      trust_score: 70,
    });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit.mockResolvedValueOnce(auditA);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-a", findings: [] });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/view report/i)).toBeInTheDocument();
    });

    const viewReportLink = screen.getByRole("link", { name: /view report/i });
    expect(viewReportLink).toHaveAttribute("href", "/audits/audit-a/report?benchmark=benchmark-123");
  });

  it("shows error badge and N/A score for failed audits", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      urls: ["https://failed-site.com", "https://success-site.com"],
      audit_ids: ["audit-failed", "audit-success"],
      trust_scores: {
        "https://failed-site.com": null,
        "https://success-site.com": 75,
      },
    });

    const failedAudit = createMockAudit({
      id: "audit-failed",
      target_url: "https://failed-site.com",
      status: "failed",
      trust_score: null,
    });

    const successAudit = createMockAudit({
      id: "audit-success",
      target_url: "https://success-site.com",
      status: "completed",
      trust_score: 75,
    });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit.mockResolvedValueOnce(failedAudit).mockResolvedValueOnce(successAudit);
    mockGetFindings.mockResolvedValue({ audit_id: "", findings: [] });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/trust score comparison/i)).toBeInTheDocument();
    });

    // Should show error badge for failed audit (within comparison section)
    const comparisonSection = screen.getByTestId("comparison-section");
    expect(within(comparisonSection).getByText(/error/i)).toBeInTheDocument();

    // Should show N/A for trust score
    expect(within(comparisonSection).getAllByText(/n\/a/i).length).toBeGreaterThan(0);
  });

  it("has Back to History button", async () => {
    const completedBenchmark = createMockBenchmark();

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit.mockResolvedValue(createMockAudit());
    mockGetFindings.mockResolvedValue({ audit_id: "", findings: [] });

    renderBenchmarkPage();

    await waitFor(() => {
      const backButton = screen.getByRole("link", { name: /back to history/i });
      expect(backButton).toHaveAttribute("href", "/history");
    });
  });

  it("shows aggregate progress meter while running", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    
    const runningBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "running",
      audit_ids: ["audit-1", "audit-2"],
    });

    const audit1 = createMockAudit({
      id: "audit-1",
      status: "running",
      events: [
        { id: 1, phase: "browser", status: "running", message: "Running", progress: 60, details: {}, created_at: "2026-03-13T10:00:00Z" },
      ],
    });

    const audit2 = createMockAudit({
      id: "audit-2",
      status: "running",
      events: [
        { id: 2, phase: "browser", status: "running", message: "Running", progress: 40, details: {}, created_at: "2026-03-13T10:00:00Z" },
      ],
    });

    mockGetBenchmark.mockResolvedValue(runningBenchmark);
    mockGetAudit.mockResolvedValueOnce(audit1).mockResolvedValueOnce(audit2);

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/aggregate progress/i)).toBeInTheDocument();
    });

    // Average of 60% and 40% is 50%
    expect(screen.getByText(/50%/i)).toBeInTheDocument();
  });

  it("calculates correct delta indicator between best and worst scores", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      urls: ["https://site-a.com", "https://site-b.com", "https://site-c.com"],
      audit_ids: ["audit-a", "audit-b", "audit-c"],
      trust_scores: {
        "https://site-a.com": 90,
        "https://site-b.com": 60,
        "https://site-c.com": 30,
      },
    });

    const auditA = createMockAudit({ id: "audit-a", target_url: "https://site-a.com", trust_score: 90 });
    const auditB = createMockAudit({ id: "audit-b", target_url: "https://site-b.com", trust_score: 60 });
    const auditC = createMockAudit({ id: "audit-c", target_url: "https://site-c.com", trust_score: 30 });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit
      .mockResolvedValueOnce(auditA)
      .mockResolvedValueOnce(auditB)
      .mockResolvedValueOnce(auditC);
    mockGetFindings.mockResolvedValue({ audit_id: "", findings: [] });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByTestId("comparison-section")).toBeInTheDocument();
    });

    // Delta should be 90 - 30 = 60 points (within delta-badge)
    const deltaValue = screen.getByTestId("delta-value");
    expect(deltaValue.textContent).toBe("60");
  });

  it("handles empty cells with '0' for scenarios with no findings", async () => {
    const completedBenchmark = createMockBenchmark({
      id: "benchmark-123",
      status: "completed",
      urls: ["https://site-a.com"],
      audit_ids: ["audit-a"],
    });

    const auditA = createMockAudit({
      id: "audit-a",
      target_url: "https://site-a.com",
      selected_scenarios: ["cookie_consent", "checkout_flow"],
      metrics: {
        finding_count: 2,
        observation_count: 5,
        site_host: "site-a.com",
        evidence_origin_label: "Mock",
        persona_comparison: [],
        scenario_breakdown: [
          { scenario: "cookie_consent", headline: "Cookie", risk_level: "high", finding_count: 2, dominant_patterns: [] },
          { scenario: "checkout_flow", headline: "Checkout", risk_level: "low", finding_count: 0, dominant_patterns: [] },
        ],
      },
    });

    mockGetBenchmark.mockResolvedValue(completedBenchmark);
    mockGetAudit.mockResolvedValueOnce(auditA);
    mockGetFindings.mockResolvedValue({ audit_id: "audit-a", findings: [] });

    renderBenchmarkPage();

    await waitFor(() => {
      expect(screen.getByText(/scenario breakdown/i)).toBeInTheDocument();
    });

    // Should show 0 for empty cells, not blank
    const zeroElements = screen.getAllByText("0");
    expect(zeroElements.length).toBeGreaterThan(0);
  });
});
