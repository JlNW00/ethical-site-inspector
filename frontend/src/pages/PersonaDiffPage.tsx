import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { Audit, Finding, PersonaComparison } from "../api/types";
import { FindingCard } from "../components/FindingCard";
import { Layout } from "../components/Layout";
import { titleize } from "../lib/format";

interface PersonaData {
  persona: string;
  comparison?: PersonaComparison;
  findings: Finding[];
  path: string;
  controls: string[];
  prices: Array<{ label: string; value: number; raw?: string }>;
  videoUrls: string[];
}

function trimText(value: string, limit = 80) {
  return value.length <= limit ? value : `${value.slice(0, limit - 1).trimEnd()}…`;
}

function extractQuoted(value: string) {
  const parts = value.split('"');
  return parts.length >= 3 ? parts[1] : value;
}

function prettyAction(action: string) {
  const clean = action.replace(/\s+/g, " ").trim();
  const quoted = extractQuoted(clean);
  if (clean.startsWith('Selected offer "') && quoted) {
    if (!/\d/.test(quoted) && quoted.split(" ").length <= 4) {
      return `Selected destination ${quoted}`;
    }
    return `Selected offer ${trimText(quoted, 68)}`;
  }
  if (clean.startsWith('Opened hotel detail "') && quoted) {
    return `Opened hotel ${trimText(quoted, 68)}`;
  }
  if (clean.startsWith('Interacted with checkout control "') && quoted) {
    return quoted;
  }
  return trimText(clean, 80);
}

function prettyPath(actions: string[]) {
  return actions.slice(0, 4).map(prettyAction).join(" → ");
}

function formatTimestamp(value?: string | null) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function getPersonaIcon(persona: string): string {
  switch (persona) {
    case "privacy_sensitive":
      return "🔒";
    case "cost_sensitive":
      return "💰";
    case "exit_intent":
      return "🚪";
    default:
      return "👤";
  }
}

export function PersonaDiffPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [audit, setAudit] = useState<Audit | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!auditId) {
      setError("No audit ID provided");
      setLoading(false);
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const [nextAudit, findingsResponse] = await Promise.all([api.getAudit(auditId), api.getFindings(auditId)]);
        if (!cancelled) {
          setAudit(nextAudit);
          setFindings(findingsResponse.findings);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load persona comparison");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [auditId]);

  const personaData: PersonaData[] = useMemo(() => {
    if (!audit) return [];

    const personas = audit.selected_personas;
    const comparisons = audit.metrics.persona_comparison ?? [];

    return personas.map((persona) => {
      const comparison = comparisons.find((c) => c.persona === persona);
      const personaFindings = findings.filter((f) => f.persona === persona);

      // Extract path from first finding with interacted_controls
      const findingWithPath = personaFindings.find(
        (f) => (f.evidence_payload as { interacted_controls?: string[] }).interacted_controls?.length,
      );
      const interactedControls =
        (findingWithPath?.evidence_payload as { interacted_controls?: string[] })?.interacted_controls ?? [];

      // Collect all unique controls
      const allControls = new Set<string>();
      personaFindings.forEach((f) => {
        f.evidence_payload.matched_buttons?.forEach((btn) => allControls.add(btn));
        f.evidence_payload.button_labels?.forEach((btn) => allControls.add(btn));
      });

      // Collect all prices
      const allPrices: Array<{ label: string; value: number; raw?: string }> = [];
      personaFindings.forEach((f) => {
        f.evidence_payload.matched_prices?.forEach((price) => {
          if (!allPrices.some((p) => p.label === price.label && p.value === price.value)) {
            allPrices.push(price);
          }
        });
        f.evidence_payload.price_points?.forEach((price) => {
          if (!allPrices.some((p) => p.label === price.label && p.value === price.value)) {
            allPrices.push(price);
          }
        });
      });

      // Collect video URLs for this persona
      const personaVideos: string[] = [];
      if (audit.video_urls) {
        Object.entries(audit.video_urls).forEach(([key, url]) => {
          // Key format: "{scenario}_{persona}"
          const parts = key.split(/[_-]/);
          const videoPersona = parts[1] ?? "";
          if (videoPersona === persona) {
            personaVideos.push(url);
          }
        });
      }

      return {
        persona,
        comparison,
        findings: personaFindings,
        path: prettyPath(interactedControls),
        controls: Array.from(allControls),
        prices: allPrices,
        videoUrls: personaVideos,
      };
    });
  }, [audit, findings]);

  // Calculate differences
  const differences = useMemo(() => {
    if (personaData.length < 2) return [];

    const diffs: Array<{ type: string; description: string; severity: "high" | "medium" | "low" }> = [];

    // Check for different findings
    const findingSets = personaData.map((p) => new Set(p.findings.map((f) => f.pattern_family)));
    const allPatterns = new Set(findingSets.flatMap((s) => Array.from(s)));

    allPatterns.forEach((pattern) => {
      const personasWithPattern = personaData.filter((p) => p.findings.some((f) => f.pattern_family === pattern));
      if (personasWithPattern.length > 0 && personasWithPattern.length < personaData.length) {
        diffs.push({
          type: "pattern",
          description: `${titleize(pattern)} only detected for ${personasWithPattern.map((p) => titleize(p.persona)).join(", ")}`,
          severity: "high",
        });
      }
    });

    // Check for price differences
    const priceDeltas = personaData.map((p) => p.comparison?.price_delta ?? 0).filter((d) => d !== 0);
    if (priceDeltas.length > 0) {
      const maxDelta = Math.max(...priceDeltas.map(Math.abs));
      diffs.push({
        type: "price",
        description: `Price variation of $${maxDelta.toFixed(2)} detected between personas`,
        severity: maxDelta > 20 ? "high" : "medium",
      });
    }

    // Check for path divergence (different number of steps)
    const steps = personaData.map((p) => p.comparison?.average_steps ?? 0).filter((s) => s > 0);
    if (steps.length >= 2) {
      const maxSteps = Math.max(...steps);
      const minSteps = Math.min(...steps);
      if (maxSteps !== minSteps) {
        diffs.push({
          type: "path",
          description: `Path length varies by ${maxSteps - minSteps} steps between personas`,
          severity: maxSteps - minSteps > 2 ? "high" : "medium",
        });
      }
    }

    // Check for friction index differences
    const frictionIndices = personaData.map((p) => p.comparison?.friction_index ?? 0).filter((f) => f > 0);
    if (frictionIndices.length >= 2) {
      const maxFriction = Math.max(...frictionIndices);
      const minFriction = Math.min(...frictionIndices);
      if (maxFriction - minFriction > 0.3) {
        diffs.push({
          type: "friction",
          description: `Significant friction difference (${(maxFriction - minFriction).toFixed(1)}) between personas`,
          severity: "high",
        });
      }
    }

    return diffs;
  }, [personaData]);

  // Group findings by scenario for each persona
  const findingsByScenario = useMemo(() => {
    return personaData.map((p) => {
      const grouped = p.findings.reduce<Record<string, Finding[]>>((acc, finding) => {
        acc[finding.scenario] ??= [];
        acc[finding.scenario].push(finding);
        return acc;
      }, {});
      return { ...p, findingsByScenario: grouped };
    });
  }, [personaData]);

  if (loading) {
    return (
      <Layout mode="loading" signals={["persona comparison"]}>
        <section className="hero-panel">
          <div className="empty-state">Loading persona comparison...</div>
        </section>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout mode="live" signals={["error"]}>
        <section className="hero-panel">
          <div className="empty-state">Error: {error}</div>
        </section>
      </Layout>
    );
  }

  const scoreDisplay = audit?.trust_score != null ? `${Math.round(audit.trust_score)}` : "--";

  return (
    <Layout
      mode={audit?.mode ?? "loading"}
      signals={[
        `${personaData.length} personas compared`,
        `${findings.length} total findings`,
        `${differences.length} differences found`,
      ]}
    >
      {/* Hero Section */}
      <section className="hero-panel">
        <div>
          <div className="brand-kicker">Persona Comparison</div>
          <h1>Compare Persona Experiences</h1>
          <p className="hero-copy">
            Side-by-side comparison of how different user personas experience the site. Highlighted differences show
            where treatment varies based on user behavior and intent.
          </p>
          <div className="hero-pills">
            <span className="signal-pill">
              {audit?.metrics.site_host ?? (audit?.target_url ? new URL(audit.target_url).host : "Unknown")}
            </span>
            <span className="signal-pill">{personaData.length} personas</span>
            <span className="signal-pill">{audit?.selected_scenarios.length ?? 0} scenarios</span>
            <span className="signal-pill">{differences.length} differences</span>
          </div>
          <p className="muted" style={{ marginTop: 16 }}>
            Audit ID: {audit?.id} | Generated: {formatTimestamp(audit?.completed_at ?? audit?.updated_at)}
          </p>
          <div className="action-row" style={{ marginTop: 24 }}>
            {auditId && (
              <Link className="btn btn-secondary" to={`/audits/${auditId}/report`}>
                Back to Report
              </Link>
            )}
            <Link className="btn btn-secondary" to="/history">
              Back to History
            </Link>
          </div>
        </div>
        <div className="hero-score">
          <div className="hero-score-label">Trust Score</div>
          <div className="hero-score-value">{scoreDisplay}</div>
          <div
            className={`severity-pill severity-${
              audit?.risk_level === "critical"
                ? "critical"
                : audit?.risk_level === "high"
                  ? "high"
                  : audit?.risk_level === "low"
                    ? "low"
                    : "medium"
            }`}
          >
            {audit?.risk_level ?? "loading"} risk
          </div>
          <div className="hero-score-subtitle">
            {differences.length > 0
              ? `${differences.length} key differences detected between persona experiences`
              : "Persona experiences are relatively consistent"}
          </div>
        </div>
      </section>

      {/* Differences Summary */}
      {differences.length > 0 && (
        <section className="content-panel">
          <div className="section-header">
            <div>
              <h2 className="section-title">Key Differences</h2>
              <p className="section-subtitle">
                Variations in experience between personas that may indicate differential treatment.
              </p>
            </div>
          </div>
          <div className="subgrid">
            {differences.map((diff, index) => (
              <article
                key={index}
                className={`summary-card ${diff.severity === "high" ? "diff-high" : diff.severity === "medium" ? "diff-medium" : ""}`}
              >
                <div className="action-row">
                  <span
                    className={`severity-pill severity-${
                      diff.severity === "high" ? "high" : diff.severity === "medium" ? "medium" : "low"
                    }`}
                  >
                    {diff.type}
                  </span>
                </div>
                <p style={{ marginTop: 12, fontWeight: 500 }}>{diff.description}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* Persona Columns */}
      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Persona Comparison</h2>
            <p className="section-subtitle">
              Each column shows the unique experience for that persona, including their path, findings, and observed UI.
            </p>
          </div>
        </div>

        <div className="persona-columns">
          {findingsByScenario.map((persona) => (
            <div key={persona.persona} className="persona-column">
              {/* Persona Header */}
              <div className="persona-header">
                <div className="persona-icon">{getPersonaIcon(persona.persona)}</div>
                <h3 className="persona-name">{titleize(persona.persona)}</h3>
                {persona.comparison && (
                  <div className="persona-metrics">
                    <span className="signal-pill">{persona.comparison.finding_count} findings</span>
                    <span className="signal-pill">{persona.comparison.average_steps} avg steps</span>
                    <span className="signal-pill">
                      friction: {(persona.comparison.friction_index * 100).toFixed(0)}%
                    </span>
                    {persona.comparison.price_delta !== 0 && (
                      <span
                        className={`signal-pill ${persona.comparison.price_delta < 0 ? "price-lower" : "price-higher"}`}
                      >
                        {persona.comparison.price_delta > 0 ? "+" : ""}${persona.comparison.price_delta.toFixed(2)}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Observed Path */}
              {persona.path && (
                <div className="persona-section">
                  <h4 className="section-label">Observed Path</h4>
                  <p className="persona-path">{persona.path}</p>
                </div>
              )}

              {/* Observed Prices */}
              {persona.prices.length > 0 && (
                <div className="persona-section">
                  <h4 className="section-label">Prices Observed</h4>
                  <div className="price-list">
                    {persona.prices.map((price, idx) => (
                      <div key={idx} className="price-item">
                        <span className="price-value">{price.raw ?? `$${price.value.toFixed(2)}`}</span>
                        <span className="price-label">{price.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* UI Controls Found */}
              {persona.controls.length > 0 && (
                <div className="persona-section">
                  <h4 className="section-label">UI Controls Found</h4>
                  <div className="control-tags">
                    {persona.controls.slice(0, 8).map((control, idx) => (
                      <span key={idx} className="control-tag">
                        {control}
                      </span>
                    ))}
                    {persona.controls.length > 8 && (
                      <span className="control-tag control-tag-more">+{persona.controls.length - 8} more</span>
                    )}
                  </div>
                </div>
              )}

              {/* Findings by Scenario */}
              <div className="persona-section">
                <h4 className="section-label">Findings</h4>
                {Object.keys(persona.findingsByScenario).length === 0 ? (
                  <div className="empty-state">No findings for this persona</div>
                ) : (
                  <div className="scenario-findings">
                    {Object.entries(persona.findingsByScenario).map(([scenario, scenarioFindings]) => (
                      <div key={scenario} className="scenario-group">
                        <h5 className="scenario-title">{titleize(scenario)}</h5>
                        <div className="finding-list">
                          {scenarioFindings.map((finding) => (
                            <FindingCard key={finding.id} finding={finding} />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Notable Patterns */}
              {persona.comparison?.notable_patterns && persona.comparison.notable_patterns.length > 0 && (
                <div className="persona-section">
                  <h4 className="section-label">Dominant Patterns</h4>
                  <div className="pattern-pills">
                    {persona.comparison.notable_patterns.map((pattern, idx) => (
                      <span key={idx} className="signal-pill">
                        {titleize(pattern)}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Session Recording Link */}
              {persona.videoUrls.length > 0 && (
                <div className="video-link-container">
                  {persona.videoUrls.length === 1 ? (
                    <a
                      href={persona.videoUrls[0]}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="video-link"
                    >
                      🎬 Watch session
                    </a>
                  ) : (
                    <div className="persona-section">
                      <h4 className="section-label">Session Recordings</h4>
                      <div className="pattern-pills">
                        {persona.videoUrls.map((url, idx) => (
                          <a
                            key={idx}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="video-link"
                            style={{ fontSize: "12px" }}
                          >
                            🎬 Watch #{idx + 1}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Target URL */}
      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Audit Details</h2>
          </div>
        </div>
        <div className="grid-3">
          <div className="summary-card">
            <div className="metric-label">Target URL</div>
            <div className="metric-value" style={{ fontSize: "20px" }}>
              {audit?.target_url}
            </div>
          </div>
          <div className="summary-card">
            <div className="metric-label">Mode</div>
            <div className="metric-value" style={{ fontSize: "20px" }}>
              {audit?.mode}
            </div>
          </div>
          <div className="summary-card">
            <div className="metric-label">Status</div>
            <div className="metric-value" style={{ fontSize: "20px" }}>
              {audit?.status}
            </div>
          </div>
        </div>
      </section>
    </Layout>
  );
}
