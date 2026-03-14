/**
 * Taxonomy constants - mirrors backend taxonomy for consistent display
 *
 * Single source of truth for dark pattern categories, scenarios, personas,
 * severity levels, regulations, and evidence types.
 */

// =============================================================================
// Dark Pattern Categories
// =============================================================================

export const DARK_PATTERN_CATEGORIES = [
  "manipulative_design",
  "deceptive_content",
  "coercive_flow",
  "obstruction",
  "sneaking",
  "social_proof_manipulation",
] as const;

export type DarkPatternCategory = (typeof DARK_PATTERN_CATEGORIES)[number];

// Legacy pattern families for backward compatibility
export const PATTERN_FAMILIES = [
  "asymmetric_choice",
  "hidden_costs",
  "confirmshaming",
  "obstruction",
  "sneaking",
  "urgency",
] as const;

export type PatternFamily = (typeof PATTERN_FAMILIES)[number];

// Mapping from legacy pattern families to new dark pattern categories
export const PATTERN_FAMILY_TO_CATEGORY: Record<PatternFamily, DarkPatternCategory> = {
  asymmetric_choice: "manipulative_design",
  hidden_costs: "deceptive_content",
  confirmshaming: "coercive_flow",
  obstruction: "obstruction",
  sneaking: "sneaking",
  urgency: "social_proof_manipulation",
};

// =============================================================================
// Audit Scenarios
// =============================================================================

export const AUDIT_SCENARIOS = [
  "cookie_consent",
  "subscription_cancellation",
  "checkout_flow",
  "account_deletion",
  "newsletter_signup",
  "pricing_comparison",
] as const;

export type ScenarioType = (typeof AUDIT_SCENARIOS)[number];

// =============================================================================
// Persona Definitions
// =============================================================================

export const PERSONA_DEFINITIONS = ["privacy_sensitive", "cost_sensitive", "exit_intent"] as const;

export type PersonaType = (typeof PERSONA_DEFINITIONS)[number];

export const PERSONA_DESCRIPTIONS: Record<PersonaType, string> = {
  privacy_sensitive: "User focused on privacy protections, data minimization, and consent transparency",
  cost_sensitive: "User focused on finding best prices, avoiding hidden fees, and cost transparency",
  exit_intent: "User attempting to leave, cancel, or abandon a service/process",
};

// =============================================================================
// Severity Levels
// =============================================================================

export const SEVERITY_LEVELS = ["low", "medium", "high", "critical"] as const;

export type SeverityType = (typeof SEVERITY_LEVELS)[number];

export const SEVERITY_RANK: Record<SeverityType, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

// =============================================================================
// Audit Status
// =============================================================================

export const AUDIT_STATUSES = ["queued", "running", "completed", "failed"] as const;

export type AuditStatusType = (typeof AUDIT_STATUSES)[number];

// =============================================================================
// Regulatory Mappings
// =============================================================================

export const REGULATIONS = ["FTC", "GDPR", "DSA", "CPRA"] as const;

export type RegulationType = (typeof REGULATIONS)[number];

// Regulatory category display info
export interface RegulationInfo {
  name: RegulationType;
  fullName: string;
  color: string;
  description: string;
}

export const REGULATION_INFO: Record<RegulationType, RegulationInfo> = {
  FTC: {
    name: "FTC",
    fullName: "Federal Trade Commission",
    color: "#f97316", // Orange
    description: "US consumer protection regulations",
  },
  GDPR: {
    name: "GDPR",
    fullName: "General Data Protection Regulation",
    color: "#3b82f6", // Blue
    description: "EU data protection and privacy",
  },
  DSA: {
    name: "DSA",
    fullName: "Digital Services Act",
    color: "#8b5cf6", // Purple
    description: "EU digital platform regulations",
  },
  CPRA: {
    name: "CPRA",
    fullName: "California Privacy Rights Act",
    color: "#10b981", // Green
    description: "California consumer privacy law",
  },
};

// Mapping from dark pattern categories to applicable regulations
export const REGULATORY_MAPPING: Record<DarkPatternCategory, RegulationType[]> = {
  manipulative_design: ["FTC", "DSA"],
  deceptive_content: ["FTC", "GDPR", "DSA"],
  coercive_flow: ["FTC", "DSA"],
  obstruction: ["GDPR", "DSA", "CPRA"],
  sneaking: ["FTC", "GDPR", "DSA", "CPRA"],
  social_proof_manipulation: ["FTC", "DSA"],
};

// Alternative mapping from legacy pattern families to regulations
export const PATTERN_FAMILY_REGULATORY_MAPPING: Record<PatternFamily, RegulationType[]> = {
  asymmetric_choice: ["FTC", "DSA"],
  hidden_costs: ["FTC", "GDPR", "DSA"],
  confirmshaming: ["FTC", "DSA"],
  obstruction: ["GDPR", "DSA", "CPRA"],
  sneaking: ["FTC", "GDPR", "DSA", "CPRA"],
  urgency: ["FTC", "DSA"],
};

// =============================================================================
// Evidence Types
// =============================================================================

export const EVIDENCE_TYPES = ["nova_ai", "heuristic", "mock", "rule_based"] as const;

export type EvidenceType = (typeof EVIDENCE_TYPES)[number];

export const EVIDENCE_TYPE_LABELS: Record<EvidenceType, string> = {
  nova_ai: "Nova AI evidence",
  heuristic: "Heuristic detection",
  mock: "Simulated",
  rule_based: "Rule-based",
};

// Evidence type confidence baseline values
export const EVIDENCE_TYPE_CONFIDENCE: Record<EvidenceType, number> = {
  nova_ai: 0.8,
  heuristic: 0.6,
  rule_based: 0.65,
  mock: 0.5,
};

// =============================================================================
// Confidence Score Thresholds
// =============================================================================

export const CONFIDENCE_THRESHOLDS = {
  nova_ai_high: 0.85,
  nova_ai_medium: 0.75,
  heuristic_high: 0.7,
  heuristic_medium: 0.55,
  minimum_viable: 0.4,
};

// =============================================================================
// Helper Functions
// =============================================================================

export function getAllCategories(): DarkPatternCategory[] {
  return [...DARK_PATTERN_CATEGORIES];
}

export function getAllScenarios(): ScenarioType[] {
  return [...AUDIT_SCENARIOS];
}

export function getAllPersonas(): PersonaType[] {
  return [...PERSONA_DEFINITIONS];
}

export function getAllSeverityLevels(): SeverityType[] {
  return [...SEVERITY_LEVELS];
}

export function getRegulationsForCategory(category: DarkPatternCategory): RegulationType[] {
  return REGULATORY_MAPPING[category] ?? [];
}

export function getRegulationsForPatternFamily(patternFamily: PatternFamily): RegulationType[] {
  return PATTERN_FAMILY_REGULATORY_MAPPING[patternFamily] ?? [];
}

export function categoryToPatternFamily(category: DarkPatternCategory): PatternFamily | null {
  const reverseMap: Record<DarkPatternCategory, PatternFamily> = {
    manipulative_design: "asymmetric_choice",
    deceptive_content: "hidden_costs",
    coercive_flow: "confirmshaming",
    obstruction: "obstruction",
    sneaking: "sneaking",
    social_proof_manipulation: "urgency",
  };
  return reverseMap[category] ?? null;
}

export function patternFamilyToCategory(patternFamily: PatternFamily): DarkPatternCategory | null {
  return PATTERN_FAMILY_TO_CATEGORY[patternFamily] ?? null;
}

export function isValidCategory(category: string): category is DarkPatternCategory {
  return DARK_PATTERN_CATEGORIES.includes(category as DarkPatternCategory);
}

export function isValidScenario(scenario: string): scenario is ScenarioType {
  return AUDIT_SCENARIOS.includes(scenario as ScenarioType);
}

export function isValidPersona(persona: string): persona is PersonaType {
  return PERSONA_DEFINITIONS.includes(persona as PersonaType);
}

export function isValidSeverity(severity: string): severity is SeverityType {
  return SEVERITY_LEVELS.includes(severity as SeverityType);
}

export function compareSeverity(severity1: SeverityType, severity2: SeverityType): number {
  return SEVERITY_RANK[severity1] - SEVERITY_RANK[severity2];
}

export function getRegulationInfo(regulation: RegulationType): RegulationInfo {
  return REGULATION_INFO[regulation];
}

export function getEvidenceTypeLabel(source?: string): string {
  if (!source) return "Evidence";
  const normalizedSource = source.toLowerCase().replace(/-/g, "_") as EvidenceType;
  return EVIDENCE_TYPE_LABELS[normalizedSource] ?? source;
}

export function formatConfidenceAsPercentage(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

export function isHighConfidence(confidence: number, evidenceType: EvidenceType): boolean {
  if (evidenceType === "nova_ai") {
    return confidence >= CONFIDENCE_THRESHOLDS.nova_ai_high;
  }
  return confidence >= CONFIDENCE_THRESHOLDS.heuristic_high;
}

export function getConfidenceQuality(confidence: number, evidenceType: EvidenceType): "high" | "medium" | "low" {
  if (isHighConfidence(confidence, evidenceType)) return "high";
  if (evidenceType === "nova_ai" && confidence >= CONFIDENCE_THRESHOLDS.nova_ai_medium) {
    return "medium";
  }
  if (evidenceType !== "nova_ai" && confidence >= CONFIDENCE_THRESHOLDS.heuristic_medium) {
    return "medium";
  }
  return "low";
}
