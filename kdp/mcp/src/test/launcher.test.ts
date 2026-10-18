import { execFileSync } from "node:child_process";
import { chmodSync, copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";

describe("MCP launcher", () => {
  const temporaryDirectories: string[] = [];

  afterEach(() => {
    for (const directory of temporaryDirectories.splice(0)) {
      rmSync(directory, { recursive: true, force: true });
    }
  });

  it("starts from package files when node_modules/.bin symlinks are absent", () => {
    const pluginRoot = mkdtempSync(join(tmpdir(), "kdp-cover-launcher-"));
    temporaryDirectories.push(pluginRoot);

    const sourceDirectory = join(pluginRoot, "src");
    const tsxDirectory = join(pluginRoot, "node_modules", "tsx", "dist");
    mkdirSync(sourceDirectory, { recursive: true });
    mkdirSync(tsxDirectory, { recursive: true });

    const entrypoint = join(sourceDirectory, "index.ts");
    writeFileSync(entrypoint, "// diagnostic entrypoint\n", "utf8");
    writeFileSync(
      join(tsxDirectory, "cli.mjs"),
      "process.stdout.write(process.argv[2]);\n",
      "utf8",
    );

    const launcher = join(pluginRoot, "run.sh");
    copyFileSync(fileURLToPath(new URL("../../run.sh", import.meta.url)), launcher);
    chmodSync(launcher, 0o755);

    expect(execFileSync(launcher, { encoding: "utf8" })).toBe(entrypoint);
  });

  it("exits with an install hint when tsx is not installed", () => {
    const pluginRoot = mkdtempSync(join(tmpdir(), "kdp-cover-launcher-"));
    temporaryDirectories.push(pluginRoot);

    const launcher = join(pluginRoot, "run.sh");
    copyFileSync(fileURLToPath(new URL("../../run.sh", import.meta.url)), launcher);
    chmodSync(launcher, 0o755);

    let failure: { status?: number; stderr?: string } | undefined;
    try {
      execFileSync(launcher, { encoding: "utf8", stdio: "pipe" });
    } catch (error) {
      failure = error as { status?: number; stderr?: string };
    }
    expect(failure?.status).toBe(1);
    expect(failure?.stderr).toContain("npm install");
  });
});
