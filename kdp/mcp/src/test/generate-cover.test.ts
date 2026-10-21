import { describe, it, expect, vi, afterEach } from "vitest";
import OpenAI from "openai";
import { buildCoverPrompt, mapOpenAIError } from "../lib/openai-client.js";
import * as openaiClient from "../lib/openai-client.js";
import { handleGenerateCover } from "../tools/generate-cover.js";
import { IMAGE_PRICE_USD } from "../lib/kdp-specs.js";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("buildCoverPrompt", () => {
  it("includes title and author in prompt", () => {
    const prompt = buildCoverPrompt({
      title: "The Silent Policy",
      author_name: "Alex Towell",
      genre: "technical",
    });
    expect(prompt).toContain("The Silent Policy");
    expect(prompt).toContain("Alex Towell");
  });

  it("includes subtitle when provided", () => {
    const prompt = buildCoverPrompt({
      title: "Echoes of the Sublime",
      subtitle: "A Journey Through Mathematics",
      author_name: "Alex Towell",
      genre: "technical",
    });
    expect(prompt).toContain("A Journey Through Mathematics");
  });

  it("uses art direction when provided", () => {
    const prompt = buildCoverPrompt({
      title: "Test Book",
      author_name: "Test Author",
      genre: "fantasy",
      art_direction: "dark moody forest with a glowing rune",
    });
    expect(prompt).toContain("dark moody forest with a glowing rune");
  });

  it("generates genre-appropriate prompt when no art direction", () => {
    const prompt = buildCoverPrompt({ title: "Test Book", author_name: "Test Author", genre: "thriller" });
    expect(prompt).toContain("Test Book");
    expect(prompt).toContain("tension");
  });
});

describe("handleGenerateCover", () => {
  it("returns the path plus the quality and its list price", async () => {
    vi.spyOn(openaiClient, "generateCoverImage").mockResolvedValue("/tmp/kdp-cover-mock.png");
    const result = await handleGenerateCover({ title: "Test", author_name: "Author", genre: "fantasy" });
    expect(result).toEqual({
      path: "/tmp/kdp-cover-mock.png",
      quality: "high",
      estimated_cost_usd: IMAGE_PRICE_USD.high,
    });
  });

  it("passes default dimensions and quality when not specified", async () => {
    const spy = vi.spyOn(openaiClient, "generateCoverImage").mockResolvedValue("/tmp/mock.png");
    await handleGenerateCover({ title: "Test", author_name: "Author", genre: "fantasy" });
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ width: 1600, height: 2560, quality: "high" }),
    );
  });

  it("prices a lower quality from the same table", async () => {
    vi.spyOn(openaiClient, "generateCoverImage").mockResolvedValue("/tmp/mock.png");
    const result = await handleGenerateCover({
      title: "Test",
      author_name: "Author",
      genre: "fantasy",
      quality: "medium",
    });
    expect(result.estimated_cost_usd).toBe(IMAGE_PRICE_USD.medium);
  });

  it("propagates errors from generateCoverImage", async () => {
    vi.spyOn(openaiClient, "generateCoverImage").mockRejectedValue(
      new Error("OPENAI_API_KEY environment variable is not set."),
    );
    await expect(
      handleGenerateCover({ title: "Test", author_name: "Author", genre: "fantasy" }),
    ).rejects.toThrow("OPENAI_API_KEY");
  });
});

describe("mapOpenAIError", () => {
  const apiError = (status: number, code: string | null, message: string) =>
    OpenAI.APIError.generate(status, { error: { message, code, type: "invalid_request_error" } }, message, new Headers());

  // Regression: every HTTP 400 was reported as a content-policy rejection.
  it("labels only moderation rejections as content policy", () => {
    const mapped = mapOpenAIError(apiError(400, "moderation_blocked", "blocked by safety system"));
    expect(mapped.message).toMatch(/Content policy rejection/);
  });

  it("reports other 400s as invalid requests", () => {
    const mapped = mapOpenAIError(apiError(400, "invalid_value", "Invalid size"));
    expect(mapped.message).not.toMatch(/Content policy/);
    expect(mapped.message).toMatch(/400/);
    expect(mapped.message).toMatch(/Invalid size/);
  });

  it("passes non-API errors through unchanged", () => {
    const original = new Error("network down");
    expect(mapOpenAIError(original)).toBe(original);
  });
});
