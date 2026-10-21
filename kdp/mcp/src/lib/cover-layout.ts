import {
  BLEED_INCHES,
  KDP_SPINE_TEXT_MIN_PAGES_EXCLUSIVE,
  PAPER,
  PRINT_DPI,
  SPINE_TEXT_MIN_WIDTH_INCHES,
  TRIM_SIZES,
  TRIM_SIZE_KEYS,
  pageRange,
  type PaperType,
  type TrimSize,
} from "./kdp-specs.js";
import { hexColor } from "./schemas.js";

export interface Zone {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface CoverDimensions {
  spine_width_inches: number;
  total_width_inches: number;
  total_height_inches: number;
  total_width_px: number;
  total_height_px: number;
  bleed_inches: number;
  has_spine_text: boolean;
  front_zone: Zone;
  spine_zone: Zone;
  back_zone: Zone;
  trim_width_inches: number;
  trim_height_inches: number;
  page_range: { min: number; max: number };
}

export function calculateSpineWidth(pageCount: number, paperType: PaperType): number {
  return pageCount * PAPER[paperType].inchesPerPage;
}

const toPx = (inches: number) => Math.round(inches * PRINT_DPI);

export function calculateCoverDimensions(opts: {
  pageCount: number;
  trimSize: TrimSize;
  paperType: PaperType;
}): CoverDimensions {
  const trim = TRIM_SIZES[opts.trimSize];
  if (!trim) {
    throw new Error(
      `Unsupported trim size "${opts.trimSize}": KDP paperback trims are ${TRIM_SIZE_KEYS.join(", ")}`,
    );
  }
  const range = pageRange(opts.trimSize, opts.paperType);
  if (!range) {
    throw new Error(`${PAPER[opts.paperType].label} is not available for the ${opts.trimSize} trim`);
  }
  if (opts.pageCount < range.min || opts.pageCount > range.max) {
    throw new Error(
      `page_count ${opts.pageCount} is outside KDP's ${range.min}-${range.max} range for ${opts.trimSize}, ${PAPER[opts.paperType].label}`,
    );
  }

  const spineWidth = calculateSpineWidth(opts.pageCount, opts.paperType);
  const total_width_inches = 2 * trim.width + spineWidth + 2 * BLEED_INCHES;
  const total_height_inches = trim.height + 2 * BLEED_INCHES;

  // Round cumulative edge positions, not each width, so the zones tile the
  // canvas exactly with no 1px gap or overrun.
  const edges = [
    BLEED_INCHES,
    BLEED_INCHES + trim.width,
    BLEED_INCHES + trim.width + spineWidth,
    BLEED_INCHES + 2 * trim.width + spineWidth,
  ].map(toPx);
  const top = toPx(BLEED_INCHES);
  const height = toPx(BLEED_INCHES + trim.height) - top;
  const zone = (left: number, right: number): Zone => ({
    x: left,
    y: top,
    width: right - left,
    height,
  });

  return {
    spine_width_inches: spineWidth,
    total_width_inches,
    total_height_inches,
    total_width_px: toPx(total_width_inches),
    total_height_px: toPx(total_height_inches),
    bleed_inches: BLEED_INCHES,
    has_spine_text:
      opts.pageCount > KDP_SPINE_TEXT_MIN_PAGES_EXCLUSIVE &&
      spineWidth >= SPINE_TEXT_MIN_WIDTH_INCHES,
    back_zone: zone(edges[0], edges[1]),
    spine_zone: zone(edges[1], edges[2]),
    front_zone: zone(edges[2], edges[3]),
    trim_width_inches: trim.width,
    trim_height_inches: trim.height,
    page_range: range,
  };
}

// ── Color helpers ──────────────────────────────────────────────────────────

export interface Rgb {
  r: number;
  g: number;
  b: number;
}

/** Parse "#rrggbb"; throws on anything else rather than producing NaN. */
export function hexToRgb(hex: string): Rgb {
  const parsed = hexColor.safeParse(hex);
  if (!parsed.success) {
    throw new Error(`Invalid hex color "${hex}": expected a 6-digit hex color like "#1a2b3c"`);
  }
  const n = Number.parseInt(parsed.data.slice(1), 16);
  return { r: (n >> 16) & 0xff, g: (n >> 8) & 0xff, b: n & 0xff };
}

export function rgbToHex({ r, g, b }: Rgb): string {
  return `#${[r, g, b].map((c) => Math.round(c).toString(16).padStart(2, "0")).join("")}`;
}

function relativeLuminance(hex: string): number {
  const toLinear = (c: number) => {
    const s = c / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const { r, g, b } = hexToRgb(hex);
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

export function contrastRatio(hex1: string, hex2: string): number {
  const l1 = relativeLuminance(hex1);
  const l2 = relativeLuminance(hex2);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

/** Darken bgHex step by step until text in textHex meets minRatio. */
export function ensureContrast(bgHex: string, textHex: string, minRatio = 4.5): string {
  if (contrastRatio(bgHex, textHex) >= minRatio) return bgHex;
  let { r, g, b } = hexToRgb(bgHex);
  while (r > 0 || g > 0 || b > 0) {
    r = Math.max(0, r - 5);
    g = Math.max(0, g - 5);
    b = Math.max(0, b - 5);
    const candidate = rgbToHex({ r, g, b });
    if (contrastRatio(candidate, textHex) >= minRatio) return candidate;
  }
  return "#000000";
}
