import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { ModeBadge } from "./ModeBadge";

describe("ModeBadge", () => {
  it('renders mode text with "mode" suffix', () => {
    render(<ModeBadge mode="mock" />);
    expect(screen.getByText("mock mode")).toBeInTheDocument();
  });

  it("has the correct CSS class", () => {
    const { container } = render(<ModeBadge mode="live" />);
    const badge = container.querySelector(".mode-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("live mode");
  });
});
