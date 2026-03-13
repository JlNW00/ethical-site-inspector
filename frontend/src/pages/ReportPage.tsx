import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { Audit, AuditEvent, Finding } from "../api/types";
import { FindingCard } from "../components/FindingCard";
import { Layout } from "../components/Layout";
import { ProgressMeter } from "../components/ProgressMeter";
import { titleize } from "../lib/format";

interface ScreenshotEntry {
  url: string;
  scenario: string;
  persona: string;
  step: string;
  timestamp: string;
}

function targetHost(targetUrl?: string, fallback?: string) {
  if (fallback) {
    return fallback;
  }
  if (!targetUrl) {
    return "Unknown target";
  }
  try {
    return new URL(targetUrl).host;
  } catch {
    return targetUrl;
  }
}

function formatTimestamp(value?: string | null) {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "2-digit",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(date);
}

function riskSummary(riskLevel?: string | null) {
  switch (riskLevel) {
    case "low":
      return "Low risk: trust signals stayed stable across the audited journeys.";
    case "moderate":
      return "Moderate risk: some trust friction was observed, but it was not dominant.";
    case "high":
      return "High risk: trust friction was repeatedly observed in the audited journeys.";
    case "critical":
      return "Critical risk: the audited journeys repeatedly added friction before commitment or exit.";
    default:
      return "Risk level reflects how consistently friction or pressure appeared in the audited paths.";
  }
}

function trimText(value: string, limit = 80) {
  return value.length <= limit ? value : `${value.slice(0, limit - 1).trimEnd()}…`;
}

function parseStepFromUrl(url: string): { scenario: string; persona: string; step: string } {
  // URL format: .../{scenario}_{persona}_{step}.png or similar
  const parts = url.split("/").pop()?.replace(/\.[^.]+$/, "").split("_") ?? [];
  // Try to extract scenario, persona, step from filename
  if (parts.length >= 3) {
    return {
      scenario: parts[0] ?? "unknown",
      persona: parts[1] ?? "unknown",
      step: parts.slice(2).join("_") ?? "unknown",
    };
  }
  return { scenario: "unknown", persona: "unknown", step: "unknown" };
}

function formatStepName(step: string): string {
  return step.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function extractScreenshotsFromFindings(findings: Finding[]): ScreenshotEntry[] {
  const entries: ScreenshotEntry[] = [];
  const seenUrls = new Set<string>();

  for (const finding of findings) {
    const urls = finding.evidence_payload.screenshot_urls ?? [];
    for (const url of urls) {
      if (seenUrls.has(url)) continue;
      seenUrls.add(url);
      const { step } = parseStepFromUrl(url);
      entries.push({
        url,
        scenario: finding.scenario,
        persona: finding.persona,
        step,
        timestamp: finding.created_at,
      });
    }
  }

  // Sort by timestamp
  return entries.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
}

function extractScreenshotsFromEvents(events: AuditEvent[]): ScreenshotEntry[] {
  const entries: ScreenshotEntry[] = [];
  const seenUrls = new Set<string>();

  for (const event of events) {
    const details = event.details as { screenshot_url?: string; scenario?: string; persona?: string; step?: string } | undefined;
    if (details?.screenshot_url && !seenUrls.has(details.screenshot_url)) {
      seenUrls.add(details.screenshot_url);
      entries.push({
        url: details.screenshot_url,
        scenario: details.scenario ?? "audit",
        persona: details.persona ?? "default",
        step: details.step ?? event.phase,
        timestamp: event.created_at,
      });
    }
  }

  return entries.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
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

export function ReportPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [audit, setAudit] = useState<Audit | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedImage, setExpandedImage] = useState<string | null>(null);

  useEffect(() => {
    if (!auditId) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const [nextAudit, findingsResponse] = await Promise.all([
          api.getAudit(auditId),
          api.getFindings(auditId),
        ]);
        if (!cancelled) {
          setAudit(nextAudit);
          setFindings(findingsResponse.findings);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load report");
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

  const groupedFindings = useMemo(() => {
    return findings.reduce<Record<string, Record<string, Finding[]>>>((accumulator, finding) => {
      accumulator[finding.scenario] ??= {};
      accumulator[finding.scenario][finding.persona] ??= [];
      accumulator[finding.scenario][finding.persona].push(finding);
      return accumulator;
    }, {});
  }, [findings]);

  const screenshotTimeline = useMemo(() => {
    const fromFindings = extractScreenshotsFromFindings(findings);
    const fromEvents = extractScreenshotsFromEvents(audit?.events ?? []);
    // Combine and dedupe by URL
    const seen = new Set<string>();
    const combined: ScreenshotEntry[] = [];
    for (const entry of [...fromEvents, ...fromFindings]) {
      if (!seen.has(entry.url)) {
        seen.add(entry.url);
        combined.push(entry);
      }
    }
    return combined.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [findings, audit?.events]);

  const personaPaths = useMemo(() => {
    return findings.reduce<Record<string, string>>((accumulator, finding) => {
      if (accumulator[finding.persona]) {
        return accumulator;
      }
      const interactedControls =
        (finding.evidence_payload as { interacted_controls?: string[] }).interacted_controls ?? [];
      if (!interactedControls.length) {
        return accumulator;
      }
      accumulator[finding.persona] = interactedControls.slice(0, 4).map(prettyAction).join(" -> ");
      return accumulator;
    }, {});
  }, [findings]);

  const trustProgress = audit?.trust_score ?? 0;
  const scoreDisplay = audit?.trust_score != null ? `${Math.round(audit.trust_score)} / 100` : "-- / 100";
  const hostLabel = targetHost(audit?.target_url, audit?.metrics.site_host);
  const heroOverview = audit
    ? `${findings.length} evidence-backed findings were generated across ${audit.selected_scenarios.length} scenarios and ${audit.selected_personas.length} personas. ${riskSummary(audit.risk_level)}`
    : "A decision-ready trust report combining persona journeys, captured evidence, and remediation guidance.";

  if (loading) {
    return (
      <Layout mode="loading" signals={["loading report"]}>
        <section className="hero-panel">
          <div>
            <div className="brand-kicker">Trust-risk report</div>
            <h1>Trust Audit Report</h1>
            <div className="hero-pills">
              <span className="signal-pill">Loading...</span>
            </div>
          </div>
          <div className="hero-score">
            <div className="hero-score-label">Trust Score</div>
            <div className="hero-score-value">-- / 100</div>
            <div style={{ marginTop: 18 }}>
              <ProgressMeter value={0} />
            </div>
          </div>
        </section>
        <section className="content-panel">
          <div className="empty-state">Loading report data...</div>
        </section>
      </Layout>
    );
  }

  // Show error state for failed audits
  if (audit?.status === "failed") {
    return (
      <Layout mode={audit?.mode ?? "live"} signals={["audit failed"]}>
        <section className="hero-panel">
          <div>
            <div className="brand-kicker">Trust-risk report</div>
            <h1>Audit Failed</h1>
            <p className="hero-copy">
              This audit encountered an error during execution and could not complete successfully.
            </p>
            <div className="hero-pills">
              <span className="signal-pill">{hostLabel}</span>
              <span className="signal-pill">{audit?.mode} mode</span>
              <span className="signal-pill">failed</span>
            </div>
            <p className="muted" style={{ marginTop: 16 }}>
              Target URL: {audit?.target_url} | Failed: {formatTimestamp(audit?.updated_at)}
            </p>
            <div className="action-row" style={{ marginTop: 24 }}>
              {auditId ? (
                <Link className="btn btn-secondary" to={`/audits/${auditId}/run`}>
                  View Run Log
                </Link>
              ) : null}
              <Link className="btn btn-secondary" to="/history">
                Back to History
              </Link>
            </div>
          </div>
          <div className="hero-score">
            <div className="hero-score-label">Status</div>
            <div className="hero-score-value" style={{ fontSize: "48px", color: "var(--critical)" }}>
              Failed
            </div>
            <div className="severity-pill severity-critical">error</div>
          </div>
        </section>

        <section className="content-panel">
          <div className="section-header">
            <div>
              <h2 className="section-title">Error Details</h2>
              <p className="section-subtitle">Information about why the audit failed.</p>
            </div>
          </div>
          <div className="subgrid">
            <div className="summary-card" style={{ borderLeft: "3px solid var(--critical)" }}>
              <div className="metric-label">Error Message</div>
              <p style={{ marginTop: 12 }}>{audit?.summary ?? "An unexpected error occurred during the audit execution."}</p>
            </div>
            {error ? (
              <div className="summary-card" style={{ borderLeft: "3px solid var(--high)" }}>
                <div className="metric-label">Load Error</div>
                <p style={{ marginTop: 12 }}>{error}</p>
              </div>
            ) : null}
          </div>
        </section>
      </Layout>
    );
  }

  return (
    <Layout
      mode={audit?.mode ?? "loading"}
      signals={[
        audit?.risk_level ? `${audit.risk_level} risk` : "loading report",
        `${findings.length} findings`,
      ]}
    >
      <section className="hero-panel">
        <div>
          <div className="brand-kicker">Trust-risk report</div>
          <h1>Trust Audit Report</h1>
          <p className="hero-copy">{heroOverview}</p>
          <div className="hero-pills">
            <span className="signal-pill">{hostLabel}</span>
            <span className="signal-pill">{audit?.mode ?? "loading"} mode</span>
            <span className="signal-pill">{audit?.metrics.evidence_origin_label ?? "Evidence loading"}</span>
            <span className="signal-pill">{audit?.selected_scenarios.length ?? 0} scenarios</span>
            <span className="signal-pill">{audit?.selected_personas.length ?? 0} personas</span>
            {(audit?.selected_personas ?? []).map((persona) => (
              <span className="signal-pill" key={persona}>
                {titleize(persona)}
              </span>
            ))}
          </div>
          <p className="muted" style={{ marginTop: 16 }}>
            Target URL: {audit?.target_url ?? "Loading"} | Generated: {formatTimestamp(audit?.completed_at ?? audit?.updated_at)}
          </p>
          <div className="action-row" style={{ marginTop: 24 }}>
            {auditId ? (
              <a className="btn btn-primary" href={api.getReportUrl(auditId)} target="_blank" rel="noreferrer">
                Open HTML report
              </a>
            ) : null}
            {auditId ? (
              <a className="btn btn-primary" href={api.getPdfUrl(auditId)} target="_blank" rel="noreferrer">
                Download PDF
              </a>
            ) : null}
            {auditId ? (
              <Link className="btn btn-primary" to={`/audits/${auditId}/diff`}>
                Compare Personas
              </Link>
            ) : null}
            {auditId ? (
              <Link className="btn btn-secondary" to={`/audits/${auditId}/run`}>
                Back to run log
              </Link>
            ) : null}
            <Link className="btn btn-secondary" to="/history">
              Back to History
            </Link>
          </div>
        </div>
        <div className="hero-score">
          <div className="hero-score-label">Trust Score</div>
          <div className="hero-score-value">{scoreDisplay}</div>
          <div className={`severity-pill severity-${audit?.risk_level === "critical" ? "critical" : audit?.risk_level === "high" ? "high" : audit?.risk_level === "low" ? "low" : "medium"}`}>
            {audit?.risk_level ?? "loading"} risk
          </div>
          <div className="hero-score-subtitle">{riskSummary(audit?.risk_level)}</div>
          <p className="muted" style={{ marginTop: 12 }}>
            Higher score = more trustworthy observed journeys. Scale: 82-100 low, 64-81 moderate, 42-63 high, 0-41 critical.
          </p>
          <div style={{ marginTop: 18 }}>
            <ProgressMeter value={trustProgress} />
          </div>
        </div>
      </section>

      {error ? <section className="content-panel"><div className="empty-state">{error}</div></section> : null}
      {audit?.status !== "completed" ? (
        <section className="content-panel">
          <div className="empty-state">
            This audit is still {audit?.status ?? "loading"}. The report view will hydrate as soon as findings are available.
          </div>
        </section>
      ) : null}

      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Executive summary</h2>
            <p className="section-subtitle">The signal judges need first: risk concentration, coverage, and whether persona experiences diverge.</p>
          </div>
        </div>
        <div className="grid-3">
          <div className="summary-card">
            <div className="metric-label">Finding count</div>
            <div className="metric-value">{findings.length}</div>
            <div className="muted">
              {(() => {
                const suppressedCount = findings.filter((f) => f.suppressed).length;
                return suppressedCount > 0
                  ? `${findings.length - suppressedCount} confirmed (${suppressedCount} suppressed)`
                  : "Evidence-backed trust and compliance concerns";
              })()}
            </div>
          </div>
          <div className="summary-card">
            <div className="metric-label">Scenarios covered</div>
            <div className="metric-value">{audit?.selected_scenarios.length ?? 0}</div>
            <div className="muted">{audit?.selected_scenarios.map(titleize).join(", ")}</div>
          </div>
          <div className="summary-card">
            <div className="metric-label">Personas compared</div>
            <div className="metric-value">{audit?.selected_personas.length ?? 0}</div>
            <div className="muted">{audit?.selected_personas.map(titleize).join(", ")}</div>
          </div>
          <div className="summary-card">
            <div className="metric-label">Evidence provenance</div>
            <div className="metric-value">{audit?.metrics.evidence_origin_label ?? "Unknown"}</div>
            <div className="muted">{audit?.metrics.site_host ?? audit?.target_url}</div>
          </div>
        </div>
      </section>

      {/* Regulatory Summary Section */}
      {(() => {
        const regulatoryCounts = findings
          .filter((f) => !f.suppressed)
          .reduce<Record<string, number>>((acc, finding) => {
            (finding.regulatory_categories ?? []).forEach((reg) => {
              acc[reg] = (acc[reg] || 0) + 1;
            });
            return acc;
          }, {});

        const hasRegulatoryFindings = Object.keys(regulatoryCounts).length > 0;

        if (!hasRegulatoryFindings) return null;

        return (
          <section className="content-panel">
            <div className="section-header">
              <div>
                <h2 className="section-title">Regulatory summary</h2>
                <p className="section-subtitle">Regulatory frameworks potentially implicated by findings.</p>
              </div>
            </div>
            <div className="regulatory-grid">
              {Object.entries(regulatoryCounts).map(([reg, count]) => {
                const info = (() => {
                  switch (reg) {
                    case "FTC":
                      return {
                        name: "FTC",
                        fullName: "Federal Trade Commission",
                        color: "#f97316",
                        description: "US consumer protection",
                      };
                    case "GDPR":
                      return {
                        name: "GDPR",
                        fullName: "General Data Protection Regulation",
                        color: "#3b82f6",
                        description: "EU data protection",
                      };
                    case "DSA":
                      return {
                        name: "DSA",
                        fullName: "Digital Services Act",
                        color: "#8b5cf6",
                        description: "EU digital platform regulations",
                      };
                    case "CPRA":
                      return {
                        name: "CPRA",
                        fullName: "California Privacy Rights Act",
                        color: "#10b981",
                        description: "California consumer privacy",
                      };
                    default:
                      return {
                        name: reg,
                        fullName: reg,
                        color: "#69a2ff",
                        description: "Regulatory framework",
                      };
                  }
                })();
                return (
                  <div
                    key={reg}
                    className="regulatory-card"
                    style={{
                      borderLeft: `4px solid ${info.color}`,
                    }}
                  >
                    <div className="regulatory-header">
                      <span
                        className="regulatory-badge"
                        style={{
                          backgroundColor: `${info.color}20`,
                          color: info.color,
                        }}
                      >
                        {info.name}
                      </span>
                      <span className="regulatory-count">{count} finding{count === 1 ? "" : "s"}</span>
                    </div>
                    <div className="regulatory-fullname">{info.fullName}</div>
                    <div className="regulatory-description">{info.description}</div>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })()}

      <div className="grid-2" style={{ marginTop: 22 }}>
        <section className="content-panel">
          <div className="section-header">
            <div>
              <h2 className="section-title">Persona comparison</h2>
              <p className="section-subtitle">How trust risk changes across user goals and sensitivities.</p>
            </div>
          </div>
          <div className="subgrid">
            {audit?.metrics.persona_comparison?.map((item) => (
              <article className="compare-card" key={item.persona}>
                <div className="action-row">
                  <span className="signal-pill">{titleize(item.persona)}</span>
                  <span className="signal-pill">{item.finding_count} findings</span>
                </div>
                <h3 className="finding-title">{item.headline}</h3>
                {personaPaths[item.persona] ? (
                  <p className="muted">
                    <strong>Observed path:</strong> {personaPaths[item.persona]}
                  </p>
                ) : null}
                <p className="muted">
                  Average steps: {item.average_steps} | Friction index: {item.friction_index} | Price delta: ${item.price_delta}
                </p>
                <p className="muted">Dominant patterns: {item.notable_patterns.map(titleize).join(", ") || "None"}</p>
              </article>
            )) ?? <div className="empty-state">Persona comparisons will appear once the audit is complete.</div>}
          </div>
        </section>

        <section className="content-panel">
          <div className="section-header">
            <div>
              <h2 className="section-title">Scenario breakdown</h2>
              <p className="section-subtitle">Where the highest trust risk concentrates within the audited journeys.</p>
            </div>
          </div>
          <div className="subgrid">
            {audit?.metrics.scenario_breakdown?.map((item) => (
              <article className="compare-card" key={item.scenario}>
                <div className="action-row">
                  <span className="signal-pill">{titleize(item.scenario)}</span>
                  <span className={`severity-pill severity-${item.risk_level === "critical" ? "critical" : item.risk_level === "high" ? "high" : "medium"}`}>
                    {item.risk_level}
                  </span>
                </div>
                <h3 className="finding-title">{item.headline}</h3>
                <p className="muted">{item.finding_count} findings</p>
                <p className="muted">Dominant patterns: {item.dominant_patterns.map(titleize).join(", ") || "None"}</p>
              </article>
            )) ?? <div className="empty-state">Scenario summaries will appear once the audit is complete.</div>}
          </div>
        </section>
      </div>

      {/* Screenshot Timeline Section */}
      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Screenshot Timeline</h2>
            <p className="section-subtitle">Chronological evidence captured during the audit journey.</p>
          </div>
        </div>
        {screenshotTimeline.length > 0 ? (
          <div className="timeline">
            {screenshotTimeline.map((entry, index) => (
              <div key={`${entry.url}-${index}`} className="timeline-item">
                <div>
                  <div className="timeline-phase">Step {index + 1}</div>
                  <div className="timeline-message">{formatStepName(entry.step)}</div>
                  <div className="timeline-details">
                    {titleize(entry.scenario)} | {titleize(entry.persona)}
                    <br />
                    {formatTimestamp(entry.timestamp)}
                  </div>
                </div>
                <div>
                  <button
                    onClick={() => setExpandedImage(entry.url)}
                    style={{
                      background: "none",
                      border: "none",
                      padding: 0,
                      cursor: "pointer",
                      display: "block",
                    }}
                    aria-label={`View screenshot: ${formatStepName(entry.step)}`}
                  >
                    <img
                      src={entry.url}
                      alt={`${formatStepName(entry.step)} - ${entry.scenario}`}
                      className="evidence-thumb"
                      style={{ margin: 0 }}
                    />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            No screenshots available. Screenshots are captured during audit execution and will appear here once the audit is complete.
          </div>
        )}
      </section>

      {/* Expanded Image Modal */}
      {expandedImage && (
        <div
          onClick={() => setExpandedImage(null)}
          onKeyDown={(e) => {
            if (e.key === "Escape") setExpandedImage(null);
          }}
          role="dialog"
          aria-modal="true"
          tabIndex={0}
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.9)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            cursor: "pointer",
          }}
        >
          <img
            src={expandedImage}
            alt="Expanded screenshot"
            style={{
              maxWidth: "90%",
              maxHeight: "90%",
              borderRadius: "12px",
              boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
            }}
          />
          <button
            onClick={() => setExpandedImage(null)}
            style={{
              position: "absolute",
              top: "20px",
              right: "20px",
              background: "rgba(255, 255, 255, 0.1)",
              border: "1px solid rgba(255, 255, 255, 0.3)",
              color: "#fff",
              padding: "12px 20px",
              borderRadius: "8px",
              cursor: "pointer",
              fontSize: "16px",
            }}
          >
            ✕ Close
          </button>
        </div>
      )}

      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Findings and evidence</h2>
            <p className="section-subtitle">Grouped by scenario and persona so stakeholder teams can triage remediations quickly.</p>
          </div>
        </div>
        {Object.keys(groupedFindings).length ? (
          <div className="subgrid">
            {Object.entries(groupedFindings).map(([scenario, personas]) => (
              <section key={scenario} className="subgrid">
                <div>
                  <h3 className="finding-title">{titleize(scenario)}</h3>
                </div>
                {Object.entries(personas).map(([persona, personaFindings]) => (
                  <div className="subgrid" key={`${scenario}-${persona}`}>
                    <div className="muted" style={{ fontWeight: 700 }}>
                      {titleize(persona)}
                    </div>
                    {personaFindings.map((finding) => (
                      <FindingCard key={finding.id} finding={finding} />
                    ))}
                  </div>
                ))}
              </section>
            ))}
          </div>
        ) : (
          <div className="empty-state">Findings will appear once the classifier finishes reasoning over the evidence.</div>
        )}
      </section>
    </Layout>
  );
}
