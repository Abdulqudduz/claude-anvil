import { stat } from "node:fs/promises";
import sharp from "sharp";
import { handleCoverSpecs, type CoverSpecsOutput } from "./cover-specs.js";
import { EBOOK_COVER, PRINT_DPI } from "../lib/kdp-specs.js";
import {
  ValidateCoverSchema,
  type CoverKind,
  type ValidateCoverInput,
} from "../lib/schemas.js";

export interface CoverCheck {
  name: string;
  status: "pass" | "fail" | "warn";
  expected: string;
  actual: string;
  note?: string;
}

export interface ValidateCoverOutput {
  valid: boolean;
  kind: CoverKind;
  checks: CoverCheck[];
  specs?: CoverSpecsOutput;
}

/** Rounding slack, in px, when comparing against computed print specs. */
const PX_TOLERANCE = 4;

function check(
  name: string,
  ok: boolean,
  expected: string,
  actual: string,
  opts: { warnOnly?: boolean; note?: string } = {},
): CoverCheck {
  return {
    name,
    status: ok ? "pass" : opts.warnOnly ? "warn" : "fail",
    expected,
    actual,
    ...(opts.note ? { note: opts.note } : {}),
  };
}

const within = (actual: number, expected: number, tol: number) =>
  Math.abs(actual - expected) <= tol;

function ebookChecks(meta: sharp.Metadata, fileBytes: number): CoverCheck[] {
  const width = meta.width ?? 0;
  const height = meta.height ?? 0;
  const size = `${width}x${height}`;
  const { recommended } = EBOOK_COVER;
  const ratio = width > 0 ? height / width : 0;
  const format = meta.format ?? "unknown";
  const accepted = (EBOOK_COVER.acceptedFormats as readonly string[]).includes(format);

  return [
    check(
      "minimum size",
      Math.max(width, height) >= EBOOK_COVER.minLongestSidePx,
      `longest side >= ${EBOOK_COVER.minLongestSidePx}px`,
      size,
    ),
    check(
      "maximum size",
      Math.max(width, height) <= EBOOK_COVER.maxSidePx,
      `each side <= ${EBOOK_COVER.maxSidePx}px`,
      size,
    ),
    check(
      "recommended size",
      width >= recommended.width && height >= recommended.height,
      `>= ${recommended.width}x${recommended.height}px (WxH)`,
      size,
      { warnOnly: true, note: "smaller covers can fail Amazon quality review" },
    ),
    check(
      "aspect ratio",
      within(ratio, EBOOK_COVER.heightToWidthRatio, EBOOK_COVER.ratioTolerance),
      `height/width ~ ${EBOOK_COVER.heightToWidthRatio}`,
      ratio.toFixed(3),
      { warnOnly: true, note: "portrait 1:1.6 is the KDP recommendation" },
    ),
    check("file format", accepted, EBOOK_COVER.acceptedFormats.join(", "), format),
    ...(accepted
      ? [
          check(
            "preferred format",
            format === EBOOK_COVER.preferredFormat,
            EBOOK_COVER.preferredFormat,
            format,
            { warnOnly: true },
          ),
        ]
      : []),
    check("color channels", (meta.channels ?? 0) >= 3, "RGB (3+ channels)", String(meta.channels ?? "unknown")),
    check(
      "file size",
      fileBytes < EBOOK_COVER.maxBytes,
      `< ${EBOOK_COVER.maxBytes / (1024 * 1024)}MB`,
      `${(fileBytes / (1024 * 1024)).toFixed(1)}MB`,
    ),
  ];
}

function printChecks(kind: CoverKind, meta: sharp.Metadata, specs: CoverSpecsOutput): CoverCheck[] {
  const width = meta.width ?? 0;
  const height = meta.height ?? 0;
  const checks: CoverCheck[] = [];

  if (kind === "full_wrap") {
    checks.push(
      check(
        "wrap width",
        within(width, specs.total_width_px, PX_TOLERANCE),
        `${specs.total_width_px}px (2 x trim + spine + 2 x bleed at ${PRINT_DPI} DPI)`,
        `${width}px`,
      ),
      check(
        "wrap height",
        within(height, specs.total_height_px, PX_TOLERANCE),
        `${specs.total_height_px}px (trim + 2 x bleed at ${PRINT_DPI} DPI)`,
        `${height}px`,
      ),
    );
  } else {
    // paperback_front: the front panel, optionally with its outer bleed.
    const bleedPx = Math.round(specs.bleed_inches * PRINT_DPI);
    const trimW = specs.front_zone.width;
    const trimH = specs.front_zone.height;
    checks.push(
      check(
        "front width",
        within(width, trimW, PX_TOLERANCE) || within(width, trimW + bleedPx, PX_TOLERANCE),
        `${trimW}px (trim) or ${trimW + bleedPx}px (with outer bleed)`,
        `${width}px`,
      ),
      check(
        "front height",
        within(height, trimH, PX_TOLERANCE) || within(height, trimH + 2 * bleedPx, PX_TOLERANCE),
        `${trimH}px (trim) or ${trimH + 2 * bleedPx}px (with bleed)`,
        `${height}px`,
      ),
    );
  }

  const density = meta.density;
  checks.push(
    check(
      "print resolution",
      density === undefined || density >= PRINT_DPI,
      `>= ${PRINT_DPI} DPI`,
      density === undefined ? "not embedded" : `${density} DPI`,
      {
        warnOnly: density === undefined,
        note:
          density === undefined
            ? "no density metadata; the pixel-dimension checks above are the authoritative signal"
            : undefined,
      },
    ),
    check(
      "color channels",
      (meta.channels ?? 0) >= 3,
      "RGB or CMYK (KDP recommends CMYK and converts RGB, so colors may shift)",
      String(meta.channels ?? "unknown"),
    ),
  );
  return checks;
}

export async function handleValidateCover(input: ValidateCoverInput): Promise<ValidateCoverOutput> {
  const args = ValidateCoverSchema.parse(input);
  const meta = await sharp(args.cover_path).metadata();
  const fileBytes = (await stat(args.cover_path)).size;

  if (args.kind === "ebook") {
    const checks = ebookChecks(meta, fileBytes);
    return { valid: checks.every((c) => c.status !== "fail"), kind: args.kind, checks };
  }

  if (args.page_count === undefined) {
    throw new Error(
      `kind "${args.kind}" requires page_count (and optionally trim_size, paper_type) to compute expected dimensions`,
    );
  }
  const specs = handleCoverSpecs({
    page_count: args.page_count,
    trim_size: args.trim_size,
    paper_type: args.paper_type,
  });
  const checks = printChecks(args.kind, meta, specs);
  return { valid: checks.every((c) => c.status !== "fail"), kind: args.kind, checks, specs };
}
