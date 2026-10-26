import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { resolve } from "node:path";
import { mkdir } from "node:fs/promises";
const work = resolve(".test-artifacts");
await mkdir(work, { recursive: true });
const env = {
  ...process.env,
  PUKANKOV_EXTERNAL_SERVERS: "1",
  PUKANKOV_E2E_PASSWORD: randomBytes(20).toString("hex"),
  DATABASE_URL: `sqlite:///${resolve(work, `e2e-${Date.now()}.db`).replaceAll("\\", "/")}`,
  PUBLIC_ORIGIN: "http://127.0.0.1:5174",
  VITE_API_TARGET: "http://127.0.0.1:8001",
};
const backend = env.PUKANKOV_INMEMORY_API
  ? null
  : spawn("python", ["scripts/e2e_server.py"], {
      env,
      windowsHide: true,
      stdio: ["ignore", "ignore", "inherit"],
    });
const frontend = env.PUKANKOV_INMEMORY_API
  ? null
  : spawn(
      process.execPath,
      [
        "node_modules/vite/bin/vite.js",
        "--host",
        "127.0.0.1",
        "--port",
        "5174",
        "--strictPort",
      ],
      { env, windowsHide: true, stdio: ["ignore", "ignore", "inherit"] },
    );
let testProcess;
const stop = () => {
  backend?.kill("SIGKILL");
  frontend?.kill("SIGKILL");
  if (testProcess && !testProcess.killed) testProcess.kill("SIGKILL");
};
process.on("SIGINT", () => {
  stop();
  process.exit(130);
});
process.on("SIGTERM", () => {
  stop();
  process.exit(143);
});
async function ready(url) {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(1000) });
      if (r.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Test server did not start: ${url}`);
}
try {
  if (!env.PUKANKOV_INMEMORY_API)
    await Promise.all([
      ready("http://127.0.0.1:8001/api/v1/health"),
      ready("http://127.0.0.1:5174"),
    ]);
  testProcess = spawn(
    process.execPath,
    ["node_modules/@playwright/test/cli.js", "test", ...process.argv.slice(2)],
    { env, windowsHide: true, stdio: "inherit" },
  );
  const code = await new Promise((resolve, reject) => {
    testProcess.once("exit", resolve);
    testProcess.once("error", reject);
  });
  testProcess = undefined;
  stop();
  process.exitCode = code ?? 1;
} catch (error) {
  stop();
  console.error(error.message);
  process.exitCode = 1;
}
