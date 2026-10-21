import { describe, it, expect } from "vitest";
import {
  calculateSpineWidth,
  calculateCoverDimensions,
  contrastRatio,
  ensureContrast,
  hexToRgb,
} from "../lib/cover-layout.js";
import {
  BLEED_INCHES,
  PAPER_TYPES,
  PRINT_DPI,
  TRIM_SIZE_KEYS,
  pageRange,
} from "../lib/kdp-specs.js";

describe("calculateSpineWidth", () => {
  it("calculates white paper spine width", () => {
    expect(calculateSpineWidth(300, "white")).toBeCloseTo(0.6756, 4);
  });

  it("calculates cream paper spine width", () => {
    expect(calculateSpineWidth(300, "cream")).toBeCloseTo(0.75, 4);
  });

  it("calculates minimum page count spine width", () => {
    expect(calculateSpineWidth(24, "white")).toBeCloseTo(0.054, 3);
  });

  // Rates from KDP's "Create a Paperback Cover" (G201953020) and the
  // groundwood beta help page.
  it("calculates groundwood paper spine width", () => {
    expect(calculateSpineWidth(300, "groundwood")).toBeCloseTo(0.705, 4);
  });

  it("calculates standard color paper spine width", () => {
    expect(calculateSpineWidth(300, "standard_color")).toBeCloseTo(0.6756, 4);
  });

  it("calculates premium color paper spine width", () => {
    expect(calculateSpineWidth(300, "premium_color")).toBeCloseTo(0.7041, 4);
  });

  it("exposes every paper type that has a spine rate, and no others", () => {
    expect([...PAPER_TYPES].sort()).toEqual(
      ["cream", "groundwood", "premium_color", "standard_color", "white"],
    );
  });
});

describe("calculateCoverDimensions", () => {
  it("calculates full wrap for 5.5x8.5 trim, 300 pages cream", () => {
    const dims = calculateCoverDimensions({
      pageCount: 300,
      trimSize: "5.5x8.5",
      paperType: "cream",
    });

    expect(dims.spine_width_inches).toBeCloseTo(0.75, 2);
    expect(dims.total_width_inches).toBeCloseTo(12.0, 2);
    expect(dims.total_height_inches).toBeCloseTo(8.75, 2);
    expect(dims.total_width_px).toBe(Math.round(12.0 * 300));
    expect(dims.total_height_px).toBe(Math.round(8.75 * 300));
    expect(dims.has_spine_text).toBe(true);
  });

  it("marks no spine text for thin books", () => {
    const dims = calculateCoverDimensions({
      pageCount: 80,
      trimSize: "5.5x8.5",
      paperType: "white",
    });
    expect(dims.has_spine_text).toBe(false);
  });

  it("reads trim dimensions from the trim table", () => {
    const dims = calculateCoverDimensions({
      pageCount: 200,
      trimSize: "6x9",
      paperType: "white",
    });
    expect(dims.trim_width_inches).toBe(6);
    expect(dims.total_height_inches).toBeCloseTo(9.25, 2);
  });

  it("rejects a trim size that KDP does not offer", () => {
    expect(() =>
      calculateCoverDimensions({
        pageCount: 200,
        // @ts-expect-error deliberately invalid
        trimSize: "40x0.1",
        paperType: "white",
      }),
    ).toThrow(/trim size/i);
  });

  it("rejects page counts outside KDP's range for the trim and paper", () => {
    expect(() =>
      calculateCoverDimensions({ pageCount: 5000, trimSize: "6x9", paperType: "white" }),
    ).toThrow(/24-828/);
    expect(() =>
      calculateCoverDimensions({ pageCount: 600, trimSize: "8.5x11", paperType: "white" }),
    ).toThrow(/24-590/);
    expect(() =>
      calculateCoverDimensions({ pageCount: 50, trimSize: "6x9", paperType: "standard_color" }),
    ).toThrow(/72-600/);
  });

  it("rejects a paper type that the trim does not offer", () => {
    expect(pageRange("8.27x11.69", "standard_color")).toBeNull();
    expect(() =>
      calculateCoverDimensions({
        pageCount: 200,
        trimSize: "8.27x11.69",
        paperType: "standard_color",
      }),
    ).toThrow(/not available/);
  });

  // Regression: zones were rounded independently, so the front zone's right
  // edge plus bleed overran the canvas by 1px (6x9, 250 pages, white).
  it("tiles the canvas with contiguous zones and a bleed on every side", () => {
    // 0.125" is 37.5px at 300 DPI, so each bleed band rounds to 37 or 38px.
    const bleed = BLEED_INCHES * PRINT_DPI;
    const nearBleed = (px: number) => expect(Math.abs(px - bleed)).toBeLessThanOrEqual(0.5);
    for (const trimSize of TRIM_SIZE_KEYS) {
      for (const pageCount of [100, 250, 333, 500]) {
        const d = calculateCoverDimensions({ pageCount, trimSize, paperType: "white" });
        expect(d.spine_zone.x).toBe(d.back_zone.x + d.back_zone.width);
        expect(d.front_zone.x).toBe(d.spine_zone.x + d.spine_zone.width);
        nearBleed(d.back_zone.x);
        nearBleed(d.total_width_px - (d.front_zone.x + d.front_zone.width));
        nearBleed(d.front_zone.y);
        nearBleed(d.total_height_px - (d.front_zone.y + d.front_zone.height));
        expect(Math.abs(d.front_zone.width - d.trim_width_inches * PRINT_DPI)).toBeLessThanOrEqual(1);
      }
    }
  });
});

describe("color helpers", () => {
  it("parses and rejects hex colors", () => {
    expect(hexToRgb("#1a2B3c")).toEqual({ r: 0x1a, g: 0x2b, b: 0x3c });
    expect(() => hexToRgb("#fff")).toThrow(/hex color/);
    expect(() => hexToRgb("navy")).toThrow(/hex color/);
  });

  it("returns 21 for black on white", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 0);
  });

  it("returns 1 for same colors", () => {
    expect(contrastRatio("#336699", "#336699")).toBeCloseTo(1, 0);
  });

  it("returns original color if contrast is sufficient", () => {
    expect(ensureContrast("#1a1a2e", "#ffffff")).toBe("#1a1a2e");
  });

  it("darkens a light color only as far as needed", () => {
    const result = ensureContrast("#ffff99", "#ffffff");
    expect(contrastRatio(result, "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(result).not.toBe("#000000");
  });

  // Regression: shorthand or named colors silently became black.
  it("throws on malformed colors instead of returning black", () => {
    expect(() => ensureContrast("#fff", "#ffffff")).toThrow(/hex color/);
  });
});
