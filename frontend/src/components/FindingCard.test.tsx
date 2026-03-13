import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FindingCard } from "./FindingCard";
import type { Finding } from "../api/types";

describe("FindingCard", () => {
  const baseFinding: Finding = {
    id: "test-1",
    scenario: "cookie_consent",
    persona: "privacy_sensitive",
    pattern_family: "asymmetric_choice",
    severity: "high",
    title: "Test Finding",
    explanation: "This is a test finding",
    remediation: "Fix it",
    evidence_excerpt: "Evidence here",
    rule_reason: "This matters",
    evidence_payload: {
      source: "nova_ai",
      source_label: "Nova AI evidence",
      screenshot_urls: [],
    },
    confidence: 0.85,
    trust_impact: 0.7,
    order_index: 1,
    regulatory_categories: ["GDPR", "DSA"],
    suppressed: false,
    created_at: "2024-01-01T00:00:00Z",
  };

  it("renders finding with regulatory badges", () => {
    render(<FindingCard finding={baseFinding} />);

    expect(screen.getByText("GDPR")).toBeInTheDocument();
    expect(screen.getByText("DSA")).toBeInTheDocument();
  });

  it("renders confidence percentage", () => {
    render(<FindingCard finding={baseFinding} />);

    expect(screen.getByText("85% confidence")).toBeInTheDocument();
  });

  it("renders evidence source label", () => {
    render(<FindingCard finding={baseFinding} />);

    expect(screen.getByText("Nova AI evidence")).toBeInTheDocument();
  });

  it("renders suppressed badge for suppressed findings", () => {
    const suppressedFinding: Finding = {
      ...baseFinding,
      suppressed: true,
    };

    render(<FindingCard finding={suppressedFinding} />);

    expect(screen.getByText("Likely false positive")).toBeInTheDocument();
  });

  it("applies suppressed styling to suppressed findings", () => {
    const suppressedFinding: Finding = {
      ...baseFinding,
      suppressed: true,
    };

    const { container } = render(<FindingCard finding={suppressedFinding} />);

    expect(container.querySelector(".finding-card-suppressed")).toBeInTheDocument();
  });

  it("does not show suppressed badge for non-suppressed findings", () => {
    render(<FindingCard finding={baseFinding} />);

    expect(screen.queryByText("Likely false positive")).not.toBeInTheDocument();
  });

  it("handles missing regulatory_categories gracefully", () => {
    const findingWithoutRegs: Finding = {
      ...baseFinding,
      regulatory_categories: [],
    };

    const { container } = render(<FindingCard finding={findingWithoutRegs} />);

    expect(container.querySelector(".regulation-row")).not.toBeInTheDocument();
  });

  it("handles missing evidence source gracefully", () => {
    const findingWithoutSource: Finding = {
      ...baseFinding,
      evidence_payload: {},
    };

    render(<FindingCard finding={findingWithoutSource} />);

    expect(screen.getByText("Evidence")).toBeInTheDocument();
  });

  it("displays all regulatory badges when multiple regulations apply", () => {
    const findingWithManyRegs: Finding = {
      ...baseFinding,
      regulatory_categories: ["FTC", "GDPR", "DSA", "CPRA"],
    };

    render(<FindingCard finding={findingWithManyRegs} />);

    expect(screen.getByText("FTC")).toBeInTheDocument();
    expect(screen.getByText("GDPR")).toBeInTheDocument();
    expect(screen.getByText("DSA")).toBeInTheDocument();
    expect(screen.getByText("CPRA")).toBeInTheDocument();
  });
});
