import { Link } from "react-router-dom";

import type { ReactNode } from "react";

import { ModeBadge } from "./ModeBadge";

interface LayoutProps {
  mode?: string;
  children: ReactNode;
  signals?: string[];
}

export function Layout({ mode, children, signals = [] }: LayoutProps) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-kicker">Amazon Nova Hackathon Build</span>
          <span className="brand-title">EthicalSiteInspector</span>
        </Link>
        <div className="mode-row">
          {mode ? <ModeBadge mode={mode} /> : null}
          {signals.map((signal) => (
            <span className="signal-pill" key={signal}>
              {signal}
            </span>
          ))}
        </div>
      </header>
      {children}
    </div>
  );
}
