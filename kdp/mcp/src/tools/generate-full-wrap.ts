import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import sharp from "sharp";
import { PDFDocument } from "pdf-lib";
import { ensureContrast, hexToRgb, rgbToHex } from "../lib/cover-layout.js";
import {
  BARCODE_ZONE_INCHES,
  PRINT_DPI,
  SPINE_TEXT_EDGE_MARGIN_INCHES,
  SPINE_TEXT_MIN_WIDTH_INCHES,
  SPINE_TITLE_ONLY_BELOW_INCHES,
} from "../lib/kdp-specs.js";
import { FullWrapSchema, type FullWrapInput } from "../lib/schemas.js";
import { handleCoverSpecs, type CoverSpecsOutput } from "./cover-specs.js";

export interface SpineTextResult {
  svgBuffer: Buffer; // SVG drawn upright: spine length wide, spine thickness tall
  titleOnly: boolean; // true if the spine is too narrow for the author name
  titleFontSize: number;
  authorFontSize: number | null;
}

export interface FullWrapOutput {
  pdf_path: string;
  /** Full-resolution 300 DPI wrap; pass this to kdp_validate_cover. */
  wrap_png_path: string;
  /** Half-resolution copy for showing the user; never validate this one. */
  preview_path: string;
  specs: CoverSpecsOutput;
}

const POINTS_PER_INCH = 72;
/** Rough average glyph advance as a fraction of font size, for fitting text. */
const GLYPH_WIDTH_EM = 0.6;
const BACK_TEXT_COLOR = "#ffffff";

const toPx = (inches: number) => Math.round(inches * PRINT_DPI);

const escapeXml = (s: string) =>
  s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

/** Largest font size <= maxSize whose estimated run of text fits in lengthPx. */
function fitFont(text: string, maxSize: number, lengthPx: number): number {
  const fit = Math.floor(lengthPx / (Math.max(1, text.length) * GLYPH_WIDTH_EM));
  return Math.max(1, Math.min(maxSize, fit));
}

// ── createBackCover ────────────────────────────────────────────────────────

export async function createBackCover(opts: {
  width: number;
  height: number;
  blurb: string;
  bgColor: string;
  isbn?: string;
}): Promise<Buffer> {
  const { width, height, blurb, bgColor, isbn } = opts;

  // KDP's barcode area, lower right of the back cover.
  const barcodeW = toPx(BARCODE_ZONE_INCHES.width);
  const barcodeH = toPx(BARCODE_ZONE_INCHES.height);
  const barcodePadding = toPx(0.25);
  const barcodeX = width - barcodeW - barcodePadding;
  const barcodeY = height - barcodeH - barcodePadding;

  // Text area: leave margins and stay above the barcode zone.
  const marginPx = toPx(0.5);
  const textWidth = width - marginPx * 2;
  const textAreaHeight = barcodeY - marginPx * 2;
  const fontSize = Math.max(28, Math.round(width * 0.022));

  const barcodeRect = `<rect x="${barcodeX}" y="${barcodeY}" width="${barcodeW}" height="${barcodeH}" fill="white" rx="4"${isbn ? "" : ' opacity="0.15"'}/>`;

  // sharp does not support foreignObject/xhtml; plain SVG text with tspan wrapping.
  const charsPerLine = Math.floor(textWidth / (fontSize * 0.55));
  const lines: string[] = [];
  let currentLine = "";
  for (const word of blurb.split(/\s+/).filter(Boolean)) {
    const candidate = currentLine ? `${currentLine} ${word}` : word;
    if (candidate.length <= charsPerLine) {
      currentLine = candidate;
    } else {
      if (currentLine) lines.push(currentLine);
      currentLine = word;
    }
  }
  if (currentLine) lines.push(currentLine);

  // Long blurbs must not run into the barcode zone or off the panel.
  const lineHeight = Math.round(fontSize * 1.5);
  const maxLines = Math.max(1, Math.floor(textAreaHeight / lineHeight));
  if (lines.length > maxLines) {
    lines.length = maxLines;
    const last = lines[maxLines - 1].split(" ");
    lines[maxLines - 1] = `${last.slice(0, -1).join(" ")} ...`;
  }
  const tspans = lines
    .map(
      (line, i) =>
        `<tspan x="${marginPx}" dy="${i === 0 ? 0 : lineHeight}">${escapeXml(line)}</tspan>`,
    )
    .join("\n    ");

  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
  <rect width="${width}" height="${height}" fill="${bgColor}"/>
  <text x="${marginPx}" y="${marginPx + fontSize}" font-family="serif" font-size="${fontSize}" fill="${BACK_TEXT_COLOR}">
    ${tspans}
  </text>
  ${barcodeRect}
</svg>`;

  return sharp(Buffer.from(svg)).resize(width, height).png().toBuffer();
}

// ── createSpineText ────────────────────────────────────────────────────────

/**
 * Spine text drawn upright (length along x), to be rotated 90 degrees
 * clockwise so it reads top to bottom: title from the top, author near the
 * bottom. Fonts stay inside KDP's 0.0625" spine-edge margin and shrink until
 * the text fits along the spine.
 */
export function createSpineText(opts: {
  title: string;
  authorName: string;
  spineWidthInches: number;
  heightPx: number;
}): SpineTextResult | null {
  const { title, authorName, spineWidthInches, heightPx } = opts;
  if (spineWidthInches < SPINE_TEXT_MIN_WIDTH_INCHES) return null;

  const titleOnly = spineWidthInches < SPINE_TITLE_ONLY_BELOW_INCHES;
  const svgW = heightPx; // spine length
  const svgH = toPx(spineWidthInches); // spine thickness
  const usable = svgH - 2 * toPx(SPINE_TEXT_EDGE_MARGIN_INCHES);
  const endMargin = toPx(0.5);

  // Title gets most of the length; the author name sits in the bottom quarter.
  const titleLength = (svgW - 2 * endMargin) * (titleOnly ? 1 : 0.68);
  const authorLength = (svgW - 2 * endMargin) * 0.27;
  const titleFontSize = fitFont(title, Math.min(48, Math.floor(usable * 0.8)), titleLength);
  const authorFontSize = titleOnly
    ? null
    : fitFont(authorName, Math.min(32, Math.floor(usable * 0.6)), authorLength);

  // Baseline offset that visually centers cap-height text across the spine.
  const baseline = (size: number) => (svgH / 2 + size * 0.35).toFixed(1);
  const titleX = endMargin + titleLength / 2;
  const authorX = svgW - endMargin - authorLength / 2;

  const authorLine =
    authorFontSize === null
      ? ""
      : `<text x="${authorX}" y="${baseline(authorFontSize)}" text-anchor="middle" font-family="sans-serif" font-size="${authorFontSize}" fill="white" opacity="0.85">${escapeXml(authorName)}</text>`;

  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${svgW}" height="${svgH}">
  <text x="${titleX}" y="${baseline(titleFontSize)}" text-anchor="middle" font-family="sans-serif" font-size="${titleFontSize}" font-weight="bold" fill="white">${escapeXml(title)}</text>
  ${authorLine}
</svg>`;

  return { svgBuffer: Buffer.from(svg), titleOnly, titleFontSize, authorFontSize };
}

// ── handleGenerateFullWrap ─────────────────────────────────────────────────

async function extractDominantColor(imagePath: string): Promise<string> {
  const { channels } = await sharp(imagePath).stats();
  return rgbToHex({ r: channels[0].mean, g: channels[1].mean, b: channels[2].mean });
}

export async function handleGenerateFullWrap(input: FullWrapInput): Promise<FullWrapOutput> {
  const args = FullWrapSchema.parse(input);
  const specs = handleCoverSpecs({
    page_count: args.page_count,
    trim_size: args.trim_size,
    paper_type: args.paper_type,
  });
  const { total_width_px: totalW, total_height_px: totalH, front_zone, spine_zone, back_zone } = specs;

  const rawBgColor = args.back_color ?? (await extractDominantColor(args.front_cover_path));
  const bgColor = ensureContrast(rawBgColor, BACK_TEXT_COLOR);

  // The canvas is the back-cover color, not black: the bleed border must
  // carry printable art, and this makes the back/spine bleed seamless.
  const canvas = sharp({
    create: { width: totalW, height: totalH, channels: 3, background: hexToRgb(bgColor) },
  });

  // The front panel owns the right/top/bottom bleed on its side of the wrap,
  // so its art runs from the front zone's left edge to the canvas edges.
  const frontBuffer = await sharp(args.front_cover_path)
    .resize(totalW - front_zone.x, totalH, { fit: "cover" })
    .png()
    .toBuffer();

  const backBuffer = await createBackCover({
    width: back_zone.width,
    height: back_zone.height,
    blurb: args.blurb,
    bgColor,
    isbn: args.isbn,
  });

  const composites: sharp.OverlayOptions[] = [
    { input: backBuffer, left: back_zone.x, top: back_zone.y },
    { input: frontBuffer, left: front_zone.x, top: 0 },
  ];

  const spine = specs.has_spine_text
    ? createSpineText({
        title: args.title,
        authorName: args.author_name,
        spineWidthInches: specs.spine_width_inches,
        heightPx: spine_zone.height,
      })
    : null;
  if (spine) {
    const upright = await sharp(spine.svgBuffer)
      .resize(spine_zone.height, spine_zone.width)
      .png()
      .toBuffer();
    // Rotate 90 degrees clockwise so the text reads top to bottom.
    const rotated = await sharp(upright).rotate(90).png().toBuffer();
    composites.push({ input: rotated, left: spine_zone.x, top: spine_zone.y });
  }

  const fullWrapBuffer = await canvas
    .composite(composites)
    .withMetadata({ density: PRINT_DPI })
    .png()
    .toBuffer();

  const stamp = Date.now();
  const wrapPngPath = join(tmpdir(), `kdp-full-wrap-${stamp}.png`);
  await writeFile(wrapPngPath, fullWrapBuffer);

  const previewPath = join(tmpdir(), `kdp-full-wrap-preview-${stamp}.png`);
  await sharp(fullWrapBuffer)
    .resize(Math.round(totalW / 2), Math.round(totalH / 2))
    .png()
    .toFile(previewPath);

  const pdfDoc = await PDFDocument.create();
  const widthPt = specs.total_width_inches * POINTS_PER_INCH;
  const heightPt = specs.total_height_inches * POINTS_PER_INCH;
  const page = pdfDoc.addPage([widthPt, heightPt]);
  const pngImage = await pdfDoc.embedPng(fullWrapBuffer);
  page.drawImage(pngImage, { x: 0, y: 0, width: widthPt, height: heightPt });
  const pdfPath = join(tmpdir(), `kdp-full-wrap-${stamp}.pdf`);
  await writeFile(pdfPath, await pdfDoc.save());

  return { pdf_path: pdfPath, wrap_png_path: wrapPngPath, preview_path: previewPath, specs };
}
