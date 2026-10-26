import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
const browser = await chromium.launch({ headless: true });
await mkdir("screenshots", { recursive: true });
for (const [name, width, height] of [
  ["desktop", 1440, 1100],
  ["mobile", 390, 844],
]) {
  const page = await browser.newPage({
    viewport: { width, height },
    deviceScaleFactor: 1,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(900);
  await page.screenshot({ path: `screenshots/${name}.png`, fullPage: true, animations: "disabled" });
  console.log(
    name,
    JSON.stringify({
      errors,
      overflow: await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      posters: await page.locator(".movie-card").count(),
      hero: await page.locator(".hero-backdrop").getAttribute("src"),
    }),
  );
  await page.close();
}
await browser.close();
