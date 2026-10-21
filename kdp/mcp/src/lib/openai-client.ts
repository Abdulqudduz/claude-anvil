import OpenAI from "openai";
import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  EBOOK_COVER,
  IMAGE_MODEL,
  IMAGE_SIZE,
  type ImageQuality,
} from "./kdp-specs.js";

export interface CoverPromptInput {
  title: string;
  subtitle?: string;
  author_name: string;
  genre: string;
  art_direction?: string;
}

// Matched in order against the lowercased genre; first substring hit wins.
const GENRE_DEFAULTS: ReadonlyArray<readonly [string, string]> = [
  ["fantasy", "epic, atmospheric scene with rich color palette, magical elements, dramatic lighting"],
  ["thriller", "dark, high-contrast imagery, urban or shadowy setting, sense of tension and danger"],
  ["romance", "warm color palette, intimate atmosphere, evocative and emotionally charged imagery"],
  ["science fiction", "futuristic elements, cosmic or technological imagery, sleek and modern aesthetic"],
  ["horror", "dark, unsettling atmosphere, muted colors with sharp contrasts, creepy imagery"],
  ["mystery", "moody lighting, shadows, hints of intrigue, muted sophisticated color palette"],
  ["literary", "elegant, understated design, artistic composition, subtle symbolism"],
  ["technical", "clean, professional design, abstract geometric patterns or diagrams, modern typography"],
];
const FALLBACK_ART_DIRECTION =
  "clean, professional layout, relevant thematic imagery, authoritative feel";

function getGenreDefault(genre: string): string {
  const lower = genre.toLowerCase();
  return GENRE_DEFAULTS.find(([key]) => lower.includes(key))?.[1] ?? FALLBACK_ART_DIRECTION;
}

export function buildCoverPrompt(input: CoverPromptInput): string {
  const artDirection = input.art_direction ?? getGenreDefault(input.genre);
  const subtitleLine = input.subtitle
    ? `\nSubtitle text: "${input.subtitle}" (smaller, below the title)`
    : "";

  return `Design a professional book cover for publication.

Title text: "${input.title}" (prominently displayed, clear and readable)${subtitleLine}
Author text: "${input.author_name}" (at the bottom of the cover)

Art direction: ${artDirection}

Requirements:
- Portrait orientation book cover
- Title and author text must be clearly legible and spelled correctly
- Professional typography that fits the genre
- The text must be part of the design, not overlaid awkwardly
- No placeholder text, lorem ipsum, or watermarks
- High quality, publication-ready artwork`;
}

/** OpenAI error codes that mean the prompt or image was refused on policy grounds. */
const POLICY_ERROR_CODES = new Set(["moderation_blocked", "content_policy_violation"]);

/** Turn an OpenAI API error into an actionable message; other errors pass through. */
export function mapOpenAIError(error: unknown): Error {
  if (!(error instanceof OpenAI.APIError)) {
    return error instanceof Error ? error : new Error(String(error));
  }
  if (error.code && POLICY_ERROR_CODES.has(error.code)) {
    return new Error(
      `Content policy rejection: ${error.message}. ` +
        "Try different art direction that avoids copyrighted or restricted content.",
    );
  }
  return new Error(
    `OpenAI image request failed (HTTP ${error.status ?? "unknown"}${error.code ? `, ${error.code}` : ""}): ${error.message}`,
  );
}

export async function generateCoverImage(
  input: CoverPromptInput & { width?: number; height?: number; quality: ImageQuality },
): Promise<string> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error(
      "OPENAI_API_KEY environment variable is not set. Set it in the shell that launches Claude Code.",
    );
  }

  const client = new OpenAI({ apiKey });
  // GPT image models always return base64; IMAGE_SIZE is their portrait size,
  // the closest to a book-cover aspect ratio.
  let response;
  try {
    response = await client.images.generate({
      model: IMAGE_MODEL,
      prompt: buildCoverPrompt(input),
      n: 1,
      size: IMAGE_SIZE,
      quality: input.quality,
      output_format: "png",
    });
  } catch (error) {
    throw mapOpenAIError(error);
  }

  const imageData = response.data?.[0];
  if (!imageData?.b64_json) {
    throw new Error("OpenAI returned no image data");
  }

  const { default: sharp } = await import("sharp");
  const resized = await sharp(Buffer.from(imageData.b64_json, "base64"))
    .resize(
      input.width ?? EBOOK_COVER.recommended.width,
      input.height ?? EBOOK_COVER.recommended.height,
      { fit: "cover" },
    )
    .png()
    .toBuffer();

  const outputPath = join(tmpdir(), `kdp-cover-${Date.now()}.png`);
  await writeFile(outputPath, resized);
  return outputPath;
}
