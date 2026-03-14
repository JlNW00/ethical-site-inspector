import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { Layout } from "../components/Layout";
import { useReadiness } from "../hooks/useReadiness";
import { titleize } from "../lib/format";

// Scenario options with correct backend values
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
    value: "subscription_cancellation",
    description: "Measure cancellation friction, retention pressure, and confirmshaming on exit.",
  },
  {
    value: "account_deletion",
    description: "Detect obstruction and friction when attempting to delete an account.",
  },
  {
    value: "newsletter_signup",
    description: "Check for pre-checked boxes, confusing opt-in language, and dark enrollment patterns.",
  },
  {
    value: "pricing_comparison",
    description: "Compare prices across personas to detect bait-and-switch or discriminatory pricing.",
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

const MAX_BENCHMARK_URLS = 5;
const MIN_BENCHMARK_URLS = 2;

// URL validation regex
const URL_REGEX = /^https?:\/\/.+/;

function isValidUrl(url: string): boolean {
  if (!url.trim()) return false;
  return URL_REGEX.test(url.trim());
}

export function SubmitPage() {
  const navigate = useNavigate();
  const { data: readiness, loading: readinessLoading } = useReadiness();
  const [targetUrl, setTargetUrl] = useState("https://www.example.com");
  const [benchmarkMode, setBenchmarkMode] = useState(false);
  const [benchmarkUrls, setBenchmarkUrls] = useState<string[]>(["", ""]);
  const [urlErrors, setUrlErrors] = useState<(string | null)[]>([]);
  const [duplicateError, setDuplicateError] = useState<string | null>(null);
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>([
    "cookie_consent",
    "checkout_flow",
    "subscription_cancellation",
    "account_deletion",
    "newsletter_signup",
    "pricing_comparison",
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

  const validateUrls = (): boolean => {
    const errors = benchmarkUrls.map((url) => {
      if (!url.trim()) return "URL is required";
      if (!isValidUrl(url)) return "Invalid URL format (must start with http:// or https://)";
      return null;
    });
    setUrlErrors(errors);

    // Check for duplicates
    const nonEmptyUrls = benchmarkUrls.filter((u) => u.trim());
    const uniqueUrls = new Set(nonEmptyUrls);
    if (uniqueUrls.size !== nonEmptyUrls.length) {
      setDuplicateError("Duplicate URLs detected. Each URL must be unique.");
      return false;
    }
    setDuplicateError(null);

    // Check minimum URLs
    const validUrls = benchmarkUrls.filter((url) => url.trim() && isValidUrl(url));
    if (validUrls.length < MIN_BENCHMARK_URLS) {
      setError(`At least ${MIN_BENCHMARK_URLS} valid URLs are required for benchmark mode.`);
      return false;
    }

    return errors.every((e) => e === null);
  };

  const addUrl = () => {
    if (benchmarkUrls.length < MAX_BENCHMARK_URLS) {
      setBenchmarkUrls([...benchmarkUrls, ""]);
      setUrlErrors([...urlErrors, null]);
    }
  };

  const removeUrl = (index: number) => {
    if (benchmarkUrls.length > MIN_BENCHMARK_URLS) {
      const newUrls = benchmarkUrls.filter((_, i) => i !== index);
      const newErrors = urlErrors.filter((_, i) => i !== index);
      setBenchmarkUrls(newUrls);
      setUrlErrors(newErrors);
    }
  };

  const updateUrl = (index: number, value: string) => {
    const newUrls = [...benchmarkUrls];
    newUrls[index] = value;
    setBenchmarkUrls(newUrls);

    // Clear error for this field if it becomes valid
    if (isValidUrl(value)) {
      const newErrors = [...urlErrors];
      newErrors[index] = null;
      setUrlErrors(newErrors);
    }

    // Clear duplicate error when user edits
    setDuplicateError(null);
  };

  const toggleBenchmarkMode = () => {
    const newMode = !benchmarkMode;
    setBenchmarkMode(newMode);
    setError(null);
    setDuplicateError(null);
    setUrlErrors([]);

    if (newMode) {
      // Switching to benchmark mode: initialize with current URL + empty slot
      setBenchmarkUrls([targetUrl, ""]);
    } else {
      // Switching to single mode: preserve first URL
      setTargetUrl(benchmarkUrls[0] || "https://www.example.com");
    }
  };

  const startAudit = async () => {
    if (!selectedScenarios.length || !selectedPersonas.length) {
      setError("Select at least one scenario and one persona.");
      return;
    }

    if (benchmarkMode) {
      if (!validateUrls()) {
        return;
      }
      const validUrls = benchmarkUrls.filter((url) => url.trim() && isValidUrl(url));
      if (validUrls.length < MIN_BENCHMARK_URLS) {
        setError(`At least ${MIN_BENCHMARK_URLS} valid URLs are required for benchmark mode.`);
        return;
      }
    }

    setError(null);
    setSubmitting(true);
    try {
      if (benchmarkMode) {
        const validUrls = benchmarkUrls.filter((url) => url.trim() && isValidUrl(url));
        const benchmark = await api.createBenchmark({
          urls: validUrls,
          selected_scenarios: selectedScenarios,
          selected_personas: selectedPersonas,
        });
        navigate(`/benchmarks/${benchmark.id}`);
      } else {
        const audit = await api.createAudit({
          target_url: targetUrl,
          scenarios: selectedScenarios,
          personas: selectedPersonas,
        });
        navigate(`/audits/${audit.id}/run`);
      }
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
            EthicalSiteInspector simulates live journeys, captures screenshots and DOM evidence, compares outcomes
            across personas, and produces a decision-ready trust-risk report with remediation guidance.
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
          <div className="hero-score-value">{readinessLoading ? "..." : (readiness?.effective_mode ?? "mock")}</div>
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
              Configure the target URL, choose the journeys to inspect, and decide which personas the trust audit should
              compare.
            </p>
          </div>
        </div>

        <div className="form-grid">
          <div className="field">
            <div className="benchmark-toggle-row">
              <label className="benchmark-toggle-label">
                <input
                  type="checkbox"
                  checked={benchmarkMode}
                  onChange={toggleBenchmarkMode}
                  className="benchmark-toggle-input"
                  data-testid="benchmark-mode-toggle"
                />
                <span className="benchmark-toggle-text">Benchmark Mode</span>
              </label>
              <span className="benchmark-toggle-hint">
                Compare {MIN_BENCHMARK_URLS}-{MAX_BENCHMARK_URLS} URLs against the same scenarios and personas
              </span>
            </div>
          </div>

          {benchmarkMode ? (
            <div className="field">
              <label>
                Target URLs ({benchmarkUrls.length}/{MAX_BENCHMARK_URLS})
              </label>
              <div className="benchmark-urls-container">
                {benchmarkUrls.map((url, index) => (
                  <div key={index} className="benchmark-url-row">
                    <input
                      className={`text-input benchmark-url-input ${urlErrors[index] ? "input-error" : ""}`}
                      type="url"
                      value={url}
                      onChange={(event) => updateUrl(index, event.target.value)}
                      placeholder={`https://www.example${index + 1}.com`}
                      data-testid={`benchmark-url-input-${index}`}
                    />
                    {benchmarkUrls.length > MIN_BENCHMARK_URLS && (
                      <button
                        type="button"
                        className="btn btn-icon btn-remove-url"
                        onClick={() => removeUrl(index)}
                        aria-label={`Remove URL ${index + 1}`}
                        data-testid={`remove-url-${index}`}
                      >
                        ✕
                      </button>
                    )}
                    {urlErrors[index] && (
                      <span className="url-field-error" data-testid={`url-error-${index}`}>
                        {urlErrors[index]}
                      </span>
                    )}
                  </div>
                ))}
                {duplicateError && (
                  <div className="url-duplicate-error" data-testid="duplicate-error">
                    {duplicateError}
                  </div>
                )}
                <button
                  type="button"
                  className="btn btn-secondary btn-add-url"
                  onClick={addUrl}
                  disabled={benchmarkUrls.length >= MAX_BENCHMARK_URLS}
                  data-testid="add-url-button"
                >
                  + Add URL
                </button>
                {benchmarkUrls.length >= MAX_BENCHMARK_URLS && (
                  <span className="max-urls-hint">Maximum {MAX_BENCHMARK_URLS} URLs allowed</span>
                )}
              </div>
            </div>
          ) : (
            <div className="field">
              <label htmlFor="target-url">Target URL</label>
              <input
                id="target-url"
                className="text-input"
                type="url"
                value={targetUrl}
                onChange={(event) => setTargetUrl(event.target.value)}
                placeholder="https://www.example.com"
                data-testid="target-url-input"
              />
            </div>
          )}

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
            <button
              className="btn btn-primary"
              type="button"
              disabled={submitting}
              onClick={startAudit}
              data-testid="start-audit-button"
            >
              {submitting ? "Starting..." : benchmarkMode ? "Start benchmark" : "Start trust audit"}
            </button>
            <span className="muted">
              Default behavior stays fully runnable without credentials. Add Nova and browser env vars later to upgrade
              to hybrid or live mode.
            </span>
          </div>
        </div>
      </section>
    </Layout>
  );
}
