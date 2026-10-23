import { useEffect, useRef, ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ChevronRight, Film, X, RefreshCw } from "lucide-react";
export function Logo() {
  return (
    <Link to="/" className="brand" aria-label="Пуканков · Начало">
      <svg viewBox="0 0 48 52" aria-hidden="true">
        <g fill="currentColor">
          <path d="M9 24h31l-4 26H13z" />
          <circle cx="11" cy="19" r="8" />
          <circle cx="24" cy="12" r="11" />
          <circle cx="37" cy="19" r="8" />
        </g>
        <path d="m19 29 2 16m9-16-2 16" stroke="#0b0b0f" strokeWidth="4" />
      </svg>
      <span>
        пуканков<span className="brand-dot">.</span>
      </span>
    </Link>
  );
}
export function SectionTitle({
  eyebrow,
  title,
  subtitle,
  to,
  link = "Виж всички",
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  to?: string;
  link?: string;
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {to && (
        <Link className="text-link" to={to}>
          {link}
          <ArrowRight size={17} />
        </Link>
      )}
    </div>
  );
}
export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    ref.current?.focus();
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeRef.current();
      if (e.key === "Tab") {
        const els = ref.current?.querySelectorAll<HTMLElement>(
          'button,a[href],input,select,textarea,[tabindex="0"]',
        );
        if (!els?.length) return;
        const first = els[0],
          last = els[els.length - 1];
        if (
          e.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === ref.current)
        ) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        tabIndex={-1}
        className={`modal ${wide ? "modal-wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="modal-heading">
          <h2>{title}</h2>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Затвори"
          >
            <X />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error | null;
  retry?: () => void;
}) {
  return (
    <div className="empty-state" role="alert">
      <Film size={36} />
      <h3>Нещо не се получи</h3>
      <p>{error?.message ?? "Опитайте отново след малко."}</p>
      {retry && (
        <button className="button secondary" onClick={retry}>
          <RefreshCw size={16} />
          Опитай отново
        </button>
      )}
    </div>
  );
}
export function Empty({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <Film size={38} />
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}
export function Loading({ cards = false }: { cards?: boolean }) {
  return cards ? (
    <div className="movie-grid">
      {Array.from({ length: 6 }, (_, i) => (
        <div className="skeleton-card" key={i}>
          <div className="skeleton poster-skeleton" />
          <div className="skeleton text-skeleton" />
          <div className="skeleton text-skeleton short" />
        </div>
      ))}
    </div>
  ) : (
    <div className="loading" role="status">
      <span className="spinner" />
      Зареждане…
    </div>
  );
}
export function Breadcrumb({
  items,
}: {
  items: { label: string; to?: string }[];
}) {
  return (
    <nav className="breadcrumb" aria-label="Път до страницата">
      <Link to="/">Начало</Link>
      {items.map((x, i) => (
        <span key={i}>
          <ChevronRight size={13} />
          {x.to ? <Link to={x.to}>{x.label}</Link> : x.label}
        </span>
      ))}
    </nav>
  );
}
export function Image({
  src,
  alt,
  className = "",
  eager = false,
}: {
  src: string;
  alt: string;
  className?: string;
  eager?: boolean;
}) {
  return (
    <img
      src={src || "/images/fallback.svg"}
      alt={alt}
      className={className}
      loading={eager ? "eager" : "lazy"}
      onError={(e) => {
        e.currentTarget.onerror = null;
        e.currentTarget.src = "/images/fallback.svg";
      }}
    />
  );
}
