import { test as base, expect } from "@playwright/test";
import { spawn, ChildProcessWithoutNullStreams } from "node:child_process";
import { createInterface } from "node:readline";
export type { Page } from "@playwright/test";
type Reply = { status: number; headers: Record<string, string>; body: string };
class Bridge {
  child: ChildProcessWithoutNullStreams;
  pending = new Map<number, (reply: Reply) => void>();
  counter = 0;
  ready: Promise<void>;
  constructor() {
    this.child = spawn(
      "python",
      ["-X", "utf8", "-u", "scripts/asgi_bridge.py"],
      { windowsHide: true, env: process.env, stdio: "pipe" },
    );
    this.child.stderr.on("data", (chunk) => process.stderr.write(chunk));
    this.ready = new Promise((resolve, reject) => {
      createInterface({ input: this.child.stdout }).on("line", (line) => {
        const item = JSON.parse(line);
        if (item.ready) resolve();
        else {
          this.pending.get(item.id)?.(item);
          this.pending.delete(item.id);
        }
      });
      this.child.once("error", reject);
      this.child.once("exit", (code) => {
        if (code) reject(new Error(`ASGI bridge exited: ${code}`));
      });
    });
  }
  async request(data: Record<string, unknown>): Promise<Reply> {
    await this.ready;
    const id = ++this.counter;
    return new Promise((resolve) => {
      this.pending.set(id, resolve);
      this.child.stdin.write(JSON.stringify({ ...data, id }) + "\n");
    });
  }
  close() {
    this.child.kill("SIGKILL");
  }
}
export const test = base.extend<{}, { bridge: Bridge | null }>({
  bridge: [
    async ({}, use) => {
      if (!process.env.PUKANKOV_INMEMORY_API) {
        await use(null);
        return;
      }
      const bridge = new Bridge();
      await bridge.ready;
      try {
        await use(bridge);
      } finally {
        bridge.close();
      }
    },
    { scope: "worker" },
  ],
  context: async ({ context, bridge }, use) => {
    if (bridge)
      await context.route("**/*", async (route) => {
        const request = route.request();
        if (!request.url().startsWith("http://127.0.0.1:5174/")) {
          await route.abort();
          return;
        }
        const reply = await bridge.request({
          url: request.url(),
          method: request.method(),
          headers: await request.allHeaders(),
          body: request.postData(),
        });
        await route.fulfill({
          status: reply.status,
          headers: reply.headers,
          body: Buffer.from(reply.body, "base64"),
        });
      });
    await use(context);
  },
});
export { expect };
