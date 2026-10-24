import { useState } from "react";
import { Navigate, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Film,
  CalendarDays,
  MapPin,
  Armchair,
  ShoppingBag,
  Users,
  Tags,
  ScrollText,
  ScanLine,
  Plus,
  ArrowUpRight,
  Pencil,
  Archive,
  X,
  Check,
  Search,
  ArrowLeft,
  ArrowRight,
  Ticket,
  TrendingUp,
} from "lucide-react";
import { api, money, dateLabel } from "../lib/api";
import { useAuth, useToast } from "../lib/context";
import { Loading, ErrorState, Empty, Modal } from "../components/UI";
import type { Movie, Cinema, Showtime, Booking, User } from "../types";
type Room = {
  id: number;
  cinema_id: number;
  name: string;
  capacity: number;
  formats: string[];
};
type Row = Record<string, unknown>;
type Dashboard = {
  revenue: number;
  orders: number;
  tickets: number;
  showtimes: number;
  movies: number;
  users: number;
  average: number;
  by_movie: { title: string; tickets: number }[];
  by_day: { date: string; total: number }[];
};
const sections = [
  ["dashboard", "Табло", LayoutDashboard],
  ["movies", "Филми", Film],
  ["showtimes", "Прожекции", CalendarDays],
  ["cinemas", "Кина", MapPin],
  ["auditoriums", "Зали", Armchair],
  ["orders", "Поръчки", ShoppingBag],
  ["users", "Потребители", Users],
  ["promotions", "Промокодове", Tags],
  ["audit-logs", "Одит", ScrollText],
  ["scan", "Проверка на билет", ScanLine],
] as const;
export default function Admin() {
  const { user, loading } = useAuth();
  const [tab, setTab] = useState("dashboard");
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" state={{ from: "/admin" }} replace />;
  if (!["admin", "staff"].includes(user.role))
    return <Navigate to="/403" replace />;
  const active = user.role === "staff" ? "scan" : tab;
  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <div className="admin-badge">
          CONTROL ROOM<span>ПУКАНКОВ · ДИПЛОМНА</span>
        </div>
        <nav aria-label="Администрация">
          {sections
            .filter(([id]) => user.role === "admin" || id === "scan")
            .map(([id, label, Icon]) => (
              <button
                key={id}
                className={active === id ? "active" : ""}
                onClick={() => setTab(id)}
              >
                <Icon size={18} />
                {label}
              </button>
            ))}
        </nav>
        <Link to="/">
          <ArrowLeft size={16} />
          Обратно към киното
        </Link>
      </aside>
      <div className="admin-main">
        <div className="admin-top">
          <div>
            <span className="eyebrow">АДМИНИСТРАЦИЯ · УЧЕБНА СИСТЕМА</span>
            <h1>{sections.find(([id]) => id === active)?.[1]}</h1>
          </div>
          <span className="admin-user">
            <span>{user.name[0]}</span>
            {user.name}
          </span>
        </div>
        {active === "dashboard" ? (
          <DashboardView />
        ) : active === "scan" ? (
          <Scanner />
        ) : (
          <Manage key={active} section={active} />
        )}
      </div>
    </div>
  );
}
function DashboardView() {
  const q = useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: () => api<Dashboard>("/admin/dashboard"),
  });
  const orders = useQuery({
    queryKey: ["admin", "orders"],
    queryFn: () => api<(Booking & { user_email: string })[]>("/admin/orders"),
  });
  if (q.isLoading) return <Loading />;
  if (q.error || !q.data) return <ErrorState error={q.error} />;
  const d = q.data;
  return (
    <>
      <div className="stat-grid">
        {[
          [TrendingUp, "Демо оборот", money(d.revenue)],
          [ShoppingBag, "Потвърдени поръчки", d.orders],
          [Ticket, "Издадени билети", d.tickets],
          [CalendarDays, "Бъдещи прожекции", d.showtimes],
          [Film, "Филми в каталога", d.movies],
          [Users, "Потребители", d.users],
        ].map(([Icon, label, value], i) => {
          const I = Icon as typeof Film;
          return (
            <div className="stat-card" key={i}>
              <I size={20} />
              <span>{String(label)}</span>
              <strong>{String(value)}</strong>
            </div>
          );
        })}
      </div>
      <div className="admin-charts">
        <section className="admin-panel">
          <h2>Продажби по дни</h2>
          {!d.by_day.length ? (
            <p className="muted">Все още няма потвърдени демо поръчки.</p>
          ) : (
            <div className="bar-chart">
              {d.by_day.map((v) => (
                <div key={v.date}>
                  <span>{dateLabel(v.date)}</span>
                  <div>
                    <i
                      style={{
                        width: `${Math.max(3, (100 * v.total) / Math.max(...d.by_day.map((x) => x.total)))}%`,
                      }}
                    />
                  </div>
                  <strong>{money(v.total)}</strong>
                </div>
              ))}
            </div>
          )}
          <p className="rating-note">
            Средна стойност на поръчка: {money(d.average)}
          </p>
        </section>
        <section className="admin-panel">
          <h2>Билети по филми</h2>
          {!d.by_movie.length ? (
            <p className="muted">Данните ще се появят след първата поръчка.</p>
          ) : (
            d.by_movie.map((v) => (
              <div className="admin-list-row" key={v.title}>
                <span>{v.title}</span>
                <strong>{v.tickets} билета</strong>
              </div>
            ))
          )}
        </section>
      </div>
      <section className="admin-panel">
        <h2>Последни поръчки</h2>
        {orders.error ? (
          <ErrorState error={orders.error} />
        ) : (
          <OrdersTable orders={orders.data?.slice(0, 8) || []} />
        )}
      </section>
      <p className="rating-note">
        Всички стойности са изчислени от записите в базата. Не са извършвани
        реални плащания.
      </p>
    </>
  );
}
function Scanner() {
  const [code, setCode] = useState(""),
    [showtime, setShowtime] = useState(""),
    [result, setResult] = useState(""),
    [error, setError] = useState("");
  const shows = useQuery({
    queryKey: ["validator-shows"],
    queryFn: () => api<Showtime[]>("/showtimes"),
  });
  return (
    <section className="admin-panel narrow">
      <ScanLine size={38} />
      <h2>Входен контрол с шестцифрен код</h2>
      <p className="muted">
        Избери прожекцията и въведи кода от билета. Успешната проверка го
        маркира като използван само веднъж — същата логика ще използва и
        клавиатурата на валидатора.
      </p>
      <form
        className="stack-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setError("");
          setResult("");
          try {
            const r = await api<{ valid: boolean; message: string }>(
              "/staff/tickets/validate",
              {
                method: "POST",
                body: JSON.stringify({
                  ticket_code: code,
                  showtime_id: Number(showtime),
                }),
              },
            );
            r.valid ? setResult(r.message) : setError(r.message);
          } catch (e) {
            setError((e as Error).message);
          }
        }}
      >
        <label>
          Прожекция
          <select
            aria-label="Прожекция за проверка"
            value={showtime}
            onChange={(e) => setShowtime(e.target.value)}
            required
          >
            <option value="">Избери прожекция…</option>
            {shows.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.movie.title} · {s.date} {s.time} · {s.cinema.name} ·{" "}
                {s.auditorium}
              </option>
            ))}
          </select>
        </label>
        <label>
          Код на билета
          <input
            className="validator-code-input"
            aria-label="Код на билета"
            inputMode="numeric"
            autoComplete="off"
            pattern="[0-9]{6}"
            minLength={6}
            maxLength={6}
            required
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            placeholder="000000"
          />
        </label>
        <button className="button" disabled={code.length !== 6 || !showtime}>
          <Check size={16} />
          Провери и използвай
        </button>
        {result && (
          <p className="success-text" role="status">
            {result}
          </p>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {shows.error && <ErrorState error={shows.error} />}
      </form>
    </section>
  );
}
function Manage({ section }: { section: string }) {
  const [edit, setEdit] = useState<Row | null>(null),
    [confirm, setConfirm] = useState<{ id: unknown; label: string } | null>(
      null,
    ),
    [details, setDetails] = useState<Row | null>(null),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(1);
  const client = useQueryClient();
  const toast = useToast();
  const q = useQuery({
    queryKey: [
      "admin",
      section,
      section === "users" ? search : "",
      section === "users" ? page : 1,
    ],
    queryFn: () =>
      api<Row[] | { items: Row[]; total: number }>(
        `/admin/${section}${section === "users" ? `?q=${encodeURIComponent(search)}&page=${page}` : ""}`,
      ),
  });
  const movies = useQuery({
    queryKey: ["admin", "movies-options"],
    queryFn: () => api<Movie[]>("/admin/movies"),
    enabled: ["movies", "showtimes"].includes(section),
  });
  const rooms = useQuery({
    queryKey: ["admin", "rooms-options"],
    queryFn: () => api<Room[]>("/admin/auditoriums"),
    enabled: ["showtimes", "auditoriums"].includes(section),
  });
  const cinemas = useQuery({
    queryKey: ["cinemas"],
    queryFn: () => api<Cinema[]>("/cinemas"),
  });
  const invalidate = async () => {
    await client.invalidateQueries({ queryKey: ["admin"] });
    client.invalidateQueries({ queryKey: ["cinemas"] });
    client.invalidateQueries({ queryKey: ["movies"] });
    client.invalidateQueries({ queryKey: ["home-movies"] });
    client.invalidateQueries({ queryKey: ["shows"] });
  };
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} retry={() => q.refetch()} />;
  const raw = Array.isArray(q.data) ? q.data : (q.data?.items ?? []);
  const rows =
    section === "users" || !search
      ? raw
      : raw.filter((r) =>
          JSON.stringify(r)
            .toLocaleLowerCase()
            .includes(search.toLocaleLowerCase()),
        );
  const addable = [
    "movies",
    "showtimes",
    "cinemas",
    "auditoriums",
    "promotions",
  ].includes(section);
  const columns: Record<string, string[]> = {
    movies: ["Заглавие", "Жанр", "Година", "Статус", "Действия"],
    showtimes: ["Филм", "Кино / зала", "Дата", "Час", "Цена", "Действия"],
    cinemas: ["Име", "Град", "Адрес", "Действия"],
    auditoriums: ["Име", "Кино", "Капацитет", "Формати"],
    orders: [
      "Поръчка",
      "Потребител",
      "Дата",
      "Сума",
      "Билети",
      "Статус",
      "Действия",
    ],
    users: ["Име", "Имейл", "Роля", "Статус", "Действия"],
    promotions: [
      "Код",
      "Предложение",
      "Отстъпка",
      "Минимум",
      "Активност",
      "Действия",
    ],
    "audit-logs": ["№", "Потребител", "Действие", "Обект", "Дата"],
  };
  const cell = (r: Row) => {
    switch (section) {
      case "movies":
        return [
          r.title,
          (r.genres as string[]).join(", "),
          r.year,
          r.status,
          <div className="table-actions">
            <button
              aria-label={`Редактирай ${r.title}`}
              onClick={() => setEdit(r)}
            >
              <Pencil size={15} />
            </button>
            <button
              aria-label={`Архивирай ${r.title}`}
              onClick={() => setConfirm({ id: r.id, label: String(r.title) })}
            >
              <Archive size={15} />
            </button>
          </div>,
        ];
      case "showtimes":
        return [
          (r.movie as Movie).title,
          `${(r.cinema as Cinema).name} / ${r.auditorium}`,
          dateLabel(String(r.starts_at)),
          r.time,
          money(Number(r.price)),
          <button
            className="text-link danger-text"
            disabled={!!r.cancelled}
            onClick={() => setConfirm({ id: r.id, label: `прожекция ${r.id}` })}
          >
            {r.cancelled ? "Отменена" : "Отмени"}
          </button>,
        ];
      case "cinemas":
        return [
          r.name,
          r.city,
          r.address,
          <Link className="text-link" to={`/cinemas/${r.slug}`}>
            Отвори
            <ArrowUpRight size={14} />
          </Link>,
        ];
      case "auditoriums":
        return [
          r.name,
          cinemas.data?.find((c) => c.id === r.cinema_id)?.name,
          r.capacity,
          (r.formats as string[]).join(", "),
        ];
      case "users":
        return [
          r.name,
          r.email,
          r.role,
          r.deletion_requested
            ? "Заявка за изтриване"
            : r.active
              ? "Активен"
              : "Неактивен",
          <button className="text-link" onClick={() => setEdit(r)}>
            Промени права
          </button>,
        ];
      case "promotions":
        return [
          r.code,
          r.title,
          `${r.percent}%`,
          money(Number(r.minimum)),
          r.active ? "Активен" : "Изключен",
          <button
            className="text-link danger-text"
            disabled={!r.active}
            onClick={() => setConfirm({ id: r.id, label: String(r.code) })}
          >
            Деактивирай
          </button>,
        ];
      case "audit-logs":
        return [
          r.id,
          r.user_id,
          r.action,
          r.object_id,
          dateLabel(String(r.created_at), true),
        ];
      default:
        return [];
    }
  };
  return (
    <section className="admin-panel">
      <div className="admin-toolbar">
        <div className="search-field">
          <Search size={17} />
          <input
            aria-label="Търсене в таблицата"
            placeholder="Търсене…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <span className="muted">{rows.length} записа</span>
        {addable && (
          <button className="button small" onClick={() => setEdit({})}>
            <Plus size={16} />
            Добави
          </button>
        )}
      </div>
      {section === "orders" ? (
        <OrdersTable
          orders={rows as unknown as (Booking & { user_email: string })[]}
          onDetails={(r) => setDetails(r as unknown as Row)}
        />
      ) : !rows.length ? (
        <Empty
          title="Все още няма записи"
          text="Добавените данни ще се появят тук."
        />
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {columns[section]?.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={String(r.id ?? i)}>
                  {cell(r).map((c, j) => (
                    <td key={j}>{c as React.ReactNode}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {section === "users" &&
        !Array.isArray(q.data) &&
        Number(q.data?.total) > 20 && (
          <div className="pagination">
            <button
              className="button secondary"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ArrowLeft size={15} />
            </button>
            <span>{page}</span>
            <button
              className="button secondary"
              disabled={page * 20 >= Number(q.data?.total)}
              onClick={() => setPage((p) => p + 1)}
            >
              <ArrowRight size={15} />
            </button>
          </div>
        )}
      {edit && (
        <Editor
          section={section}
          row={edit}
          movies={movies.data || []}
          rooms={rooms.data || []}
          cinemas={cinemas.data || []}
          close={() => setEdit(null)}
          done={async () => {
            setEdit(null);
            await invalidate();
            toast("Промените са записани.");
          }}
        />
      )}
      {confirm && (
        <Modal title="Потвърди действието" onClose={() => setConfirm(null)}>
          <p>Потвърждаваш ли промяната за „{confirm.label}“?</p>
          <p className="muted">Действието ще бъде записано в одитния журнал.</p>
          <button
            className="button"
            onClick={async () => {
              try {
                await api(`/admin/${section}/${confirm.id}`, {
                  method: "DELETE",
                });
                setConfirm(null);
                await invalidate();
                toast("Промяната е изпълнена.");
              } catch (e) {
                toast((e as Error).message);
              }
            }}
          >
            Потвърди
          </button>
        </Modal>
      )}
      {details && (
        <Modal title={`Поръчка ${details.id}`} onClose={() => setDetails(null)}>
          <p>
            {String(details.user_email)} · {money(Number(details.total))} ·{" "}
            {String(details.status)}
          </p>
          <h3>История</h3>
          {(details.events as Booking["events"]).map((v, i) => (
            <p key={i}>
              {v.status} ·{" "}
              {new Date(v.created_at).toLocaleString("bg-BG", {
                timeZone: "Europe/Sofia",
              })}
            </p>
          ))}
          <h3>Билети</h3>
          {(details.items as Booking["items"]).map((v) => (
            <p key={v.ticket_id}>
              Ред {v.row}, място {v.number} · {v.ticket_id}
            </p>
          ))}
        </Modal>
      )}
    </section>
  );
}
function OrdersTable({
  orders,
  onDetails,
}: {
  orders: (Booking & { user_email: string })[];
  onDetails?: (b: Booking & { user_email: string }) => void;
}) {
  return !orders.length ? (
    <p className="muted">Все още няма поръчки.</p>
  ) : (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {[
              "Поръчка",
              "Потребител",
              "Дата",
              "Сума",
              "Билети",
              "Статус",
              ...(onDetails ? ["Детайли"] : []),
            ].map((t) => (
              <th key={t}>{t}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {orders.map((b) => (
            <tr key={b.id}>
              <td>{b.id}</td>
              <td>{b.user_email}</td>
              <td>{dateLabel(b.created_at)}</td>
              <td>{money(b.total)}</td>
              <td>{b.items.length}</td>
              <td>
                <span
                  className={`status-badge ${b.status === "confirmed" ? "green" : ""}`}
                >
                  {b.status}
                </span>
              </td>
              {onDetails && (
                <td>
                  <button className="text-link" onClick={() => onDetails(b)}>
                    Виж
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
type Field = {
  key: string;
  label: string;
  type?: string;
  options?: { value: string | number; label: string }[];
  required?: boolean;
  min?: number;
  max?: number;
};
function Editor({
  section,
  row,
  movies,
  rooms,
  cinemas,
  close,
  done,
}: {
  section: string;
  row: Row;
  movies: Movie[];
  rooms: Room[];
  cinemas: Cinema[];
  close: () => void;
  done: () => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const existing = !!row.id;
  const fields: Record<string, Field[]> = {
    movies: [
      { key: "title", label: "Заглавие", required: true },
      { key: "slug", label: "Slug (на латиница, с тирета)", required: true },
      { key: "original_title", label: "Оригинално заглавие", required: true },
      {
        key: "description",
        label: "Описание",
        type: "textarea",
        required: true,
      },
      {
        key: "year",
        label: "Година",
        type: "number",
        min: 1900,
        max: 2100,
        required: true,
      },
      {
        key: "duration",
        label: "Продължителност (мин.)",
        type: "number",
        min: 1,
        max: 600,
        required: true,
      },
      {
        key: "genres",
        label: "Жанрове (разделени със запетая)",
        required: true,
      },
      { key: "director", label: "Режисьор" },
      { key: "cast", label: "Актьори (разделени със запетая)" },
      {
        key: "age",
        label: "Възраст",
        options: ["0+", "6+", "12+", "16+", "18+"].map((x) => ({
          value: x,
          label: x,
        })),
      },
      { key: "language", label: "Аудио" },
      { key: "subtitles", label: "Субтитри" },
      { key: "poster", label: "Постер (HTTPS URL)", type: "url" },
      { key: "backdrop", label: "Фон (HTTPS URL)", type: "url" },
      { key: "trailer", label: "YouTube video ID (11 символа)" },
      { key: "rating", label: "Демо рейтинг", type: "number", min: 0, max: 10 },
      {
        key: "release_date",
        label: "Оригинална премиера",
        type: "date",
        required: true,
      },
      {
        key: "status",
        label: "Статус",
        options: [
          { value: "active", label: "В киното" },
          { value: "upcoming", label: "Скоро" },
          { value: "archived", label: "Архив" },
        ],
      },
      { key: "featured", label: "Препоръчан филм", type: "checkbox" },
    ],
    showtimes: [
      {
        key: "movie_id",
        label: "Филм",
        options: movies.map((m) => ({ value: m.id, label: m.title })),
        required: true,
      },
      {
        key: "auditorium_id",
        label: "Зала",
        options: rooms.map((r) => ({
          value: r.id,
          label: `${cinemas.find((c) => c.id === r.cinema_id)?.name} · ${r.name}`,
        })),
        required: true,
      },
      {
        key: "starts_at",
        label: `Начало (${Intl.DateTimeFormat().resolvedOptions().timeZone})`,
        type: "datetime-local",
        required: true,
      },
      {
        key: "price",
        label: "Цена (€)",
        type: "number",
        min: 1,
        max: 500,
        required: true,
      },
      {
        key: "format",
        label: "Формат",
        options: ["2D", "IMAX", "3D", "4DX"].map((x) => ({
          value: x,
          label: x,
        })),
      },
    ],
    cinemas: [
      { key: "name", label: "Име", required: true },
      { key: "slug", label: "Slug", required: true },
      { key: "city", label: "Град", required: true },
      { key: "address", label: "Адрес", required: true },
      { key: "description", label: "Описание", type: "textarea" },
      { key: "image", label: "Изображение", type: "url" },
    ],
    auditoriums: [
      {
        key: "cinema_id",
        label: "Кино",
        options: cinemas.map((c) => ({ value: c.id, label: c.name })),
        required: true,
      },
      { key: "name", label: "Име на залата", required: true },
      {
        key: "rows",
        label: "Брой редове",
        type: "number",
        min: 1,
        max: 20,
        required: true,
      },
      {
        key: "seats_per_row",
        label: "Места на ред",
        type: "number",
        min: 4,
        max: 30,
        required: true,
      },
      { key: "formats", label: "Формати (2D, IMAX)", required: true },
    ],
    promotions: [
      { key: "code", label: "Код (главни латински букви)", required: true },
      { key: "title", label: "Име на офертата", required: true },
      {
        key: "percent",
        label: "Отстъпка (%)",
        type: "number",
        min: 1,
        max: 50,
        required: true,
      },
      { key: "minimum", label: "Минимална сума (€)", type: "number", min: 0 },
      {
        key: "starts_at",
        label: "Начало",
        type: "datetime-local",
        required: true,
      },
      { key: "ends_at", label: "Край", type: "datetime-local", required: true },
      {
        key: "max_uses",
        label: "Общ лимит",
        type: "number",
        min: 1,
        required: true,
      },
      {
        key: "per_user",
        label: "Лимит за потребител",
        type: "number",
        min: 1,
        required: true,
      },
      { key: "active", label: "Активна", type: "checkbox" },
    ],
    users: [
      {
        key: "role",
        label: "Роля",
        options: ["user", "staff", "admin"].map((x) => ({
          value: x,
          label: x,
        })),
      },
      { key: "active", label: "Активен профил", type: "checkbox" },
    ],
  };
  const defaults: Row = {
    year: 2026,
    duration: 120,
    rating: 0,
    age: "12+",
    language: "Английски",
    subtitles: "Български",
    status: "active",
    price: 12,
    rows: 7,
    seats_per_row: 12,
    formats: "2D, IMAX",
    minimum: 0,
    max_uses: 100,
    per_user: 2,
    active: true,
  };
  return (
    <Modal
      title={existing ? "Редакция на запис" : "Нов демонстрационен запис"}
      onClose={close}
      wide
    >
      <form
        className="editor-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setError("");
          setBusy(true);
          const data = new FormData(e.currentTarget);
          const payload: Row = {};
          for (const f of fields[section]) {
            const raw = data.get(f.key);
            payload[f.key] =
              f.type === "checkbox"
                ? raw === "on"
                : f.type === "number" || f.key.endsWith("_id")
                  ? Number(raw)
                  : ["genres", "cast", "formats"].includes(f.key)
                    ? String(raw || "")
                        .split(",")
                        .map((x) => x.trim())
                        .filter(Boolean)
                    : f.type === "datetime-local"
                      ? new Date(String(raw)).toISOString()
                      : String(raw || "");
          }
          try {
            await api(`/admin/${section}${existing ? `/${row.id}` : ""}`, {
              method: existing
                ? section === "users"
                  ? "PATCH"
                  : "PUT"
                : "POST",
              body: JSON.stringify(payload),
            });
            await done();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {fields[section]?.map((f) => {
          const value = row[f.key] ?? defaults[f.key] ?? "";
          return (
            <label
              key={f.key}
              className={
                f.type === "textarea"
                  ? "editor-full"
                  : f.type === "checkbox"
                    ? "checkbox-label"
                    : ""
              }
            >
              {f.type === "checkbox" ? (
                <>
                  <input
                    type="checkbox"
                    name={f.key}
                    defaultChecked={!!value}
                  />
                  {f.label}
                </>
              ) : (
                <>
                  {f.label}
                  {f.options ? (
                    <select
                      name={f.key}
                      defaultValue={String(value)}
                      required={f.required}
                    >
                      {!value && <option value="">Избери…</option>}
                      {f.options.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  ) : f.type === "textarea" ? (
                    <textarea
                      name={f.key}
                      defaultValue={String(value)}
                      required={f.required}
                      minLength={10}
                      rows={4}
                    />
                  ) : (
                    <input
                      name={f.key}
                      type={f.type || "text"}
                      defaultValue={
                        Array.isArray(value) ? value.join(", ") : String(value)
                      }
                      required={f.required}
                      min={f.min}
                      max={f.max}
                      step={f.type === "number" ? "0.1" : undefined}
                    />
                  )}
                </>
              )}
            </label>
          );
        })}
        {error && (
          <p className="form-error editor-full" role="alert">
            {error}
          </p>
        )}
        <div className="editor-full button-row">
          <button className="button" disabled={busy}>
            {busy ? "Записване…" : "Запази"}
            <Check size={16} />
          </button>
          <button type="button" className="button secondary" onClick={close}>
            <X size={16} />
            Откажи
          </button>
        </div>
      </form>
    </Modal>
  );
}
