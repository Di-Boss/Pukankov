import { test, expect, Page } from "./fixtures";
import { mkdir } from "node:fs/promises";
async function browserRequest(
  page: Page,
  method: string,
  path: string,
  options: { headers?: Record<string, string>; data?: unknown } = {},
) {
  const result = await page.evaluate(
    async ({ method, path, options }) => {
      const response = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json", ...options.headers },
        body: options.data ? JSON.stringify(options.data) : undefined,
      });
      return { status: response.status, body: await response.json() };
    },
    { method, path, options },
  );
  return {
    json: async () => result.body,
    ok: () => result.status >= 200 && result.status < 300,
  };
}
async function completeCardPayment(page: Page, success = true) {
  await page
    .getByLabel("Номер на карта", { exact: true })
    .fill("4242 4242 4242 4242");
  await page
    .getByLabel("Име на притежателя", { exact: true })
    .fill("IVAN IVANOV");
  await page.getByLabel("Валидна до", { exact: true }).fill("1230");
  await page.getByLabel("CVV", { exact: true }).fill("123");
  await page.getByRole("checkbox", { name: "Приемам", exact: false }).check();
  if (success)
    await page
      .getByRole("checkbox", { name: "Успешна транзакция", exact: true })
      .check();
  await page.getByRole("button", { name: /^Плати / }).click();
}

async function register(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Име и фамилия").fill("Кино Зрител");
  await page.getByLabel("Имейл адрес").fill(`viewer-${Date.now()}@example.com`);
  await page.getByLabel("Парола", { exact: true }).fill("BrowserPassword123!");
  await page.getByLabel("Потвърди паролата").fill("BrowserPassword123!");
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Създай профил", exact: true })
    .click();
  await expect(page).toHaveURL(/\/profile$/);
}
test("homepage, search and film details", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator(".hero")).toContainText("ОРБИТА");
  await expect(page.locator(".home-movies .movie-card")).toHaveCount(5);
  await mkdir("screenshots", { recursive: true });
  await page
    .locator('img[loading="lazy"]')
    .evaluateAll((images) =>
      images.forEach((img) => img.setAttribute("loading", "eager")),
    );
  await page.waitForFunction(() =>
    Array.from(document.images).every((img) => img.complete),
  );
  await page.screenshot({
    path: "screenshots/desktop-home.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: "Търси филм", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Търсене", exact: true })
    .fill("Град от светлина");
  await page.locator(".search-results").getByRole("link").first().click();
  await expect(
    page.getByRole("heading", {
      name: "Град от светлина",
      exact: true,
      level: 1,
    }),
  ).toBeVisible();
  await expect(page.locator(".showtime-results")).toBeVisible();
  expect(errors).toEqual([]);
});
test("catalog filters, empty results and pagination", async ({ page }) => {
  await page.goto("/movies");
  await expect(page.locator(".catalog-grid .movie-card")).toHaveCount(12);
  await page
    .getByRole("combobox", { name: "Жанр", exact: true })
    .selectOption("Анимация");
  await expect(page.locator(".results-label")).toContainText("2 филма");
  await page
    .getByRole("textbox", { name: "Търси в каталога" })
    .fill("zz-no-such-film");
  await expect(
    page.getByRole("heading", { name: "Тази история още не е тук" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Покажи всички филми" }).click();
  await page.getByRole("button", { name: "Напред", exact: true }).click();
  await expect(page).toHaveURL(/page=2/);
});
test("register, select seats, apply promo, checkout, numeric tickets and access control", async ({
  page,
}) => {
  await register(page);
  await page.goto("/showtimes");
  await page.locator(".showtime-slot").first().click();
  await page.locator(".seat:not([disabled])").nth(2).click();
  await page.locator(".seat:not([disabled])").nth(3).click();
  await expect(page.locator(".selected-seats>div")).toHaveCount(2);
  await page.getByRole("button", { name: "Продължи към поръчката" }).click();
  await expect(page).toHaveURL("/checkout");
  await expect(page.locator(".hold-timer")).toContainText(
    "Твоите места те очакват",
  );
  await page
    .getByRole("textbox", { name: "Промокод", exact: true })
    .fill("KINO20");
  await page.getByRole("button", { name: "Приложи", exact: true }).click();
  await expect(page.locator(".discount-line")).toContainText("KINO20");
  await page.screenshot({
    path: "screenshots/desktop-checkout.png",
    fullPage: true,
    animations: "disabled",
  });
  const paymentRequest = page.waitForRequest(
    (r) =>
      r.url().endsWith("/api/v1/payments/checkout") && r.method() === "POST",
  );
  await completeCardPayment(page);
  expect(Object.keys((await paymentRequest).postDataJSON()).sort()).toEqual([
    "hold_id",
    "promo_code",
    "terms",
    "transaction_success",
  ]);
  await expect(
    page.getByRole("heading", { name: "Мястото ти е запазено." }),
  ).toBeVisible();
  await expect(page.locator(".electronic-ticket")).toHaveCount(2);
  await expect(page.locator(".ticket-code")).toHaveCount(2);
  for (const code of await page.locator(".ticket-code").allTextContents())
    expect(code).toMatch(/^[0-9]{6}$/);
  await page.screenshot({
    path: "screenshots/desktop-tickets.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.goto("/my-tickets");
  await expect(page.locator(".electronic-ticket")).toHaveCount(2);
  await page.goto("/admin");
  await expect(page).toHaveURL("/403");
});
test("mobile checkout and electronic ticket", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await register(page);
  await page.goto("/showtimes");
  await page.locator(".showtime-slot").first().click();
  await page.locator(".seat:not([disabled])").first().click();
  await page.getByRole("button", { name: "Продължи към поръчката" }).click();
  await expect(page.locator(".hold-timer")).toBeVisible();
  await page.screenshot({
    path: "screenshots/mobile-checkout.png",
    fullPage: true,
    animations: "disabled",
  });
  await completeCardPayment(page);
  await expect(page.locator(".electronic-ticket")).toHaveCount(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("unchecked transaction refuses payment, issues no ticket and permits a fresh purchase", async ({
  page,
}) => {
  await register(page);
  await page.goto("/showtimes");
  await page.locator(".showtime-slot").first().click();
  await page.locator(".seat:not([disabled])").first().click();
  await page.getByRole("button", { name: "Продължи към поръчката" }).click();
  await completeCardPayment(page, false);
  await expect(page.getByRole("alert")).toContainText(
    "Транзакцията е отказана",
  );
  await expect(page.locator(".electronic-ticket")).toHaveCount(0);
  await page.getByRole("link", { name: "Избери местата отново" }).click();
  await page.locator(".seat:not([disabled])").first().click();
  await page.getByRole("button", { name: "Продължи към поръчката" }).click();
  await completeCardPayment(page, true);
  await expect(page.locator(".ticket-code")).toHaveCount(1);
});

test("favorites persist across pages", async ({ page }) => {
  await register(page);
  await page.goto("/movies");
  await page
    .getByRole("button", {
      name: "Добави в любими: Последната орбита",
      exact: true,
    })
    .click();
  await page.goto("/favorites");
  await expect(page.locator(".movie-card")).toHaveCount(1);
  await page.reload();
  await expect(page.locator(".movie-card")).toHaveCount(1);
  await page
    .getByRole("button", {
      name: "Премахни от любими: Последната орбита",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Тук ще живеят любимите ти филми" }),
  ).toBeVisible();
});
test("search modal supports keyboard close", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Търси филм", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
test("admin creates a movie and screening and sees actual data", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("Имейл адрес").fill("e2e-admin@example.com");
  await page
    .getByLabel("Парола", { exact: true })
    .fill(process.env.PUKANKOV_E2E_PASSWORD!);
  await page
    .getByRole("button", { name: "Влез в профила си", exact: true })
    .click();
  await expect(page).toHaveURL("/profile");
  const headers = { "X-Requested-With": "Pukankov" };
  const show = (
    await (await browserRequest(page, "GET", "/api/v1/showtimes")).json()
  )[0];
  const seats = (
    await (
      await browserRequest(page, "GET", `/api/v1/showtimes/${show.id}/seats`)
    ).json()
  ).seats
    .filter((s: { status: string }) => s.status === "available")
    .slice(0, 1);
  const hold = await (
    await browserRequest(page, "POST", "/api/v1/bookings/holds", {
      headers,
      data: {
        showtime_id: show.id,
        seat_ids: seats.map((s: { id: number }) => s.id),
      },
    })
  ).json();
  expect(
    (
      await browserRequest(page, "POST", "/api/v1/payments/checkout", {
        headers,
        data: { hold_id: hold.id, terms: true, transaction_success: true },
      })
    ).ok(),
  ).toBe(true);
  await page.goto("/admin");
  await expect(page.locator(".stat-card")).toHaveCount(6);
  await page.getByRole("button", { name: "Филми", exact: true }).click();
  await page.getByRole("button", { name: "Добави", exact: true }).click();
  const modal = page.getByRole("dialog");
  await modal
    .getByLabel("Заглавие", { exact: true })
    .fill("Нашият тестов филм");
  await modal
    .getByLabel("Slug (на латиница, с тирета)")
    .fill("our-browser-test-film");
  await modal.getByLabel("Оригинално заглавие").fill("Our Browser Test Film");
  await modal
    .getByLabel("Описание", { exact: true })
    .fill("Демонстрационен филм, добавен от браузърен тест.");
  await modal.getByLabel("Жанрове (разделени със запетая)").fill("Драма");
  await modal.getByLabel("Оригинална премиера").fill("2026-10-27");
  await modal.getByRole("button", { name: "Запази", exact: true }).click();
  await expect(modal).toHaveCount(0);
  await expect(page.locator("table")).toContainText("Нашият тестов филм");
  await page.getByRole("button", { name: "Прожекции", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Прожекции", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Добави", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("combobox", { name: "Филм", exact: true })
    .selectOption({ label: "Нашият тестов филм" });
  await page
    .getByRole("dialog")
    .getByRole("combobox", { name: "Зала", exact: true })
    .selectOption({ index: 1 });
  const future = new Date();
  future.setDate(future.getDate() + 10);
  const day = future.toISOString().slice(0, 10);
  await page
    .getByRole("dialog")
    .locator('input[type="datetime-local"]')
    .fill(`${day}T11:00`);
  await page
    .getByRole("dialog")
    .getByRole("combobox", { name: "Формат", exact: true })
    .selectOption("2D");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Запази", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator("table")).toContainText("Нашият тестов филм");
  await page.getByRole("button", { name: "Поръчки", exact: true }).click();
  await expect(page.locator("table")).toContainText("confirmed");
  await page.getByRole("button", { name: "Одит", exact: true }).click();
  await expect(page.locator("table")).toContainText("movie.create");
});
test("all public routes render without JavaScript failures", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  for (const path of [
    "/cinemas",
    "/cinemas/vitosha",
    "/offers",
    "/about",
    "/contact",
    "/faq",
    "/terms",
    "/privacy",
    "/forgot-password",
    "/favorites",
    "/my-tickets",
    "/profile",
    "/checkout",
    "/403",
    "/missing-page",
  ]) {
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("main h1,main h3").first()).toBeVisible();
  }
  expect(errors).toEqual([]);
});
for (const width of [360, 390, 768, 1024, 1440, 1920])
  test(`responsive home and seat layout at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.locator(".hero")).toContainText("ОРБИТА");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.goto("/showtimes");
    await page.locator(".showtime-slot").first().click();
    await expect(page.locator(".seat-map")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
