import { describe, it, expect, beforeAll } from "vitest";
import sharp from "sharp";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  createBackCover,
  createSpineText,
  handleGenerateFullWrap,
} from "../tools/generate-full-wrap.js";
import { handleValidateCover } from "../tools/validate-cover.js";

// Compositing a 300 DPI wrap takes ~4s alone and longer when the suite runs
// files in parallel, so the I/O-heavy tests get an explicit budget.
const RENDER_TIMEOUT_MS = 60_000;

let testCoverPath: string;

beforeAll(async () => {
  testCoverPath = join(tmpdir(), `test-front-cover-${process.pid}.png`);
  await sharp({
    create: { width: 1600, height: 2560, channels: 3, background: { r: 30, g: 60, b: 120 } },
  })
    .png()
    .toFile(testCoverPath);
});

describe("createBackCover", () => {
  it("creates a back cover image with correct dimensions", async () => {
    const result = await createBackCover({
      width: 1650,
      height: 2550,
      blurb: "A thrilling adventure through time and space.",
      bgColor: "#1a1a2e",
    });
    const metadata = await sharp(result).metadata();
    expect(metadata.width).toBe(1650);
    expect(metadata.height).toBe(2550);
  });
});

describe("createSpineText", () => {
  it("returns null for thin books", () => {
    expect(
      createSpineText({ title: "Test", authorName: "Author", spineWidthInches: 0.2, heightPx: 2550 }),
    ).toBeNull();
  });

  it("returns title-only for narrow spines", () => {
    const result = createSpineText({
      title: "Test Book",
      authorName: "Author Name",
      spineWidthInches: 0.35,
      heightPx: 2550,
    });
    expect(result!.titleOnly).toBe(true);
  });

  it("returns full text for wide spines", () => {
    const result = createSpineText({
      title: "Test Book",
      authorName: "Author Name",
      spineWidthInches: 0.8,
      heightPx: 2550,
    });
    expect(result!.titleOnly).toBe(false);
  });

  // KDP: at least 0.0625" between spine text and each spine edge.
  it("keeps the font inside the spine-edge margins", () => {
    const spineWidthInches = 0.35;
    const result = createSpineText({
      title: "T",
      authorName: "A",
      spineWidthInches,
      heightPx: 2550,
    })!;
    const usablePx = Math.round(spineWidthInches * 300) - 2 * Math.round(0.0625 * 300);
    expect(result.titleFontSize).toBeLessThanOrEqual(usablePx);
  });

  it("shrinks a long title so it fits along the spine", () => {
    const longTitle = "An Extraordinarily Long Title That Would Never Fit At Full Size On Any Spine";
    const result = createSpineText({
      title: longTitle,
      authorName: "Author Name",
      spineWidthInches: 0.8,
      heightPx: 2550,
    })!;
    const short = createSpineText({
      title: "Short",
      authorName: "Author Name",
      spineWidthInches: 0.8,
      heightPx: 2550,
    })!;
    expect(result.titleFontSize).toBeLessThan(short.titleFontSize);
  });
});

describe("handleGenerateFullWrap", () => {
  it(
    "writes a PDF, a full-resolution PNG, and a half-resolution preview",
    async () => {
      const result = await handleGenerateFullWrap({
        front_cover_path: testCoverPath,
        title: "Test Book",
        author_name: "Test Author",
        blurb: "A short blurb for testing.",
        page_count: 250,
        trim_size: "5.5x8.5",
        paper_type: "cream",
      });
      expect(existsSync(result.pdf_path)).toBe(true);
      expect(existsSync(result.wrap_png_path)).toBe(true);
      expect(existsSync(result.preview_path)).toBe(true);
      const full = await sharp(result.wrap_png_path).metadata();
      expect(full.width).toBe(result.specs.total_width_px);
      expect(full.height).toBe(result.specs.total_height_px);
      expect(full.density).toBe(300);
    },
    RENDER_TIMEOUT_MS,
  );

  // Regression: kdp-publish validated the half-resolution preview, which can
  // never pass. The generator's full-resolution PNG must pass the validator.
  it(
    "produces a wrap PNG that passes kdp_validate_cover end to end",
    async () => {
      const args = { page_count: 250, trim_size: "6x9", paper_type: "white" } as const;
      const result = await handleGenerateFullWrap({
        front_cover_path: testCoverPath,
        title: "Test Book",
        author_name: "Test Author",
        blurb: "A short blurb for testing.",
        ...args,
      });
      const verdict = await handleValidateCover({
        cover_path: result.wrap_png_path,
        kind: "full_wrap",
        ...args,
      });
      expect(verdict.checks.filter((c) => c.status !== "pass")).toEqual([]);
      expect(verdict.valid).toBe(true);
    },
    RENDER_TIMEOUT_MS,
  );

  it("rejects a malformed back_color instead of rendering black", async () => {
    await expect(
      handleGenerateFullWrap({
        front_cover_path: testCoverPath,
        title: "Test Book",
        author_name: "Test Author",
        blurb: "Blurb.",
        page_count: 250,
        back_color: "#fff",
      }),
    ).rejects.toThrow(/hex color/);
  });
});
