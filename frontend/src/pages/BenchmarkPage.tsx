import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { Benchmark } from "../api/types";
import { Layout } from "../components/Layout";

export function BenchmarkPage() {
  const { benchmarkId } = useParams<{ benchmarkId: string }>();
  const navigate = useNavigate();
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!benchmarkId) {
      setError("No benchmark ID provided");
      setLoading(false);
      return;
    }

    let cancelled = false;

    const fetchBenchmark = async () => {
      try {
        const data = await api.getBenchmark(benchmarkId);
        if (!cancelled) {
          setBenchmark(data);
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

    fetchBenchmark();

    return () => {
      cancelled = true;
    };
  }, [benchmarkId]);

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
          <button className="btn btn-secondary" onClick={() => navigate("/history")}>
            Back to History
          </button>
        </section>
      </Layout>
    );
  }

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
      </section>

      <section className="content-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">URLs under comparison</h2>
            <p className="section-subtitle">
              Each URL is audited with the same scenarios and personas for fair comparison.
            </p>
          </div>
        </div>

        <div className="benchmark-urls-list">
          {benchmark.urls.map((url, index) => (
            <div key={index} className="benchmark-url-card">
              <div className="url-index">{index + 1}</div>
              <div className="url-info">
                <span className="url-text">{url}</span>
                {benchmark.audit_ids[index] && (
                  <span className="audit-status">
                    Audit ID: {benchmark.audit_ids[index]}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="action-row">
          <button className="btn btn-secondary" onClick={() => navigate("/history")}>
            Back to History
          </button>
        </div>
      </section>
    </Layout>
  );
}
