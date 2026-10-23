import { Link, useNavigate } from "react-router-dom";
import { Heart, ArrowUpRight, Star } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Image } from "./UI";
import { useAuth, useToast } from "../lib/context";
import { api } from "../lib/api";
import type { Movie } from "../types";
export function FavoriteButton({ movie }: { movie: Movie }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const client = useQueryClient();
  const toast = useToast();
  const favorites = useQuery({
    queryKey: ["favorites", user?.id],
    queryFn: () => api<Movie[]>("/me/favorites"),
    enabled: !!user,
  });
  const saved = favorites.data?.some((m) => m.id === movie.id) ?? false;
  return (
    <button
      className={`save-button ${saved ? "saved" : ""}`}
      aria-label={`${saved ? "Премахни от" : "Добави в"} любими: ${movie.title}`}
      aria-pressed={saved}
      onClick={async () => {
        if (!user) {
          navigate("/login");
          return;
        }
        try {
          await api(`/me/favorites/${movie.id}`, {
            method: saved ? "DELETE" : "POST",
          });
          await client.invalidateQueries({ queryKey: ["favorites"] });
          toast(
            saved
              ? "Филмът е премахнат от любими."
              : "Филмът е добавен в любими.",
          );
        } catch (e) {
          toast((e as Error).message);
        }
      }}
    >
      <Heart size={17} fill={saved ? "currentColor" : "none"} />
    </button>
  );
}
export function MovieCard({
  movie,
  index,
  rank = false,
}: {
  movie: Movie;
  index?: number;
  rank?: boolean;
}) {
  return (
    <article
      className={`movie-card ${rank ? "rank-card" : ""}`}
      style={{ animationDelay: `${(index ?? 0) * 60}ms` }}
    >
      {rank && <span className="rank-number">{(index ?? 0) + 1}</span>}
      <div className="poster-wrap">
        <Link to={`/movies/${movie.slug}`} className="poster-link">
          <Image src={movie.poster} alt={`Постер на ${movie.title}`} />
          <span className="poster-shade" />
          <span className="poster-action">
            Виж филма
            <ArrowUpRight size={17} />
          </span>
        </Link>
        <div className="poster-badges">
          {movie.featured && movie.status === "active" ? (
            <span className="badge yellow">ПРЕМИЕРА</span>
          ) : movie.genres.includes("Анимация") ? (
            <span className="badge light">ЗА ЦЯЛОТО СЕМЕЙСТВО</span>
          ) : movie.status === "upcoming" ? (
            <span className="badge">СКОРО</span>
          ) : null}
        </div>
        <FavoriteButton movie={movie} />
        <span className="rating" title="Демонстрационен рейтинг">
          <Star size={12} fill="currentColor" />
          {movie.rating.toFixed(1)}
        </span>
      </div>
      <Link className="movie-title" to={`/movies/${movie.slug}`}>
        <h3>{movie.title}</h3>
      </Link>
      <p className="movie-meta">
        {movie.genres.slice(0, 2).join(" / ")}
        <span>·</span>
        {movie.duration} мин.
      </p>
      <div className="movie-card-bottom">
        <span>
          {movie.year}
          <i />
          {movie.age}
        </span>
        <Link to={`/movies/${movie.slug}#showtimes`}>
          {movie.status === "upcoming" ? "Виж филма" : "Купи билет"}
          <ArrowUpRight size={13} />
        </Link>
      </div>
    </article>
  );
}
