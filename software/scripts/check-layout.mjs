import { chromium } from "@playwright/test";
const b = await chromium.launch();
for (const width of [768, 1024]) {
  const p = await b.newPage({ viewport: { width, height: 900 } });
  await p.goto("http://127.0.0.1:5173/");
  await p.waitForTimeout(1000);
  console.log(
    width,
    await p.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      viewport: innerWidth,
      client: document.documentElement.clientWidth,
      body: document.body.scrollWidth,
      offenders: [...document.querySelectorAll("body *")]
        .filter((e) => e.scrollWidth > e.clientWidth + 2 && e.tagName !== "svg")
        .map((e) => ({
          tag: e.tagName,
          cl: e.className,
          client: e.clientWidth,
          scroll: e.scrollWidth,
          r: Math.round(e.getBoundingClientRect().right),
          overflow: getComputedStyle(e).overflow,
        }))
        .slice(0, 40),
    })),
  );
  await p.screenshot({ path: `screenshots/layout-${width}.png` });
  await p.close();
}
await b.close();
