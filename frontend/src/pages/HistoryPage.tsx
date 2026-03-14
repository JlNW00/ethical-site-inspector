import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import type { Audit, AuditStatus, Benchmark, BenchmarkStatus } from "../api/types";
import { Layout } from "../components/Layout";
import { relativeTime, titleize } from "../lib/format";

// HistoryItemType is defined below using type inference

interface HistoryItemAudit {
  type: "audit";
  data: Audit;
}

interface HistoryItemBenchmark {
  type: "benchmark";
  data: Benchmark;
}

type HistoryItem = HistoryItemAudit | HistoryItemBenchmark;

function getStatusBadgeClass(status: AuditStatus | BenchmarkStatus): string {
  switch (status) {
    case "completed":
      return "status-badge status-completed";
    case "failed":
      return "status-badge status-failed";
    case "running":
      return "status-badge status-running";
    case "queued":
      return "status-badge status-queued";
    default:
      return "status-badge";
  }
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

export function HistoryPage() {
  const navigate = useNavigate();
  const [audits, setAudits] = useState<Audit[]>([]);
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | AuditStatus>("all");
  const [urlSearch, setUrlSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [rerunningId, setRerunningId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [auditsData, benchmarksData] = await Promise.all([
          api.getAudits(),
          api.getBenchmarks(),
        ]);
        if (!cancelled) {
          setAudits(auditsData);
          setBenchmarks(benchmarksData);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load history");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  // Combine audits and benchmarks into a single history list
  const historyItems = useMemo<HistoryItem[]>(() => {
    const auditItems: HistoryItem[] = audits.map((a) => ({ type: "audit", data: a }));
    const benchmarkItems: HistoryItem[] = benchmarks.map((b) => ({ type: "benchmark", data: b }));
    // Sort by created_at desc (newest first)
    return [...auditItems, ...benchmarkItems].sort((a, b) => {
      const aDate = new Date(a.data.created_at).getTime();
      const bDate = new Date(b.data.created_at).getTime();
      return bDate - aDate;
    });
  }, [audits, benchmarks]);

  // Filter history items by status and URL search
  const filteredItems = useMemo(() => {
    return historyItems.filter((item) => {
      const matchesStatus = statusFilter === "all" || item.data.status === statusFilter;
      if (item.type === "audit") {
        const matchesUrl = urlSearch === "" || item.data.target_url.toLowerCase().includes(urlSearch.toLowerCase());
        return matchesStatus && matchesUrl;
      } else {
        // For benchmarks, search in URLs array
        const matchesUrl = urlSearch === "" || item.data.urls.some((u) => u.toLowerCase().includes(urlSearch.toLowerCase()));
        return matchesStatus && matchesUrl;
      }
    });
  }, [historyItems, statusFilter, urlSearch]);

  // Get only audit IDs for compare selection (benchmarks excluded)
  const selectedAuditIds = useMemo(() => {
    return Array.from(selectedIds).filter((id) => {
      // Only include if it's an audit (not a benchmark)
      return audits.some((a) => a.id === id);
    });
  }, [selectedIds, audits]);

  const toggleSelection = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleRerun = async (audit: Audit) => {
    setRerunningId(audit.id);
    try {
      const newAudit = await api.createAudit({
        target_url: audit.target_url,
        scenarios: audit.selected_scenarios,
        personas: audit.selected_personas,
      });
      navigate(`/audits/${newAudit.id}/run`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rerun audit");
    } finally {
      setRerunningId(null);
    }
  };

  const handleCompare = () => {
    if (selectedIds.size !== 2) return;
    const [a, b] = Array.from(selectedIds);
    navigate(`/compare?a=${a}&b=${b}`);
  };

  const handleAuditRowClick = (auditId: string) => {
    navigate(`/audits/${auditId}/report`);
  };

  const handleBenchmarkRowClick = (benchmarkId: string) => {
    navigate(`/benchmarks/${benchmarkId}`);
  };

  const filterTabs: { label: string; value: "all" | AuditStatus }[] = [
    { label: "All", value: "all" },
    { label: "Completed", value: "completed" },
    { label: "Failed", value: "failed" },
    { label: "Running", value: "running" },
    { label: "Queued", value: "queued" },
  ];

  const compareEnabled = selectedAuditIds.length === 2;

  // Get the most recent activity timestamp from all items
  const latestActivity = useMemo(() => {
    if (historyItems.length === 0) return null;
    return historyItems[0].data;
  }, [historyItems]);

  return (
    <Layout mode="live" signals={["audit history"]}>
      <section className="hero-panel">
        <div>
          <div className="brand-kicker">Audit History</div>
          <h1>View and manage past audits</h1>
          <p className="hero-copy">
            Browse previous audits and benchmarks, filter by status, search by URL, rerun previous configurations, or compare results
            side-by-side.
          </p>
          <div className="hero-pills">
            <span className="signal-pill">{audits.length} audits</span>
            <span className="signal-pill">{benchmarks.length} benchmarks</span>
            <span className="signal-pill">{filteredItems.length} shown</span>
          </div>
        </div>
        <div className="hero-score">
          <div className="hero-score-label">Latest Activity</div>
          <div className="hero-score-value" style={{ fontSize: "48px" }}>
            {latestActivity ? formatTimestamp(latestActivity.updated_at).split(",")[0] : "--"}
          </div>
          <div className="hero-score-subtitle">
            {latestActivity ? `Last updated ${relativeTime(latestActivity.updated_at ?? "")}` : "No activity recorded yet"}
          </div>
        </div>
      </section>

      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Filter & Search</h2>
            <p className="section-subtitle">Refine the audit list by status or target URL.</p>
          </div>
          <div className="action-row">
            <button
              className="btn btn-secondary"
              onClick={handleCompare}
              disabled={!compareEnabled}
              title={compareEnabled ? "Compare selected audits" : "Select exactly 2 audits to compare (benchmarks excluded)"}
            >
              Compare ({selectedAuditIds.length}/2)
            </button>
          </div>
        </div>

        <div className="filter-bar">
          <div className="filter-tabs" role="tablist">
            {filterTabs.map((tab) => (
              <button
                key={tab.value}
                role="tab"
                aria-selected={statusFilter === tab.value}
                className={`filter-tab ${statusFilter === tab.value ? "active" : ""}`}
                onClick={() => setStatusFilter(tab.value)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="search-field">
            <input
              type="text"
              className="text-input search-input"
              placeholder="Search by URL..."
              value={urlSearch}
              onChange={(e) => setUrlSearch(e.target.value)}
            />
          </div>
        </div>
      </section>

      {error ? (
        <section className="content-panel">
          <div className="empty-state">Error: {error}</div>
        </section>
      ) : null}

      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">Audit History</h2>
            <p className="section-subtitle">
              Click any audit row to view its full report. Use checkboxes to select audits for comparison.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">Loading history...</div>
        ) : filteredItems.length === 0 ? (
          <div className="empty-state">
            {audits.length === 0 && benchmarks.length === 0
              ? "No audits or benchmarks found. Start by creating a new audit from the home page."
              : "No items match the current filters."}
          </div>
        ) : (
          <div className="audit-list">
            {filteredItems.map((item) => {
              if (item.type === "audit") {
                const audit = item.data;
                return (
                  <article key={audit.id} data-testid="audit-row" className="audit-card">
                    <div className="audit-card-row">
                      <div className="audit-select">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(audit.id)}
                          onChange={() => toggleSelection(audit.id)}
                          onClick={(e) => e.stopPropagation()}
                          aria-label={`Select audit ${audit.id}`}
                        />
                      </div>
                      <div
                        className="audit-main"
                        onClick={() => handleAuditRowClick(audit.id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            handleAuditRowClick(audit.id);
                          }
                        }}
                      >
                        <div className="audit-header">
                          <span className={getStatusBadgeClass(audit.status)}>{audit.status}</span>
                          <span className="audit-url" title={audit.target_url}>
                            {audit.target_url}
                          </span>
                          <span className="audit-mode">{audit.mode}</span>
                        </div>
                        <div className="audit-details">
                          <div className="audit-metric">
                            <span className="metric-label">Trust Score</span>
                            <span className="metric-value" style={{ fontSize: "24px" }}>
                              {audit.trust_score ?? "--"}
                            </span>
                          </div>
                          <div className="audit-metric">
                            <span className="metric-label">Scenarios</span>
                            <span className="metric-value" style={{ fontSize: "24px" }}>
                              {audit.selected_scenarios.length}
                            </span>
                            <span className="muted">{audit.selected_scenarios.map(titleize).join(", ")}</span>
                          </div>
                          <div className="audit-metric">
                            <span className="metric-label">Personas</span>
                            <span className="metric-value" style={{ fontSize: "24px" }}>
                              {audit.selected_personas.length}
                            </span>
                            <span className="muted">{audit.selected_personas.map(titleize).join(", ")}</span>
                          </div>
                          <div className="audit-metric">
                            <span className="metric-label">Created</span>
                            <span className="muted">{formatTimestamp(audit.created_at)}</span>
                          </div>
                        </div>
                      </div>
                      <div className="audit-actions">
                        <button
                          className="btn btn-secondary"
                          onClick={(e) => {
                            e.stopPropagation();
                            void handleRerun(audit);
                          }}
                          disabled={rerunningId === audit.id}
                          aria-label={`Rerun audit for ${audit.target_url}`}
                        >
                          {rerunningId === audit.id ? "Rerunning..." : "Rerun"}
                        </button>
                      </div>
                    </div>
                  </article>
                );
              } else {
                const benchmark = item.data;
                return (
                  <article key={benchmark.id} data-testid="benchmark-row" className="audit-card benchmark-card">
                    <div className="audit-card-row">
                      <div className="audit-select">
                        <input
                          type="checkbox"
                          disabled
                          checked={false}
                          title="Benchmarks cannot be compared"
                          aria-label={`Benchmark ${benchmark.id} (not selectable for compare)`}
                        />
                      </div>
                      <div
                        className="audit-main"
                        onClick={() => handleBenchmarkRowClick(benchmark.id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            handleBenchmarkRowClick(benchmark.id);
                          }
                        }}
                      >
                        <div className="audit-header">
                          <span className={getStatusBadgeClass(benchmark.status)}>{benchmark.status}</span>
                          <span className="audit-url">Benchmark: {benchmark.urls.length} URLs</span>
                          <span className="audit-mode benchmark-badge">Benchmark</span>
                        </div>
                        <div className="audit-details">
                          <div className="audit-metric">
                            <span className="metric-label">URLs</span>
                            <span className="metric-value" style={{ fontSize: "24px" }}>
                              {benchmark.urls.length}
                            </span>
                            <span className="muted">{benchmark.urls.slice(0, 3).join(", ")}
                              {benchmark.urls.length > 3 ? ` +${benchmark.urls.length - 3} more` : ""}
                            </span>
                          </div>
                          <div className="audit-metric">
                            <span className="metric-label">Completed Audits</span>
                            <span className="metric-value" style={{ fontSize: "24px" }}>
                              {benchmark.audit_ids.filter((id) => {
                                const audit = audits.find((a) => a.id === id);
                                return audit?.status === "completed";
                              }).length} / {benchmark.audit_ids.length}
                            </span>
                          </div>
                          <div className="audit-metric">
                            <span className="metric-label">Trust Scores</span>
                            <span className="metric-value" style={{ fontSize: "24px" }}>
                              {benchmark.trust_scores ? Object.keys(benchmark.trust_scores).length : 0}
                            </span>
                            <span className="muted">URLs scored</span>
                          </div>
                          <div className="audit-metric">
                            <span className="metric-label">Created</span>
                            <span className="muted">{formatTimestamp(benchmark.created_at)}</span>
                          </div>
                        </div>
                      </div>
                      <div className="audit-actions">
                        <span className="benchmark-hint muted">Compare not available</span>
                      </div>
                    </div>
                  </article>
                );
              }
            })}
          </div>
        )}
      </section>
    </Layout>
  );
}
