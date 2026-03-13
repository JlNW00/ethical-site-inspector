import type { Finding } from "../api/types";
import { titleize } from "../lib/format";

interface FindingCardProps {
  finding: Finding;
}

function trimText(value: string, limit = 80) {
  return value.length <= limit ? value : `${value.slice(0, limit - 1).trimEnd()}…`;
}

function extractQuoted(value: string) {
  const parts = value.split('"');
  return parts.length >= 3 ? parts[1] : value;
}

function prettyAction(action: string) {
  const clean = action.replace(/\s+/g, " ").trim();
  const quoted = extractQuoted(clean);
  if (clean.startsWith('Selected offer "') && quoted) {
    if (!/\d/.test(quoted) && quoted.split(" ").length <= 4) {
      return `Selected destination ${quoted}`;
    }
    return `Selected offer ${trimText(quoted, 68)}`;
  }
  if (clean.startsWith('Opened hotel detail "') && quoted) {
    return `Opened hotel ${trimText(quoted, 68)}`;
  }
  if (clean.startsWith('Interacted with checkout control "') && quoted) {
    return quoted;
  }
  return trimText(clean, 80);
}

function prettyPath(actions: string[]) {
  return actions.slice(0, 4).map(prettyAction).join(" -> ");
}

function observedEvidenceLabel(finding: Finding, hasPath: boolean) {
  if (hasPath) {
    return "Observed evidence";
  }
  if (finding.evidence_payload.matched_prices?.length) {
    return "Observed pricing";
  }
  if (finding.evidence_payload.matched_buttons?.length) {
    return "Observed controls";
  }
  return "Observed evidence";
}

function displayEvidenceExcerpt(finding: Finding, observedPath: string) {
  if (!observedPath) {
    return finding.evidence_excerpt;
  }
  if (finding.evidence_excerpt.includes("Friction signals:")) {
    const [, suffix] = finding.evidence_excerpt.split("Friction signals:");
    return `${observedPath}. Friction signals:${suffix}`;
  }
  if (finding.evidence_excerpt.includes("scenario interactions were captured")) {
    return observedPath;
  }
  return finding.evidence_excerpt;
}

export function FindingCard({ finding }: FindingCardProps) {
  const screenshots = finding.evidence_payload.screenshot_urls ?? [];
  const matchedButtons = finding.evidence_payload.matched_buttons ?? [];
  const matchedPrices = finding.evidence_payload.matched_prices ?? [];
  const supportingEvidence = finding.evidence_payload.supporting_evidence ?? [];
  const sourceLabel = finding.evidence_payload.source_label ?? "Evidence";
  const interactedControls = (finding.evidence_payload as { interacted_controls?: string[] }).interacted_controls ?? [];
  const observedPath = prettyPath(interactedControls);
  const evidenceLabel = observedEvidenceLabel(finding, Boolean(observedPath));
  const displayExcerpt = displayEvidenceExcerpt(finding, observedPath);

  return (
    <article className="finding-card">
      <div className="action-row">
        <span className={`severity-pill severity-${finding.severity}`}>{finding.severity}</span>
        <span className="signal-pill">{titleize(finding.pattern_family)}</span>
        <span className="signal-pill">{Math.round(finding.confidence * 100)}% confidence</span>
        <span className="signal-pill">{sourceLabel}</span>
      </div>
      <h3 className="finding-title">{finding.title}</h3>
      <p className="muted">
        {titleize(finding.scenario)} | {titleize(finding.persona)}
      </p>
      {finding.evidence_payload.page_title || finding.evidence_payload.page_url ? (
        <p className="muted">
          {finding.evidence_payload.page_title ?? finding.evidence_payload.site_host}
          {finding.evidence_payload.page_url ? ` | ${finding.evidence_payload.page_url}` : ""}
        </p>
      ) : null}
      <p>{finding.explanation}</p>
      {observedPath ? (
        <p>
          <strong>Observed path:</strong> {observedPath}
        </p>
      ) : null}
      <p>
        <strong>{evidenceLabel}:</strong> {displayExcerpt}
      </p>
      <p>
        <strong>Why it matters:</strong> {finding.rule_reason}
      </p>
      <p>
        <strong>Remediation:</strong> {finding.remediation}
      </p>
      {matchedButtons.length || matchedPrices.length || supportingEvidence.length ? (
        <div className="muted">
          {matchedButtons.length ? (
            <p>
              <strong>Observed controls:</strong> {matchedButtons.join(", ")}
            </p>
          ) : null}
          {matchedPrices.length ? (
            <p>
              <strong>Observed prices:</strong>{" "}
              {matchedPrices
                .map((price) => `${price.raw ?? `$${price.value.toFixed(2)}`} in ${price.label}`)
                .join(" | ")}
            </p>
          ) : null}
          {supportingEvidence.length ? (
            <p>
              <strong>Supporting evidence:</strong> {supportingEvidence.slice(0, 3).join(" | ")}
            </p>
          ) : null}
        </div>
      ) : null}
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
