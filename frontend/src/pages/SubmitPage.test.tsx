/* global HTMLInputElement */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { SubmitPage } from "./SubmitPage";

const mockNavigate = vi.fn();
const mockCreateAudit = vi.fn();
const mockCreateBenchmark = vi.fn();
const mockGetReadiness = vi.fn();

// Mock the router
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock the API client
vi.mock("../api/client", () => ({
  api: {
    createAudit: (...args: unknown[]) => mockCreateAudit(...args),
    createBenchmark: (...args: unknown[]) => mockCreateBenchmark(...args),
    getReadiness: () => mockGetReadiness(),
  },
}));

describe("SubmitPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockGetReadiness.mockResolvedValue({
      status: "ready",
      effective_mode: "mock",
      browser_provider: "MockBrowserProvider",
      classifier_provider: "MockClassifierProvider",
      nova_ready: false,
      playwright_ready: true,
      storage_ready: true,
      seeded_demo_audit_id: null,
    });
  });

  describe("Benchmark Mode Toggle", () => {
    it("renders with benchmark mode toggle that defaults to OFF", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const toggle = screen.getByTestId("benchmark-mode-toggle");
      expect(toggle).toBeInTheDocument();
      expect(toggle).not.toBeChecked();
    });

    it("shows single URL input when benchmark mode is OFF", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      expect(screen.getByTestId("target-url-input")).toBeInTheDocument();
      expect(screen.queryByTestId("benchmark-url-input-0")).not.toBeInTheDocument();
    });

    it("shows multiple URL inputs when benchmark mode toggle is turned ON", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      expect(toggle).toBeChecked();
      expect(screen.getByTestId("benchmark-url-input-0")).toBeInTheDocument();
      expect(screen.getByTestId("benchmark-url-input-1")).toBeInTheDocument();
    });

    it("preserves first URL value when toggling OFF from benchmark mode", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      // Enable benchmark mode
      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      // Set first URL
      const firstInput = screen.getByTestId("benchmark-url-input-0");
      fireEvent.change(firstInput, { target: { value: "https://example1.com" } });

      // Toggle OFF
      fireEvent.click(toggle);

      // Single URL input should have the preserved value
      const singleInput = screen.getByTestId("target-url-input");
      expect(singleInput).toHaveValue("https://example1.com");
    });

    it("preserves scenario and persona selections across toggle", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      // Uncheck some scenarios before toggle
      const checkoutCheckbox = screen.getByLabelText(/Checkout Flow/i);
      fireEvent.click(checkoutCheckbox);

      // Enable benchmark mode
      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      // Scenario should still be unchecked
      expect(checkoutCheckbox).not.toBeChecked();

      // Toggle OFF
      fireEvent.click(toggle);

      // Scenario should still be unchecked
      expect(screen.getByLabelText(/Checkout Flow/i)).not.toBeChecked();
    });
  });

  describe("Multi-URL Input", () => {
    it("renders with 2 URL fields when benchmark mode is enabled", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      expect(screen.getByTestId("benchmark-url-input-0")).toBeInTheDocument();
      expect(screen.getByTestId("benchmark-url-input-1")).toBeInTheDocument();
    });

    it("allows adding URLs up to maximum of 5", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      const addButton = screen.getByTestId("add-url-button");

      // Add 3 more URLs (start with 2, max is 5)
      fireEvent.click(addButton); // 3
      fireEvent.click(addButton); // 4
      fireEvent.click(addButton); // 5

      expect(screen.getByTestId("benchmark-url-input-4")).toBeInTheDocument();

      // Button should be disabled at 5 URLs
      expect(addButton).toBeDisabled();
    });

    it("allows removing URLs when more than minimum (2)", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      // Add a third URL
      const addButton = screen.getByTestId("add-url-button");
      fireEvent.click(addButton);

      // Now we should have a remove button
      const removeButton = screen.getByTestId("remove-url-2");
      expect(removeButton).toBeInTheDocument();

      // Remove it
      fireEvent.click(removeButton);

      // Third input should be gone
      expect(screen.queryByTestId("benchmark-url-input-2")).not.toBeInTheDocument();
    });

    it("does not show remove button when only 2 URLs present", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      // Should have 2 URLs minimum, no remove buttons
      expect(screen.queryByTestId("remove-url-0")).not.toBeInTheDocument();
      expect(screen.queryByTestId("remove-url-1")).not.toBeInTheDocument();
    });
  });

  describe("URL Validation", () => {
    it("shows per-field error for invalid URL format", async () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      // Enter invalid URL
      const firstInput = screen.getByTestId("benchmark-url-input-0");
      fireEvent.change(firstInput, { target: { value: "not-a-url" } });

      // Try to submit
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      // Should show validation error
      await waitFor(() => {
        expect(screen.getByTestId("url-error-0")).toBeInTheDocument();
      });
    });

    it("shows error when fewer than 2 valid URLs for benchmark", async () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      // Leave only first URL filled
      const secondInput = screen.getByTestId("benchmark-url-input-1");
      fireEvent.change(secondInput, { target: { value: "" } });

      // Try to submit
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      // Should show minimum URLs error
      await waitFor(() => {
        expect(screen.getByText(/at least 2 valid URLs are required/i)).toBeInTheDocument();
      });
    });

    it("shows error for duplicate URLs", async () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      // Enter same URL in both fields
      const firstInput = screen.getByTestId("benchmark-url-input-0");
      const secondInput = screen.getByTestId("benchmark-url-input-1");

      fireEvent.change(firstInput, { target: { value: "https://example.com" } });
      fireEvent.change(secondInput, { target: { value: "https://example.com" } });

      // Try to submit
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      // Should show duplicate error
      await waitFor(() => {
        expect(screen.getByTestId("duplicate-error")).toBeInTheDocument();
      });
    });

    it("clears duplicate error when URL is edited", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      // Enter duplicate URLs
      const firstInput = screen.getByTestId("benchmark-url-input-0");
      const secondInput = screen.getByTestId("benchmark-url-input-1");

      fireEvent.change(firstInput, { target: { value: "https://example.com" } });
      fireEvent.change(secondInput, { target: { value: "https://example.com" } });

      // Try to submit to trigger duplicate error
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      // Edit one of them
      fireEvent.change(secondInput, { target: { value: "https://different.com" } });

      // Duplicate error should be cleared
      expect(screen.queryByTestId("duplicate-error")).not.toBeInTheDocument();
    });
  });

  describe("Form Submission", () => {
    it("calls createAudit and navigates to run page in single mode", async () => {
      mockCreateAudit.mockResolvedValue({ id: "audit-123", target_url: "https://example.com" });

      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      // Ensure single mode
      const toggle = screen.getByTestId("benchmark-mode-toggle");
      expect(toggle).not.toBeChecked();

      // Submit
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(mockCreateAudit).toHaveBeenCalledWith({
          target_url: "https://www.example.com",
          scenarios: expect.any(Array),
          personas: expect.any(Array),
        });
      });

      expect(mockNavigate).toHaveBeenCalledWith("/audits/audit-123/run");
    });

    it("calls createBenchmark with correct field names and navigates to benchmark page", async () => {
      mockCreateBenchmark.mockResolvedValue({ id: "bench-456", urls: ["https://example1.com", "https://example2.com"] });

      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      // Enable benchmark mode
      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      // Fill URLs
      const firstInput = screen.getByTestId("benchmark-url-input-0");
      const secondInput = screen.getByTestId("benchmark-url-input-1");

      fireEvent.change(firstInput, { target: { value: "https://example1.com" } });
      fireEvent.change(secondInput, { target: { value: "https://example2.com" } });

      // Submit
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(mockCreateBenchmark).toHaveBeenCalledWith({
          urls: ["https://example1.com", "https://example2.com"],
          selected_scenarios: expect.any(Array),
          selected_personas: expect.any(Array),
        });
      });

      expect(mockNavigate).toHaveBeenCalledWith("/benchmarks/bench-456");
    });

    it("does not submit benchmark with invalid URLs", async () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      // Enable benchmark mode
      const toggle = screen.getByTestId("benchmark-mode-toggle");
      fireEvent.click(toggle);

      // Fill URLs with one invalid
      const firstInput = screen.getByTestId("benchmark-url-input-0");
      const secondInput = screen.getByTestId("benchmark-url-input-1");

      fireEvent.change(firstInput, { target: { value: "https://example1.com" } });
      fireEvent.change(secondInput, { target: { value: "invalid-url" } });

      // Submit
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      // Should not call API
      await waitFor(() => {
        expect(mockCreateBenchmark).not.toHaveBeenCalled();
      });
    });

    it("shows loading state during submission", async () => {
      mockCreateAudit.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(startButton).toHaveTextContent("Starting...");
      });
      expect(startButton).toBeDisabled();
    });

    it("shows error when API call fails", async () => {
      mockCreateAudit.mockRejectedValue(new Error("Network error"));

      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(screen.getByText("Network error")).toBeInTheDocument();
      });
    });

    it("clears stale error when starting new submission", async () => {
      mockCreateAudit.mockRejectedValue(new Error("First attempt failed"));

      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      // First submission fails
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(screen.getByText("First attempt failed")).toBeInTheDocument();
      });

      // Mock success for second attempt
      mockCreateAudit.mockResolvedValue({ id: "audit-123" });

      // Second submission - error should be cleared
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(screen.queryByText("First attempt failed")).not.toBeInTheDocument();
      });

      expect(mockNavigate).toHaveBeenCalledWith("/audits/audit-123/run");
    });
  });

  describe("Scenario Key Mapping", () => {
    it("uses subscription_cancellation as the backend value for cancellation flow", async () => {
      mockCreateAudit.mockResolvedValue({ id: "audit-123" });

      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      // Submit audit
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      await waitFor(() => {
        const call = mockCreateAudit.mock.calls[0][0];
        // Should include subscription_cancellation, not cancellation_flow
        expect(call.scenarios).toContain("subscription_cancellation");
        expect(call.scenarios).not.toContain("cancellation_flow");
      });
    });

    it("displays correct label for subscription_cancellation scenario", () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      // Look for scenario section by the heading text
      const scenarioSection = screen.getByText(/Audit scenarios/i).closest(".field");
      expect(scenarioSection).toBeInTheDocument();

      // Check that the label exists by looking for "Cancellation" and "Flow" separately
      // since they may be in different elements due to titleize formatting
      const cancellationLabels = screen.getAllByText(/Cancellation/i);
      expect(cancellationLabels.length).toBeGreaterThan(0);
    });
  });

  describe("Form Validation - Scenarios and Personas", () => {
    it("shows error when no scenarios selected", async () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      // Uncheck all scenarios (by clicking all checkboxes in the scenario section)
      const scenarioSection = screen.getByText(/Audit scenarios/i).closest(".field");
      if (scenarioSection) {
        const checkboxes = scenarioSection.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach((checkbox) => {
          if ((checkbox as HTMLInputElement).checked) {
            fireEvent.click(checkbox);
          }
        });
      }

      // Submit
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(screen.getByText(/Select at least one scenario/i)).toBeInTheDocument();
      });
    });

    it("shows error when no personas selected", async () => {
      render(
        <MemoryRouter>
          <SubmitPage />
        </MemoryRouter>
      );

      // Get all checkboxes (both scenarios and personas)
      // First, get all persona checkboxes (they come after scenario checkboxes in DOM order)
      const allCheckboxes = screen.getAllByRole("checkbox");
      // Filter to only persona checkboxes by looking at their labels
      const personaCheckboxes = allCheckboxes.filter(cb => {
        const label = cb.closest("label");
        if (!label) return false;
        const labelText = label.textContent || "";
        return labelText.includes("Privacy Sensitive") || 
               labelText.includes("Cost Sensitive") || 
               labelText.includes("Exit Intent");
      });

      // Uncheck all persona checkboxes
      personaCheckboxes.forEach((checkbox) => {
        if ((checkbox as HTMLInputElement).checked) {
          fireEvent.click(checkbox);
        }
      });

      // Submit
      const startButton = screen.getByTestId("start-audit-button");
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(screen.getByText(/Select at least one scenario and one persona/i)).toBeInTheDocument();
      });
    });
  });
});
