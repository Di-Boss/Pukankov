import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { MapPin, ArrowUpRight, Ticket } from "lucide-react";
import { api, money, dateLabel } from "../lib/api";
import {
  Breadcrumb,
  Image,
  Loading,
  ErrorState,
  Empty,
} from "../components/UI";
import type { Cinema, MovieList, Showtime } from "../types";
export function Showtimes() {
  return (
    <div className="container page">
      <Breadcrumb items={[{ label: "Прожекции" }]} />
      <div className="page-heading">
        <span className="eyebrow">ДОБЪР ДЕН ЗА ГОЛЯМО КИНО</span>
        <h1>
          Твоето време за кино<span className="yellow-text">.</span>
        </h1>
        <p>Избери история, намери удобно време и се настани.</p>
      </div>
      <ShowtimeList />
    </div>
  );
}
export function ShowtimeList({
  movieId,
  cinemaId,
}: {
  movieId?: number;
  cinemaId?: number;
}) {
  const [params, setParams] = useSearchParams();
  const [localDate, setLocalDate] = useState("");
  const chosenCinema = cinemaId
    ? String(cinemaId)
    : params.get("cinema_id") || "";
  const chosenMovie = movieId ? String(movieId) : params.get("movie_id") || "";
  const chosenDate = localDate || params.get("date") || "";
  const cinemas = useQuery({
    queryKey: ["cinemas"],
    queryFn: () => api<Cinema[]>("/cinemas"),
    staleTime: 300000,
  });
  const movies = useQuery({
    queryKey: ["quick-movies"],
    queryFn: () => api<MovieList>("/movies?status=active&page_size=50"),
  });
  const shows = useQuery({
    queryKey: ["shows", chosenCinema, chosenMovie, params.get("from_hour")],
    queryFn: () => {
      const p = new URLSearchParams();
      if (chosenCinema) p.set("cinema_id", chosenCinema);
      if (chosenMovie) p.set("movie_id", chosenMovie);
      if (params.get("from_hour")) p.set("from_hour", params.get("from_hour")!);
      return api<Showtime[]>(`/showtimes?${p}`);
    },
    refetchInterval: 60000,
  });
  const dates = [...new Set(shows.data?.map((s) => s.date))];
  const effectiveDate = chosenDate || dates[0];
  const filtered = shows.data?.filter((s) => s.date === effectiveDate) ?? [];
  const grouped = Object.values(
    filtered.reduce<
      Record<string, { movie: Showtime["movie"]; shows: Showtime[] }>
    >((acc, s) => {
      const key = String(s.movie_id);
      if (!acc[key]) acc[key] = { movie: s.movie, shows: [] };
      acc[key].shows.push(s);
      return acc;
    }, {}),
  );
  const update = (k: string, v: string) => {
    setLocalDate("");
    setParams(
      (p) => {
        v ? p.set(k, v) : p.delete(k);
        p.delete("date");
        return p;
      },
      { replace: true },
    );
  };
  return (
    <div className="showtime-module">
      <div className="showtime-filters">
        {!cinemaId && (
          <label>
            <MapPin size={17} />
            <select
              aria-label="Кино"
              value={chosenCinema}
              onChange={(e) => update("cinema_id", e.target.value)}
            >
              <option value="">Всички кина</option>
              {cinemas.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} · {c.city}
                </option>
              ))}
            </select>
          </label>
        )}
        {!movieId && (
          <label>
            <Ticket size={17} />
            <select
              aria-label="Филм"
              value={chosenMovie}
              onChange={(e) => update("movie_id", e.target.value)}
            >
              <option value="">Всички филми</option>
              {movies.data?.items.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.title}
                </option>
              ))}
            </select>
          </label>
        )}
        <select
          aria-label="Часов диапазон"
          value={params.get("from_hour") || ""}
          onChange={(e) => update("from_hour", e.target.value)}
        >
          <option value="">По всяко време</option>
          <option value="16">След 16:00</option>
          <option value="19">Вечер · след 19:00</option>
        </select>
        <span className="demo-label">ПРИМЕРНА ПРОГРАМА</span>
      </div>
      <div className="date-tabs">
        {dates.map((d, i) => (
          <button
            key={d}
            className={d === effectiveDate ? "active" : ""}
            onClick={() => {
              setLocalDate(d);
              setParams(
                (p) => {
                  p.set("date", d);
                  return p;
                },
                { replace: true },
              );
            }}
          >
            <span>
              {i === 0
                ? "Най-близка дата"
                : new Intl.DateTimeFormat("bg-BG", { weekday: "long" }).format(
                    new Date(d + "T12:00:00"),
                  )}
            </span>
            <strong>{dateLabel(d)}</strong>
          </button>
        ))}
      </div>
      {shows.isLoading ? (
        <Loading />
      ) : shows.error ? (
        <ErrorState error={shows.error} retry={() => shows.refetch()} />
      ) : !filtered.length ? (
        <Empty
          title="Още подготвяме следващата прожекция"
          text="За този избор няма конфигурирани бъдещи прожекции. Опитай друго кино или филм."
        />
      ) : (
        <div className="showtime-results">
          {grouped.map((g) => (
            <article className="showtime-movie" key={g.movie.id}>
              {!movieId && (
                <Link
                  className="showtime-poster"
                  to={`/movies/${g.movie.slug}`}
                >
                  <Image src={g.movie.poster} alt={g.movie.title} />
                </Link>
              )}
              <div className="showtime-movie-body">
                {!movieId && (
                  <>
                    <Link to={`/movies/${g.movie.slug}`}>
                      <h2>{g.movie.title}</h2>
                    </Link>
                    <p className="muted">
                      {g.movie.genres.join(" / ")} · {g.movie.duration} мин. ·{" "}
                      {g.movie.age}
                    </p>
                  </>
                )}
                <div className="showtime-slots">
                  {g.shows.map((s) => (
                    <Link
                      className="showtime-slot"
                      key={s.id}
                      to={`/booking/${s.id}/seats`}
                    >
                      <div>
                        <strong>{s.time}</strong>
                        <span>{s.format}</span>
                      </div>
                      <p>{s.cinema.name}</p>
                      <small>
                        {s.auditorium} · {s.movie.language}
                      </small>
                      <div className="slot-bottom">
                        <span>от {money(s.price)}</span>
                        <ArrowUpRight size={17} />
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
