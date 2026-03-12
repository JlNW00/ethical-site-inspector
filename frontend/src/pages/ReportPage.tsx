import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { Audit, Finding } from "../api/types";
import { FindingCard } from "../components/FindingCard";
import { Layout } from "../components/Layout";
import { ProgressMeter } from "../components/ProgressMeter";
import { titleize } from "../lib/format";

export function ReportPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [audit, setAudit] = useState<Audit | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auditId) {
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const [nextAudit, findingsResponse] = await Promise.all([api.getAudit(auditId), api.getFindings(auditId)]);
        if (!cancelled) {
          setAudit(nextAudit);
          setFindings(findingsResponse.findings);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load report");
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

  const trustProgress = audit?.trust_score ?? 0;

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
          <h1>{audit?.target_url ?? "Loading report..."}</h1>
          <p className="hero-copy">
            A decision-ready trust report combining rule-based detections, persona deltas, captured evidence, and remediation guidance.
          </p>
          <div className="hero-pills">
            {(audit?.selected_personas ?? []).map((persona) => (
              <span className="signal-pill" key={persona}>
                {titleize(persona)}
              </span>
            ))}
          </div>
          <div className="action-row" style={{ marginTop: 24 }}>
            {auditId ? (
              <a className="btn btn-primary" href={api.getReportUrl(auditId)} target="_blank" rel="noreferrer">
                Open HTML report
              </a>
            ) : null}
            {auditId ? (
              <Link className="btn btn-secondary" to={`/audits/${auditId}/run`}>
                Back to run log
              </Link>
            ) : null}
          </div>
        </div>
        <div className="hero-score">
          <div className="hero-score-label">Trust score</div>
          <div className="hero-score-value">{audit?.trust_score ?? "--"}</div>
          <div className="hero-score-subtitle">{audit?.summary ?? "Report summary is loading."}</div>
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
            <div className="muted">Evidence-backed trust and compliance concerns</div>
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
        </div>
      </section>

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
