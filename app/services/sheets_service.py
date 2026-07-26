"""Запис опублікованих товарів у Google Sheets через Apps Script Web App.

Замість сервіс-акаунта використовуємо простий веб-застосунок Apps Script,
розгорнутий прямо в таблиці (див. google_apps_script.gs). Додаток надсилає
POST-запит, а скрипт додає рядок і за потреби створює заголовки.
"""
from __future__ import annotations

import httpx

from app import config


def append_sale(product_id: str, description: str, price: str, caption: str, post_url: str = "") -> None:
    """Додає рядок продажу в таблицю. Якщо URL не налаштований — тихо пропускає."""
    if not config.SHEETS_WEBHOOK_URL:
        return

    payload = {
        "token": config.SHEETS_WEBHOOK_TOKEN,
        "type": "sale",
        "product_id": product_id,
        "description": description,
        "price": price,
        "caption": caption,
        "post_url": post_url,
    }
    resp = httpx.post(config.SHEETS_WEBHOOK_URL, json=payload, timeout=30, follow_redirects=True)
    resp.raise_for_status()
