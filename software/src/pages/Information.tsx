import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  MapPin,
  ArrowUpRight,
  Ticket,
  Copy,
  Check,
  Plus,
  Minus,
  ArrowRight,
  Mail,
  Film,
  Armchair,
  Volume2,
} from "lucide-react";
import { api, money, dateLabel } from "../lib/api";
import { useToast } from "../lib/context";
import {
  Breadcrumb,
  Image,
  Loading,
  ErrorState,
  Empty,
} from "../components/UI";
import { ShowtimeList } from "./Showtimes";
import type { Cinema, Offer } from "../types";
export function Cinemas() {
  const data = useQuery({
    queryKey: ["cinemas"],
    queryFn: () => api<Cinema[]>("/cinemas"),
  });
  return (
    <div className="container page">
      <Breadcrumb items={[{ label: "Нашите кина" }]} />
      <div className="page-heading">
        <span className="eyebrow">
          ЕДНА ЛЮБОВ КЪМ КИНОТО. МНОГО МЕСТА ЗА НЕЯ.
        </span>
        <h1>
          Твоето място е тук<span className="yellow-text">.</span>
        </h1>
        <p>Открий света на Пуканков. Демонстрационни кина и адреси.</p>
      </div>
      {data.isLoading ? (
        <Loading />
      ) : data.error ? (
        <ErrorState error={data.error} />
      ) : (
        <div className="cinema-grid">
          {data.data?.map((c, i) => (
            <Link className="cinema-card" to={`/cinemas/${c.slug}`} key={c.id}>
              <div className="cinema-image">
                <Image src={c.image} alt={`Кино салон · ${c.name}`} />
                <span className="badge yellow">{c.city}</span>
                <span className="cinema-index">0{i + 1}</span>
              </div>
              <div>
                <h2>
                  {c.name}
                  <ArrowUpRight size={22} />
                </h2>
                <p>
                  <MapPin size={14} />
                  {c.address}
                </p>
                <span className="cinema-features">
                  IMAX · Dolby Atmos · Premium комфорт
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
export function CinemaDetail() {
  const { slug } = useParams();
  const c = useQuery({
    queryKey: ["cinema", slug],
    queryFn: () => api<Cinema>(`/cinemas/${slug}`),
  });
  if (c.isLoading) return <Loading />;
  if (c.error || !c.data)
    return (
      <div className="container page">
        <ErrorState error={c.error} />
      </div>
    );
  return (
    <div className="container page">
      <Breadcrumb
        items={[{ label: "Кина", to: "/cinemas" }, { label: c.data.name }]}
      />
      <div className="cinema-detail-image">
        <Image src={c.data.image} alt={c.data.name} eager />
        <div>
          <span className="eyebrow">{c.data.city} · DEMO КИНО</span>
          <h1>{c.data.name}</h1>
          <p>
            <MapPin size={17} />
            {c.data.address}
          </p>
        </div>
      </div>
      <p className="cinema-description">{c.data.description}</p>
      <div className="cinema-perks">
        <span>
          <Film />
          Лазерна прожекция
        </span>
        <span>
          <Volume2 />
          Пространствен звук
        </span>
        <span>
          <Armchair />
          Премиум кресла
        </span>
      </div>
      <section className="section">
        <h2>Програмата тук</h2>
        <ShowtimeList cinemaId={c.data.id} />
      </section>
    </div>
  );
}
export function Offers() {
  const data = useQuery({
    queryKey: ["offers"],
    queryFn: () => api<Offer[]>("/offers"),
  });
  const toast = useToast();
  return (
    <div className="container page">
      <Breadcrumb items={[{ label: "Промоции" }]} />
      <div className="page-heading">
        <span className="eyebrow">ОЩЕ ЕДНА ПРИЧИНА ДА ОТИДЕШ НА КИНО</span>
        <h1>
          Повече кино. Повече емоции<span className="yellow-text">.</span>
        </h1>
        <p>
          Демонстрационни предложения с истински работещи правила за отстъпка.
        </p>
      </div>
      {data.isLoading ? (
        <Loading />
      ) : data.error ? (
        <ErrorState error={data.error} />
      ) : (
        <div className="offers-grid">
          {data.data?.map((p, i) => (
            <article
              key={p.id}
              className={`offer-card ${i % 2 ? "orange" : "gold"}`}
            >
              <div className="offer-card-top">
                <Ticket size={34} />
                <span>DEMO ПРЕДЛОЖЕНИЕ</span>
              </div>
              <strong className="offer-percent">
                −{p.percent}
                <span>%</span>
              </strong>
              <h2>{p.title}</h2>
              <p>
                За поръчки от {money(p.minimum)}. Валиден до{" "}
                {dateLabel(p.ends_at, true)}. Максимум {p.per_user} използвания
                на потребител; до {p.max_uses} общо.
              </p>
              <button
                className="promo-code"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(p.code);
                    toast(`Кодът ${p.code} е копиран.`);
                  } catch {
                    toast(`Твоят код е ${p.code}`);
                  }
                }}
              >
                {p.code}
                <Copy size={17} />
              </button>
              <Link className="button black" to="/showtimes">
                Избери кино история
                <ArrowUpRight size={16} />
              </Link>
            </article>
          ))}
        </div>
      )}
      <div className="notice">
        <Check size={20} />
        <p>
          Промокодът се проверява от сървъра и се прилага само след въвеждане
          при поръчка. Всички цени и отстъпки са демонстрационни.
        </p>
      </div>
      <div className="coming-offers">
        <h2>За всяка компания има кино вечер.</h2>
        <p>
          Семейни пакети и комбинации с пуканки ще бъдат достъпни при
          конфигуриране на предложенията.
        </p>
      </div>
    </div>
  );
}
const faqs = [
  [
    "Как да купя билет в учебната система?",
    "Избери филм и прожекция, отбележи свободните места и влез или създай профил. Попълни измислените картови данни и избери резултат с отметката „Успешна транзакция“. Без отметката плащането се отказва и не се издават билети. Не се прехвърлят реални средства.",
  ],
  [
    "Колко време са задържани местата ми?",
    "След продължаване към поръчка местата се задържат за 5 минути. В checkout има обратно броене. След изтичане местата отново стават достъпни.",
  ],
  [
    "Къде ще намеря билетите си?",
    "Влез в профила си и отвори „Моите билети“. От всяка поръчка можеш да отвориш билетите и да използваш „Печат / Запази като PDF“.",
  ],
  [
    "Мога ли да използвам билета в истинско кино?",
    "Не. Пуканков е демонстрационна платформа. Кината, адресите и прожекциите са примерни, а билетите не дават право на реален достъп.",
  ],
  [
    "Как работят промокодовете?",
    "Копирай активен код от „Промоции“ и го въведи при поръчка. Сървърът проверява периода, минималната сума и лимитите за използване.",
  ],
  [
    "Изпращате ли билетите по имейл?",
    "В текущата демонстрация билетите се пазят в профила и не се изпращат по имейл. SMTP може да бъде конфигуриран за възстановяване на парола.",
  ],
  [
    "Как да заявя изтриване на данните си?",
    "Отвори „Моят профил“ и избери „Заяви изтриване на профила“. Заявката се записва за административен преглед. Можеш и да изтеглиш собствените си данни.",
  ],
];
export function FAQ() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <div className="container page narrow">
      <Breadcrumb items={[{ label: "Често задавани въпроси" }]} />
      <div className="page-heading">
        <span className="eyebrow">ПРЕДИ СВЕТЛИНИТЕ ДА УГАСНАТ</span>
        <h1>
          Всичко, което искаш да знаеш<span className="yellow-text">.</span>
        </h1>
      </div>
      <div className="faq-list">
        {faqs.map(([q, a], i) => (
          <div className="faq-item" key={q}>
            <button
              aria-expanded={open === i}
              aria-controls={`faq-${i}`}
              onClick={() => setOpen(open === i ? null : i)}
            >
              {q}
              {open === i ? <Minus size={19} /> : <Plus size={19} />}
            </button>
            {open === i && <p id={`faq-${i}`}>{a}</p>}
          </div>
        ))}
      </div>
      <div className="notice">
        <Mail size={20} />
        <p>
          Не намери отговор? Виж{" "}
          <Link to="/contact">как да се свържеш с нас</Link>.
        </p>
      </div>
    </div>
  );
}
export function About() {
  return (
    <div className="container page">
      <Breadcrumb items={[{ label: "За нас" }]} />
      <div className="about-intro">
        <span className="eyebrow">ХОРА С ГОЛЯМА ЛЮБОВ КЪМ КИНОТО</span>
        <h1>
          Понякога един филм
          <br />е всичко, от което
          <br />
          имаш <span className="yellow-text">нужда.</span>
        </h1>
        <p>
          Пуканков е идея за кино, което събира хората. За онзи момент, в който
          светлините угасват, светът притихва и историята започва.
        </p>
        <Link className="button" to="/movies">
          Намери своята история
          <ArrowRight size={18} />
        </Link>
      </div>
      <div className="about-photo">
        <Image
          src="/images/originals/cinema.svg"
          alt="Кино зала с червени кресла"
        />
      </div>
      <div className="about-columns">
        <div>
          <h2>Създадено за преживяване.</h2>
          <p>
            От първия поглед към постера до последните надписи — всяка стъпка
            има значение. Създадохме място, в което откриването на филми и
            изборът на места са част от удоволствието.
          </p>
        </div>
        <div>
          <h2>Демонстрация с голяма идея.</h2>
          <p>
            Това е измислен бранд и работеща демонстрационна кино платформа.
            Кината, адресите и програмата не са реални. Не приемаме истински
            плащания.
          </p>
        </div>
      </div>
    </div>
  );
}
export function Contact() {
  return (
    <div className="container page narrow">
      <Breadcrumb items={[{ label: "Контакти" }]} />
      <div className="page-heading">
        <span className="eyebrow">ДОБРИТЕ ИСТОРИИ ЗАПОЧВАТ С РАЗГОВОР</span>
        <h1>
          Насреща сме<span className="yellow-text">.</span>
        </h1>
        <p>
          Това е демонстрационен проект. Посочените контакти и адреси са
          примерни.
        </p>
      </div>
      <div className="contact-card">
        <Mail size={27} />
        <div>
          <h2>hello@pukankov.example</h2>
          <p>Примерен адрес, който не получава съобщения.</p>
        </div>
      </div>
      <div className="contact-card">
        <MapPin size={27} />
        <div>
          <h2>Нашите демонстрационни кина</h2>
          <p>София · Пловдив · Варна</p>
          <Link className="text-link" to="/cinemas">
            Разгледай кината
            <ArrowUpRight size={15} />
          </Link>
        </div>
      </div>
      <Link to="/faq" className="button secondary">
        Виж често задаваните въпроси
        <ArrowRight size={17} />
      </Link>
    </div>
  );
}
export function Legal({ privacy = false }: { privacy?: boolean }) {
  return (
    <div className="container page legal-page">
      <Breadcrumb
        items={[{ label: privacy ? "Поверителност" : "Общи условия" }]}
      />
      <div className="page-heading">
        <span className="eyebrow">ПРОЗРАЧНО И РАЗБИРАЕМО</span>
        <h1>{privacy ? "Твоите данни са твои." : "Общи условия."}</h1>
        <p>Информация за демонстрационната среда · 27 октомври 2026 г.</p>
      </div>
      <div className="prose">
        {privacy ? (
          <>
            <h2>Какво съхраняваме</h2>
            <p>
              При регистрация записваме име, имейл и защитен хеш на паролата.
              Съхраняваме твоите любими филми, резервации, поръчки и
              демонстрационни билети, за да работи профилът ти. Не събираме
              банкови данни.
            </p>
            <h2>Сесии и бисквитки</h2>
            <p>
              Използваме необходима HttpOnly бисквитка за сесията със срок до 12
              часа. Изборът на град се пази в браузъра, а временната резервация
              — в sessionStorage. Не зареждаме рекламни или аналитични
              бисквитки.
            </p>
            <h2>Външни услуги</h2>
            <p>
              Демонстрационните изображения са включени локално в сайта. Шрифтът
              се зарежда от Google Fonts. При отваряне на трейлър се зарежда
              YouTube с домейна youtube-nocookie.com. Тези услуги получават
              необходимите за връзката технически данни.
            </p>
            <h2>Достъп и изтриване</h2>
            <p>
              От профила можеш да изтеглиш данните си и да запишеш заявка за
              изтриване. Заявките изискват административен преглед. Не въвеждай
              чувствителни или реални платежни данни в демонстрацията.
            </p>
            <h2>Преди реално публикуване</h2>
            <p>
              Операторът трябва да определи юридическото лице, правните
              основания, сроковете за съхранение, процедурата за изпълнение на
              права и реални контакти. Настоящият текст описва демонстрацията и
              не е готова политика за търговска услуга.
            </p>
          </>
        ) : (
          <>
            <h2>Демонстрационна платформа</h2>
            <p>
              Пуканков е измислена кино верига. Показаните кина, адреси,
              прожекции, рейтинги и промоции са примерни. Генерираните билети не
              важат за реални кино прожекции.
            </p>
            <h2>Поръчки и плащания</h2>
            <p>
              Плащането е учебна симулация с картова форма. Не се приемат реални
              плащания. Въвеждай само измислени картови данни — те остават в
              браузъра и не се съхраняват. Цените се изчисляват на сървъра и се
              показват в евро.
            </p>
            <h2>Резервации</h2>
            <p>
              Можеш да избереш до 8 места. Сървърът ги задържа за 5 минути след
              продължаване към поръчка. След изтичане на срока или отказ местата
              се освобождават. Поръчката се потвърждава само при успешно
              завършване на сървърната симулация на транзакция. Всеки билет има
              уникален шестцифрен код за клавиатурата на валидатора.
            </p>
            <h2>Профил и отговорност</h2>
            <p>
              Пази паролата си. Профилът позволява достъп само до собствените
              билети и поръчки. Не използвай автоматизирани заявки за блокиране
              на местата или за заобикаляне на лимитите.
            </p>
            <h2>Изображения и съдържание</h2>
            <p>
              Каталогът съдържа 15 измислени филмови концепции с оригинални
              сюжети и векторни илюстрации, създадени за дипломния проект.
              Посочените екипи са художествени персонажи. Проектът не предоставя
              пълнометражни филми за гледане или изтегляне.
            </p>
            <h2>Въпроси</h2>
            <p>
              Виж <Link to="/faq">често задаваните въпроси</Link> за информация
              за демонстрационния процес.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
export function NotFound({ forbidden = false }: { forbidden?: boolean }) {
  return (
    <div className="container page">
      <div className="not-found-code">{forbidden ? "403" : "404"}</div>
      <Empty
        title={
          forbidden
            ? "Тази врата е само за екипа"
            : "Тази сцена я няма в сценария"
        }
        text={
          forbidden
            ? "Твоят профил няма права за тази страница."
            : "Страницата не е намерена. Но има много добри истории, които те очакват."
        }
        action={
          <Link className="button" to="/">
            Към началото
            <ArrowRight size={17} />
          </Link>
        }
      />
    </div>
  );
}
