import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import sharp from "sharp";
import { existsSync } from "node:fs";

// Stub the OpenAI client so no test ever calls the real API. APIError stays
// real so error mapping is exercised against the SDK's own class.
const generate = vi.fn();
vi.mock("openai", async (importOriginal) => {
  const actual = await importOriginal<typeof import("openai")>();
  class FakeOpenAI {
    static APIError = actual.default.APIError;
    images = { generate };
  }
  return { ...actual, default: FakeOpenAI };
});

const { generateCoverImage } = await import("../lib/openai-client.js");
const { default: OpenAI } = await import("openai");
const { IMAGE_MODEL, IMAGE_SIZE } = await import("../lib/kdp-specs.js");

const input = { title: "T", author_name: "A", genre: "fantasy", quality: "low" as const };

describe("generateCoverImage (stubbed OpenAI)", () => {
  const savedKey = process.env.OPENAI_API_KEY;
  beforeEach(() => {
    process.env.OPENAI_API_KEY = "sk-test";
    generate.mockReset();
  });
  afterEach(() => {
    process.env.OPENAI_API_KEY = savedKey;
  });

  it("requires OPENAI_API_KEY before calling the API", async () => {
    delete process.env.OPENAI_API_KEY;
    await expect(generateCoverImage(input)).rejects.toThrow(/OPENAI_API_KEY/);
    expect(generate).not.toHaveBeenCalled();
  });

  it("sends the model, size, and quality from kdp-specs and resizes the result", async () => {
    const png = await sharp({
      create: { width: 1024, height: 1536, channels: 3, background: { r: 1, g: 2, b: 3 } },
    })
      .png()
      .toBuffer();
    generate.mockResolvedValue({ data: [{ b64_json: png.toString("base64") }] });

    const path = await generateCoverImage({ ...input, width: 800, height: 1280 });
    expect(generate).toHaveBeenCalledWith(
      expect.objectContaining({ model: IMAGE_MODEL, size: IMAGE_SIZE, quality: "low" }),
    );
    expect(existsSync(path)).toBe(true);
    const meta = await sharp(path).metadata();
    expect([meta.width, meta.height]).toEqual([800, 1280]);
  });

  it("fails when the API returns no image", async () => {
    generate.mockResolvedValue({ data: [] });
    await expect(generateCoverImage(input)).rejects.toThrow(/no image data/);
  });

  it("maps a moderation rejection to a content-policy message", async () => {
    generate.mockRejectedValue(
      OpenAI.APIError.generate(
        400,
        { error: { message: "blocked", code: "moderation_blocked" } },
        "blocked",
        new Headers(),
      ),
    );
    await expect(generateCoverImage(input)).rejects.toThrow(/Content policy rejection/);
  });
});
