# Публичен API за ESP32: филм → прожекция → място → плащане

**RFID четенето е изцяло в ESP32.** Към сървъра не се изпращат UID, номер на карта или данни за четеца. Няма регистрация на карти и няма баланс. Устройството изпраща само `payment_success: true` или `false` за вече създадената резервация. Това е учебната логика на терминала, без банков доставчик.

## Общ backend и публичен адрес

За постоянен адрес използвай [настройката с фиксиран ngrok домейн](stable-public-api.md)
и `START-STABLE-API.cmd`. Описаните по-долу временни тунели са за кратки тестове.

Сайтът на порт 8000 и отделният `app.public_gateway:app` на порт 8002 използват една база. Свободните, задържаните и продадените места са общи. Тунелът публикува gateway, без уеб администрацията, акаунтите или файла на базата.

От `software/`, с инсталиран официален [cloudflared](https://developers.cloudflare.com/tunnel/get-started/):

```powershell
python scripts/run_public_api.py --cloudflared C:/tools/cloudflared.exe
```

При съществуваща база от друго копие на сайта:

```powershell
python scripts/run_public_api.py --database-path C:/path/to/backend/pukankov.db --cloudflared C:/tools/cloudflared.exe
```

Launcher прилага миграциите, обновява програмата и отпечатва `PUBLIC_API_URL`. Адресът и текущото състояние са в `.local/public-api.json`. Остави терминала отворен; Ctrl+C спира API и тунела. Без тунел: `--local-only`. Порт: `--port 8002`.

[Cloudflare Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) не изисква акаунт и дава временен HTTPS адрес. Адресът се сменя при нов тунел и работи докато процесите и компютърът работят. За постоянен адрес използвай named tunnel с домейн или постоянно хостване.

В подготвената локална среда `outputs/START-PUBLIC-API.cmd` използва базата на съществуващия сайт. Общият `DATABASE_URL` е записан и в игнорирания `backend/.env`, за да сочат локалните CLI команди към същата база.

## Ключ на терминала

Създаване от `software/backend/`:

```powershell
python -m app.device_cli create --name "ESP32 ticket kiosk" --role kiosk
```

Към всяка `/api/v1/devices/*` заявка добави:

```http
Authorization: Bearer YOUR_DEVICE_KEY
Content-Type: application/json
```

Няма cookie или браузърен вход. Swagger е на `<BASE_URL>/api/docs` → **Authorize** → само ключът, без префикса Bearer. Health е `GET /api/v1/health` и не изисква ключ.

Ключът на вече подготвеното устройство е в `.local/esp32.private.json`, извън Git, заедно с текущия адрес. Не го публикувай в GitHub или публичен Wokwi sketch. Launcher обновява адреса в този файл при нов тунел.

## 1. Филми с бъдещи прожекции

```http
GET /api/v1/devices/movies
```

```json
[
  {
    "id": 28,
    "title": "Град от светлина",
    "duration": 118,
    "age": "12+",
    "year": 2026
  }
]
```

Филтри: `q`, `date=YYYY-MM-DD`, `cinema_id`. Предстоящи филми без програма не се връщат. Всички числови ID в този документ са примери — вземи действителните от отговорите.

## 2. Дата, час и зала

```http
GET /api/v1/devices/showtimes?movie_id=28&date=2026-10-29&limit=10&offset=0
```

Допълнителни филтри: `cinema_id`, `from_hour=0..23`, `to_hour=1..24` (краят е изключен). `limit`: 1–100, по подразбиране 25; за следваща страница увеличи `offset`. `X-Total-Count` е общият брой.

```json
[
  {
    "id": 149,
    "movie_id": 28,
    "movie_title": "Град от светлина",
    "cinema_id": 1,
    "cinema": "Пуканков Витоша",
    "city": "София",
    "auditorium_id": 1,
    "auditorium": "Зала 1 · IMAX",
    "date": "2026-10-29",
    "time": "18:00",
    "starts_at": "2026-10-29T16:00:00+00:00",
    "format": "IMAX",
    "price": 12,
    "currency": "EUR",
    "timezone": "Europe/Sofia",
    "available_seats": 84,
    "held_seats": 0,
    "sold_seats": 0
  }
]
```

Дата и час са местни за Europe/Sofia; `starts_at` е UTC. Изтеклите holds не намаляват свободния брой. Наличността е моментна снимка — окончателната проверка става при POST hold.

## 3. Свободно място

```http
GET /api/v1/devices/showtimes/149/seats
```

Отговорът съдържа `showtime`, `max_seats`, `seats`. Столът има `id`, `row`, `number`, `category`, `price`, `accessible`, `status`. Избирай само `status:"available"`. Другите са `held`, `sold`, `unavailable`.

**Изпращай `seat.id`, а не номера на стола.** Номерата се повтарят по редове и зали. Премиум място може да има по-висока цена.

## 4. Резервация за 5 минути

```http
POST /api/v1/devices/bookings/holds

{"showtime_id":149,"seat_ids":[1]}
```

HTTP 201 връща `id`, `status`, `expires_at`, `server_time`, `showtime`, `items`, `total`. Запази **hold ID**. До 8 места; задържането веднага е видимо в сайта.

- Проверка: `GET /api/v1/devices/bookings/holds/HOLD_ID`.
- Отказ: `DELETE /api/v1/devices/bookings/holds/HOLD_ID`.

Терминалът може да управлява само собствените си holds.

## 5. Резултат от локалното RFID четене

ESP32 чака карта и я чете локално. При успешно четене:

```http
POST /api/v1/devices/payments/checkout

{"hold_id":"HOLD_ID","payment_success":true}
```

Не изпращай UID. При липса на карта продължи да чакаш локално; не изпращай false при всяко празно polling прочитане. `false` е окончателен отказ/грешка на тази покупка.

Входни полета: `hold_id`, задължителен JSON boolean `payment_success`, опционален `promo_code`, опционален `terms` (по подразбиране true; false отказва заявката). Клиентска сума, UID и `transaction_success` не се приемат. Сумата се взема от задържаните места на сървъра.

Успех:

```json
{
  "success": true,
  "booking_id": "PK-...",
  "status": "confirmed",
  "movie": "Град от светлина",
  "showtime_id": 149,
  "date": "2026-10-29",
  "showtime": "18:00",
  "starts_at": "2026-10-29T16:00:00+00:00",
  "amount": 12,
  "currency": "EUR",
  "payment_method": "terminal_signal",
  "is_simulation": true,
  "tickets": [{ "ticket_code": "482617", "seat": "A1", "status": "valid" }],
  "ticket_code": "482617"
}
```

Използвай `tickets[]`, когато има повече от един билет; единичното `ticket_code` тогава е null. Receipt: `GET /api/v1/devices/bookings/BOOKING_ID`. Използван билет се връща със `status:"used"`.

При `payment_success:false` се връща HTTP 200 със `success:false`, `status:"cancelled"`, празни `tickets` и освободени места. За нов опит започни нов hold.

**При timeout повтори същия hold и същия резултат.** Сървърът връща същата поръчка, без дублиране. Първият записан резултат е окончателен: false след true не отменя билет; true след false не съживява отказан hold.

## Статуси и достъп

| HTTP | Значение                                                            |
| ---- | ------------------------------------------------------------------- |
| 401  | Липсващ, невалиден или отзован device ключ                          |
| 403  | Грешна роля или зала                                                |
| 404  | Липсваща или чужда резервация/поръчка                               |
| 409  | Заето място, отменена прожекция или изтекъл hold                    |
| 422  | Невалидна дата/час/payload; липсващ или не-boolean резултат         |
| 429  | 20 платежни опита/минута/устройство; общо 120 auth заявки/минута/IP |

За еднократно допускане създай отделен `validator` ключ и изпрати `ticket_code` (опционално `showtime_id` за конкретна прожекция) на `POST /api/validator/validate`. Kiosk ключът не може да валидира. Виж [devices.md](devices.md).

Няма API за RFID карти или картови таблици в актуалната схема. Схемата на Payment/Booking пази резултата, сумата и историята. Миграция `0004` премахва старите картови таблици, запазвайки поръчките и записите за плащане.

## ESP32 логика

```cpp
// RFID library and UID processing stay on the terminal.
if (cardReadSuccessfully) {
  // POST /api/v1/devices/payments/checkout
  // {"hold_id":"savedHoldId","payment_success":true}
}
```

Използвай HTTPS с проверка на CA и актуален часовник, без `setInsecure()`. Подготвените заявки са в [esp32-terminal.http](examples/esp32-terminal.http). Firmware за конкретен дисплей/keypad/RFID четец и физическа Wokwi симулация са отделен хардуерен етап.
