"""Публікація товару в Telegram-групу з кнопками під постом."""
from __future__ import annotations

import httpx

from app import config

_API = "https://api.telegram.org/bot{token}/{method}"


def _url(method: str) -> str:
    return _API.format(token=config.TELEGRAM_BOT_TOKEN, method=method)


def build_keyboard(product_id: str) -> dict:
    """Кнопки під публікацією: оплата, питання, доставка.

    «Оплатити» — зовнішнє посилання на банку monobank.
    «Задати питання» та «Доставка» — callback, які обробляє бот (Haiku).
    """
    pay_url = config.MONOBANK_JAR_URL or config.PUBLIC_BASE_URL
    return {
        "inline_keyboard": [
            [{"text": "💳 Оплатити", "url": pay_url}],
            [
                {"text": "❓ Задати питання", "callback_data": f"ask:{product_id}"},
                {"text": "🚚 Доставка", "callback_data": f"delivery:{product_id}"},
            ],
        ]
    }


def publish_product(photo_bytes: bytes, caption: str, product_id: str) -> dict:
    """Надсилає фото з підписом і кнопками в групу. Повертає відповідь Telegram API."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_GROUP_CHAT_ID:
        raise RuntimeError("Не налаштовано TELEGRAM_BOT_TOKEN або TELEGRAM_GROUP_CHAT_ID")

    files = {"photo": ("product.jpg", photo_bytes, "image/jpeg")}
    data = {
        "chat_id": config.TELEGRAM_GROUP_CHAT_ID,
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": __import__("json").dumps(build_keyboard(product_id)),
    }
    resp = httpx.post(_url("sendPhoto"), data=data, files=files, timeout=60)
    resp.raise_for_status()
    return resp.json()
