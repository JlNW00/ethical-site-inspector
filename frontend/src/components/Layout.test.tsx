import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import { Layout } from "./Layout";

describe("Layout", () => {
  it("renders the brand title and navigation links", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Layout mode="live" signals={["test signal"]}>
          <div>Test Content</div>
        </Layout>
      </MemoryRouter>,
    );

    expect(screen.getByText("EthicalSiteInspector")).toBeInTheDocument();
    expect(screen.getByText("Amazon Nova Hackathon Build")).toBeInTheDocument();
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("History")).toBeInTheDocument();
    expect(screen.getByText("Test Content")).toBeInTheDocument();
  });

  it("marks Home link as active when on home page", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Layout mode="live">
          <div>Content</div>
        </Layout>
      </MemoryRouter>,
    );

    const homeLink = screen.getByText("Home");
    expect(homeLink).toHaveClass("active");
  });

  it("marks History link as active when on history page", () => {
    render(
      <MemoryRouter initialEntries={["/history"]}>
        <Layout mode="live">
          <div>Content</div>
        </Layout>
      </MemoryRouter>,
    );

    const historyLink = screen.getByText("History");
    expect(historyLink).toHaveClass("active");
  });

  it("renders breadcrumbs when provided", () => {
    render(
      <MemoryRouter initialEntries={["/audits/123/report"]}>
        <Layout
          mode="live"
          breadcrumbs={[
            { label: "History", path: "/history" },
            { label: "Report", path: "/audits/123/report", isActive: true },
          ]}
        >
          <div>Report Content</div>
        </Layout>
      </MemoryRouter>,
    );

    // Use getAllByText since "History" appears in both nav and breadcrumbs
    const historyElements = screen.getAllByText("History");
    expect(historyElements.length).toBeGreaterThanOrEqual(1);
    // "Report" should be unique in breadcrumbs
    expect(screen.getByText("Report")).toBeInTheDocument();
  });

  it("renders back link when provided", () => {
    render(
      <MemoryRouter initialEntries={["/audits/123/report"]}>
        <Layout mode="live" backLink={{ to: "/history", label: "Back to History" }}>
          <div>Content</div>
        </Layout>
      </MemoryRouter>,
    );

    const backLink = screen.getByText("Back to History");
    expect(backLink).toBeInTheDocument();
  });

  it("renders mode badge and signals", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Layout mode="live" signals={["running", "test scenario"]}>
          <div>Content</div>
        </Layout>
      </MemoryRouter>,
    );

    expect(screen.getByText(/live.*mode/i)).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
    expect(screen.getByText("test scenario")).toBeInTheDocument();
  });

  it("home link navigates to home page", () => {
    render(
      <MemoryRouter initialEntries={["/history"]}>
        <Routes>
          <Route path="/" element={<div>Home Page</div>} />
          <Route
            path="/history"
            element={
              <Layout mode="live">
                <div>History Page</div>
              </Layout>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    const homeLink = screen.getByText("Home");
    expect(homeLink).toHaveAttribute("href", "/");
  });

  it("history link navigates to history page", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Layout mode="live">
          <div>Content</div>
        </Layout>
      </MemoryRouter>,
    );

    const historyLink = screen.getByText("History");
    expect(historyLink).toHaveAttribute("href", "/history");
  });
});

describe("Navigation flow", () => {
  it("has working navigation from home to history", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Layout mode="live">
          <div>Content</div>
        </Layout>
      </MemoryRouter>,
    );

    const historyLink = screen.getByText("History");
    expect(historyLink).toBeInTheDocument();
    expect(historyLink.tagName.toLowerCase()).toBe("a");
  });

  it("has working navigation from history to home", () => {
    render(
      <MemoryRouter initialEntries={["/history"]}>
        <Layout mode="live">
          <div>Content</div>
        </Layout>
      </MemoryRouter>,
    );

    const homeLink = screen.getByText("Home");
    expect(homeLink).toBeInTheDocument();
    expect(homeLink.tagName.toLowerCase()).toBe("a");
  });
});
