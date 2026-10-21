// Zod input schemas for every MCP tool. index.ts registers these shapes and
// each handler parses its input with the same schema, so validation and
// defaults are defined once and the TypeScript types are inferred from them.
import { z } from "zod";
import {
  DEFAULT_IMAGE_QUALITY,
  DEFAULT_PAPER_TYPE,
  DEFAULT_TRIM_SIZE,
  EBOOK_COVER,
  IMAGE_QUALITIES,
  PAPER_TYPES,
  TRIM_SIZE_KEYS,
} from "./kdp-specs.js";

const trimSize = z
  .enum(TRIM_SIZE_KEYS)
  .default(DEFAULT_TRIM_SIZE)
  .describe(`KDP paperback trim size "WxH" in inches: ${TRIM_SIZE_KEYS.join(", ")}`);

const paperType = z
  .enum(PAPER_TYPES)
  .default(DEFAULT_PAPER_TYPE)
  .describe("Paper and ink type (sets spine width and page limits)");

const pageCount = z.number().int().positive().describe("Interior page count");

/** A "#rrggbb" color. Validated so a bad value fails loudly, never silently. */
export const hexColor = z
  .string()
  .regex(/^#[0-9a-fA-F]{6}$/, 'expected a 6-digit hex color like "#1a2b3c"');

export const coverSpecsShape = {
  page_count: pageCount,
  trim_size: trimSize,
  paper_type: paperType,
};
export const CoverSpecsSchema = z.object(coverSpecsShape);
export type CoverSpecsInput = z.input<typeof CoverSpecsSchema>;

export const generateCoverShape = {
  title: z.string().min(1).describe("Book title"),
  subtitle: z.string().optional().describe("Book subtitle"),
  author_name: z.string().min(1).describe("Author or pen name"),
  genre: z.string().describe('Book genre, e.g. "epic fantasy", "thriller", "technical"'),
  art_direction: z
    .string()
    .optional()
    .describe("Visual description for the cover art. If omitted, a genre-appropriate prompt is generated."),
  width: z
    .number()
    .int()
    .positive()
    .max(EBOOK_COVER.maxSidePx)
    .default(EBOOK_COVER.recommended.width)
    .describe("Output width in pixels (portrait)"),
  height: z
    .number()
    .int()
    .positive()
    .max(EBOOK_COVER.maxSidePx)
    .default(EBOOK_COVER.recommended.height)
    .describe("Output height in pixels (portrait)"),
  quality: z
    .enum(IMAGE_QUALITIES)
    .default(DEFAULT_IMAGE_QUALITY)
    .describe("Image generation quality; sets the per-image price"),
};
export const GenerateCoverSchema = z.object(generateCoverShape);
export type GenerateCoverInput = z.input<typeof GenerateCoverSchema>;
export type GenerateCoverArgs = z.output<typeof GenerateCoverSchema>;

export const fullWrapShape = {
  front_cover_path: z.string().describe("Path to the approved front cover image"),
  title: z.string().min(1).describe("Book title (for spine text)"),
  author_name: z.string().min(1).describe("Author name (for spine text)"),
  blurb: z.string().describe("Back cover blurb text"),
  page_count: pageCount,
  trim_size: trimSize,
  paper_type: paperType,
  isbn: z.string().optional().describe("ISBN (marks barcode zone on back cover)"),
  back_color: hexColor
    .optional()
    .describe('Back cover background "#rrggbb". If omitted, extracted from the front cover.'),
};
export const FullWrapSchema = z.object(fullWrapShape);
export type FullWrapInput = z.input<typeof FullWrapSchema>;

export const COVER_KINDS = ["ebook", "paperback_front", "full_wrap"] as const;
export type CoverKind = (typeof COVER_KINDS)[number];

export const validateCoverShape = {
  cover_path: z.string().describe("Path to the cover image (or full-resolution wrap PNG) to validate"),
  kind: z.enum(COVER_KINDS).describe("What the file is supposed to be"),
  page_count: pageCount
    .optional()
    .describe("Required for print kinds: page count to compute expected dimensions"),
  trim_size: trimSize,
  paper_type: paperType,
};
export const ValidateCoverSchema = z.object(validateCoverShape);
export type ValidateCoverInput = z.input<typeof ValidateCoverSchema>;
