"""Запис у Google Sheets через універсальний Apps Script Web App.

Додаток сам передає назву аркуша, заголовки та рядок — Apps Script лише додає рядок
(і за потреби створює аркуш із заголовками). Див. google_apps_script.gs.
"""
from __future__ import annotations

import json as _json
from datetime import datetime, timezone

import httpx

from app import config


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def _post(sheet: str, header: list[str], row: list) -> None:
    """Надсилає рядок у вказаний аркуш. Якщо URL не налаштований — тихо пропускає."""
    if not config.SHEETS_WEBHOOK_URL:
        return
    payload = {
        "token": config.SHEETS_WEBHOOK_TOKEN,
        "sheet": sheet,
        "header": header,
        "row": [("" if v is None else str(v)) for v in row],
    }
    resp = httpx.post(
        config.SHEETS_WEBHOOK_URL,
        content=_json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=30,
        follow_redirects=True,
    )
    resp.raise_for_status()


# --- Опубліковані товари (публікації з дашборда) ---
_SALE_HEADER = ["Дата", "ID товару", "Опис", "Ціна", "Підпис", "Посилання на пост"]


def append_sale(product_id: str, description: str, price: str, caption: str, post_url: str = "") -> None:
    _post("Опубліковані товари", _SALE_HEADER, [_now(), product_id, description, price, caption, post_url])


# --- Повідомлення (переписка з клієнтами) ---
_MESSAGE_HEADER = ["Дата", "Telegram ID", "Нікнейм", "Ім'я", "Телефон", "Запитання", "Відповідь", "Тип"]


def log_message(tg_id, username: str, name: str, phone: str,
                question: str, answer: str, kind: str = "") -> None:
    """Додає рядок переписки в аркуш «Повідомлення». Помилки не піднімає нагору."""
    try:
        _post("Повідомлення", _MESSAGE_HEADER,
              [_now(), tg_id, username, name, phone, question, answer, kind])
    except Exception as e:  # noqa: BLE001 — лог не має ламати відповідь бота
        print(f"[sheets_service] log_message failed: {e}")


# --- Натиснули Оплатити через бота ---
_PAYMENT_HEADER = ["Дата", "Telegram ID", "Нікнейм", "Ім'я", "Телефон", "Дія"]


def log_payment_click(tg_id, username: str, name: str, phone: str) -> None:
    """Кожне натискання «Оплатити» у боті — окремий рядок."""
    try:
        _post("Натиснули Оплатити через бота", _PAYMENT_HEADER,
              [_now(), tg_id, username, name, phone, "Натиснув «Оплатити»"])
    except Exception as e:  # noqa: BLE001
        print(f"[sheets_service] log_payment_click failed: {e}")


# --- Нові підписники каналу (Telegram) ---
_SUBSCRIBER_HEADER = ["Дата", "Telegram ID", "Нікнейм", "Ім'я", "Дія"]


def log_channel_subscriber(tg_id, username: str, name: str, action: str = "Приєднався до каналу") -> None:
    """Новий підписник каналу в Telegram — окремий рядок."""
    try:
        _post("Нові підписники каналу", _SUBSCRIBER_HEADER,
              [_now(), tg_id, username, name, action])
    except Exception as e:  # noqa: BLE001
        print(f"[sheets_service] log_channel_subscriber failed: {e}")


def history_for(tg_id, limit: int = 6) -> list[dict]:
    """Памʼять діалогу по Telegram ID: останні пари питання/відповідь цього клієнта
    з аркуша «Повідомлення» у форматі для Claude
    ([{'role':'user',...}, {'role':'assistant',...}, ...]).

    Використовується, щоб бот памʼятав контекст і не вітався щоразу.
    Будь-яка помилка → порожня історія (бот усе одно відповість).
    """
    try:
        rows: list = []
        for sh in read_all():
            if sh.get("name") == "Повідомлення":
                rows = sh.get("values", [])
                break
        tgid = str(tg_id)
        # колонки: Дата | Telegram ID | Нікнейм | Ім'я | Телефон | Запитання | Відповідь | Тип
        # (рядок-заголовок, якщо він є, відсіється фільтром r[7] == "повідомлення")
        pairs: list[tuple[str, str]] = []
        for r in rows:
            if len(r) >= 8 and str(r[1]) == tgid and r[7] == "повідомлення":
                q, a = (r[5] or "").strip(), (r[6] or "").strip()
                if q and a:
                    pairs.append((q, a))
        msgs: list[dict] = []
        for q, a in pairs[-limit:]:
            msgs.append({"role": "user", "content": q})
            msgs.append({"role": "assistant", "content": a})
        return msgs
    except Exception as e:  # noqa: BLE001 — памʼять не має ламати відповідь
        print(f"[sheets_service] history_for failed: {e}")
        return []


def read_all() -> list[dict]:
    """Читає всі аркуші через Apps Script (doGet). Повертає [{name, values}]."""
    if not config.SHEETS_WEBHOOK_URL:
        return []
    resp = httpx.get(
        config.SHEETS_WEBHOOK_URL,
        params={"token": config.SHEETS_WEBHOOK_TOKEN},
        timeout=30,
        follow_redirects=True,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("sheets", []) if data.get("ok") else []
