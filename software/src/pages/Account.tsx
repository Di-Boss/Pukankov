import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Eye,
  EyeOff,
  Ticket,
  Heart,
  LogOut,
  ShieldCheck,
  Download,
} from "lucide-react";
import { api } from "../lib/api";
import { useAuth, useToast } from "../lib/context";
import {
  Breadcrumb,
  Loading,
  Empty,
  ErrorState,
  Modal,
} from "../components/UI";
import { MovieCard } from "../components/MovieCard";
import type { Movie, User } from "../types";
const formSchema = z.object({
  name: z.string().optional(),
  email: z.string().email("Въведи валиден имейл."),
  password: z.string().min(1, "Въведи парола.").max(64, "Максимум 64 символа."),
  confirm: z.string().optional(),
  terms: z.boolean().optional(),
});
type Fields = z.infer<typeof formSchema>;
export function AuthPage({
  register: registerMode = false,
}: {
  register?: boolean;
}) {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState(""),
    [visible, setVisible] = useState(false);
  const form = useForm<Fields>({
    resolver: zodResolver(formSchema),
    defaultValues: { terms: false },
  });
  const submit = form.handleSubmit(async (data) => {
    setError("");
    if (registerMode) {
      if (!data.name || data.name.trim().length < 2) {
        form.setError("name", { message: "Въведи име и фамилия." });
        return;
      }
      if (data.password.length < 10) {
        form.setError("password", {
          message: "Паролата трябва да има поне 10 символа.",
        });
        return;
      }
      if (data.password !== data.confirm) {
        form.setError("confirm", { message: "Паролите не съвпадат." });
        return;
      }
      if (!data.terms) {
        form.setError("terms", { message: "Приеми общите условия." });
        return;
      }
    }
    try {
      await api<User>(`/auth/${registerMode ? "register" : "login"}`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      await refresh();
      navigate(
        (location.state as { from?: string } | null)?.from || "/profile",
        { replace: true },
      );
    } catch (e) {
      setError((e as Error).message);
    }
  });
  return (
    <div className="auth-page">
      <div className="auth-art">
        <div className="auth-art-overlay" />
        <div>
          <span className="eyebrow">ПУКАНКОВ · ТВОЯТ КИНО СВЯТ</span>
          <h2>
            Всяка голяма
            <br />
            история започва
            <br />с едно <span>„хайде“.</span>
          </h2>
          <p>Любимите филми. Твоите места. Големите емоции.</p>
        </div>
      </div>
      <div className="auth-form-wrap">
        <span className="eyebrow">ДОБРЕ ДОШЪЛ В КИНОТО</span>
        <h1>
          {registerMode
            ? "Твоята история започва тук."
            : "Радваме се да те видим."}
        </h1>
        <p className="muted">
          {registerMode
            ? "Създай профил и открий следващото си приключение."
            : "Влез за своите билети, любими филми и още кино."}
        </p>
        <form onSubmit={submit} className="stack-form" noValidate>
          {registerMode && (
            <label>
              Име и фамилия
              <input
                autoComplete="name"
                {...form.register("name")}
                placeholder="Как да те наричаме?"
              />
              {form.formState.errors.name && (
                <small className="form-error">
                  {form.formState.errors.name.message}
                </small>
              )}
            </label>
          )}
          <label>
            Имейл адрес
            <input
              type="email"
              autoComplete="email"
              {...form.register("email")}
              placeholder="you@example.com"
            />
            {form.formState.errors.email && (
              <small className="form-error">
                {form.formState.errors.email.message}
              </small>
            )}
          </label>
          <label>
            Парола
            <div className="password-input">
              <input
                type={visible ? "text" : "password"}
                autoComplete={
                  registerMode ? "new-password" : "current-password"
                }
                {...form.register("password")}
                placeholder={
                  registerMode ? "Поне 10 символа" : "Въведи паролата си"
                }
              />
              <button
                type="button"
                aria-label={visible ? "Скрий паролата" : "Покажи паролата"}
                onClick={() => setVisible(!visible)}
              >
                {visible ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {form.formState.errors.password && (
              <small className="form-error">
                {form.formState.errors.password.message}
              </small>
            )}
          </label>
          {registerMode ? (
            <>
              <label>
                Потвърди паролата
                <input
                  type="password"
                  autoComplete="new-password"
                  {...form.register("confirm")}
                  placeholder="Още веднъж, за сигурност"
                />
                {form.formState.errors.confirm && (
                  <small className="form-error">
                    {form.formState.errors.confirm.message}
                  </small>
                )}
              </label>
              <label className="checkbox-label">
                <input type="checkbox" {...form.register("terms")} />
                <span>
                  Приемам{" "}
                  <Link to="/terms" target="_blank">
                    общите условия
                  </Link>{" "}
                  и съм запознат с{" "}
                  <Link to="/privacy" target="_blank">
                    политиката за поверителност
                  </Link>
                  .
                </span>
              </label>
              {form.formState.errors.terms && (
                <small className="form-error">
                  {form.formState.errors.terms.message}
                </small>
              )}
            </>
          ) : (
            <Link to="/forgot-password" className="forgot-link">
              Забравена парола?
            </Link>
          )}
          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}
          <button
            className="button full"
            disabled={form.formState.isSubmitting}
          >
            {form.formState.isSubmitting
              ? "Момент…"
              : registerMode
                ? "Създай профил"
                : "Влез в профила си"}
            <ArrowRight size={17} />
          </button>
        </form>
        <p className="auth-switch">
          {registerMode ? "Вече имаш профил?" : "За първи път си тук?"}{" "}
          <Link
            state={location.state}
            to={registerMode ? "/login" : "/register"}
          >
            {registerMode ? "Влез" : "Създай профил"}
          </Link>
        </p>
        <p className="safe-label">
          <ShieldCheck size={14} />
          Сигурна сесия · Демонстрационна платформа
        </p>
      </div>
    </div>
  );
}
export function ForgotPassword() {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [message, setMessage] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <div className="container page narrow">
      <Breadcrumb
        items={[
          { label: "Вход", to: "/login" },
          { label: "Възстановяване на парола" },
        ]}
      />
      <div className="page-heading">
        <span className="eyebrow">ОБРАТНО КЪМ ХУБАВИТЕ ИСТОРИИ</span>
        <h1>{token ? "Нова парола" : "Забравена парола?"}</h1>
        <p>
          {token
            ? "Избери нова парола с поне 10 символа."
            : "Въведи имейла на профила си, за да поискаш инструкции."}
        </p>
      </div>
      <form
        className="stack-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setError("");
          setBusy(true);
          try {
            const r = await api<{
              message: string;
              email_configured?: boolean;
            }>(token ? "/auth/reset-password" : "/auth/forgot-password", {
              method: "POST",
              body: JSON.stringify(token ? { token, password } : { email }),
            });
            setMessage(
              r.message +
                (r.email_configured === false
                  ? " Имейл услугата не е настроена в тази демонстрация."
                  : ""),
            );
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {token ? (
          <label>
            Нова парола
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              minLength={10}
              maxLength={64}
              required
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
        ) : (
          <label>
            Имейл адрес
            <input
              type="email"
              value={email}
              required
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
        )}
        {message && (
          <p className="notice" role="status">
            {message}
          </p>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button className="button" disabled={busy}>
          {busy
            ? "Момент…"
            : token
              ? "Запази новата парола"
              : "Поискай инструкции"}
          <ArrowRight size={16} />
        </button>
        <Link to="/login" className="text-link">
          Обратно към входа
        </Link>
      </form>
    </div>
  );
}
export function Favorites() {
  const { user, loading } = useAuth();
  const data = useQuery({
    queryKey: ["favorites", user?.id],
    queryFn: () => api<Movie[]>("/me/favorites"),
    enabled: !!user,
  });
  return (
    <div className="container page">
      <Breadcrumb items={[{ label: "Любими филми" }]} />
      <div className="page-heading">
        <span className="eyebrow">ИСТОРИИТЕ, КОИТО СИ ИЗБРАЛ</span>
        <h1>
          Събрани за теб<span className="yellow-text">.</span>
        </h1>
        <p>Твоят личен списък с кино, което си струва.</p>
      </div>
      {loading ? (
        <Loading />
      ) : !user ? (
        <Empty
          title="Запази добрите истории"
          text="Влез в профила си, за да събереш любимите си филми."
          action={
            <Link className="button" to="/login" state={{ from: "/favorites" }}>
              Вход
              <ArrowRight size={16} />
            </Link>
          }
        />
      ) : data.isLoading ? (
        <Loading />
      ) : data.error ? (
        <ErrorState error={data.error} />
      ) : !data.data?.length ? (
        <Empty
          title="Тук ще живеят любимите ти филми"
          text="Докосни сърцето върху постер, за да добавиш първия."
          action={
            <Link className="button" to="/movies">
              Разгледай филмите
            </Link>
          }
        />
      ) : (
        <div className="movie-grid catalog-grid">
          {data.data.map((m) => (
            <MovieCard movie={m} key={m.id} />
          ))}
        </div>
      )}
    </div>
  );
}
export function Profile() {
  const { user, loading, refresh, logout } = useAuth();
  const [name, setName] = useState(""),
    [error, setError] = useState(""),
    [deleteOpen, setDeleteOpen] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();
  if (loading) return <Loading />;
  if (!user)
    return (
      <div className="container page">
        <Empty
          title="Твоят кино профил"
          text="Влез, за да управляваш профила и билетите си."
          action={
            <Link className="button" to="/login">
              Вход
            </Link>
          }
        />
      </div>
    );
  return (
    <div className="container page">
      <Breadcrumb items={[{ label: "Моят профил" }]} />
      <div className="profile-heading">
        <div className="profile-avatar">{user.name[0]}</div>
        <div>
          <span className="eyebrow">ТВОЯТ ЛИЧЕН КИНО СВЯТ</span>
          <h1>
            Здравей, {user.name.split(" ")[0]}
            <span className="yellow-text">.</span>
          </h1>
          <p className="muted">
            Следващата добра история е на един билет разстояние.
          </p>
        </div>
      </div>
      <div className="profile-links">
        <Link to="/my-tickets">
          <Ticket />
          <strong>Моите билети</strong>
          <ArrowRight size={18} />
        </Link>
        <Link to="/favorites">
          <Heart />
          <strong>Любими филми</strong>
          <ArrowRight size={18} />
        </Link>
        {user.role === "admin" && (
          <Link to="/admin">
            <ShieldCheck />
            <strong>Администрация</strong>
            <ArrowRight size={18} />
          </Link>
        )}
      </div>
      <div className="profile-columns">
        <section className="checkout-card">
          <h2>Лична информация</h2>
          <form
            className="stack-form"
            onSubmit={async (e) => {
              e.preventDefault();
              setError("");
              try {
                await api("/me", {
                  method: "PATCH",
                  body: JSON.stringify({ name: name || user.name }),
                });
                await refresh();
                toast("Профилът е обновен.");
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            <label>
              Име и фамилия
              <input
                value={name || user.name}
                minLength={2}
                maxLength={100}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label>
              Имейл адрес
              <input value={user.email} readOnly />
            </label>
            <button className="button">Запази промените</button>
          </form>
        </section>
        <section className="checkout-card">
          <h2>Сигурност</h2>
          <form
            className="stack-form"
            onSubmit={async (e) => {
              e.preventDefault();
              const passwordForm = e.currentTarget;
              const f = new FormData(passwordForm);
              setError("");
              try {
                await api("/me/password", {
                  method: "POST",
                  body: JSON.stringify(Object.fromEntries(f)),
                });
                passwordForm.reset();
                toast("Паролата е променена.");
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            <label>
              Текуща парола
              <input
                type="password"
                name="current_password"
                autoComplete="current-password"
                required
              />
            </label>
            <label>
              Нова парола
              <input
                type="password"
                name="password"
                autoComplete="new-password"
                minLength={10}
                maxLength={64}
                required
              />
            </label>
            <button className="button secondary">Промени паролата</button>
          </form>
        </section>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="profile-privacy">
        <h3>Твоите данни. Твоят контрол.</h3>
        <p className="muted">
          Изтегли копие на профила и поръчките си или заяви изтриване за преглед
          от администратора.
        </p>
        <div className="button-row">
          <button
            className="button secondary"
            onClick={async () => {
              try {
                const d = await api("/me/export");
                const u = URL.createObjectURL(
                  new Blob([JSON.stringify(d, null, 2)], {
                    type: "application/json",
                  }),
                );
                const a = document.createElement("a");
                a.href = u;
                a.download = "pukankov-my-data.json";
                a.click();
                URL.revokeObjectURL(u);
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            <Download size={16} />
            Изтегли данните
          </button>
          <button
            className="text-link danger-text"
            disabled={user.deletion_requested}
            onClick={() => setDeleteOpen(true)}
          >
            {user.deletion_requested
              ? "Заявката за изтриване е записана"
              : "Заяви изтриване на профила"}
          </button>
          <button
            className="text-link"
            onClick={async () => {
              await logout();
              navigate("/");
            }}
          >
            <LogOut size={16} />
            Изход
          </button>
        </div>
      </div>
      {deleteOpen && (
        <Modal
          title="Заявка за изтриване на профила"
          onClose={() => setDeleteOpen(false)}
        >
          <p>
            Ще запишем заявката за административен преглед. Профилът няма да
            бъде изтрит автоматично.
          </p>
          <button
            className="button"
            onClick={async () => {
              try {
                const r = await api<{ message: string }>("/me", {
                  method: "DELETE",
                });
                toast(r.message);
                await refresh();
                setDeleteOpen(false);
              } catch (e) {
                toast((e as Error).message);
              }
            }}
          >
            Изпрати заявка
          </button>
        </Modal>
      )}
    </div>
  );
}
