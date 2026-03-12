import type { Finding } from "../api/types";
import { titleize } from "../lib/format";

interface FindingCardProps {
  finding: Finding;
}

export function FindingCard({ finding }: FindingCardProps) {
  const screenshots = finding.evidence_payload.screenshot_urls ?? [];

  return (
    <article className="finding-card">
      <div className="action-row">
        <span className={`severity-pill severity-${finding.severity}`}>{finding.severity}</span>
        <span className="signal-pill">{titleize(finding.pattern_family)}</span>
        <span className="signal-pill">{Math.round(finding.confidence * 100)}% confidence</span>
      </div>
      <h3 className="finding-title">{finding.title}</h3>
      <p className="muted">
        {titleize(finding.scenario)} | {titleize(finding.persona)}
      </p>
      <p>{finding.explanation}</p>
      <p>
        <strong>Evidence:</strong> {finding.evidence_excerpt}
      </p>
      <p>
        <strong>Why it matters:</strong> {finding.rule_reason}
      </p>
      <p>
        <strong>Remediation:</strong> {finding.remediation}
      </p>
      {screenshots.length > 0 ? (
        <div className="evidence-grid" style={{ marginTop: 16 }}>
          {screenshots.slice(0, 3).map((url) => (
            <img className="evidence-thumb" key={url} src={url} alt={finding.title} />
          ))}
        </div>
      ) : null}
    </article>
  );
}
