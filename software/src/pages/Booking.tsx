import { useState, useEffect } from "react";
import { Link, useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { SimulatedCardPayment } from "../components/SimulatedCardPayment";
import {
  ArrowLeft,
  ArrowRight,
  Armchair,
  MapPin,
  Clock3,
  Check,
  ShieldCheck,
  Ticket,
  Printer,
  Download,
  Timer,
  Accessibility,
  CheckCircle2,
} from "lucide-react";
import { api, money, dateLabel } from "../lib/api";
import { useAuth, useToast } from "../lib/context";
import {
  Breadcrumb,
  Image,
  Loading,
  Empty,
  ErrorState,
} from "../components/UI";
import type { Seat, Showtime, Hold, Booking } from "../types";
function Steps({ step }: { step: number }) {
  return (
    <div className="booking-steps">
      {["Избери места", "Детайли и плащане", "Твоят билет"].map((s, i) => (
        <div className={step === i ? "active" : step > i ? "done" : ""} key={s}>
          <span>{step > i ? <Check size={14} /> : i + 1}</span>
          <p>{s}</p>
          {i < 2 && <i />}
        </div>
      ))}
    </div>
  );
}
function ShowSummary({ show }: { show: Showtime }) {
  return (
    <div className="booking-film">
      <Image src={show.movie.poster} alt={show.movie.title} />
      <div>
        <span className="eyebrow">
          {show.format} · {show.movie.age}
        </span>
        <h2>{show.movie.title}</h2>
        <p>
          <MapPin size={14} />
          {show.cinema.name}
        </p>
        <p>{show.auditorium}</p>
        <p>
          <Clock3 size={14} />
          {dateLabel(show.starts_at, true)} · {show.time}
        </p>
      </div>
    </div>
  );
}
export function Seats() {
  const { showtimeId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const toast = useToast();
  const [selected, setSelected] = useState<number[]>(() => {
      try {
        return JSON.parse(
          sessionStorage.getItem(`seats-${showtimeId}`) || "[]",
        );
      } catch {
        return [];
      }
    }),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const data = useQuery({
    queryKey: ["seats", showtimeId],
    queryFn: () =>
      api<{ showtime: Showtime; seats: Seat[]; max_seats: number }>(
        `/showtimes/${showtimeId}/seats`,
      ),
    refetchInterval: 10000,
    staleTime: 0,
  });
  useEffect(() => {
    sessionStorage.setItem(`seats-${showtimeId}`, JSON.stringify(selected));
  }, [selected, showtimeId]);
  const seats = data.data?.seats ?? [];
  const chosen = seats.filter((s) => selected.includes(s.id));
  const rows = [...new Set(seats.map((s) => s.row))];
  const proceed = async () => {
    if (!user) {
      toast("Влез в профила си, за да запазиш избраните места.");
      navigate("/login", { state: { from: `/booking/${showtimeId}/seats` } });
      return;
    }
    setBusy(true);
    setError("");
    try {
      const hold = await api<Hold>("/bookings/holds", {
        method: "POST",
        body: JSON.stringify({
          showtime_id: Number(showtimeId),
          seat_ids: selected,
        }),
      });
      sessionStorage.setItem("pukankov_hold", hold.id);
      sessionStorage.removeItem(`seats-${showtimeId}`);
      navigate("/checkout");
    } catch (e) {
      setError((e as Error).message);
      await data.refetch();
    } finally {
      setBusy(false);
    }
  };
  if (data.isLoading) return <Loading />;
  if (data.error || !data.data)
    return (
      <div className="container page">
        <ErrorState error={data.error} />
      </div>
    );
  const show = data.data.showtime;
  return (
    <div className="container page">
      <Breadcrumb
        items={[
          { label: show.movie.title, to: `/movies/${show.movie.slug}` },
          { label: "Избор на места" },
        ]}
      />
      <Steps step={0} />
      <div className="booking-layout">
        <div className="seat-panel">
          <div className="section-heading">
            <div>
              <span className="eyebrow">НАЙ-ДОБРОТО МЯСТО Е ТВОЕТО</span>
              <h1>
                Настани се удобно<span className="yellow-text">.</span>
              </h1>
            </div>
            <span className="hall-label">{show.auditorium}</span>
          </div>
          <p className="muted">
            Избери до {data.data.max_seats} места. Местата се задържат за 5
            минути след продължаване.
          </p>
          <div className="seat-scroll">
            <div className="seat-map">
              <div className="cinema-screen">
                <span>ЕКРАН</span>
              </div>
              <div className="seat-rows">
                {rows.map((row) => (
                  <div className="seat-row" key={row}>
                    <span className="row-label">{row}</span>
                    {seats
                      .filter((s) => s.row === row)
                      .map((s, i) => (
                        <button
                          key={s.id}
                          disabled={s.status !== "available"}
                          className={`seat ${s.category} ${selected.includes(s.id) ? "selected" : ""} ${s.status !== "available" ? "occupied" : ""} ${i === 5 ? "aisle" : ""}`}
                          title={`Ред ${s.row}, място ${s.number} · ${money(s.price)}${s.category === "premium" ? " · Премиум" : ""}`}
                          aria-label={`Ред ${s.row}, място ${s.number}, ${s.status === "available" ? "свободно" : "заето"}, ${money(s.price)}`}
                          aria-pressed={selected.includes(s.id)}
                          onClick={() => {
                            setError("");
                            if (selected.includes(s.id))
                              setSelected((v) => v.filter((id) => id !== s.id));
                            else if (selected.length < data.data!.max_seats)
                              setSelected((v) => [...v, s.id]);
                            else
                              toast(
                                `Избери максимум ${data.data!.max_seats} места.`,
                              );
                          }}
                        >
                          {s.accessible ? (
                            <Accessibility size={17} />
                          ) : selected.includes(s.id) ? (
                            <Check size={16} />
                          ) : s.status !== "available" ? (
                            <span>×</span>
                          ) : (
                            s.number
                          )}
                        </button>
                      ))}
                    <span className="row-label">{row}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="seat-legend">
            <span>
              <i />
              Свободно
            </span>
            <span>
              <i className="selected" />
              Избрано
            </span>
            <span>
              <i className="occupied" />
              Заето ×
            </span>
            <span>
              <i className="premium" />
              Премиум +3 €
            </span>
            <span>
              <Accessibility size={14} />
              Достъпно
            </span>
          </div>
          <div className="seat-note">
            <ShieldCheck size={17} />
            <p>
              Наличността се проверява отново при резервация. Програмата и
              покупката са демонстрационни.
            </p>
          </div>
        </div>
        <aside className="booking-sidebar">
          <ShowSummary show={show} />
          <div className="summary-divider" />
          <h3>
            Твоите места <span className="count-chip">{chosen.length}</span>
          </h3>
          {!chosen.length ? (
            <p className="muted">Избери своите места от схемата.</p>
          ) : (
            <div className="selected-seats">
              {chosen.map((s) => (
                <div key={s.id}>
                  <span>
                    <Armchair size={15} />
                    Ред {s.row}, място {s.number}
                    <small>
                      {s.category === "premium" ? "Премиум" : "Стандартен"}
                    </small>
                  </span>
                  <strong>{money(s.price)}</strong>
                </div>
              ))}
            </div>
          )}
          <div className="summary-total">
            <span>Общо</span>
            <strong>{money(chosen.reduce((n, s) => n + s.price, 0))}</strong>
          </div>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button
            className="button full"
            disabled={
              !chosen.length ||
              busy ||
              chosen.some((s) => s.status !== "available")
            }
            onClick={proceed}
          >
            {busy ? "Задържане на местата…" : "Продължи към поръчката"}
            <ArrowRight size={17} />
          </button>
          <Link
            className="back-link"
            to={`/movies/${show.movie.slug}#showtimes`}
          >
            <ArrowLeft size={14} />
            Избери друга прожекция
          </Link>
        </aside>
      </div>
    </div>
  );
}
export function Checkout() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const client = useQueryClient();
  const holdId = sessionStorage.getItem("pukankov_hold");
  const [code, setCode] = useState(""),
    [cardValid, setCardValid] = useState(false),
    [transactionSuccess, setTransactionSuccess] = useState(false),
    [failed, setFailed] = useState(false),
    [promo, setPromo] = useState<{
      code: string;
      discount: number;
      total: number;
    } | null>(null),
    [terms, setTerms] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [timeLeft, setTimeLeft] = useState(300);
  const hold = useQuery({
    queryKey: ["hold", holdId],
    queryFn: () => api<Hold>(`/bookings/holds/${holdId}`),
    enabled: !!user && !!holdId,
    staleTime: 0,
    refetchInterval: 15000,
  });
  useEffect(() => {
    if (!hold.data) return;
    const offset = Date.parse(hold.data.server_time) - Date.now();
    const tick = () =>
      setTimeLeft(
        Math.max(
          0,
          Math.ceil(
            (Date.parse(hold.data!.expires_at) - Date.now() - offset) / 1000,
          ),
        ),
      );
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [hold.data]);
  if (loading) return <Loading />;
  if (!user) return <SignIn />;
  if (!holdId)
    return (
      <div className="container page">
        <Empty
          title="Твоята история започва с филм"
          text="Първо избери прожекция и места."
          action={
            <Link className="button" to="/showtimes">
              Към програмата
            </Link>
          }
        />
      </div>
    );
  if (hold.isLoading) return <Loading />;
  if (hold.error || !hold.data)
    return (
      <div className="container page">
        <ErrorState error={hold.error} />
      </div>
    );
  const h = hold.data;
  const paymentFailed = failed || h.status === "cancelled";
  const expired = timeLeft <= 0 || h.status !== "active";
  const pay = async () => {
    setBusy(true);
    setError("");
    try {
      const b = await api<Booking>("/payments/checkout", {
        method: "POST",
        body: JSON.stringify({
          hold_id: h.id,
          promo_code: promo?.code || "",
          terms,
          transaction_success: transactionSuccess,
        }),
      });
      if (b.status !== "confirmed") {
        setFailed(true);
        setError(
          "Транзакцията е отказана. Не е издаден билет. Местата са освободени — избери ги отново, за да повториш плащането.",
        );
        client.invalidateQueries({ queryKey: ["hold", holdId] });
        return;
      }
      sessionStorage.removeItem("pukankov_hold");
      client.invalidateQueries({ queryKey: ["tickets"] });
      navigate(`/booking/success/${b.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="container page">
      <Steps step={1} />
      <div className="page-heading">
        <span className="eyebrow">ОСТАВА САМО ЕДНА СТЪПКА</span>
        <h1>
          Твоята кино вечер<span className="yellow-text">.</span>
        </h1>
      </div>
      <div className="booking-layout checkout-layout">
        <div>
          <div className={`hold-timer ${expired ? "expired" : ""}`}>
            <Timer size={22} />
            <div>
              <strong>
                {paymentFailed
                  ? "Плащането е отказано"
                  : expired
                    ? "Задържането на местата е изтекло"
                    : "Твоите места те очакват"}
              </strong>
              <p>
                {paymentFailed
                  ? "Местата са освободени. Можеш да започнеш нова покупка."
                  : expired
                    ? "Избери местата отново, за да продължиш."
                    : "Завърши поръчката преди изтичане на времето."}
              </p>
            </div>
            <b>
              {String(Math.floor(timeLeft / 60)).padStart(2, "0")}:
              {String(timeLeft % 60).padStart(2, "0")}
            </b>
          </div>
          <div className="checkout-card">
            <h2>Данни за поръчката</h2>
            <div className="customer-summary">
              <UserSummary name={user.name} email={user.email} />
              <Link to="/profile" className="text-link">
                Моят профил
              </Link>
            </div>
          </div>
          <div className="checkout-card">
            <h2>Имаш промокод?</h2>
            <form
              className="promo-form"
              onSubmit={async (e) => {
                e.preventDefault();
                setError("");
                try {
                  const p = await api<{
                    code: string;
                    discount: number;
                    total: number;
                  }>("/promotions/validate", {
                    method: "POST",
                    body: JSON.stringify({ hold_id: h.id, code }),
                  });
                  setPromo(p);
                  toast("Демонстрационната отстъпка е приложена.");
                } catch (e) {
                  setPromo(null);
                  setError((e as Error).message);
                }
              }}
            >
              <input
                aria-label="Промокод"
                value={code}
                onChange={(e) => {
                  setCode(e.target.value.toUpperCase());
                  setPromo(null);
                }}
                placeholder="Въведи промокод"
              />
              <button className="button secondary" disabled={expired || !code}>
                Приложи
              </button>
            </form>
            {promo && (
              <p className="success-text">
                <CheckCircle2 size={16} />
                {promo.code} · −{money(promo.discount)}
              </p>
            )}
          </div>
          <div className="checkout-card">
            <SimulatedCardPayment
              transactionSuccess={transactionSuccess}
              onTransactionSuccess={setTransactionSuccess}
              onValidChange={setCardValid}
            />
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={terms}
                onChange={(e) => setTerms(e.target.checked)}
              />
              <span>
                Приемам{" "}
                <Link to="/terms" target="_blank">
                  общите условия
                </Link>{" "}
                и разбирам, че плащането е учебна симулация.
              </span>
            </label>
          </div>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          {paymentFailed && (
            <Link
              className="button secondary"
              to={`/booking/${h.showtime.id}/seats`}
            >
              Избери местата отново
              <ArrowRight size={16} />
            </Link>
          )}
        </div>
        <aside className="booking-sidebar">
          <ShowSummary show={h.showtime} />
          <div className="summary-divider" />
          <h3>Твоите места</h3>
          <div className="selected-seats">
            {h.items.map((s) => (
              <div key={s.id}>
                <span>
                  Ред {s.row}, място {s.number}
                </span>
                <strong>{money(s.price)}</strong>
              </div>
            ))}
          </div>
          {promo && (
            <div className="discount-line">
              <span>Отстъпка · {promo.code}</span>
              <strong>−{money(promo.discount)}</strong>
            </div>
          )}
          <div className="summary-total">
            <span>Общо</span>
            <strong>{money(promo?.total ?? h.total)}</strong>
          </div>
          <button
            className="button full"
            disabled={!terms || !cardValid || busy || expired || paymentFailed}
            onClick={pay}
          >
            {busy
              ? "Обработка на плащането…"
              : `Плати ${money(promo?.total ?? h.total)}`}
            <ArrowRight size={17} />
          </button>
          <button
            className="back-link"
            onClick={async () => {
              try {
                await api(`/bookings/holds/${h.id}`, { method: "DELETE" });
                sessionStorage.removeItem("pukankov_hold");
                navigate(`/booking/${h.showtime.id}/seats`);
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Откажи и освободи местата
          </button>
          <p className="safe-label">
            <ShieldCheck size={13} />
            Не се извършва реално плащане
          </p>
        </aside>
      </div>
    </div>
  );
}
function UserSummary({ name, email }: { name: string; email: string }) {
  return (
    <div className="user-summary">
      <span>{name[0]}</span>
      <div>
        <strong>{name}</strong>
        <p>{email}</p>
      </div>
    </div>
  );
}
function SignIn() {
  const location = useLocation();
  return (
    <div className="container page">
      <Empty
        title="Твоето кино пространство"
        text="Влез в профила си, за да видиш и запазиш своите билети."
        action={
          <Link
            to="/login"
            state={{ from: location.pathname }}
            className="button"
          >
            Влез в профила си
            <ArrowRight size={16} />
          </Link>
        }
      />
    </div>
  );
}
export function BookingSuccess() {
  const { bookingId } = useParams();
  const { user, loading } = useAuth();
  const query = useQuery({
    queryKey: ["booking", bookingId],
    queryFn: () => api<Booking>(`/bookings/${bookingId}`),
    enabled: !!user,
  });
  if (loading || (query.isLoading && user)) return <Loading />;
  if (!user) return <SignIn />;
  if (query.error || !query.data)
    return (
      <div className="container page">
        <ErrorState error={query.error} />
      </div>
    );
  const b = query.data;
  return (
    <div className="container page success-page">
      <Steps step={2} />
      <div className="success-heading">
        <span className="success-icon">
          <Check size={29} />
        </span>
        <span className="eyebrow">ГОЛЕМИЯТ ЕКРАН ТЕ ОЧАКВА</span>
        <h1>
          {b.status === "confirmed"
            ? "Мястото ти е запазено."
            : "Поръчката не е потвърдена."}
        </h1>
        <p>Поръчка {b.id} · Плащане чрез учебния картов симулатор</p>
      </div>
      <div className="ticket-list">
        {b.items.map((item) => (
          <TicketView key={item.ticket_id} booking={b} item={item} />
        ))}
      </div>
      <div className="success-actions">
        <button className="button" onClick={() => window.print()}>
          <Printer size={17} />
          Печат / Запази като PDF
        </button>
        <Link className="button secondary" to="/my-tickets">
          <Ticket size={17} />
          Моите билети
        </Link>
      </div>
      <p className="muted center">
        Билетите са записани в профила ти. Имейл не е изпратен от
        демонстрационната среда.
      </p>
    </div>
  );
}
export function TicketView({
  booking: b,
  item,
}: {
  booking: Booking;
  item: Booking["items"][number];
}) {
  return (
    <article className="electronic-ticket">
      <div className="ticket-art">
        <Image src={b.showtime.movie.poster} alt={b.showtime.movie.title} />
      </div>
      <div className="ticket-body">
        <div className="ticket-brand">
          <span>ПУКАНКОВ.</span>
          <span className="demo-label">ЕЛЕКТРОНЕН БИЛЕТ</span>
        </div>
        <h2>{b.showtime.movie.title}</h2>
        <p>
          {b.showtime.cinema.name} · {b.showtime.auditorium}
        </p>
        <div className="ticket-facts">
          <div>
            <span>ДАТА</span>
            <strong>{dateLabel(b.showtime.starts_at)}</strong>
          </div>
          <div>
            <span>ЧАС</span>
            <strong>{b.showtime.time}</strong>
          </div>
          <div>
            <span>РЕД</span>
            <strong>{item.row}</strong>
          </div>
          <div>
            <span>МЯСТО</span>
            <strong>{item.number}</strong>
          </div>
        </div>
        <span className="ticket-id">
          {b.id} · {item.ticket_id} · {item.used_at ? "ИЗПОЛЗВАН" : "ВАЛИДЕН"}
        </span>
      </div>
      <div className="ticket-code-panel">
        <span>КОД НА БИЛЕТА</span>
        <code
          className="ticket-code"
          aria-label={`Код на билета ${item.ticket_code}`}
        >
          {item.ticket_code}
        </code>
        <span>ВЪВЕДИ НА КЛАВИАТУРАТА НА ВХОДА</span>
        <strong>{money(item.price)}</strong>
      </div>
    </article>
  );
}
export function MyTickets() {
  const { user, loading } = useAuth();
  const data = useQuery({
    queryKey: ["tickets", user?.id],
    queryFn: () => api<Booking[]>("/me/tickets"),
    enabled: !!user,
  });
  if (loading) return <Loading />;
  if (!user) return <SignIn />;
  return (
    <div className="container page">
      <Breadcrumb items={[{ label: "Моите билети" }]} />
      <div className="page-heading">
        <span className="eyebrow">ТВОИТЕ СЛЕДВАЩИ ПРИКЛЮЧЕНИЯ</span>
        <h1>
          Моите билети<span className="yellow-text">.</span>
        </h1>
        <p>Всичките ти кино истории на едно място.</p>
      </div>
      {data.isLoading ? (
        <Loading />
      ) : data.error ? (
        <ErrorState error={data.error} />
      ) : !data.data?.length ? (
        <Empty
          title="Първата история те очаква"
          text="Все още нямаш демонстрационни билети. Открий следващия си любим филм."
          action={
            <Link className="button" to="/showtimes">
              Намери прожекция
              <ArrowRight size={16} />
            </Link>
          }
        />
      ) : (
        <div className="my-bookings">
          {data.data.map((b) => (
            <div className="booking-group" key={b.id}>
              <div className="section-heading">
                <span className="muted">
                  {b.id} · {dateLabel(b.created_at, true)} ·{" "}
                  {b.status === "confirmed" ? "Потвърдена" : "Отказана"}
                </span>
                {b.status === "confirmed" && (
                  <Link className="text-link" to={`/booking/success/${b.id}`}>
                    <Download size={15} />
                    Отвори / Печат
                  </Link>
                )}
              </div>
              {b.items.map((item) => (
                <TicketView key={item.ticket_id} booking={b} item={item} />
              ))}
              {!b.items.length && (
                <p className="muted">Няма издадени билети за тази поръчка.</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
