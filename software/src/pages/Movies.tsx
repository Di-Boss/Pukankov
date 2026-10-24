import { useState, useEffect, useCallback } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  SlidersHorizontal,
  Star,
  Clock3,
  Play,
  Ticket,
  ArrowLeft,
  ArrowRight,
} from "lucide-react";
import { api, duration } from "../lib/api";
import { MovieCard, FavoriteButton } from "../components/MovieCard";
import {
  Breadcrumb,
  Loading,
  ErrorState,
  Empty,
  Image,
  SectionTitle,
} from "../components/UI";
import { Trailer } from "./Home";
import { ShowtimeList } from "./Showtimes";
import type { Movie, MovieList } from "../types";
const genres = [
  "Екшън",
  "Комедия",
  "Драма",
  "Трилър",
  "Ужаси",
  "Научна фантастика",
  "Анимация",
  "Приключенски",
  "Фентъзи",
  "Романтика",
];
export function Movies() {
  const [params, setParams] = useSearchParams(),
    [search, setSearch] = useState(params.get("q") || ""),
    [advanced, setAdvanced] = useState(false);
  const urlQuery = params.get("q") || "";
  useEffect(() => setSearch(urlQuery), [urlQuery]);
  const query = useQuery({
    queryKey: ["movies", params.toString()],
    queryFn: () => api<MovieList>(`/movies?${params}`),
  });
  const update = (key: string, value: string) => {
    setParams((p) => {
      value ? p.set(key, value) : p.delete(key);
      if (key !== "page") p.delete("page");
      return p;
    });
  };
  useEffect(() => {
    const timer = setTimeout(() => {
      if (search !== (params.get("q") || "")) update("q", search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);
  return (
    <div className="container page">
      <Breadcrumb items={[{ label: "Филми" }]} />
      <div className="page-heading">
        <span className="eyebrow">ЗА ВСЯКО НАСТРОЕНИЕ ИМА ИСТОРИЯ</span>
        <h1>
          Намери своя филм<span className="yellow-text">.</span>
        </h1>
        <p>Големи светове, незабравими герои и място за теб.</p>
      </div>
      <div className="catalog-toolbar">
        <div className="search-field">
          <Search size={18} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Търси в каталога"
            placeholder="Търси филм, жанр или актьор…"
          />
        </div>
        <select
          aria-label="Жанр"
          value={params.get("genre") || ""}
          onChange={(e) => update("genre", e.target.value)}
        >
          <option value="">Всички жанрове</option>
          {genres.map((g) => (
            <option key={g}>{g}</option>
          ))}
        </select>
        <select
          aria-label="Статус"
          value={params.get("status") || ""}
          onChange={(e) => update("status", e.target.value)}
        >
          <option value="">Всички филми</option>
          <option value="active">Сега в киното</option>
          <option value="upcoming">Скоро в киното</option>
          <option value="archived">Архив</option>
        </select>
        <select
          aria-label="Сортирай"
          value={params.get("sort") || "popular"}
          onChange={(e) => update("sort", e.target.value)}
        >
          <option value="popular">По популярност</option>
          <option value="rating">По рейтинг</option>
          <option value="newest">Най-нови</option>
          <option value="title">По азбучен ред</option>
        </select>
        <button
          className={`icon-button filter-button ${advanced ? "active" : ""}`}
          aria-label="Още филтри"
          aria-expanded={advanced}
          onClick={() => setAdvanced(!advanced)}
        >
          <SlidersHorizontal size={19} />
        </button>
      </div>
      {advanced && (
        <div className="advanced-filters">
          <label>
            Година
            <select
              value={params.get("year") || ""}
              onChange={(e) => update("year", e.target.value)}
            >
              <option value="">Всички години</option>
              {[2024, 2023, 2022, 2019, 2018, 2017, 2016, 2014, 2010, 2000].map(
                (y) => (
                  <option key={y}>{y}</option>
                ),
              )}
            </select>
          </label>
          <label>
            Минимален рейтинг
            <select
              value={params.get("min_rating") || ""}
              onChange={(e) => update("min_rating", e.target.value)}
            >
              <option value="">Всички оценки</option>
              <option value="8">8+</option>
              <option value="9">9+</option>
            </select>
          </label>
          <label>
            Продължителност
            <select
              value={params.get("max_duration") || ""}
              onChange={(e) => update("max_duration", e.target.value)}
            >
              <option value="">Без ограничение</option>
              <option value="100">До 100 мин.</option>
              <option value="130">До 130 мин.</option>
            </select>
          </label>
          <label>
            Възраст
            <select
              value={params.get("age") || ""}
              onChange={(e) => update("age", e.target.value)}
            >
              <option value="">Всички възрасти</option>
              {["0+", "6+", "12+", "16+", "18+"].map((a) => (
                <option key={a}>{a}</option>
              ))}
            </select>
          </label>
          <label>
            Аудио
            <select
              value={params.get("language") || ""}
              onChange={(e) => update("language", e.target.value)}
            >
              <option value="">Всички езици</option>
              <option>Английски</option>
              <option>Български</option>
            </select>
          </label>
          <button
            className="text-link"
            onClick={() => {
              setSearch("");
              setParams({});
            }}
          >
            Изчисти филтрите
          </button>
        </div>
      )}
      <div className="results-label">
        {query.data
          ? `${query.data.total} филма те очакват`
          : "Зареждане на филми…"}
        <span>Демонстрационен каталог и рейтинги</span>
      </div>
      {query.isLoading ? (
        <Loading cards />
      ) : query.error ? (
        <ErrorState error={query.error} retry={() => query.refetch()} />
      ) : !query.data?.items.length ? (
        <Empty
          title="Тази история още не е тук"
          text="Промени търсенето или изчисти филтрите."
          action={
            <button
              className="button secondary"
              onClick={() => {
                setSearch("");
                setParams({});
              }}
            >
              Покажи всички филми
            </button>
          }
        />
      ) : (
        <>
          <div className="movie-grid catalog-grid">
            {query.data.items.map((m, i) => (
              <MovieCard key={m.id} movie={m} index={i} />
            ))}
          </div>
          {query.data.total > 12 && (
            <div className="pagination">
              <button
                className="button secondary"
                disabled={query.data.page <= 1}
                onClick={() => update("page", String(query.data!.page - 1))}
              >
                <ArrowLeft size={16} />
                Назад
              </button>
              <span>
                {query.data.page} / {Math.ceil(query.data.total / 12)}
              </span>
              <button
                className="button secondary"
                disabled={query.data.page * 12 >= query.data.total}
                onClick={() => update("page", String(query.data!.page + 1))}
              >
                Напред
                <ArrowRight size={16} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
export function MovieDetail() {
  const { slug } = useParams();
  const [trailer, setTrailer] = useState(false);
  const closeTrailer = useCallback(() => setTrailer(false), []);
  const movie = useQuery({
    queryKey: ["movie", slug],
    queryFn: () => api<Movie>(`/movies/slug/${slug}`),
  });
  const related = useQuery({
    queryKey: ["related", movie.data?.genres[0]],
    queryFn: () =>
      api<MovieList>(
        `/movies?genre=${encodeURIComponent(movie.data!.genres[0])}&page_size=6`,
      ),
    enabled: !!movie.data,
  });
  if (movie.isLoading) return <Loading />;
  if (movie.error || !movie.data)
    return (
      <div className="container page">
        <ErrorState error={movie.error} />
      </div>
    );
  const m = movie.data;
  return (
    <>
      <section className="detail-hero">
        <Image src={m.backdrop} alt="" eager />
        <div className="detail-gradient" />
      </section>
      <div className="container detail-content">
        <Breadcrumb
          items={[{ label: "Филми", to: "/movies" }, { label: m.title }]}
        />
        <div className="movie-detail-layout">
          <div className="detail-poster">
            <Image src={m.poster} alt={m.title} eager />
            <FavoriteButton movie={m} />
          </div>
          <div className="detail-copy">
            <span className="eyebrow">
              {m.status === "upcoming"
                ? "СКОРО НА ГОЛЯМ ЕКРАН"
                : "СЕГА В КИНОТО"}{" "}
              · АВТОРСКИ ФИЛМ
            </span>
            <h1>{m.title}</h1>
            <p className="original-title">{m.original_title}</p>
            <div className="hero-meta">
              <span className="hero-score">
                <Star size={16} fill="currentColor" />
                {m.rating.toFixed(1)}
              </span>
              <span>{m.year}</span>
              <span>
                <Clock3 size={15} />
                {duration(m.duration)}
              </span>
              <span className="age-tag">{m.age}</span>
            </div>
            <div className="genre-chips">
              {m.genres.map((g) => (
                <Link to={`/movies?genre=${encodeURIComponent(g)}`} key={g}>
                  {g}
                </Link>
              ))}
            </div>
            <p className="synopsis">{m.description}</p>
            <dl className="movie-facts">
              <div>
                <dt>Режисьор</dt>
                <dd>{m.director}</dd>
              </div>
              <div>
                <dt>В ролите</dt>
                <dd>{m.cast.join(", ")}</dd>
              </div>
              <div>
                <dt>Аудио / Субтитри</dt>
                <dd>
                  {m.language} / {m.subtitles}
                </dd>
              </div>
            </dl>
            <div className="hero-buttons">
              <a className="button" href="#showtimes">
                <Ticket size={18} />
                Избери прожекция
              </a>
              {m.trailer && (
                <button
                  className="button secondary"
                  onClick={() => setTrailer(true)}
                >
                  <Play size={16} />
                  Гледай трейлъра
                </button>
              )}
            </div>
            <p className="rating-note">
              Оценката и прожекциите са демонстрационни. Годината е от
              оригиналното издание.
            </p>
          </div>
        </div>
        <section className="section" id="showtimes">
          <SectionTitle
            eyebrow="ЗАПАЗИ СВОЕТО МЯСТО"
            title="Кога ти се гледа?"
          />
          <ShowtimeList movieId={m.id} />
        </section>
        <section className="section">
          <SectionTitle title="Още истории за теб" to="/movies" />
          <div className="movie-grid">
            {related.data?.items
              .filter((x) => x.id !== m.id)
              .slice(0, 5)
              .map((x) => (
                <MovieCard key={x.id} movie={x} />
              ))}
          </div>
        </section>
      </div>
      {trailer && <Trailer movie={m} onClose={closeTrailer} />}
    </>
  );
}
