# API

База: `/api/v1`. Интерактивна OpenAPI документация при development: `/api/docs`. Mutating заявки: `Content-Type: application/json` и `X-Requested-With: Pukankov`. Cookie сесията се управлява от браузъра. API връща `detail` при грешка; 401 за липсваща/изтекла сесия, 403 за права/CSRF, 404 за липсващ или чужд ресурс, 409 за конфликт, 422 за валидация, 429 за лимит.

## Публично

- `GET /health`
- `GET /movies?q=&genre=&year=&min_rating=&max_duration=&age=&status=&language=&sort=&page=&page_size=` → `{items,total,page,page_size}`. `sort`: popular/rating/newest/title. Максимум 50 резултата на страница.
- `GET /movies/featured`, `/movies/top`, `/movies/upcoming`
- `GET /movies/{id}`, `/movies/slug/{slug}`
- `GET /cinemas`, `/cinemas/{slug}`, `/cinemas/{id}/auditoriums`
- `GET /showtimes?movie_id=&cinema_id=&date=YYYY-MM-DD&from_hour=&to_hour=` → само бъдещи неотменени прожекции от видимия каталог; локален ден за Europe/Sofia.
- `GET /showtimes/{id}`, `/showtimes/{id}/seats`
- `GET /offers`

Не изпращай празни стойности за числовите query параметри; пропусни ги.

## Профили

- `POST /auth/register`: `{name,email,password,terms:true}`. Парола 10–64 символа. Роля винаги user.
- `POST /auth/login`: `{email,password}`
- `POST /auth/logout`
- `POST /auth/forgot-password`: `{email}`. Не разкрива дали съществува профил. `email_configured` показва само дали средата има SMTP.
- `POST /auth/reset-password`: `{token,password}`. Токените са еднократни и хеширани; 30 минути.
- `GET /me`, `PATCH /me` с `{name}`
- `POST /me/password`: `{current_password,password}`
- `GET /me/export`, `DELETE /me` (записва заявка за изтриване)
- `GET /me/favorites`, `POST /me/favorites/{movie_id}`, `DELETE /me/favorites/{movie_id}`

## Покупка

- `POST /bookings/holds`: `{showtime_id,seat_ids:[...]}` → `{id,expires_at,server_time,status,showtime,items,total}`. До 8 места, до 3 активни holds на потребител.
- `GET /bookings/holds/{id}`, `DELETE /bookings/holds/{id}`
- `POST /promotions/validate`: `{hold_id,code}` → `{code,discount,total}`
- `POST /payments/checkout`: `{hold_id,promo_code:"",terms:true,transaction_success:true}` → confirmed booking с `items[].ticket_code` (шестцифрен string). `transaction_success:false` или липсващо поле освобождава местата и записва cancelled booking без билети. Картови данни не се приемат/изискват. Режим: учебен симулатор.
- `POST /payments/webhooks/{provider}` → 503, доставчикът не е конфигуриран. Никакво външно събитие не потвърждава билет в тази версия.
- `GET /bookings/{id}`, `/me/bookings`, `/me/tickets` → само собствени записи.
- `POST /staff/tickets/validate`: `{ticket_code:"482617",showtime_id:123}` → атомарно проверява и маркира като използван; само staff/admin. Логическите откази, включително повторна употреба, връщат HTTP 200 с `valid:false`, `reason`, `message`. Успех: `valid:true`, данни за филм/място, `status:"used"`.

## Устройства

Bearer маршрути за kiosk/validator са описани в [devices.md](devices.md). Използват същите резервационни и билетни услуги и наличност като сайта. Поддържан е и `POST /api/validator/validate`.

## Администрация

Всички `/admin/*` изискват admin, дори при директни API заявки.

- `GET /admin/dashboard`
- `GET|POST /admin/movies`, `PUT /admin/movies/{id}`, `DELETE /admin/movies/{id}` (архив)
- `GET|POST /admin/showtimes`, `DELETE /admin/showtimes/{id}` (отмяна без продадени билети)
- `GET|POST /admin/cinemas`, `/admin/auditoriums`
- `PATCH /admin/seats/{id}`: `{category,surcharge,active}`; отказва промяна при съществуващ claim.
- `GET /admin/orders` → до 200 последни, включва събития и билети.
- `GET /admin/users?q=&role=&page=` → страници по 20.
- `PATCH /admin/users/{id}`: `{role,active}`; собствените права не могат да се променят.
- `GET|POST /admin/promotions`, `DELETE /admin/promotions/{id}` (деактивиране)
- `GET /admin/audit-logs` → до 200 последни.

Виж OpenAPI за полетата на административните форми. Новите прожекции изискват timezone-aware ISO timestamp, съществуващ филм/зала, поддържан формат, бъдещо начало и свободен интервал с 20 минути подготовка.
