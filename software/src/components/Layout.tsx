import { useState, useEffect, useCallback } from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import {
  Search,
  Heart,
  UserRound,
  Ticket,
  MapPin,
  ChevronDown,
  Menu,
  X,
  ArrowUpRight,
  Instagram,
  Facebook,
  Film,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Logo, Modal, Image, Loading, Empty, ErrorState } from "./UI";
import { api } from "../lib/api";
import { useAuth } from "../lib/context";
import type { Cinema, MovieList } from "../types";
const links = [
  ["/", "Начало"],
  ["/movies", "Филми"],
  ["/showtimes", "Прожекции"],
  ["/cinemas", "Нашите кина"],
  ["/offers", "Промоции"],
];
export function Header() {
  const [search, setSearch] = useState(false),
    [menu, setMenu] = useState(false),
    [locationOpen, setLocationOpen] = useState(false),
    [city, setCity] = useState(
      () => localStorage.getItem("pukankov_city") || "София",
    );
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const cinemas = useQuery({
    queryKey: ["cinemas"],
    queryFn: () => api<Cinema[]>("/cinemas"),
    staleTime: 300000,
  });
  useEffect(() => {
    setMenu(false);
    setLocationOpen(false);
  }, [location.pathname]);
  const closeSearch = useCallback(() => setSearch(false), []);
  return (
    <>
      <header className="site-header">
        <div className="header-inner">
          <Logo />
          <nav className="desktop-nav" aria-label="Главна навигация">
            {links.map(([to, text]) => (
              <NavLink key={to} to={to} end={to === "/"}>
                {text}
                {text === "Промоции" && <span className="nav-dot" />}
              </NavLink>
            ))}
          </nav>
          <div className="header-actions">
            <div className="city-picker">
              <button
                className="city-button"
                onClick={() => setLocationOpen(!locationOpen)}
                aria-expanded={locationOpen}
              >
                <MapPin size={15} />
                <span>{city}</span>
                <ChevronDown size={13} />
              </button>
              {locationOpen && (
                <div className="city-menu">
                  {cinemas.data?.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        setCity(c.city);
                        localStorage.setItem("pukankov_city", c.city);
                        setLocationOpen(false);
                        navigate(`/showtimes?cinema_id=${c.id}`);
                      }}
                    >
                      <MapPin size={14} />
                      {c.city}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <span className="header-divider" />
            <button
              className="icon-button"
              aria-label="Търси филм"
              onClick={() => setSearch(true)}
            >
              <Search size={19} />
            </button>
            <Link
              className="icon-button favorite-nav"
              to="/favorites"
              aria-label="Любими филми"
            >
              <Heart size={19} />
            </Link>
            <Link className="login-link" to={user ? "/profile" : "/login"}>
              <UserRound size={17} />
              <span>{user ? user.name.split(" ")[0] : "Вход"}</span>
            </Link>
            <Link className="button small header-ticket" to="/showtimes">
              <Ticket size={16} />
              Купи билет
            </Link>
            <button
              className="icon-button mobile-menu"
              aria-label={menu ? "Затвори менюто" : "Отвори менюто"}
              aria-expanded={menu}
              onClick={() => setMenu(!menu)}
            >
              {menu ? <X /> : <Menu />}
            </button>
          </div>
        </div>
        {menu && (
          <nav className="mobile-nav">
            {links.map(([to, text]) => (
              <NavLink key={to} to={to}>
                {text}
              </NavLink>
            ))}
            <Link to="/favorites">Любими филми</Link>
            <Link to={user ? "/profile" : "/login"}>
              {user ? "Моят профил" : "Вход / Регистрация"}
            </Link>
            <Link to="/showtimes" className="button">
              Купи билет
            </Link>
          </nav>
        )}
      </header>
      {search && <SearchDialog close={closeSearch} />}
    </>
  );
}
function SearchDialog({ close }: { close: () => void }) {
  const [value, setValue] = useState(""),
    [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), 250);
    return () => clearTimeout(t);
  }, [value]);
  const results = useQuery({
    queryKey: ["search", debounced],
    queryFn: () =>
      api<MovieList>(`/movies?q=${encodeURIComponent(debounced)}&page_size=6`),
    enabled: debounced.trim().length > 0,
  });
  return (
    <Modal title="Твоята следваща кино история" onClose={close}>
      <div className="search-field">
        <Search size={21} />
        <input
          autoFocus
          placeholder="Заглавие, жанр или актьор…"
          aria-label="Търсене"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </div>
      {!debounced ? (
        <p className="muted">
          Опитай „Последната орбита“, „анимация“ или „Мира“.
        </p>
      ) : results.isLoading ? (
        <Loading />
      ) : results.error ? (
        <ErrorState error={results.error} retry={() => results.refetch()} />
      ) : results.data?.items.length ? (
        <div className="search-results">
          {results.data.items.map((m) => (
            <Link to={`/movies/${m.slug}`} onClick={close} key={m.id}>
              <Image src={m.poster} alt="" />
              <div>
                <h3>{m.title}</h3>
                <p>
                  {m.year} · {m.genres[0]} · {m.duration} мин.
                </p>
              </div>
              <ArrowUpRight size={18} />
            </Link>
          ))}
        </div>
      ) : (
        <Empty
          title="Няма намерени филми"
          text="Опитай с друго заглавие или жанр."
        />
      )}
    </Modal>
  );
}
export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-top">
          <div className="footer-brand">
            <Logo />
            <p>
              Големите истории заслужават голям екран.
              <br />
              Твоето място е в киното.
            </p>
            <div className="social-links">
              <a
                href="https://www.instagram.com/"
                target="_blank"
                rel="noreferrer"
                aria-label="Instagram (обща страница)"
              >
                <Instagram size={18} />
              </a>
              <a
                href="https://www.facebook.com/"
                target="_blank"
                rel="noreferrer"
                aria-label="Facebook (обща страница)"
              >
                <Facebook size={18} />
              </a>
              <Film size={18} />
            </div>
          </div>
          <div>
            <h4>В света на киното</h4>
            <Link to="/movies">Всички филми</Link>
            <Link to="/showtimes">Програма</Link>
            <Link to="/movies?status=upcoming">Скоро в киното</Link>
            <Link to="/offers">Промоции</Link>
          </div>
          <div>
            <h4>Пуканков</h4>
            <Link to="/about">За нас</Link>
            <Link to="/cinemas">Нашите кина</Link>
            <Link to="/contact">Контакти</Link>
            <Link to="/faq">Често задавани въпроси</Link>
          </div>
          <div className="footer-cta">
            <span className="eyebrow">НЯМА МАЛКИ ИСТОРИИ.</span>
            <h3>Има голям екран.</h3>
            <Link className="text-link" to="/showtimes">
              Намери своя филм
              <ArrowUpRight size={18} />
            </Link>
          </div>
        </div>
        <div className="footer-bottom">
          <span>
            © {new Date().getFullYear()} Пуканков. Създадено за любовта към
            киното.
          </span>
          <div>
            <Link to="/terms">Общи условия</Link>
            <Link to="/privacy">Поверителност и бисквитки</Link>
            <span className="demo-label">ДИПЛОМЕН ПРОЕКТ</span>
          </div>
        </div>
        <p className="demo-disclosure">
          Дипломен проект с 15 авторски филмови концепции. Кината, прожекциите,
          рейтингите и офертите са примерни. Не се извършват реални плащания.
          Изображенията принадлежат на съответните правоносители.
        </p>
      </div>
    </footer>
  );
}
