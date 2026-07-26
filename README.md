# Polya-Flowers 🌸

Автоматизація продажу квітів ручної роботи: дашборд для підготовки публікацій,
покращення фото, генерація підпису українською (Claude) та публікація в Telegram-групу
з кнопками оплати/питань/доставки. Продажі зберігаються в Google Sheets.

## Як це працює

1. Донька заходить у **дашборд**, завантажує фото букета, додає опис і ціну → **«Обробити»**.
2. Система покращує фото (гарний фон + підпис) і генерує текст (**Claude Sonnet**).
3. Вона бачить результат, за потреби редагує підпис → **«Публікація»**.
4. Пост із кнопками йде в **Telegram-групу**, запис додається в **Google Sheets**.
5. Питання/доставку в чаті обробляє бот (**Claude Haiku**) — додається наступним кроком.

## Технології

- **Python + FastAPI** — бекенд і дашборд
- **Claude** — Haiku (спілкування), Sonnet (тексти)
- **OpenAI / Pillow** — обробка фото
- **Telegram Bot API** — публікації та кнопки
- **Google Sheets** — облік продажів
- **monobank «Банка»** — оплата (Apple/Google Pay на боці клієнта)
- **Render** — хостинг з авто-деплоєм із GitHub

## Структура

```
app/
  main.py              # маршрути FastAPI + логіка дашборда
  config.py            # читання секретів зі змінних оточення
  services/
    text_service.py    # генерація підпису (Claude Sonnet)
    image_service.py   # обробка фото товару
    telegram_service.py# публікація в групу з кнопками
    sheets_service.py  # запис у Google Sheets
  templates/           # дашборд + логін (українською)
render.yaml            # blueprint для Render
.env.example           # перелік потрібних секретів
```

## Локальний запуск

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # заповнити значення
uvicorn app.main:app --reload
```
Відкрити http://localhost:8000

## Секрети

Ніколи не комітяться. Локально — у `.env`; на Render — у розділі **Environment**.
Перелік див. у [.env.example](.env.example).

## Деплой

Push у гілку `main` → Render автоматично перезбирає та оновлює сервіс.
