export type AuditStatus = "queued" | "running" | "completed" | "failed";
export type Severity = "low" | "medium" | "high" | "critical";

export interface AuditEvent {
  id: number;
  phase: string;
  status: string;
  message: string;
  progress: number;
  details: Record<string, unknown>;
  created_at: string;
}

export interface Finding {
  id: string;
  scenario: string;
  persona: string;
  pattern_family: string;
  severity: Severity;
  title: string;
  explanation: string;
  remediation: string;
  evidence_excerpt: string;
  rule_reason: string;
  evidence_payload: {
    source?: string;
    source_label?: string;
    site_host?: string;
    page_title?: string;
    page_url?: string;
    screenshot_urls?: string[];
    button_labels?: string[];
    matched_buttons?: string[];
    matched_prices?: Array<{ label: string; value: number; raw?: string }>;
    supporting_evidence?: string[];
    checkbox_states?: Record<string, boolean>;
    price_points?: Array<{ label: string; value: number }>;
    friction_indicators?: string[];
    activity_log?: string[];
    interacted_controls?: string[];
  };
  confidence: number;
  trust_impact: number;
  order_index: number;
  created_at: string;
}

export interface Audit {
  id: string;
  target_url: string;
  mode: string;
  status: AuditStatus;
  summary: string | null;
  trust_score: number | null;
  risk_level: string | null;
  selected_scenarios: string[];
  selected_personas: string[];
  report_public_url: string | null;
  metrics: {
    finding_count?: number;
    observation_count?: number;
    site_host?: string;
    evidence_origin_label?: string;
    persona_comparison?: PersonaComparison[];
    scenario_breakdown?: ScenarioBreakdown[];
  };
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  events: AuditEvent[];
}

export interface PersonaComparison {
  persona: string;
  headline: string;
  finding_count: number;
  friction_index: number;
  average_steps: number;
  price_delta: number;
  notable_patterns: string[];
}

export interface ScenarioBreakdown {
  scenario: string;
  headline: string;
  risk_level: string;
  finding_count: number;
  dominant_patterns: string[];
}

export interface FindingsResponse {
  audit_id: string;
  findings: Finding[];
}

export interface Readiness {
  status: "ready";
  configured_mode: string;
  effective_mode: string;
  browser_provider: string;
  classifier_provider: string;
  storage_provider: string;
  nova_ready: boolean;
  playwright_ready: boolean;
  storage_ready: boolean;
  seeded_demo_audit_id: string | null;
}

export interface CreateAuditRequest {
  target_url: string;
  scenarios: string[];
  personas: string[];
}

export interface AuditListParams {
  status?: string;
  url_contains?: string;
}
