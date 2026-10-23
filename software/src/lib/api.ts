export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      ...options,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "Pukankov",
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(
      0,
      path === "/payments/checkout"
        ? "Не получихме потвърждение за плащането. Провери „Моите билети“ преди нов опит."
        : "Няма връзка със сървъра. Проверете връзката и опитайте отново.",
    );
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    throw new ApiError(
      response.status,
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? "Проверете въведените данни."
          : path === "/payments/checkout"
            ? "Не получихме потвърждение за плащането. Провери „Моите билети“ преди нов опит."
            : "Не успяхме да заредим данните. Опитайте отново.",
    );
  }
  return body as T;
}
export const money = (n: number) =>
  new Intl.NumberFormat("bg-BG", { style: "currency", currency: "EUR" }).format(
    n,
  );
export const duration = (n: number) =>
  `${Math.floor(n / 60)} ч. ${n % 60} мин.`;
export const dateLabel = (s: string, full = false) =>
  new Intl.DateTimeFormat("bg-BG", {
    timeZone: "Europe/Sofia",
    day: "numeric",
    month: full ? "long" : "short",
    ...(full ? { year: "numeric" as const } : {}),
  }).format(new Date(s.length === 10 ? `${s}T12:00:00+02:00` : s));
export const sofiaToday = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Sofia",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
