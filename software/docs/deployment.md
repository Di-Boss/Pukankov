# Внедряване

Настоящата версия е за локална DEMO употреба. Реална продажба не е активирана. Този документ описва основата и необходимото довършване.

## Изграждане

1. Инсталирай Node 22+ и Python 3.11+.
2. `npm ci` и `npm run build` в корена.
3. `pip install -r requirements.txt` в `backend/`.
4. Конфигурирай PostgreSQL DATABASE_URL и PUBLIC_ORIGIN.
5. `python -m alembic upgrade head`.
6. `python -m app.seed` **само в демо среда**. Seed създава измислени кина и програма; не го използвай като търговски каталог.
7. `python -m app.cli create-admin --email ...` — интерактивна парола.
8. `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` зад HTTPS reverse proxy. FastAPI обслужва frontend build от `dist/`.

Dockerfile и Compose подготвят същата демо среда с PostgreSQL. Compose публикува само localhost:8000 и не излага PostgreSQL порт. `docker compose up --build` изисква случайна POSTGRES_PASSWORD в `.env`; използвай hex парола, за да е безопасна в URL. Volume `cinema_data` запазва данните; не го премахвай, когато искаш да запазиш поръчките.

## Настройки

- `DATABASE_URL`: PostgreSQL в production; SQLite се отказва при production startup.
- `ENVIRONMENT=production`: Secure cookie, HSTS, изключени OpenAPI docs, строг Origin.
- `PUBLIC_ORIGIN=https://your-domain`: точният публичен HTTPS произход без краен slash.
- `HOLD_SECONDS=300`, `MAX_SEATS=8`.
- `PAYMENT_MODE=simulation`: учебна картова форма и контролирана успешна/отказана транзакция. Старият alias `demo` се приема за съвместимост. Друга стойност отказва checkout.
- SMTP полетата са незадължителни за password recovery; настрой TLS и отделен акаунт.

В production не използвай Vite dev server. HTTPS termination трябва да изпраща коректни forwarded headers и да ограничава доверените proxy адреси. Сайтът очаква frontend и API от един произход; не е необходим wildcard CORS.

## Преди реална услуга

Трябва да бъдат реализирани и проверени: PSP checkout, signature verification и уникални webhook events; refund workflow; email verification и ticket delivery с durable queue; общ rate limiter; почистване на изтекли записи и tokens; валидиране на PostgreSQL конкурентност; пълен GDPR retention/deletion процес; правно одобрени политики и права върху изображения; метаданни/canonical и sitemap за реален домейн; автоматизирани backups, monitoring и възстановяване при инцидент. Направи отделни integration, load, security и accessibility проверки.

Не маркирай реална поръчка като paid/confirmed чрез административна промяна на статус или frontend redirect. Потвърждението трябва да произлиза от валидиран платежен доставчик в транзакционния service слой.
