import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { Audit, Benchmark, Finding } from "../api/types";
import { Layout } from "../components/Layout";
import { ProgressMeter } from "../components/ProgressMeter";
import { titleize } from "../lib/format";

interface AuditWithFindings {
  audit: Audit;
  findings: Finding[];
}

interface ProgressInfo {
  progress: number;
  status: string;
}

export function BenchmarkPage() {
  const { benchmarkId } = useParams<{ benchmarkId: string }>();
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [audits, setAudits] = useState<Record<string, AuditWithFindings>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch per-URL progress for running benchmarks
  const [progressInfo, setProgressInfo] = useState<Record<string, ProgressInfo>>({});

  useEffect(() => {
    if (!benchmarkId) {
      setError("No benchmark ID provided");
      setLoading(false);
      return;
    }

    let cancelled = false;
    let timer: number | undefined;

    const fetchBenchmark = async () => {
      try {
        const data = await api.getBenchmark(benchmarkId);
        if (!cancelled) {
          setBenchmark(data);
          setError(null);

          // If benchmark is running, fetch per-audit progress
          if (data.status === "running") {
            const progressPromises = data.audit_ids.map(async (auditId) => {
              try {
                const audit = await api.getAudit(auditId);
                const events = audit.events || [];
                const progress = events.length > 0
                  ? Math.max(...events.map((e) => e.progress))
                  : 0;
                return { auditId, progress, status: audit.status };
              } catch {
                return { auditId, progress: 0, status: "unknown" };
              }
            });

            const progressResults = await Promise.all(progressPromises);
            const progressMap: Record<string, ProgressInfo> = {};
            progressResults.forEach(({ auditId, progress, status }) => {
              progressMap[auditId] = { progress, status };
            });
            setProgressInfo(progressMap);
          }

          // If benchmark is completed, fetch full audit details
          if (data.status === "completed" && Object.keys(audits).length === 0) {
            const auditPromises = data.audit_ids.map(async (auditId, index) => {
              try {
                const audit = await api.getAudit(auditId);
                const findingsRes = await api.getFindings(auditId);
                return {
                  auditId,
                  url: data.urls[index],
                  data: { audit, findings: findingsRes.findings },
                };
              } catch {
                return null;
              }
            });

            const results = await Promise.all(auditPromises);
            const auditsMap: Record<string, AuditWithFindings> = {};
            results.forEach((result) => {
              if (result) {
                auditsMap[result.url] = result.data;
              }
            });
            setAudits(auditsMap);
          }

          // Continue polling if still running or queued
          if (data.status === "running" || data.status === "queued") {
            timer = window.setTimeout(fetchBenchmark, 1500);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load benchmark");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void fetchBenchmark();

    return () => {
      cancelled = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [benchmarkId]);

  // Calculate aggregate progress
  const aggregateProgress = useMemo(() => {
    const progresses = Object.values(progressInfo);
    if (progresses.length === 0) return 0;
    const total = progresses.reduce((sum, p) => sum + p.progress, 0);
    return Math.round(total / progresses.length);
  }, [progressInfo]);

  // Sort URLs by trust score (highest first) for completed benchmarks
  const sortedUrls = useMemo(() => {
    if (!benchmark || !benchmark.trust_scores) return [];

    return benchmark.urls
      .map((url, index) => ({
        url,
        auditId: benchmark.audit_ids[index],
        score: benchmark.trust_scores?.[url] ?? null,
      }))
      .sort((a, b) => {
        // Handle null scores (failed audits) - put them at the end
        if (a.score === null && b.score === null) return 0;
        if (a.score === null) return 1;
        if (b.score === null) return -1;
        return b.score - a.score;
      });
  }, [benchmark]);

  // Calculate delta between best and worst scores
  const scoreDelta = useMemo(() => {
    if (!benchmark || !benchmark.trust_scores) return 0;
    const scores = Object.values(benchmark.trust_scores).filter((s): s is number => s !== null);
    if (scores.length < 2) return 0;
    return Math.max(...scores) - Math.min(...scores);
  }, [benchmark]);



  // Get all unique scenarios across audits
  const allScenarios = useMemo(() => {
    const scenarios = new Set<string>();
    Object.values(audits).forEach((auditData) => {
      if (auditData?.audit?.selected_scenarios) {
        auditData.audit.selected_scenarios.forEach((s) => scenarios.add(s));
      }
    });
    return Array.from(scenarios);
  }, [audits]);

  // Calculate scenario finding counts per URL
  const scenarioGridData = useMemo(() => {
    const grid: Record<string, Record<string, number>> = {};

    allScenarios.forEach((scenario) => {
      grid[scenario] = {};
      sortedUrls.forEach(({ url }) => {
        const auditData = audits[url];
        if (auditData) {
          const breakdown = auditData.audit.metrics?.scenario_breakdown?.find(
            (b) => b.scenario === scenario
          );
          grid[scenario][url] = breakdown?.finding_count ?? 0;
        } else {
          grid[scenario][url] = 0;
        }
      });
    });

    return grid;
  }, [allScenarios, sortedUrls, audits]);

  // Calculate summary stats
  const summaryStats = useMemo(() => {
    if (!benchmark || sortedUrls.length === 0) return null;

    const highest = sortedUrls[0];
    const lowest = sortedUrls[sortedUrls.length - 1];

    // Collect all pattern families from findings
    const patternCounts: Record<string, number> = {};
    Object.values(audits).forEach((auditData) => {
      if (auditData?.findings) {
        auditData.findings.forEach((f) => {
          if (f?.pattern_family) {
            patternCounts[f.pattern_family] = (patternCounts[f.pattern_family] || 0) + 1;
          }
        });
      }
    });

    const topPatterns = Object.entries(patternCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([pattern]) => pattern);

    // Determine overall risk word based on average trust score
    const avgScore = sortedUrls.reduce((sum, u) => sum + (u.score || 0), 0) / sortedUrls.length;
    let riskWord = "low";
    if (avgScore < 30) riskWord = "critical";
    else if (avgScore < 50) riskWord = "high";
    else if (avgScore < 70) riskWord = "moderate";

    return { highest, lowest, topPatterns, riskWord, avgScore };
  }, [benchmark, sortedUrls, audits]);

  if (loading) {
    return (
      <Layout mode="mock">
        <section className="content-panel">
          <div className="loading-state">Loading benchmark...</div>
        </section>
      </Layout>
    );
  }

  if (error || !benchmark) {
    return (
      <Layout mode="mock">
        <section className="content-panel">
          <div className="empty-state">{error || "Benchmark not found"}</div>
          <Link className="btn btn-secondary" to="/history">
            Back to History
          </Link>
        </section>
      </Layout>
    );
  }

  const isRunning = benchmark.status === "running" || benchmark.status === "queued";
  const isCompleted = benchmark.status === "completed";

  return (
    <Layout mode="mock">
      <section className="hero-panel">
        <div>
          <div className="brand-kicker">Benchmark Results</div>
          <h1>Comparing {benchmark.urls.length} URLs</h1>
          <div className="hero-pills">
            <span className={`signal-pill status-${benchmark.status}`}>{benchmark.status}</span>
          </div>
        </div>
        {isRunning && (
          <div className="hero-score">
            <div className="hero-score-label">Aggregate Progress</div>
            <div className="hero-score-value">{aggregateProgress}%</div>
            <div className="hero-score-subtitle">
              Polling for updates every 1.5 seconds
            </div>
            <div style={{ marginTop: 18 }}>
              <ProgressMeter value={aggregateProgress} />
            </div>
          </div>
        )}
      </section>

      {/* Progress Section - shown while running */}
      {isRunning && (
        <section className="content-panel" data-testid="progress-section">
          <div className="section-header">
            <div>
              <h2 className="section-title">Per-URL Progress</h2>
              <p className="section-subtitle">
                Live progress for each URL being audited.
              </p>
            </div>
          </div>
          <div className="benchmark-progress-list">
            {benchmark.urls.map((url, index) => {
              const auditId = benchmark.audit_ids[index];
              const progress = progressInfo[auditId]?.progress ?? 0;
              return (
                <div key={url} className="benchmark-progress-item">
                  <div className="benchmark-progress-header">
                    <span className="benchmark-progress-url">{url}</span>
                    <span className="benchmark-progress-percent">{progress}%</span>
                  </div>
                  <ProgressMeter value={progress} />
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Comparison View - shown when completed */}
      {isCompleted && (
        <>
          <section className="content-panel" data-testid="comparison-section">
            <div className="section-header">
              <div>
                <h2 className="section-title">Trust Score Comparison</h2>
                <p className="section-subtitle">
                  URLs ranked by trust score, highest first. Delta shows the spread between best and worst.
                </p>
              </div>
              {scoreDelta > 0 && (
                <div className="delta-badge" data-testid="delta-badge">
                  <span className="delta-value" data-testid="delta-value">{scoreDelta}</span>
                  <span className="delta-label">point spread</span>
                </div>
              )}
            </div>

            <div className="trust-score-cards">
              {sortedUrls.map(({ url, auditId, score }) => {
                const auditData = audits[url]?.audit;
                const isFailed = score === null && auditData?.status === "failed";

                return (
                  <div key={url} className={`trust-score-card ${isFailed ? "failed" : ""}`}>
                    <div className="trust-score-header">
                      <span className="trust-score-url" title={url}>
                        {url.replace(/^https?:\/\//, "")}
                      </span>
                      {isFailed && <span className="error-badge">Error</span>}
                    </div>
                    <div className="trust-score-body">
                      {isFailed ? (
                        <div className="trust-score-na">N/A</div>
                      ) : (
                        <>
                          <div className="trust-score-value">{score}%</div>
                          <ProgressMeter value={score || 0} />
                        </>
                      )}
                    </div>
                    <div className="trust-score-footer">
                      <Link
                        className="btn btn-secondary btn-sm"
                        to={`/audits/${auditId}/report?benchmark=${benchmark.id}`}
                      >
                        View Report
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Scenario Breakdown Grid */}
          <section className="content-panel" data-testid="scenario-section">
            <div className="section-header">
              <div>
                <h2 className="section-title">Scenario Breakdown</h2>
                <p className="section-subtitle">
                  Finding counts per scenario across all URLs. Rows are scenarios, columns are URLs.
                </p>
              </div>
            </div>

            <div className="scenario-grid" data-testid="scenario-grid">
              <div className="scenario-grid-header">
                <div className="scenario-grid-cell scenario-label">Scenario</div>
                {sortedUrls.map(({ url }) => (
                  <div key={url} className="scenario-grid-cell url-label" title={url}>
                    {url.replace(/^https?:\/\//, "").slice(0, 20)}
                    {url.length > 20 ? "..." : ""}
                  </div>
                ))}
              </div>
              {allScenarios.map((scenario) => (
                <div key={scenario} className="scenario-grid-row">
                  <div className="scenario-grid-cell scenario-name">
                    {titleize(scenario)}
                  </div>
                  {sortedUrls.map(({ url }) => (
                    <div key={url} className="scenario-grid-cell finding-count">
                      {scenarioGridData[scenario]?.[url] ?? 0}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </section>

          {/* Unified Summary */}
          {summaryStats && (
            <section className="content-panel" data-testid="summary-section">
              <div className="section-header">
                <div>
                  <h2 className="section-title">Unified Summary</h2>
                  <p className="section-subtitle">
                    Key insights across all audited URLs.
                  </p>
                </div>
              </div>

              <div className="summary-grid">
                <div className="summary-card">
                  <div className="summary-card-label">Highest Scoring</div>
                  <div className="summary-card-value">
                    {summaryStats.highest.url.replace(/^https?:\/\//, "")}
                  </div>
                  <div className="summary-card-sub">
                    {summaryStats.highest.score}% trust score
                  </div>
                </div>

                <div className="summary-card">
                  <div className="summary-card-label">Lowest Scoring</div>
                  <div className="summary-card-value">
                    {summaryStats.lowest.url.replace(/^https?:\/\//, "")}
                  </div>
                  <div className="summary-card-sub">
                    {summaryStats.lowest.score !== null
                      ? `${summaryStats.lowest.score}% trust score`
                      : "Audit failed"}
                  </div>
                </div>

                <div className="summary-card">
                  <div className="summary-card-label">Common Patterns</div>
                  <div className="summary-card-patterns">
                    {summaryStats.topPatterns.length > 0 ? (
                      summaryStats.topPatterns.map((p) => (
                        <span key={p} className="pattern-badge">
                          {titleize(p)}
                        </span>
                      ))
                    ) : (
                      <span className="muted">No patterns detected</span>
                    )}
                  </div>
                </div>

                <div className="summary-card">
                  <div className="summary-card-label">Overall Risk</div>
                  <div className={`summary-card-risk risk-${summaryStats.riskWord}`}>
                    {titleize(summaryStats.riskWord)}
                  </div>
                  <div className="summary-card-sub">
                    Average trust score: {Math.round(summaryStats.avgScore)}%
                  </div>
                </div>
              </div>
            </section>
          )}
        </>
      )}

      {/* Failed State */}
      {benchmark.status === "failed" && (
        <section className="content-panel">
          <div className="error-state">
            <div className="error-state-icon">❌</div>
            <h3 className="error-state-title">Benchmark Failed</h3>
            <p className="error-state-message">
              The benchmark encountered an error and could not complete successfully.
            </p>
          </div>
        </section>
      )}

      {/* Action Row */}
      <div className="action-row" style={{ marginTop: 22 }}>
        <Link className="btn btn-secondary" to="/history">
          Back to History
        </Link>
      </div>
    </Layout>
  );
}
