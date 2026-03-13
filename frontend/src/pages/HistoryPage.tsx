import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import type { Audit, AuditStatus } from "../api/types";
import { Layout } from "../components/Layout";
import { relativeTime, titleize } from "../lib/format";

type FilterStatus = "all" | AuditStatus;

function getStatusBadgeClass(status: AuditStatus): string {
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<FilterStatus>("all");
  const [urlSearch, setUrlSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [rerunningId, setRerunningId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await api.getAudits();
        if (!cancelled) {
          setAudits(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load audits");
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

  const filteredAudits = useMemo(() => {
    return audits.filter((audit) => {
      const matchesStatus = statusFilter === "all" || audit.status === statusFilter;
      const matchesUrl =
        urlSearch === "" ||
        audit.target_url.toLowerCase().includes(urlSearch.toLowerCase());
      return matchesStatus && matchesUrl;
    });
  }, [audits, statusFilter, urlSearch]);

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

  const handleRowClick = (auditId: string) => {
    navigate(`/audits/${auditId}/report`);
  };

  const filterTabs: { label: string; value: FilterStatus }[] = [
    { label: "All", value: "all" },
    { label: "Completed", value: "completed" },
    { label: "Failed", value: "failed" },
    { label: "Running", value: "running" },
    { label: "Queued", value: "queued" },
  ];

  const compareEnabled = selectedIds.size === 2;

  return (
    <Layout mode="live" signals={["audit history"]}>
      <section className="hero-panel">
        <div>
          <div className="brand-kicker">Audit History</div>
          <h1>View and manage past audits</h1>
          <p className="hero-copy">
            Browse previous audits, filter by status, search by URL, rerun previous
            configurations, or compare results side-by-side.
          </p>
          <div className="hero-pills">
            <span className="signal-pill">{audits.length} total audits</span>
            <span className="signal-pill">{filteredAudits.length} shown</span>
          </div>
        </div>
        <div className="hero-score">
          <div className="hero-score-label">Latest Activity</div>
          <div className="hero-score-value" style={{ fontSize: "48px" }}>
            {audits.length > 0 ? formatTimestamp(audits[0]?.updated_at).split(",")[0] : "--"}
          </div>
          <div className="hero-score-subtitle">
            {audits.length > 0
              ? `Last updated ${relativeTime(audits[0]?.updated_at ?? "")}`
              : "No audits recorded yet"}
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
              title={compareEnabled ? "Compare selected audits" : "Select exactly 2 audits to compare"}
            >
              Compare ({selectedIds.size}/2)
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
              Click any audit row to view its full report. Use checkboxes to select
              audits for comparison.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state">Loading audits...</div>
        ) : filteredAudits.length === 0 ? (
          <div className="empty-state">
            {audits.length === 0
              ? "No audits found. Start by creating a new audit from the home page."
              : "No audits match the current filters."}
          </div>
        ) : (
          <div className="audit-list">
            {filteredAudits.map((audit) => (
              <article
                key={audit.id}
                data-testid="audit-row"
                className="audit-card"
              >
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
                    onClick={() => handleRowClick(audit.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        handleRowClick(audit.id);
                      }
                    }}
                  >
                    <div className="audit-header">
                      <span className={getStatusBadgeClass(audit.status)}>
                        {audit.status}
                      </span>
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
                        <span className="muted">
                          {audit.selected_scenarios.map(titleize).join(", ")}
                        </span>
                      </div>
                      <div className="audit-metric">
                        <span className="metric-label">Personas</span>
                        <span className="metric-value" style={{ fontSize: "24px" }}>
                          {audit.selected_personas.length}
                        </span>
                        <span className="muted">
                          {audit.selected_personas.map(titleize).join(", ")}
                        </span>
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
            ))}
          </div>
        )}
      </section>
    </Layout>
  );
}
