# ESP32 / Wokwi и Raspberry Pi

Сайтът, автоматът и входният контрол използват една FastAPI услуга и една база. Няма директно изпращане на билети между устройствата. Сървърът определя наличността, цената, плащането и дали билетът вече е използван.

## Ключове

От `backend/`, след миграциите:

```powershell
python -m app.device_cli create --name "Автомат 1" --role kiosk
python -m app.device_cli create --name "Вход зала 1" --role validator --auditorium-id 1
python -m app.device_cli revoke DEVICE_ID
```

Ключът се показва само веднъж; базата пази хеш. Пази го извън публичния Wokwi проект. Validator не може да продава, kiosk не може да валидира. Опционалният `auditorium-id` ограничава достъпа до залата. Служебният профил на устройството няма интерактивен вход. Отзоваването действа от следващата заявка.

Всички заявки имат `Authorization: Bearer DEVICE_KEY`. POST изисква `Content-Type: application/json`. Cookie сесия и `X-Requested-With` не са нужни за тези bearer endpoints; уеб маршрутите запазват CSRF защитата.

## Продажба от автомат

1. `GET /api/v1/devices/showtimes` — актуални прожекции и ID.
2. `GET /api/v1/devices/showtimes/SHOWTIME_ID/seats` — seat ID и наличност.
3. `POST /api/v1/devices/bookings/holds` с `{"showtime_id":123,"seat_ids":[41]}` — връща `id` на задържането за 5 минути. Местата са общи със сайта.
4. `POST /api/v1/devices/payments/checkout` с `{"hold_id":"HOLD_ID","terms":true,"transaction_success":true}`.
5. При `success:true` покажи/отпечатай `tickets[].ticket_code`. За един билет има и `ticket_code`. При изгубен отговор повтори със същия hold ID: поръчката и кодовете са същите.

Примерен резултат:

```json
{
  "success": true,
  "booking_id": "...",
  "status": "confirmed",
  "movie": "Последната орбита",
  "showtime": "2026-10-28T17:00:00+00:00",
  "tickets": [{ "ticket_code": "482617", "seat": "A1", "status": "valid" }],
  "ticket_code": "482617"
}
```

`transaction_success:false` или липсващо поле отказва учебната транзакция и освобождава местата: `success:false`, `status:"cancelled"`, празни `tickets`. Започни нов hold за нов опит. Не се обработват банкови карти или реални средства.

## Вход с keypad

Избери ID на прожекцията от програмата. След точно 6 ASCII цифри изпрати:

```http
POST /api/validator/validate
Authorization: Bearer DEVICE_KEY
Content-Type: application/json

{"ticket_code":"482617","showtime_id":123}
```

Работи и `POST /api/v1/devices/tickets/validate`. Успехът включва `valid:true`, `ticket_code`, `movie`, `seat`, `status:"used"`, `message`. Зелена светлина и отваряне на входа само при HTTP 200 и `valid:true`. Логическите откази са HTTP 200 с `valid:false`, `reason`, `message`: `invalid_code`, `wrong_showtime` (включително друга зала), `cancelled`, `expired`, `already_used`. Невалиден формат е 422, липсващ/отзован ключ — 401, грешна роля — 403, лимит — 429.

Проверката и маркирането са една транзакция. При два едновременни опита само единият успява. При изгубен успешен отговор повторният опит връща `already_used`; няма автоматично повторно отключване или офлайн разрешение. Не използвай локално копие като източник на истина.

Кодът е случаен от 100000 до 999999, уникален и не се използва повторно. Има 900000 възможни стойности; преди изчерпването трябва да се увеличи дължината чрез миграция. Кодът не замества ключа на устройството. Лимити: 30 проверки/минута на validator, 120 удостоверявания/минута на IP. Лимитерът е за един процес.

## Мрежа

`127.0.0.1` в ESP32 симулатора не сочи към компютъра със сайта. За локален backend Wokwi предлага частен IoT gateway и `host.wokwi.internal`; публичният gateway не дава достъп до локалната мрежа. Виж [ESP32 WiFi](https://docs.wokwi.com/guides/esp32-wifi) и [VS Code конфигурация](https://docs.wokwi.com/vscode/project-config).

За физически Pi използвай LAN адрес или HTTPS домейн. Само при необходимост стартирай backend с `--host 0.0.0.0` в доверена мрежа; launcher слуша на localhost. За отдалечен достъп използвай HTTPS и проверка на сертификати.

Firmware, keypad, дисплей, принтер и реална Wokwi симулация са следваща стъпка. API договорът и конкурентните проверки са тествани. Минимален клиент: [`hardware/raspberry-pi/validate_ticket.py`](../../hardware/raspberry-pi/validate_ticket.py), с URL, ключ и прожекция от environment.
