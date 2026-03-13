import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import type { Audit, Finding } from "../api/types";
import { Layout } from "../components/Layout";
import { ProgressMeter } from "../components/ProgressMeter";
import { titleize } from "../lib/format";

interface AuditData {
  audit: Audit;
  findings: Finding[];
}

function formatTimestamp(value?: string | null): string {
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

function getSeverityClass(riskLevel?: string | null): string {
  switch (riskLevel) {
    case "critical":
      return "severity-critical";
    case "high":
      return "severity-high";
    case "moderate":
      return "severity-medium";
    case "low":
      return "severity-low";
    default:
      return "severity-medium";
  }
}

function getScoreDeltaColor(delta: number): string {
  if (delta > 0) return "var(--accent)";
  if (delta < 0) return "var(--critical)";
  return "var(--medium)";
}

export function ComparePage() {
  const [searchParams] = useSearchParams();
  const auditIdA = searchParams.get("a");
  const auditIdB = searchParams.get("b");

  const [auditA, setAuditA] = useState<AuditData | null>(null);
  const [auditB, setAuditB] = useState<AuditData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auditIdA || !auditIdB) {
      setError("Missing audit IDs. Please provide both 'a' and 'b' query parameters.");
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function loadAudits() {
      try {
        const [auditAResponse, auditBResponse, findingsAResponse, findingsBResponse] = await Promise.all([
          api.getAudit(auditIdA as string),
          api.getAudit(auditIdB as string),
          api.getFindings(auditIdA as string),
          api.getFindings(auditIdB as string),
        ]);

        if (!cancelled) {
          setAuditA({ audit: auditAResponse, findings: findingsAResponse.findings });
          setAuditB({ audit: auditBResponse, findings: findingsBResponse.findings });
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Error loading comparison");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadAudits();

    return () => {
      cancelled = true;
    };
  }, [auditIdA, auditIdB]);

  // Calculate comparison metrics
  const comparison = useMemo(() => {
    if (!auditA || !auditB) return null;

    const scoreA = auditA.audit.trust_score ?? 0;
    const scoreB = auditB.audit.trust_score ?? 0;
    const scoreDelta = scoreB - scoreA;

    const findingsA = auditA.findings.length;
    const findingsB = auditB.findings.length;
    const findingsDelta = findingsB - findingsA;

    // Group findings by scenario for each audit
    const findingsByScenarioA = auditA.findings.reduce<Record<string, number>>((acc, finding) => {
      acc[finding.scenario] = (acc[finding.scenario] || 0) + 1;
      return acc;
    }, {});

    const findingsByScenarioB = auditB.findings.reduce<Record<string, number>>((acc, finding) => {
      acc[finding.scenario] = (acc[finding.scenario] || 0) + 1;
      return acc;
    }, {});

    // Get all unique scenarios
    const allScenarios = new Set([
      ...Object.keys(findingsByScenarioA),
      ...Object.keys(findingsByScenarioB),
      ...auditA.audit.selected_scenarios,
      ...auditB.audit.selected_scenarios,
    ]);

    return {
      scoreDelta,
      findingsDelta,
      findingsByScenarioA,
      findingsByScenarioB,
      allScenarios: Array.from(allScenarios),
    };
  }, [auditA, auditB]);

  if (loading) {
    return (
      <Layout mode="loading" signals={["comparing audits"]}>
        <section className="hero-panel">
          <div className="empty-state">Loading comparison...</div>
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

  if (!auditA || !auditB || !comparison) {
    return (
      <Layout mode="live" signals={["error"]}>
        <section className="hero-panel">
          <div className="empty-state">Unable to load audit comparison data.</div>
        </section>
      </Layout>
    );
  }

  const { scoreDelta, findingsDelta, findingsByScenarioA, findingsByScenarioB, allScenarios } = comparison;

  return (
    <Layout
      mode="live"
      signals={["audit comparison", `${auditA.findings.length} vs ${auditB.findings.length} findings`]}
    >
      {/* Hero Section with Diff Summary */}
      <section className="hero-panel">
        <div>
          <div className="brand-kicker">Audit Comparison</div>
          <h1>Compare Two Audits</h1>
          <p className="hero-copy">
            Side-by-side comparison of trust scores, risk levels, and findings across two audits of {" "}
            {auditA.audit.target_url}.
          </p>
          <div className="hero-pills">
            <span className="signal-pill">{auditA.audit.selected_scenarios.length} scenarios</span>
            <span className="signal-pill">{auditA.audit.selected_personas.length} personas</span>
            <span className="signal-pill">
              {findingsDelta > 0 ? "+" : ""}
              {findingsDelta} findings delta
            </span>
          </div>
          <div className="action-row" style={{ marginTop: 24 }}>
            <Link className="btn btn-secondary" to="/history">
              Back to History
            </Link>
          </div>
        </div>

        <div className="hero-score">
          <div className="hero-score-label">Trust Score Delta</div>
          <div
            className="hero-score-value"
            style={{
              fontSize: "64px",
              color: getScoreDeltaColor(scoreDelta),
            }}
          >
            {scoreDelta > 0 ? "+" : ""}
            {scoreDelta}
          </div>
          <div className="hero-score-subtitle">
            {scoreDelta > 0
              ? "Audit B has a higher trust score"
              : scoreDelta < 0
                ? "Audit B has a lower trust score"
                : "Both audits have the same trust score"}
          </div>
          <div style={{ marginTop: 12 }}>
            <span className="muted">{auditA.audit.trust_score ?? "--"} → {auditB.audit.trust_score ?? "--"}</span>
          </div>
        </div>
      </section>

      {/* Comparison Columns */}
      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Audit Comparison</h2>
            <p className="section-subtitle">
              Comparing two audits side by side with trust scores, risk levels, and finding counts.
            </p>
          </div>
        </div>

        <div className="compare-columns">
          {/* Audit A Column */}
          <div className="compare-column">
            <div className="compare-column-header">
              <h3 className="compare-column-title">Audit A</h3>
              <span className="signal-pill">{formatTimestamp(auditA.audit.completed_at)}</span>
            </div>

            <div className="compare-metric-card">
              <div className="metric-label">Trust Score</div>
              <div className="compare-score-value">{auditA.audit.trust_score ?? "--"}</div>
              <div style={{ marginTop: 12 }}>
                <ProgressMeter value={auditA.audit.trust_score ?? 0} />
              </div>
            </div>

            <div className="compare-metric-card">
              <div className="metric-label">Risk Level</div>
              <div style={{ marginTop: 8 }}>
                <span className={`severity-pill ${getSeverityClass(auditA.audit.risk_level)}`}>
                  {auditA.audit.risk_level ?? "unknown"}
                </span>
              </div>
            </div>

            <div className="compare-metric-card">
              <div className="metric-label">Total Findings</div>
              <div className="compare-score-value">{auditA.findings.length}</div>
            </div>

            <div className="compare-metric-card">
              <div className="metric-label">Scenarios Tested</div>
              <div className="metric-value" style={{ fontSize: "24px" }}>
                {auditA.audit.selected_scenarios.length}
              </div>
              <div className="muted" style={{ marginTop: 4 }}>
                {auditA.audit.selected_scenarios.map(titleize).join(", ")}
              </div>
            </div>

            <div className="compare-metric-card">
              <div className="metric-label">Personas Tested</div>
              <div className="metric-value" style={{ fontSize: "24px" }}>
                {auditA.audit.selected_personas.length}
              </div>
              <div className="muted" style={{ marginTop: 4 }}>
                {auditA.audit.selected_personas.map(titleize).join(", ")}
              </div>
            </div>

            <div className="action-row" style={{ marginTop: 16 }}>
              <Link className="btn btn-secondary" to={`/audits/${auditA.audit.id}/report`}>
                View Report
              </Link>
              <Link className="btn btn-secondary" to={`/audits/${auditA.audit.id}/run`}>
                View Run Log
              </Link>
            </div>
          </div>

          {/* Audit B Column */}
          <div className="compare-column">
            <div className="compare-column-header">
              <h3 className="compare-column-title">Audit B</h3>
              <span className="signal-pill">{formatTimestamp(auditB.audit.completed_at)}</span>
            </div>

            <div className="compare-metric-card">
              <div className="metric-label">Trust Score</div>
              <div className="compare-score-value">{auditB.audit.trust_score ?? "--"}</div>
              <div style={{ marginTop: 12 }}>
                <ProgressMeter value={auditB.audit.trust_score ?? 0} />
              </div>
            </div>

            <div className="compare-metric-card">
              <div className="metric-label">Risk Level</div>
              <div style={{ marginTop: 8 }}>
                <span className={`severity-pill ${getSeverityClass(auditB.audit.risk_level)}`}>
                  {auditB.audit.risk_level ?? "unknown"}
                </span>
              </div>
            </div>

            <div className="compare-metric-card">
              <div className="metric-label">Total Findings</div>
              <div className="compare-score-value">{auditB.findings.length}</div>
            </div>

            <div className="compare-metric-card">
              <div className="metric-label">Scenarios Tested</div>
              <div className="metric-value" style={{ fontSize: "24px" }}>
                {auditB.audit.selected_scenarios.length}
              </div>
              <div className="muted" style={{ marginTop: 4 }}>
                {auditB.audit.selected_scenarios.map(titleize).join(", ")}
              </div>
            </div>

            <div className="compare-metric-card">
              <div className="metric-label">Personas Tested</div>
              <div className="metric-value" style={{ fontSize: "24px" }}>
                {auditB.audit.selected_personas.length}
              </div>
              <div className="muted" style={{ marginTop: 4 }}>
                {auditB.audit.selected_personas.map(titleize).join(", ")}
              </div>
            </div>

            <div className="action-row" style={{ marginTop: 16 }}>
              <Link className="btn btn-secondary" to={`/audits/${auditB.audit.id}/report`}>
                View Report
              </Link>
              <Link className="btn btn-secondary" to={`/audits/${auditB.audit.id}/run`}>
                View Run Log
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Scenario Comparison */}
      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Scenario Breakdown</h2>
            <p className="section-subtitle">
              Finding counts per scenario for each audit.
            </p>
          </div>
        </div>

        <div className="scenario-compare-grid">
          {allScenarios.map((scenario) => {
            const countA = findingsByScenarioA[scenario] || 0;
            const countB = findingsByScenarioB[scenario] || 0;
            const delta = countB - countA;

            return (
              <div key={scenario} className="scenario-compare-card">
                <h4 className="scenario-compare-title">{titleize(scenario)}</h4>
                <div className="scenario-compare-counts">
                  <div className="scenario-count">
                    <span className="scenario-count-label">Audit A</span>
                    <span className="scenario-count-value">{countA}</span>
                  </div>
                  <div className="scenario-count">
                    <span className="scenario-count-label">Audit B</span>
                    <span className="scenario-count-value">{countB}</span>
                  </div>
                </div>
                {delta !== 0 && (
                  <div
                    className="scenario-delta"
                    style={{
                      color: delta > 0 ? "var(--critical)" : "var(--accent)",
                    }}
                  >
                    {delta > 0 ? "+" : ""}
                    {delta} {Math.abs(delta) === 1 ? "finding" : "findings"}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Key Differences Summary */}
      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Key Differences</h2>
            <p className="section-subtitle">
              Summary of the most significant changes between the two audits.
            </p>
          </div>
        </div>

        <div className="grid-3">
          <div className="summary-card">
            <div className="metric-label">Trust Score Change</div>
            <div
              className="metric-value"
              style={{
                color: getScoreDeltaColor(scoreDelta),
              }}
            >
              {scoreDelta > 0 ? "+" : ""}
              {scoreDelta} points
            </div>
            <div className="muted">
              {scoreDelta > 10
                ? "Significant improvement"
                : scoreDelta < -10
                  ? "Significant decline"
                  : "Relatively stable"}
            </div>
          </div>

          <div className="summary-card">
            <div className="metric-label">Finding Count Change</div>
            <div
              className="metric-value"
              style={{
                color: findingsDelta > 0 ? "var(--critical)" : findingsDelta < 0 ? "var(--accent)" : "var(--medium)",
              }}
            >
              {findingsDelta > 0 ? "+" : ""}
              {findingsDelta} {Math.abs(findingsDelta) === 1 ? "finding" : "findings"}
            </div>
            <div className="muted">
              {findingsDelta > 0
                ? "More issues detected"
                : findingsDelta < 0
                  ? "Fewer issues detected"
                  : "Same number of findings"}
            </div>
          </div>

          <div className="summary-card">
            <div className="metric-label">Risk Level Comparison</div>
            <div className="metric-value" style={{ fontSize: "20px" }}>
              <span className={`severity-pill ${getSeverityClass(auditA.audit.risk_level)}`}>
                {auditA.audit.risk_level ?? "unknown"}
              </span>
              <span style={{ margin: "0 8px" }}>→</span>
              <span className={`severity-pill ${getSeverityClass(auditB.audit.risk_level)}`}>
                {auditB.audit.risk_level ?? "unknown"}
              </span>
            </div>
            <div className="muted">
              {auditA.audit.risk_level === auditB.audit.risk_level
                ? "Risk level unchanged"
                : "Risk level changed"}
            </div>
          </div>
        </div>
      </section>

      {/* Audit Details */}
      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Audit Details</h2>
          </div>
        </div>

        <div className="grid-2">
          <div className="summary-card">
            <div className="metric-label">Target URL</div>
            <div className="metric-value" style={{ fontSize: "18px", wordBreak: "break-all" }}>
              {auditA.audit.target_url}
            </div>
            <div className="muted" style={{ marginTop: 8 }}>
              Both audits target the same URL
            </div>
          </div>

          <div className="summary-card">
            <div className="metric-label">Audit Mode</div>
            <div className="metric-value" style={{ fontSize: "18px" }}>
              {auditA.audit.mode} / {auditB.audit.mode}
            </div>
            <div className="muted" style={{ marginTop: 8 }}>
              Evidence origin: {auditA.audit.metrics.evidence_origin_label}
            </div>
          </div>
        </div>
      </section>
    </Layout>
  );
}
