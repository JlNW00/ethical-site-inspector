import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { Audit } from "../api/types";
import { Layout } from "../components/Layout";
import { ProgressMeter } from "../components/ProgressMeter";
import { relativeTime, titleize } from "../lib/format";

export function RunPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [audit, setAudit] = useState<Audit | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auditId) {
      return;
    }

    let cancelled = false;
    let timer: number | undefined;

    const load = async () => {
      try {
        const nextAudit = await api.getAudit(auditId);
        if (cancelled) {
          return;
        }
        setAudit(nextAudit);
        setError(null);
        if (nextAudit.status !== "completed" && nextAudit.status !== "failed") {
          timer = window.setTimeout(load, 1500);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load audit");
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [auditId]);

  const events = audit?.events ?? [];
  const progress = useMemo(() => {
    if (!events.length) {
      return 0;
    }
    return Math.max(...events.map((event) => event.progress));
  }, [events]);
  const latestEvent = events[events.length - 1];
  const evidence = events
    .map((event) => ({
      url: typeof event.details.image_url === "string" ? event.details.image_url : null,
      caption:
        typeof event.details.scenario === "string" && typeof event.details.persona === "string"
          ? `${titleize(event.details.scenario)} | ${titleize(event.details.persona)}`
          : event.message,
    }))
    .filter((item): item is { url: string; caption: string } => Boolean(item.url));

  return (
    <Layout
      mode={audit?.mode ?? "loading"}
      signals={[
        audit ? `${audit.status} status` : "loading audit",
        latestEvent?.phase ? `${latestEvent.phase} phase` : "queue phase",
      ]}
    >
      <section className="hero-panel">
        <div>
          <div className="brand-kicker">Audit run console</div>
          <h1>{audit ? audit.target_url : "Preparing audit run..."}</h1>
          <p className="hero-copy">
            Live progress across scenarios, persona variants, and evidence capture. Judges should be able to see the agentic run behavior directly.
          </p>
          <div className="hero-pills">
            {(audit?.selected_scenarios ?? []).map((scenario) => (
              <span className="signal-pill" key={scenario}>
                {titleize(scenario)}
              </span>
            ))}
          </div>
        </div>
        <div className="hero-score">
          <div className="hero-score-label">Progress</div>
          <div className="hero-score-value">{progress}%</div>
          <div className="hero-score-subtitle">
            {latestEvent?.message ?? "Audit queued. Waiting for the first browser pass."}
          </div>
          <div style={{ marginTop: 18 }}>
            <ProgressMeter value={progress} />
          </div>
        </div>
      </section>

      {error ? (
        <section className="content-panel">
          <div className="error-state">
            <div className="error-state-icon">⚠️</div>
            <h3 className="error-state-title">Error Loading Audit</h3>
            <p className="error-state-message">{error}</p>
            <div className="action-row" style={{ marginTop: 16 }}>
              <Link className="btn btn-secondary" to="/history">
                Back to History
              </Link>
              <button
                className="btn btn-primary"
                type="button"
                onClick={() => window.location.reload()}
              >
                Retry
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {audit?.status === "failed" ? (
        <section className="content-panel">
          <div className="error-state">
            <div className="error-state-icon">❌</div>
            <h3 className="error-state-title">Audit Failed</h3>
            <p className="error-state-message">
              The audit encountered an error and could not complete successfully.
            </p>
            {audit.summary && (
              <p className="error-state-details">Details: {audit.summary}</p>
            )}
            <div className="action-row" style={{ marginTop: 16 }}>
              <Link className="btn btn-secondary" to="/history">
                Back to History
              </Link>
              <Link
                className="btn btn-primary"
                to={`/audits/${audit.id}/report`}
              >
                View Error Report
              </Link>
            </div>
          </div>
        </section>
      ) : null}

      {!error && audit?.status !== "failed" && (
        <section className="content-panel">
          <div className="section-header">
            <div>
              <h2 className="section-title">Run state</h2>
              <p className="section-subtitle">
                Current mode, scenario coverage, and evidence throughput for the active audit.
              </p>
            </div>
            {audit?.status === "completed" ? (
              <Link className="btn btn-primary" to={`/audits/${audit.id}/report`}>
                Open report
              </Link>
            ) : null}
          </div>
          <div className="grid-3">
            <div className="metric-card">
              <div className="metric-label">Current focus</div>
              <div className="metric-value">
                {latestEvent?.details.scenario && typeof latestEvent.details.scenario === "string"
                  ? titleize(latestEvent.details.scenario)
                  : "Queueing"}
              </div>
              <div className="muted">
                {latestEvent?.details.persona && typeof latestEvent.details.persona === "string"
                  ? titleize(latestEvent.details.persona)
                  : "Waiting for persona branch"}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Evidence captured</div>
              <div className="metric-value">{evidence.length}</div>
              <div className="muted">Screenshots surfaced through the activity feed</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Final trust score</div>
              <div className="metric-value">{audit?.trust_score ?? "--"}</div>
              <div className="muted">{audit?.status === "completed" ? `${audit.risk_level} risk` : "Calculated after classification"}</div>
            </div>
          </div>
        </section>
      )}

      {!error && audit?.status !== "failed" && (
        <div className="grid-2" style={{ marginTop: 22 }}>
          <section className="content-panel">
            <div className="section-header">
              <div>
                <h2 className="section-title">Activity timeline</h2>
                <p className="section-subtitle">A granular event feed showing progress, captured artifacts, and reasoning milestones.</p>
              </div>
            </div>
            <div className="timeline">
              {events.length ? (
                [...events].reverse().map((event) => (
                  <div className="timeline-item" key={event.id}>
                    <div className="timeline-phase">{event.phase}</div>
                    <div>
                      <div className="timeline-message">{event.message}</div>
                      <div className="timeline-details">
                        {relativeTime(event.created_at)}
                        {typeof event.details.scenario === "string" ? ` | ${titleize(event.details.scenario)}` : ""}
                        {typeof event.details.persona === "string" ? ` | ${titleize(event.details.persona)}` : ""}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-state">Waiting for the first timeline event.</div>
              )}
            </div>
          </section>

          <section className="content-panel">
            <div className="section-header">
              <div>
                <h2 className="section-title">Evidence previews</h2>
                <p className="section-subtitle">Captured screenshots flow in here while the audit runs.</p>
              </div>
            </div>
            {evidence.length ? (
              <div className="evidence-grid">
                {evidence.slice(0, 6).map((item, index) => (
                  <article className="evidence-card" key={`${item.url}-${index}`}>
                    <img className="evidence-thumb" src={item.url} alt={item.caption} />
                    <div style={{ marginTop: 12, fontWeight: 600 }}>{item.caption}</div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state">Evidence will appear once a scenario run completes its first capture step.</div>
            )}
          </section>
        </div>
      )}
    </Layout>
  );
}
