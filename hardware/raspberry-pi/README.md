# Raspberry Pi клиент за входен контрол

`validate_ticket.py` е минимален терминален клиент за общия API. Използва стандартната Python библиотека. Въвеждането чрез `input()` може да бъде заменено с keypad обработчик; GPIO и реле не са реализирани.

## Стартиране

Създай validator ключ от `software/backend/`, избери бъдеща прожекция и задай средата. Пример за PowerShell при локално изпитване:

```powershell
$env:PUKANKOV_URL='http://127.0.0.1:8000'
$env:PUKANKOV_DEVICE_KEY='PASTE_YOUR_PRIVATE_DEVICE_KEY'
$env:PUKANKOV_SHOWTIME_ID='123'
python hardware/raspberry-pi/validate_ticket.py
```

На Raspberry Pi / Linux, от корена:

```bash
export PUKANKOV_URL='https://your-cinema-host.example'
read -rsp 'Device key: ' PUKANKOV_DEVICE_KEY; echo
export PUKANKOV_DEVICE_KEY
export PUKANKOV_SHOWTIME_ID='123'
python3 hardware/raspberry-pi/validate_ticket.py
```

Замени примерния адрес и ID с действителните. Ключът не се записва в кода. Ако Pi и backend са на различни машини, използвай достъпен LAN адрес или HTTPS домейн.

Въведи точно 6 цифри. Празен ред прекратява програмата. При timeout, мрежова грешка или отрицателен отговор няма разрешение за вход. При положителен отговор билетът вече е отбелязан като използван на сървъра; това е реална промяна на тестовия билет.

## Статус на проверката

Клиентът е синтактично проверен и API е покрит с автоматизирани тестове. Изпитване върху физическо Raspberry Pi, keypad и реле не е извършвано. Виж [сценариите](../docs/validation-scenarios.md).
