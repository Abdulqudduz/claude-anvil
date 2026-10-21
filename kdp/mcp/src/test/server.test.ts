import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { describe, it, expect } from "vitest";

const MCP_DIR = fileURLToPath(new URL("../..", import.meta.url));

/** Start the real server over stdio, send JSON-RPC requests, collect replies. */
async function talk(requests: object[], expectReplies: number): Promise<any[]> {
  const child = spawn("bash", [join(MCP_DIR, "run.sh")], {
    env: { ...process.env, CLAUDE_PLUGIN_DATA: undefined, OPENAI_API_KEY: undefined },
  });
  const replies: any[] = [];
  let buffer = "";
  const done = new Promise<void>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("server did not answer in time")), 20_000);
    child.stdout.on("data", (chunk) => {
      buffer += chunk;
      let newline;
      while ((newline = buffer.indexOf("\n")) >= 0) {
        replies.push(JSON.parse(buffer.slice(0, newline)));
        buffer = buffer.slice(newline + 1);
        if (replies.length >= expectReplies) {
          clearTimeout(timer);
          resolve();
        }
      }
    });
  });
  for (const r of requests) child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", ...r })}\n`);
  try {
    await done;
  } finally {
    child.kill();
  }
  return replies;
}

describe("kdp-cover MCP server over stdio", () => {
  it("lists the four tools and answers kdp_cover_specs, rejecting unknown trims", async () => {
    const replies = await talk(
      [
        {
          id: 1,
          method: "initialize",
          params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "test", version: "1" } },
        },
        { method: "notifications/initialized" },
        { id: 2, method: "tools/list" },
        {
          id: 3,
          method: "tools/call",
          params: { name: "kdp_cover_specs", arguments: { page_count: 250, trim_size: "6x9", paper_type: "white" } },
        },
        {
          id: 4,
          method: "tools/call",
          params: { name: "kdp_cover_specs", arguments: { page_count: 250, trim_size: "40x0.1" } },
        },
      ],
      4,
    );
    const byId = Object.fromEntries(replies.map((r) => [r.id, r]));

    const names = byId[2].result.tools.map((t: { name: string }) => t.name).sort();
    expect(names).toEqual(["kdp_cover_specs", "kdp_generate_cover", "kdp_generate_full_wrap", "kdp_validate_cover"]);
    const cover = byId[2].result.tools.find((t: { name: string }) => t.name === "kdp_generate_cover");
    expect(cover.description).toContain("high $0.25");

    const specs = JSON.parse(byId[3].result.content[0].text);
    expect(specs.total_width_px).toBe(3844);
    expect(byId[3].result.isError).toBeUndefined();

    expect(byId[4].result.isError).toBe(true);
  }, 30_000);
});
