import { Link, useLocation } from "react-router-dom";

import type { ReactNode } from "react";

import { ModeBadge } from "./ModeBadge";

interface Breadcrumb {
  label: string;
  path: string;
  isActive?: boolean;
}

interface LayoutProps {
  mode?: string;
  children: ReactNode;
  signals?: string[];
  breadcrumbs?: Breadcrumb[];
  backLink?: {
    to: string;
    label: string;
  };
}

export function Layout({ mode, children, signals = [], breadcrumbs, backLink }: LayoutProps) {
  const location = useLocation();
  const currentPath = location.pathname;

  // Determine active nav link based on current path
  const isActive = (path: string) => {
    if (path === "/") {
      return currentPath === "/";
    }
    return currentPath.startsWith(path);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-kicker">Amazon Nova Hackathon Build</span>
          <span className="brand-title">EthicalSiteInspector</span>
        </Link>
        <nav className="nav-links">
          <Link to="/" className={`nav-link ${isActive("/") && currentPath === "/" ? "active" : ""}`}>
            Home
          </Link>
          <Link to="/history" className={`nav-link ${isActive("/history") ? "active" : ""}`}>
            History
          </Link>
        </nav>
        <div className="mode-row">
          {mode ? <ModeBadge mode={mode} /> : null}
          {signals.map((signal) => (
            <span className="signal-pill" key={signal}>
              {signal}
            </span>
          ))}
        </div>
      </header>

      {/* Breadcrumbs */}
      {(breadcrumbs || backLink) && (
        <nav className="breadcrumbs-nav" aria-label="Breadcrumb">
          {backLink && (
            <Link to={backLink.to} className="breadcrumb-back-link">
              <span className="breadcrumb-back-icon">←</span>
              {backLink.label}
            </Link>
          )}
          {breadcrumbs && (
            <ol className="breadcrumbs-list">
              <li className="breadcrumb-item">
                <Link to="/" className="breadcrumb-link">Home</Link>
              </li>
              {breadcrumbs.map((crumb, index) => (
                <li key={crumb.path} className="breadcrumb-item">
                  <span className="breadcrumb-separator">/</span>
                  {crumb.isActive || index === breadcrumbs.length - 1 ? (
                    <span className="breadcrumb-current" aria-current="page">
                      {crumb.label}
                    </span>
                  ) : (
                    <Link to={crumb.path} className="breadcrumb-link">
                      {crumb.label}
                    </Link>
                  )}
                </li>
              ))}
            </ol>
          )}
        </nav>
      )}

      <main className="page-content">{children}</main>
    </div>
  );
}
