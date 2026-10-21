import { describe, it, expect } from "vitest";
import { join } from "node:path";
import { tmpdir } from "node:os";
import sharp from "sharp";
import { handleValidateCover } from "../tools/validate-cover.js";
import { handleCoverSpecs } from "../tools/cover-specs.js";

async function makeImage(
  width: number,
  height: number,
  format: "png" | "jpeg" = "png",
): Promise<string> {
  const p = join(tmpdir(), `kdp-validate-${width}x${height}-${process.pid}.${format}`);
  await sharp({
    create: { width, height, channels: 3, background: { r: 30, g: 60, b: 90 } },
  })
    .toFormat(format)
    .toFile(p);
  return p;
}

const statusOf = (checks: { name: string; status: string }[], name: string) =>
  checks.find((c) => c.name === name)?.status;

describe("handleValidateCover: ebook", () => {
  it("passes a recommended-size JPEG cover with no warnings", async () => {
    const p = await makeImage(1600, 2560, "jpeg");
    const result = await handleValidateCover({ cover_path: p, kind: "ebook" });
    expect(result.valid).toBe(true);
    expect(result.checks.every((c) => c.status === "pass")).toBe(true);
  });

  // KDP now accepts PNG; JPEG is only preferred.
  it("passes a PNG cover, warning only that JPEG is preferred", async () => {
    const p = await makeImage(1600, 2560, "png");
    const result = await handleValidateCover({ cover_path: p, kind: "ebook" });
    expect(result.valid).toBe(true);
    expect(statusOf(result.checks, "file format")).toBe("pass");
    expect(statusOf(result.checks, "preferred format")).toBe("warn");
  });

  it("fails below KDP's 500px longest-side minimum", async () => {
    const p = await makeImage(300, 480);
    const result = await handleValidateCover({ cover_path: p, kind: "ebook" });
    expect(result.valid).toBe(false);
    expect(statusOf(result.checks, "minimum size")).toBe("fail");
  });

  it("only warns between the minimum and the recommended size", async () => {
    const p = await makeImage(500, 800);
    const result = await handleValidateCover({ cover_path: p, kind: "ebook" });
    expect(result.valid).toBe(true);
    expect(statusOf(result.checks, "minimum size")).toBe("pass");
    expect(statusOf(result.checks, "recommended size")).toBe("warn");
  });

  it("fails a side over KDP's 10,000px maximum", async () => {
    const p = await makeImage(1000, 10080, "jpeg");
    const result = await handleValidateCover({ cover_path: p, kind: "ebook" });
    expect(result.valid).toBe(false);
    expect(statusOf(result.checks, "maximum size")).toBe("fail");
  });

  it("warns (not fails) on an off-ratio but large ebook cover", async () => {
    const p = await makeImage(2560, 2560);
    const result = await handleValidateCover({ cover_path: p, kind: "ebook" });
    expect(result.valid).toBe(true);
    expect(statusOf(result.checks, "aspect ratio")).toBe("warn");
  });
});

describe("handleValidateCover: full_wrap", () => {
  it("passes a wrap rendered at exactly the computed specs", async () => {
    const specs = handleCoverSpecs({ page_count: 300, trim_size: "5.5x8.5", paper_type: "cream" });
    const p = await makeImage(specs.total_width_px, specs.total_height_px);
    const result = await handleValidateCover({
      cover_path: p,
      kind: "full_wrap",
      page_count: 300,
      trim_size: "5.5x8.5",
      paper_type: "cream",
    });
    expect(result.valid).toBe(true);
    expect(result.specs?.total_width_px).toBe(specs.total_width_px);
  });

  it("fails a wrap sized for the wrong page count", async () => {
    const wrong = handleCoverSpecs({ page_count: 120, trim_size: "5.5x8.5", paper_type: "cream" });
    const p = await makeImage(wrong.total_width_px, wrong.total_height_px);
    const result = await handleValidateCover({
      cover_path: p,
      kind: "full_wrap",
      page_count: 300,
      trim_size: "5.5x8.5",
      paper_type: "cream",
    });
    expect(result.valid).toBe(false);
    expect(statusOf(result.checks, "wrap width")).toBe("fail");
  });

  it("requires page_count for print kinds", async () => {
    const p = await makeImage(100, 100);
    await expect(handleValidateCover({ cover_path: p, kind: "full_wrap" })).rejects.toThrow(
      /requires page_count/,
    );
  });
});

describe("handleValidateCover: paperback_front", () => {
  it("accepts trim-exact and bleed-extended front covers", async () => {
    const specs = handleCoverSpecs({ page_count: 300, trim_size: "6x9", paper_type: "white" });
    const bleedPx = Math.round(specs.bleed_inches * 300);
    const trimExact = await makeImage(specs.front_zone.width, specs.front_zone.height);
    const withBleed = await makeImage(
      specs.front_zone.width + bleedPx,
      specs.front_zone.height + 2 * bleedPx,
    );
    for (const p of [trimExact, withBleed]) {
      const result = await handleValidateCover({
        cover_path: p,
        kind: "paperback_front",
        page_count: 300,
        trim_size: "6x9",
        paper_type: "white",
      });
      expect(result.valid).toBe(true);
    }
  });
});
