import { execFileSync, spawnSync } from "node:child_process";
import {
  chmodSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";

const MCP_DIR = fileURLToPath(new URL("../..", import.meta.url));
const PLUGIN_DIR = join(MCP_DIR, "..");

// Fake tsx entrypoint: prints the script path it was asked to run.
const FAKE_TSX = "process.stdout.write(process.argv[2]);\n";

// Fake npm: logs its invocation, prints noise on stdout (which must never
// reach the MCP channel), and creates the fake tsx entrypoint in its cwd.
const FAKE_NPM = `#!/bin/sh
echo "NPM STDOUT NOISE"
echo "$PWD $*" >> "$NPM_LOG"
[ -n "$NPM_FAIL" ] && exit 3
mkdir -p node_modules/tsx/dist
printf '%s\\n' '${FAKE_TSX.trim()}' > node_modules/tsx/dist/cli.mjs
`;

const temporaryDirectories: string[] = [];
function tempDir(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  temporaryDirectories.push(dir);
  return dir;
}

afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    rmSync(directory, { recursive: true, force: true });
  }
});

/** A minimal plugin tree: real launcher scripts, fake package and source. */
function makePlugin(opts: { withRootTsx?: boolean } = {}) {
  const root = tempDir("kdp-plugin-");
  const mcp = join(root, "mcp");
  mkdirSync(join(mcp, "src"), { recursive: true });
  for (const f of ["run.sh", "launcher-lib.sh"]) {
    copyFileSync(join(MCP_DIR, f), join(mcp, f));
  }
  chmodSync(join(mcp, "run.sh"), 0o755);
  writeFileSync(join(mcp, "package.json"), '{"name":"fake","type":"module"}\n');
  writeFileSync(join(mcp, "package-lock.json"), '{"lockfileVersion":3}\n');
  writeFileSync(join(mcp, "tsconfig.json"), "{}\n");
  writeFileSync(join(mcp, "src", "index.ts"), "// entrypoint\n");
  mkdirSync(join(root, "hooks", "scripts"), { recursive: true });
  copyFileSync(
    join(PLUGIN_DIR, "hooks", "scripts", "detect-kdp-setup.sh"),
    join(root, "hooks", "scripts", "detect-kdp-setup.sh"),
  );
  if (opts.withRootTsx) {
    mkdirSync(join(mcp, "node_modules", "tsx", "dist"), { recursive: true });
    writeFileSync(join(mcp, "node_modules", "tsx", "dist", "cli.mjs"), FAKE_TSX);
  }

  const bin = tempDir("kdp-bin-");
  writeFileSync(join(bin, "npm"), FAKE_NPM);
  chmodSync(join(bin, "npm"), 0o755);
  const npmLog = join(bin, "npm.log");
  writeFileSync(npmLog, "");

  return { root, mcp, bin, npmLog };
}

function run(
  plugin: ReturnType<typeof makePlugin>,
  env: Record<string, string | undefined>,
  args: string[] = [],
) {
  const result = spawnSync(join(plugin.mcp, "run.sh"), args, {
    encoding: "utf8",
    env: {
      ...process.env,
      PATH: `${plugin.bin}:${process.env.PATH}`,
      NPM_LOG: plugin.npmLog,
      CLAUDE_PLUGIN_DATA: undefined,
      ...env,
    },
  });
  return result;
}

const npmCalls = (plugin: ReturnType<typeof makePlugin>) =>
  readFileSync(plugin.npmLog, "utf8").split("\n").filter(Boolean);

describe("MCP launcher (run.sh)", () => {
  it("runs from the plugin root when it already has node_modules", () => {
    const plugin = makePlugin({ withRootTsx: true });
    const result = run(plugin, {});
    expect(result.status).toBe(0);
    expect(result.stdout).toBe(join(plugin.mcp, "src", "index.ts"));
    expect(npmCalls(plugin)).toEqual([]);
  });

  it("exits with an install hint when deps are missing and CLAUDE_PLUGIN_DATA is unset", () => {
    const plugin = makePlugin();
    const result = run(plugin, {});
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("npm install");
  });

  it("installs into CLAUDE_PLUGIN_DATA once and runs a copy of src from there", () => {
    const plugin = makePlugin();
    const data = tempDir("kdp-data-");

    const first = run(plugin, { CLAUDE_PLUGIN_DATA: data });
    expect(first.status).toBe(0);
    // npm's stdout must not leak into the MCP stdio channel.
    expect(first.stdout).not.toContain("NPM STDOUT NOISE");
    expect(first.stdout.startsWith(join(data, "run-"))).toBe(true);
    expect(first.stdout.endsWith(join("src", "index.ts"))).toBe(true);
    expect(existsSync(first.stdout)).toBe(true);
    expect(npmCalls(plugin)).toHaveLength(1);
    expect(npmCalls(plugin)[0]).toMatch(/ ci --omit=dev/);
    // Nothing was written into the (possibly read-only) plugin root.
    expect(existsSync(join(plugin.mcp, "node_modules"))).toBe(false);

    const second = run(plugin, { CLAUDE_PLUGIN_DATA: data });
    expect(second.stdout).toBe(first.stdout);
    expect(npmCalls(plugin)).toHaveLength(1);
  });

  it("reuses deps when only src changes, and reinstalls when the lockfile changes", () => {
    const plugin = makePlugin();
    const data = tempDir("kdp-data-");
    const first = run(plugin, { CLAUDE_PLUGIN_DATA: data });

    writeFileSync(join(plugin.mcp, "src", "index.ts"), "// edited entrypoint\n");
    const afterSrc = run(plugin, { CLAUDE_PLUGIN_DATA: data });
    expect(afterSrc.status).toBe(0);
    expect(afterSrc.stdout).not.toBe(first.stdout);
    expect(readFileSync(afterSrc.stdout, "utf8")).toContain("edited");
    expect(npmCalls(plugin)).toHaveLength(1);

    writeFileSync(join(plugin.mcp, "package-lock.json"), '{"lockfileVersion":3,"v":2}\n');
    const afterLock = run(plugin, { CLAUDE_PLUGIN_DATA: data });
    expect(afterLock.status).toBe(0);
    expect(npmCalls(plugin)).toHaveLength(2);
    expect(readdirSync(data).filter((d) => d.startsWith("deps-"))).toHaveLength(2);
  });

  it("fails cleanly when npm ci fails, then retries on the next start", () => {
    const plugin = makePlugin();
    const data = tempDir("kdp-data-");
    const failed = run(plugin, { CLAUDE_PLUGIN_DATA: data, NPM_FAIL: "1" });
    expect(failed.status).toBe(1);
    expect(failed.stdout).toBe("");
    expect(failed.stderr).toContain("npm ci failed");
    expect(readdirSync(data).filter((d) => !d.startsWith("."))).toEqual([]);

    const retried = run(plugin, { CLAUDE_PLUGIN_DATA: data });
    expect(retried.status).toBe(0);
    expect(npmCalls(plugin)).toHaveLength(2);
  });

  it("takes over an install lock left by a dead process", () => {
    const plugin = makePlugin();
    const data = tempDir("kdp-data-");
    mkdirSync(join(data, ".install.lock"));
    writeFileSync(join(data, ".install.lock", "pid"), "999999999\n");
    const result = run(plugin, { CLAUDE_PLUGIN_DATA: data });
    expect(result.status).toBe(0);
    expect(existsSync(join(data, ".install.lock"))).toBe(false);
  });

  it("--install-only installs and exits without starting the server", () => {
    const plugin = makePlugin();
    const data = tempDir("kdp-data-");
    const result = run(plugin, { CLAUDE_PLUGIN_DATA: data }, ["--install-only"]);
    expect(result.status).toBe(0);
    expect(result.stdout).toBe("");
    expect(npmCalls(plugin)).toHaveLength(1);
  });

  it("ships a launcher that the real package.json and lockfile can satisfy", () => {
    const pkg = JSON.parse(readFileSync(join(MCP_DIR, "package.json"), "utf8"));
    // run.sh executes tsx at runtime and installs with --omit=dev.
    expect(pkg.dependencies.tsx).toBeDefined();
    const lock = JSON.parse(readFileSync(join(MCP_DIR, "package-lock.json"), "utf8"));
    expect(lock.packages["node_modules/tsx"].dev).toBeUndefined();
  });
});

describe("SessionStart hook (detect-kdp-setup.sh)", () => {
  function hook(
    plugin: ReturnType<typeof makePlugin>,
    project: string,
    env: Record<string, string | undefined> = {},
  ): string {
    return execFileSync("bash", [join(plugin.root, "hooks", "scripts", "detect-kdp-setup.sh")], {
      encoding: "utf8",
      env: {
        ...process.env,
        PATH: `${plugin.bin}:${process.env.PATH}`,
        NPM_LOG: plugin.npmLog,
        CLAUDE_PLUGIN_ROOT: plugin.root,
        CLAUDE_PROJECT_DIR: project,
        CLAUDE_PLUGIN_DATA: undefined,
        OPENAI_API_KEY: "sk-test",
        ...env,
      },
    });
  }

  function bookProject(): string {
    const project = tempDir("kdp-project-");
    mkdirSync(join(project, ".claude"));
    writeFileSync(join(project, ".claude", "kdp.local.md"), "---\nkdp: {}\n---\n");
    return project;
  }

  it("stays silent outside book projects, even with nothing installed", () => {
    const plugin = makePlugin();
    const project = tempDir("kdp-project-");
    writeFileSync(join(project, "paper.tex"), "\\documentclass{article}\n");
    expect(hook(plugin, project, { OPENAI_API_KEY: undefined })).toBe("");
  });

  it("treats a manuscript-like file as a book project", () => {
    const plugin = makePlugin();
    const project = tempDir("kdp-project-");
    writeFileSync(join(project, "manuscript.docx"), "");
    expect(hook(plugin, project)).toContain("npm install");
  });

  it("stays silent in a book project when the server is ready and the key is set", () => {
    const plugin = makePlugin({ withRootTsx: true });
    expect(hook(plugin, bookProject())).toBe("");
  });

  it("gives the npm install hint when deps are missing and there is no data dir", () => {
    const plugin = makePlugin();
    const out = hook(plugin, bookProject());
    expect(out).toContain("npm install");
  });

  it("warns about a missing OPENAI_API_KEY only in book projects", () => {
    const plugin = makePlugin({ withRootTsx: true });
    expect(hook(plugin, bookProject(), { OPENAI_API_KEY: undefined })).toContain("OPENAI_API_KEY");
  });

  it("prewarms the CLAUDE_PLUGIN_DATA install in the background", async () => {
    const plugin = makePlugin();
    const data = tempDir("kdp-data-");
    const out = hook(plugin, bookProject(), { CLAUDE_PLUGIN_DATA: data });
    expect(out).toContain(`installing kdp-cover MCP dependencies into ${data}`);

    const deadline = Date.now() + 15_000;
    const ready = () =>
      readdirSync(data).some((d) => d.startsWith("run-") && existsSync(join(data, d, ".ready")));
    while (!ready() && Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 100));
    }
    expect(ready()).toBe(true);
    // The same readiness check run.sh uses now passes, so the hook goes quiet.
    while (existsSync(join(data, ".install.lock")) && Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 100));
    }
    expect(hook(plugin, bookProject(), { CLAUDE_PLUGIN_DATA: data })).toBe("");
  }, 30_000);
});
