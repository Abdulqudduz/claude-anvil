import { describe, it, expect } from "vitest";
import { handleCoverSpecs } from "../tools/cover-specs.js";

describe("handleCoverSpecs", () => {
  it("returns specs for standard fiction paperback", () => {
    const result = handleCoverSpecs({
      page_count: 250,
      trim_size: "5.5x8.5",
      paper_type: "cream",
    });

    expect(result.spine_width_inches).toBeCloseTo(0.625, 2);
    expect(result.total_width_inches).toBeGreaterThan(11);
    expect(result.total_height_inches).toBeCloseTo(8.75, 2);
    expect(result.total_height_px).toBe(Math.round(8.75 * 300));
    expect(result.has_spine_text).toBe(true);
    expect(result.bleed_inches).toBe(0.125);
    expect(result.trim_width_inches).toBe(5.5);
    expect(result.page_range).toEqual({ min: 24, max: 776 });
  });

  it("returns no spine text for short books", () => {
    const result = handleCoverSpecs({ page_count: 60, trim_size: "5.5x8.5", paper_type: "white" });
    expect(result.has_spine_text).toBe(false);
  });

  it("uses defaults when optional fields omitted", () => {
    const result = handleCoverSpecs({ page_count: 200 });
    expect(result.total_height_inches).toBeCloseTo(8.75, 2);
  });

  it("rejects unknown trim sizes and paper types through the shared schema", () => {
    // @ts-expect-error deliberately invalid
    expect(() => handleCoverSpecs({ page_count: 200, trim_size: "A4" })).toThrow();
    // @ts-expect-error deliberately invalid
    expect(() => handleCoverSpecs({ page_count: 200, paper_type: "glossy" })).toThrow();
  });
});
