import { describe, it, expect } from "vitest";
import type { PatternFamily } from "./taxonomy";
import {
  DARK_PATTERN_CATEGORIES,
  AUDIT_SCENARIOS,
  PERSONA_DEFINITIONS,
  SEVERITY_LEVELS,
  REGULATIONS,
  REGULATION_INFO,
  PATTERN_FAMILY_TO_CATEGORY,
  getRegulationsForCategory,
  getRegulationsForPatternFamily,
  isValidCategory,
  isValidScenario,
  isValidPersona,
  isValidSeverity,
  compareSeverity,
  getEvidenceTypeLabel,
  formatConfidenceAsPercentage,
  getConfidenceQuality,
} from "./taxonomy";

describe("taxonomy constants", () => {
  it("has the expected dark pattern categories", () => {
    expect(DARK_PATTERN_CATEGORIES).toContain("manipulative_design");
    expect(DARK_PATTERN_CATEGORIES).toContain("deceptive_content");
    expect(DARK_PATTERN_CATEGORIES).toContain("coercive_flow");
    expect(DARK_PATTERN_CATEGORIES).toContain("obstruction");
    expect(DARK_PATTERN_CATEGORIES).toContain("sneaking");
    expect(DARK_PATTERN_CATEGORIES).toContain("social_proof_manipulation");
  });

  it("has the expected audit scenarios", () => {
    expect(AUDIT_SCENARIOS).toContain("cookie_consent");
    expect(AUDIT_SCENARIOS).toContain("subscription_cancellation");
    expect(AUDIT_SCENARIOS).toContain("checkout_flow");
    expect(AUDIT_SCENARIOS).toContain("account_deletion");
    expect(AUDIT_SCENARIOS).toContain("newsletter_signup");
    expect(AUDIT_SCENARIOS).toContain("pricing_comparison");
  });

  it("has the expected personas", () => {
    expect(PERSONA_DEFINITIONS).toContain("privacy_sensitive");
    expect(PERSONA_DEFINITIONS).toContain("cost_sensitive");
    expect(PERSONA_DEFINITIONS).toContain("exit_intent");
  });

  it("has the expected severity levels", () => {
    expect(SEVERITY_LEVELS).toEqual(["low", "medium", "high", "critical"]);
  });

  it("has the expected regulations", () => {
    expect(REGULATIONS).toContain("FTC");
    expect(REGULATIONS).toContain("GDPR");
    expect(REGULATIONS).toContain("DSA");
    expect(REGULATIONS).toContain("CPRA");
  });

  it("provides regulation info for all regulations", () => {
    REGULATIONS.forEach((reg) => {
      expect(REGULATION_INFO[reg]).toBeDefined();
      expect(REGULATION_INFO[reg].name).toBe(reg);
      expect(REGULATION_INFO[reg].fullName).toBeDefined();
      expect(REGULATION_INFO[reg].color).toBeDefined();
    });
  });

  it("correctly maps pattern families to categories", () => {
    expect(PATTERN_FAMILY_TO_CATEGORY.asymmetric_choice).toBe("manipulative_design");
    expect(PATTERN_FAMILY_TO_CATEGORY.hidden_costs).toBe("deceptive_content");
    expect(PATTERN_FAMILY_TO_CATEGORY.confirmshaming).toBe("coercive_flow");
    expect(PATTERN_FAMILY_TO_CATEGORY.obstruction).toBe("obstruction");
    expect(PATTERN_FAMILY_TO_CATEGORY.sneaking).toBe("sneaking");
    expect(PATTERN_FAMILY_TO_CATEGORY.urgency).toBe("social_proof_manipulation");
  });
});

describe("taxonomy helper functions", () => {
  describe("getRegulationsForCategory", () => {
    it("returns correct regulations for manipulative_design", () => {
      const regs = getRegulationsForCategory("manipulative_design");
      expect(regs).toContain("FTC");
      expect(regs).toContain("DSA");
    });

    it("returns correct regulations for deceptive_content", () => {
      const regs = getRegulationsForCategory("deceptive_content");
      expect(regs).toContain("FTC");
      expect(regs).toContain("GDPR");
      expect(regs).toContain("DSA");
    });

    it("returns correct regulations for obstruction", () => {
      const regs = getRegulationsForCategory("obstruction");
      expect(regs).toContain("GDPR");
      expect(regs).toContain("DSA");
      expect(regs).toContain("CPRA");
    });
  });

  describe("getRegulationsForPatternFamily", () => {
    it("returns correct regulations for hidden_costs pattern family", () => {
      const regs = getRegulationsForPatternFamily("hidden_costs");
      expect(regs).toContain("FTC");
      expect(regs).toContain("GDPR");
      expect(regs).toContain("DSA");
    });

    it("returns empty array for unknown pattern family", () => {
      const regs = getRegulationsForPatternFamily("unknown_pattern" as PatternFamily);
      expect(regs).toEqual([]);
    });
  });

  describe("validation functions", () => {
    it("isValidCategory returns true for valid categories", () => {
      expect(isValidCategory("manipulative_design")).toBe(true);
      expect(isValidCategory("deceptive_content")).toBe(true);
    });

    it("isValidCategory returns false for invalid categories", () => {
      expect(isValidCategory("invalid_category")).toBe(false);
      expect(isValidCategory("")).toBe(false);
    });

    it("isValidScenario returns true for valid scenarios", () => {
      expect(isValidScenario("cookie_consent")).toBe(true);
      expect(isValidScenario("checkout_flow")).toBe(true);
    });

    it("isValidScenario returns false for invalid scenarios", () => {
      expect(isValidScenario("invalid_scenario")).toBe(false);
      expect(isValidScenario("")).toBe(false);
    });

    it("isValidPersona returns true for valid personas", () => {
      expect(isValidPersona("privacy_sensitive")).toBe(true);
      expect(isValidPersona("cost_sensitive")).toBe(true);
    });

    it("isValidPersona returns false for invalid personas", () => {
      expect(isValidPersona("invalid_persona")).toBe(false);
      expect(isValidPersona("")).toBe(false);
    });

    it("isValidSeverity returns true for valid severities", () => {
      expect(isValidSeverity("low")).toBe(true);
      expect(isValidSeverity("critical")).toBe(true);
    });

    it("isValidSeverity returns false for invalid severities", () => {
      expect(isValidSeverity("invalid")).toBe(false);
      expect(isValidSeverity("")).toBe(false);
    });
  });

  describe("compareSeverity", () => {
    it("returns positive when first severity is higher", () => {
      expect(compareSeverity("high", "low")).toBeGreaterThan(0);
      expect(compareSeverity("critical", "medium")).toBeGreaterThan(0);
    });

    it("returns negative when first severity is lower", () => {
      expect(compareSeverity("low", "high")).toBeLessThan(0);
      expect(compareSeverity("medium", "critical")).toBeLessThan(0);
    });

    it("returns zero when severities are equal", () => {
      expect(compareSeverity("high", "high")).toBe(0);
      expect(compareSeverity("low", "low")).toBe(0);
    });
  });

  describe("getEvidenceTypeLabel", () => {
    it("returns correct labels for evidence types", () => {
      expect(getEvidenceTypeLabel("nova_ai")).toBe("Nova AI evidence");
      expect(getEvidenceTypeLabel("heuristic")).toBe("Heuristic detection");
      expect(getEvidenceTypeLabel("rule_based")).toBe("Rule-based");
      expect(getEvidenceTypeLabel("mock")).toBe("Simulated");
    });

    it("returns original value for unknown types", () => {
      expect(getEvidenceTypeLabel("unknown")).toBe("unknown");
    });

    it("returns 'Evidence' for undefined", () => {
      expect(getEvidenceTypeLabel(undefined)).toBe("Evidence");
    });
  });

  describe("formatConfidenceAsPercentage", () => {
    it("formats confidence as percentage", () => {
      expect(formatConfidenceAsPercentage(0.85)).toBe("85%");
      expect(formatConfidenceAsPercentage(0.756)).toBe("76%");
      expect(formatConfidenceAsPercentage(0.5)).toBe("50%");
      expect(formatConfidenceAsPercentage(1.0)).toBe("100%");
      expect(formatConfidenceAsPercentage(0)).toBe("0%");
    });
  });

  describe("getConfidenceQuality", () => {
    it("returns 'high' for high confidence nova_ai", () => {
      expect(getConfidenceQuality(0.9, "nova_ai")).toBe("high");
    });

    it("returns 'medium' for medium confidence nova_ai", () => {
      expect(getConfidenceQuality(0.8, "nova_ai")).toBe("medium");
    });

    it("returns 'low' for low confidence nova_ai", () => {
      expect(getConfidenceQuality(0.7, "nova_ai")).toBe("low");
    });

    it("returns 'high' for high confidence heuristic", () => {
      expect(getConfidenceQuality(0.75, "heuristic")).toBe("high");
    });

    it("returns 'medium' for medium confidence heuristic", () => {
      expect(getConfidenceQuality(0.6, "heuristic")).toBe("medium");
    });

    it("returns 'low' for low confidence heuristic", () => {
      expect(getConfidenceQuality(0.5, "heuristic")).toBe("low");
    });
  });
});
