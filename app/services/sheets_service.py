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


# --- Продажі ---
_SALE_HEADER = ["Дата", "ID товару", "Опис", "Ціна", "Підпис", "Посилання на пост"]


def append_sale(product_id: str, description: str, price: str, caption: str, post_url: str = "") -> None:
    _post("Продажі", _SALE_HEADER, [_now(), product_id, description, price, caption, post_url])


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
