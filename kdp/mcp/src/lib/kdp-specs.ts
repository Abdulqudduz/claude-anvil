// Single source of truth for every KDP and image-generation constant the MCP
// server uses. Tool schemas, layout math, validation, and the cost estimates
// all derive from these tables; docs/kdp-reference.md cites the same KDP pages
// and should be updated together with this file.
//
// Sources (checked 2026-10-21):
// - Paperback cover: https://kdp.amazon.com/en_US/help/topic/G201953020
// - Trim sizes and page ranges: https://kdp.amazon.com/en_US/help/topic/G201834560
// - eBook cover: https://kdp.amazon.com/en_US/help/topic/G6GTK3T3NUHKLEFX
// - OpenAI image pricing: https://developers.openai.com/api/docs/models/gpt-image-1

/** Print resolution KDP requires for covers and interior images. */
export const PRINT_DPI = 300;

/** Bleed on the top, bottom, and outside edges of a paperback cover. */
export const BLEED_INCHES = 0.125;

/** KDP prints spine text only on books with more than this many pages. */
export const KDP_SPINE_TEXT_MIN_PAGES_EXCLUSIVE = 79;

/**
 * Conservative readability threshold this plugin applies on top of KDP's page
 * rule: below 0.3" of spine, text is technically allowed but hard to read.
 */
export const SPINE_TEXT_MIN_WIDTH_INCHES = 0.3;

/** Below this width the spine carries the title only, no author name. */
export const SPINE_TITLE_ONLY_BELOW_INCHES = 0.5;

/** KDP: at least 0.0625" between spine text and each spine edge. */
export const SPINE_TEXT_EDGE_MARGIN_INCHES = 0.0625;

/** Barcode area KDP reserves on the back cover (lower right). */
export const BARCODE_ZONE_INCHES = { width: 2, height: 1.2 } as const;

/** Paper types: spine thickness per page and the minimum page count. */
export const PAPER = {
  white: { inchesPerPage: 0.002252, minPages: 24, label: "black ink, white paper" },
  cream: { inchesPerPage: 0.0025, minPages: 24, label: "black ink, cream paper" },
  groundwood: { inchesPerPage: 0.00235, minPages: 24, label: "black ink, groundwood paper (beta)" },
  standard_color: { inchesPerPage: 0.002252, minPages: 72, label: "standard color ink, white paper" },
  premium_color: { inchesPerPage: 0.002347, minPages: 24, label: "premium color ink, white paper" },
} as const;

export type PaperType = keyof typeof PAPER;

/** Non-empty tuple so zod's z.enum() accepts it directly. */
export const PAPER_TYPES = Object.keys(PAPER) as [PaperType, ...PaperType[]];

/**
 * Maximum page count per paper type. KDP groups trims into a few limit
 * profiles; null means the paper is not offered for that trim.
 */
const PAGE_LIMITS = {
  standard: { white: 828, cream: 776, groundwood: 812, standard_color: 600, premium_color: 828 },
  wide: { white: 800, cream: 750, groundwood: 784, standard_color: 600, premium_color: 800 },
  a4: { white: 780, cream: 730, groundwood: 764, standard_color: null, premium_color: 590 },
  large: { white: 590, cream: 550, groundwood: 578, standard_color: 600, premium_color: 590 },
} as const satisfies Record<string, Record<PaperType, number | null>>;

/** KDP paperback trim sizes (Amazon.com), keyed by the "WxH" inch label. */
export const TRIM_SIZES = {
  "5x8": { width: 5, height: 8, limits: PAGE_LIMITS.standard },
  "5.06x7.81": { width: 5.06, height: 7.81, limits: PAGE_LIMITS.standard },
  "5.25x8": { width: 5.25, height: 8, limits: PAGE_LIMITS.standard },
  "5.5x8.5": { width: 5.5, height: 8.5, limits: PAGE_LIMITS.standard },
  "6x9": { width: 6, height: 9, limits: PAGE_LIMITS.standard },
  "6.14x9.21": { width: 6.14, height: 9.21, limits: PAGE_LIMITS.standard },
  "6.69x9.61": { width: 6.69, height: 9.61, limits: PAGE_LIMITS.standard },
  "7x10": { width: 7, height: 10, limits: PAGE_LIMITS.standard },
  "7.44x9.69": { width: 7.44, height: 9.69, limits: PAGE_LIMITS.standard },
  "7.5x9.25": { width: 7.5, height: 9.25, limits: PAGE_LIMITS.standard },
  "8x10": { width: 8, height: 10, limits: PAGE_LIMITS.standard },
  "8.25x6": { width: 8.25, height: 6, limits: PAGE_LIMITS.wide },
  "8.25x8.25": { width: 8.25, height: 8.25, limits: PAGE_LIMITS.wide },
  "8.27x11.69": { width: 8.27, height: 11.69, limits: PAGE_LIMITS.a4 },
  "8.5x8.5": { width: 8.5, height: 8.5, limits: PAGE_LIMITS.large },
  "8.5x11": { width: 8.5, height: 11, limits: PAGE_LIMITS.large },
} as const;

export type TrimSize = keyof typeof TRIM_SIZES;

export const TRIM_SIZE_KEYS = Object.keys(TRIM_SIZES) as [TrimSize, ...TrimSize[]];

export const DEFAULT_TRIM_SIZE: TrimSize = "5.5x8.5";
export const DEFAULT_PAPER_TYPE: PaperType = "cream";

/** Allowed page range for a trim/paper combination, or null if not offered. */
export function pageRange(
  trim: TrimSize,
  paper: PaperType,
): { min: number; max: number } | null {
  const max = TRIM_SIZES[trim].limits[paper];
  return max === null ? null : { min: PAPER[paper].minPages, max };
}

/** Kindle eBook cover requirements. */
export const EBOOK_COVER = {
  recommended: { width: 1600, height: 2560 },
  minLongestSidePx: 500,
  maxSidePx: 10_000,
  heightToWidthRatio: 1.6,
  ratioTolerance: 0.08,
  maxBytes: 50 * 1024 * 1024,
  acceptedFormats: ["jpeg", "png", "gif", "tiff"],
  preferredFormat: "jpeg",
} as const;

/** Image model used for front covers and its native portrait output size. */
export const IMAGE_MODEL = "gpt-image-1";
export const IMAGE_SIZE = "1024x1536";

/** OpenAI list price per image for IMAGE_MODEL at IMAGE_SIZE, in USD. */
export const IMAGE_PRICE_USD = {
  low: 0.016,
  medium: 0.063,
  high: 0.25,
} as const;

export type ImageQuality = keyof typeof IMAGE_PRICE_USD;

export const IMAGE_QUALITIES = Object.keys(IMAGE_PRICE_USD) as [
  ImageQuality,
  ...ImageQuality[],
];

export const DEFAULT_IMAGE_QUALITY: ImageQuality = "high";
