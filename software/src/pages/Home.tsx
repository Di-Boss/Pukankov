import { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  Ticket,
  Play,
  Star,
  Clock3,
  ChevronLeft,
  ChevronRight,
  MapPin,
  CalendarDays,
  Film,
  MoveUpRight,
  Volume2,
  Armchair,
  ScanLine,
} from "lucide-react";
import { api, dateLabel } from "../lib/api";
import { MovieCard } from "../components/MovieCard";
import {
  SectionTitle,
  Loading,
  ErrorState,
  Image,
  Modal,
} from "../components/UI";
import type { Movie, MovieList, Cinema, Showtime } from "../types";
export function Trailer({
  movie,
  onClose,
}: {
  movie: Movie;
  onClose: () => void;
}) {
  return (
    <Modal title={`${movie.title} · Трейлър`} onClose={onClose} wide>
      <div className="video-frame">
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${movie.trailer}?autoplay=1&rel=0`}
          title={`Официален трейлър: ${movie.title}`}
          allow="autoplay; encrypted-media; picture-in-picture"
          allowFullScreen
        />
      </div>
      <p className="muted small-text">
        Видеото се зарежда от YouTube при отваряне на този прозорец.
      </p>
    </Modal>
  );
}
export default function Home() {
  const [slide, setSlide] = useState(0),
    [trailer, setTrailer] = useState<Movie | null>(null),
    [tab, setTab] = useState("active");
  const all = useQuery({
    queryKey: ["home-movies"],
    queryFn: () => api<MovieList>("/movies?page_size=50"),
  });
  const top = useQuery({
    queryKey: ["top"],
    queryFn: () => api<Movie[]>("/movies/top"),
  });
  const closeTrailer = useCallback(() => setTrailer(null), []);
  const slides = all.data?.items.filter((m) => m.featured) ?? [];
  const hero = slides[slide % Math.max(slides.length, 1)];
  useEffect(() => {
    const t = setInterval(() => setSlide((s) => (s + 1) % 3), 14000);
    return () => clearInterval(t);
  }, []);
  const displayed =
    tab === "top"
      ? top.data?.slice(0, 5)
      : all.data?.items.filter((m) => m.status === tab).slice(0, 5);
  return (
    <>
      <section
        className={`hero ${hero?.slug === "last-orbit" ? "original-hero" : ""}`}
        aria-label="Препоръчани филми"
      >
        {hero && (
          <Image src={hero.backdrop} alt="" className="hero-backdrop" eager />
        )}
        <div className="hero-gradient" />
        <div className="hero-grain" />
        <div className="container hero-content">
          {hero ? (
            <>
              <div className="hero-label">
                <span className="live-dot" />
                {hero.slug === "last-orbit"
                  ? "ПУКАНКОВ ОРИГИНАЛИ"
                  : "ИСТОРИИ, КОИТО ОСТАВАТ"}
                <span className="hero-format">
                  {hero.slug === "last-orbit" ? "IMAX" : "DOLBY ATMOS"}
                </span>
              </div>
              {hero.slug === "last-orbit" ? (
                <div className="original-feature-title">
                  <h1>
                    <span>ПОСЛЕДНАТА</span>ОРБИТА
                  </h1>
                  <span>ЕДИН СИГНАЛ. ПОСЛЕДЕН ШАНС.</span>
                </div>
              ) : (
                <h1 className="hero-movie-title">{hero.title}</h1>
              )}
              <div className="hero-meta">
                <span className="hero-score">
                  <Star size={15} fill="currentColor" />
                  {hero.rating.toFixed(1)}
                </span>
                <span>{hero.year}</span>
                <span>{hero.genres[0]}</span>
                <span>
                  <Clock3 size={14} />
                  {hero.duration} мин.
                </span>
                <span className="age-tag">{hero.age}</span>
              </div>
              <p className="hero-description">{hero.description}</p>
              <div className="hero-buttons">
                <Link className="button" to={`/movies/${hero.slug}#showtimes`}>
                  <Ticket size={18} />
                  Купи билет
                  <ArrowUpRight size={17} />
                </Link>
                {hero.trailer ? (
                  <button
                    className="button glass"
                    onClick={() => setTrailer(hero)}
                  >
                    <span className="play-circle">
                      <Play size={11} fill="currentColor" />
                    </span>
                    Гледай трейлъра
                  </button>
                ) : (
                  <Link className="button glass" to={`/movies/${hero.slug}`}>
                    <Film size={17} />
                    Открий историята
                  </Link>
                )}
              </div>
              <div className="hero-footnote">
                <span className="tiny-line" />
                НЯКОИ ИСТОРИИ СА СЪЗДАДЕНИ ЗА ГОЛЯМ ЕКРАН.
              </div>
            </>
          ) : all.error ? (
            <ErrorState error={all.error} retry={() => all.refetch()} />
          ) : (
            <Loading />
          )}
        </div>
        <div className="container hero-bottom">
          <div className="hero-indicators">
            {slides.map((x, i) => (
              <button
                key={x.id}
                className={slide === i ? "active" : ""}
                onClick={() => setSlide(i)}
                aria-label={`Покажи ${x.title}`}
                aria-pressed={slide === i}
              >
                <span>0{i + 1}</span>
                <i />
              </button>
            ))}
          </div>
          <div className="hero-arrows">
            <span>ОТКРИЙ СЛЕДВАЩАТА ИСТОРИЯ</span>
            <button
              onClick={() => setSlide((s) => (s + 2) % 3)}
              aria-label="Предишен филм"
            >
              <ChevronLeft size={19} />
            </button>
            <button
              onClick={() => setSlide((s) => (s + 1) % 3)}
              aria-label="Следващ филм"
            >
              <ChevronRight size={19} />
            </button>
          </div>
        </div>
        <div className="hero-side-label">THE CINEMA EXPERIENCE</div>
      </section>
      <div className="container">
        <QuickBooking />
        <section className="section now-playing">
          <div className="section-heading">
            <div>
              <div className="eyebrow">
                <span className="live-dot" />
                СВЕТЛИНИ. КАМЕРА. КИНО.
              </div>
              <h2>
                На голям екран<span className="yellow-text">.</span>
              </h2>
            </div>
            <div className="section-controls">
              <div className="tabs">
                {[
                  ["active", "Сега в киното"],
                  ["upcoming", "Скоро"],
                  ["top", "Топ рейтинг"],
                ].map(([v, l]) => (
                  <button
                    key={v}
                    className={tab === v ? "active" : ""}
                    onClick={() => setTab(v)}
                  >
                    {l}
                  </button>
                ))}
              </div>
              <Link
                to={`/movies${tab === "top" ? "?sort=rating" : `?status=${tab}`}`}
                className="round-link"
                aria-label="Виж всички филми"
              >
                <ArrowUpRight size={20} />
              </Link>
            </div>
          </div>
          {all.error ? (
            <ErrorState error={all.error} retry={() => all.refetch()} />
          ) : !displayed ? (
            <Loading cards />
          ) : (
            <div className="movie-grid home-movies">
              {displayed.map((m, i) => (
                <MovieCard movie={m} index={i} key={m.id} />
              ))}
            </div>
          )}
          <div className="section-bottom">
            <span>
              <i className="live-dot" />
              Всяка история заслужава да бъде видяна.
            </span>
            <Link className="text-link" to="/movies">
              Разгледай всички филми
              <ArrowRight size={16} />
            </Link>
          </div>
        </section>
        <section className="experience-strip">
          <div>
            <ScanLine />
            <span>
              Картината, която те поглъща<strong>IMAX® LASER</strong>
            </span>
          </div>
          <div>
            <Volume2 />
            <span>
              Звукът, който усещаш<strong>DOLBY ATMOS®</strong>
            </span>
          </div>
          <div>
            <Armchair />
            <span>
              Твоето най-удобно място<strong>PREMIUM COMFORT</strong>
            </span>
          </div>
          <Link to="/cinemas">
            Повече от кино
            <ArrowUpRight size={18} />
          </Link>
        </section>
        <section className="section offer-home">
          <div className="offer-copy">
            <span className="eyebrow dark">ХУБАВИТЕ МОМЕНТИ СА СПОДЕЛЕНИ</span>
            <h2>
              Двама в киното.
              <br />
              Двойно повече емоции.
            </h2>
            <p>
              Любим човек, голям екран и една добра история.
              <br />
              Открий нашите предложения за следващата кино вечер.
            </p>
            <Link className="button black" to="/offers">
              Виж предложенията
              <ArrowUpRight size={17} />
            </Link>
            <span className="offer-demo">
              Демонстрационни предложения · Виж условията
            </span>
          </div>
          <div className="offer-visual" aria-hidden="true">
            <span className="offer-type">
              GOOD
              <br />
              TIMES.
            </span>
            <div className="graphic-ticket ticket-one">
              <span>ПУКАНКОВ</span>
              <strong>
                КИНО ЗА
                <br />
                ДВАМА
              </strong>
              <i>ADMIT TWO · ENJOY MORE</i>
              <div className="ticket-perf" />
              <b>−20%</b>
            </div>
            <div className="graphic-ticket ticket-two">
              <span>ПУКАНКОВ</span>
              <strong>
                ГОЛЕМИ
                <br />
                ЕМОЦИИ.
              </strong>
              <i>YOUR NEXT GREAT STORY</i>
            </div>
            <span className="offer-asterisk">✳</span>
          </div>
        </section>
        <section className="section">
          <SectionTitle
            eyebrow="ОЧАКВАНЕТО Е ЧАСТ ОТ МАГИЯТА"
            title="Следващите големи истории"
            subtitle="Добави ги в любими. Най-доброто предстои."
            to="/movies?status=upcoming"
            link="Скоро в киното"
          />
          <div className="upcoming-grid">
            {all.data?.items
              .filter((m) => m.status === "upcoming")
              .slice(0, 3)
              .map((m) => (
                <Link
                  to={`/movies/${m.slug}`}
                  className="upcoming-card"
                  key={m.id}
                >
                  <Image src={m.backdrop} alt={m.title} />
                  <div className="upcoming-gradient" />
                  <span className="badge">АВТОРСКА ПРЕМИЕРА</span>
                  <div className="upcoming-info">
                    <div>
                      <p>{m.genres.join(" / ")}</p>
                      <h3>{m.title}</h3>
                    </div>
                    <span className="round-link">
                      <ArrowUpRight size={20} />
                    </span>
                  </div>
                </Link>
              ))}
          </div>
        </section>
        <section className="section top-section">
          <SectionTitle
            eyebrow="ИСТОРИИ, КОИТО СИ СТРУВАТ"
            title="Голямото кино. Големите любимци."
            to="/movies?sort=rating"
            link="Цялата класация"
          />
          <div className="top-grid">
            {top.data?.slice(0, 5).map((m, i) => (
              <MovieCard movie={m} key={m.id} index={i} rank />
            ))}
          </div>
          <p className="rating-note">
            ★ Оценките са примерни и служат само за демонстрация.
          </p>
        </section>
        <section className="cinema-manifesto">
          <span className="eyebrow">
            ИЗЛЕЗ ОТ ЕЖЕДНЕВИЕТО. ВЛЕЗ В ИСТОРИЯТА.
          </span>
          <h2>
            Животът е по-хубав
            <br />с малко <span>кино.</span>
          </h2>
          <Link to="/cinemas" className="button secondary">
            Открий своето кино
            <MoveUpRight size={17} />
          </Link>
          <div className="manifesto-coordinate">
            42°41′51.0″N &nbsp; 23°19′26.0″E &nbsp; · &nbsp; SOFIA, BG
          </div>
        </section>
      </div>
      {trailer && <Trailer movie={trailer} onClose={closeTrailer} />}
    </>
  );
}
function QuickBooking() {
  const navigate = useNavigate();
  const [cinema, setCinema] = useState(""),
    [movie, setMovie] = useState(""),
    [date, setDate] = useState("");
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
    queryKey: ["all-showtimes"],
    queryFn: () => api<Showtime[]>("/showtimes"),
  });
  const dates = [...new Set(shows.data?.map((s) => s.date))];
  return (
    <form
      className="quick-booking"
      onSubmit={(e) => {
        e.preventDefault();
        const p = new URLSearchParams();
        if (cinema) p.set("cinema_id", cinema);
        if (movie) p.set("movie_id", movie);
        if (date) p.set("date", date);
        navigate(`/showtimes?${p}`);
      }}
    >
      <div className="quick-title">
        <span className="quick-title-icon">
          <Ticket size={23} />
        </span>
        <div>
          <strong>Твоят билет за кино</strong>
          <span>Няколко клика. Голяма история.</span>
        </div>
      </div>
      <label className="quick-select">
        <MapPin size={17} />
        <div>
          <span>ИЗБЕРИ КИНО</span>
          <select
            aria-label="Избери кино"
            value={cinema}
            onChange={(e) => setCinema(e.target.value)}
          >
            <option value="">Всички кина</option>
            {cinemas.data?.map((c) => (
              <option value={c.id} key={c.id}>
                {c.name} · {c.city}
              </option>
            ))}
          </select>
        </div>
      </label>
      <label className="quick-select">
        <Film size={17} />
        <div>
          <span>ИЗБЕРИ ФИЛМ</span>
          <select
            aria-label="Избери филм"
            value={movie}
            onChange={(e) => setMovie(e.target.value)}
          >
            <option value="">Всички филми</option>
            {movies.data?.items.map((m) => (
              <option value={m.id} key={m.id}>
                {m.title}
              </option>
            ))}
          </select>
        </div>
      </label>
      <label className="quick-select">
        <CalendarDays size={17} />
        <div>
          <span>КОГА ТИ СЕ ГЛЕДА?</span>
          <select
            aria-label="Избери дата"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          >
            <option value="">Избери дата</option>
            {dates.map((d, i) => (
              <option key={d} value={d}>
                {i === 0 ? "Днес / Най-близка дата" : dateLabel(d)}
              </option>
            ))}
          </select>
        </div>
      </label>
      <button className="button" type="submit">
        Намери прожекция
        <ArrowRight size={17} />
      </button>
    </form>
  );
}
