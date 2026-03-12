import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { Layout } from "../components/Layout";
import { useReadiness } from "../hooks/useReadiness";
import { titleize } from "../lib/format";

const scenarioOptions = [
  {
    value: "cookie_consent",
    description: "Inspect how consent banners steer acceptance, hide refusal, or pre-select tracking.",
  },
  {
    value: "checkout_flow",
    description: "Track hidden fees, upsells, urgency messaging, and bundled extras during purchase.",
  },
  {
    value: "cancellation_flow",
    description: "Measure cancellation friction, retention pressure, and confirmshaming on exit.",
  },
] as const;

const personaOptions = [
  {
    value: "privacy_sensitive",
    description: "Simulates a user looking for privacy-preserving choices and low-tracking defaults.",
  },
  {
    value: "cost_sensitive",
    description: "Focuses on transparent pricing, fee changes, and discount-linked persuasion.",
  },
  {
    value: "exit_intent",
    description: "Tests how flows react when the user appears ready to leave or decline.",
  },
] as const;

export function SubmitPage() {
  const navigate = useNavigate();
  const { data: readiness, loading: readinessLoading } = useReadiness();
  const [targetUrl, setTargetUrl] = useState("https://www.example.com");
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>([
    "cookie_consent",
    "checkout_flow",
    "cancellation_flow",
  ]);
  const [selectedPersonas, setSelectedPersonas] = useState<string[]>([
    "privacy_sensitive",
    "cost_sensitive",
    "exit_intent",
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const readinessSignals = useMemo(() => {
    if (!readiness) {
      return ["loading environment"];
    }

    return [
      `${readiness.browser_provider.replace("Provider", "")} browser`,
      `${readiness.classifier_provider.replace("Provider", "")} reasoning`,
      readiness.nova_ready ? "Nova ready" : "Mock AI active",
    ];
  }, [readiness]);

  const toggleSelection = (current: string[], value: string) =>
    current.includes(value) ? current.filter((item) => item !== value) : [...current, value];

  const startAudit = async () => {
    if (!selectedScenarios.length || !selectedPersonas.length) {
      setError("Select at least one scenario and one persona.");
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      const audit = await api.createAudit({
        target_url: targetUrl,
        scenarios: selectedScenarios,
        personas: selectedPersonas,
      });
      navigate(`/audits/${audit.id}/run`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start audit");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout mode={readiness?.effective_mode ?? "loading"} signals={readinessSignals}>
      <section className="hero-panel">
        <div>
          <div className="brand-kicker">Agentic trust audit for live websites</div>
          <h1>Evidence-backed UX trust reports built for Amazon Nova.</h1>
          <p className="hero-copy">
            EthicalSiteInspector simulates live journeys, captures screenshots and DOM evidence, compares outcomes across
            personas, and produces a decision-ready trust-risk report with remediation guidance.
          </p>
          <div className="hero-pills">
            <span className="signal-pill">UI Automation</span>
            <span className="signal-pill">Agentic AI</span>
            <span className="signal-pill">HTML report export</span>
          </div>
          <div className="action-row" style={{ marginTop: 24 }}>
            {readiness?.seeded_demo_audit_id ? (
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => navigate(`/audits/${readiness.seeded_demo_audit_id}/report`)}
              >
                Open seeded demo report
              </button>
            ) : null}
          </div>
        </div>
        <div className="hero-score">
          <div className="hero-score-label">Runtime posture</div>
          <div className="hero-score-value">{readinessLoading ? "..." : readiness?.effective_mode ?? "mock"}</div>
          <div className="hero-score-subtitle">
            {readiness?.nova_ready
              ? "Amazon Nova classification is ready for live reasoning."
              : "Mock classification is active until Nova credentials are added."}
          </div>
        </div>
      </section>

      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Launch an audit</h2>
            <p className="section-subtitle">
              Configure the target URL, choose the journeys to inspect, and decide which personas the trust audit should compare.
            </p>
          </div>
        </div>

        <div className="form-grid">
          <div className="field">
            <label htmlFor="target-url">Target URL</label>
            <input
              id="target-url"
              className="text-input"
              type="url"
              value={targetUrl}
              onChange={(event) => setTargetUrl(event.target.value)}
              placeholder="https://www.example.com"
            />
          </div>

          <div className="field">
            <label>Audit scenarios</label>
            <div className="choice-grid">
              {scenarioOptions.map((option) => {
                const selected = selectedScenarios.includes(option.value);
                return (
                  <label className={`choice-card ${selected ? "selected" : ""}`} key={option.value}>
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => setSelectedScenarios((current) => toggleSelection(current, option.value))}
                    />
                    <span className="choice-card-title">{titleize(option.value)}</span>
                    <span className="choice-card-copy">{option.description}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="field">
            <label>Personas</label>
            <div className="choice-grid">
              {personaOptions.map((option) => {
                const selected = selectedPersonas.includes(option.value);
                return (
                  <label className={`choice-card ${selected ? "selected" : ""}`} key={option.value}>
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => setSelectedPersonas((current) => toggleSelection(current, option.value))}
                    />
                    <span className="choice-card-title">{titleize(option.value)}</span>
                    <span className="choice-card-copy">{option.description}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {error ? <div className="empty-state">{error}</div> : null}

          <div className="action-row">
            <button className="btn btn-primary" type="button" disabled={submitting} onClick={startAudit}>
              {submitting ? "Starting audit..." : "Start trust audit"}
            </button>
            <span className="muted">
              Default behavior stays fully runnable without credentials. Add Nova and browser env vars later to upgrade to hybrid or live mode.
            </span>
          </div>
        </div>
      </section>
    </Layout>
  );
}
