import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { handleCoverSpecs } from "./tools/cover-specs.js";
import { handleGenerateCover } from "./tools/generate-cover.js";
import { handleGenerateFullWrap } from "./tools/generate-full-wrap.js";
import { handleValidateCover } from "./tools/validate-cover.js";
import {
  coverSpecsShape,
  fullWrapShape,
  generateCoverShape,
  validateCoverShape,
} from "./lib/schemas.js";
import { IMAGE_PRICE_USD } from "./lib/kdp-specs.js";

const server = new McpServer({ name: "kdp-cover", version: "0.2.0" });

/** Run a handler and return its result as JSON, or its error as an MCP error. */
async function respond(run: () => unknown | Promise<unknown>) {
  try {
    const result = await run();
    return { content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }] };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { content: [{ type: "text" as const, text: `Error: ${message}` }], isError: true };
  }
}

const priceList = Object.entries(IMAGE_PRICE_USD)
  .map(([quality, usd]) => `${quality} $${usd}`)
  .join(", ");

server.tool(
  "kdp_cover_specs",
  "Calculate KDP paperback cover dimensions (spine width, zone layout, bleed, allowed page range) from page count, trim size, and paper type. Pure math, no image generation.",
  coverSpecsShape,
  async (args) => respond(() => handleCoverSpecs(args)),
);

server.tool(
  "kdp_generate_cover",
  `Generate a front cover image with artwork and typography via OpenAI image generation. Returns the PNG path and the list price charged. Price per call by quality: ${priceList}.`,
  generateCoverShape,
  async (args) => respond(() => handleGenerateCover(args)),
);

server.tool(
  "kdp_generate_full_wrap",
  "Composite a full paperback cover wrap: front cover image + calculated spine + programmatic back cover with blurb text. Returns a KDP-ready PDF, the full-resolution wrap PNG (validate this one), and a half-resolution preview PNG (show this one).",
  fullWrapShape,
  async (args) => respond(() => handleGenerateFullWrap(args)),
);

server.tool(
  "kdp_validate_cover",
  "Validate an existing cover image against KDP requirements: pixel dimensions, aspect ratio, format, channels, and file size for eBooks; computed wrap/front dimensions and print resolution for paperbacks. Reads image metadata only (PNG/JPEG/TIFF, not PDF); for a generated wrap pass wrap_png_path.",
  validateCoverShape,
  async (args) => respond(() => handleValidateCover(args)),
);

async function main() {
  await server.connect(new StdioServerTransport());
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
