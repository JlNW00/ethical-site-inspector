import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";

import { ProgressMeter } from "./ProgressMeter";

describe("ProgressMeter", () => {
  it("renders with correct width style for a given value", () => {
    const { container } = render(<ProgressMeter value={45} />);
    const bar = container.querySelector(".meter-bar") as HTMLElement;
    expect(bar).toBeInTheDocument();
    expect(bar.style.width).toBe("45%");
  });

  it("clamps value at 0 when given a negative number", () => {
    const { container } = render(<ProgressMeter value={-10} />);
    const bar = container.querySelector(".meter-bar") as HTMLElement;
    expect(bar.style.width).toBe("0%");
  });

  it("clamps value at 100 when given a number above 100", () => {
    const { container } = render(<ProgressMeter value={150} />);
    const bar = container.querySelector(".meter-bar") as HTMLElement;
    expect(bar.style.width).toBe("100%");
  });

  it("has an accessible label", () => {
    const { container } = render(<ProgressMeter value={50} />);
    const track = container.querySelector('[aria-label="Audit progress"]');
    expect(track).toBeInTheDocument();
  });
});
