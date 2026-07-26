"""Запис опублікованих товарів у Google Sheets."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

from app import config

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_HEADER = ["Дата", "ID товару", "Опис", "Ціна", "Підпис", "Посилання на пост"]


def _client() -> gspread.Client:
    """Авторизація сервіс-акаунтом: або з JSON у змінній, або з файлу."""
    if config.GOOGLE_SERVICE_ACCOUNT_JSON:
        info = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    else:
        creds = Credentials.from_service_account_file(
            config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=_SCOPES
        )
    return gspread.authorize(creds)


def append_sale(product_id: str, description: str, price: str, caption: str, post_url: str = "") -> None:
    """Додає рядок у перший аркуш таблиці. Створює заголовок, якщо аркуш порожній."""
    if not config.GOOGLE_SHEET_ID:
        raise RuntimeError("Не налаштовано GOOGLE_SHEET_ID")

    sheet = _client().open_by_key(config.GOOGLE_SHEET_ID).sheet1
    if not sheet.get_all_values():
        sheet.append_row(_HEADER, value_input_option="USER_ENTERED")

    row = [
        datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"),
        product_id,
        description,
        price,
        caption,
        post_url,
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")
