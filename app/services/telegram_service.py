"""Публікація товару в Telegram-групу з кнопками під постом."""
from __future__ import annotations

import httpx

from app import config

_API = "https://api.telegram.org/bot{token}/{method}"


def _url(method: str) -> str:
    return _API.format(token=config.TELEGRAM_BOT_TOKEN, method=method)


def build_keyboard(product_id: str) -> dict:
    """Кнопки під публікацією: оплата, питання, доставка.

    Усі три — зовнішні посилання:
    «Оплатити» — банка monobank.
    «Задати питання» / «Доставка» — діп-лінк у приватний чат із ботом
    (t.me/<bot>?start=…), де бот продовжує спілкування (а не в групі).
    """
    bot = config.TELEGRAM_BOT_USERNAME
    return {
        "inline_keyboard": [
            # Оплата веде в бота (?start=pay) — щоб зафіксувати натискання,
            # далі бот дає кнопку переходу на monobank.
            [{"text": "💳 Оплатити", "url": f"https://t.me/{bot}?start=pay"}],
            [
                {"text": "❓ Задати питання", "url": f"https://t.me/{bot}?start=ask"},
                {"text": "🚚 Доставка", "url": f"https://t.me/{bot}?start=delivery"},
            ],
            [{"text": "🌐 Перейти на сайт", "url": config.SITE_URL}],
        ]
    }


def send_message(chat_id: int | str, text: str, reply_to: int | None = None,
                 reply_markup: dict | None = None) -> dict:
    """Надсилає текстове повідомлення від імені бота (за потреби з кнопками)."""
    data = {"chat_id": chat_id, "text": text}
    if reply_to:
        data["reply_parameters"] = __import__("json").dumps({"message_id": reply_to, "allow_sending_without_reply": True})
    if reply_markup:
        data["reply_markup"] = __import__("json").dumps(reply_markup)
    resp = httpx.post(_url("sendMessage"), data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def answer_callback(callback_query_id: str, text: str = "") -> None:
    """Підтверджує натискання inline-кнопки (прибирає «годинник» на кнопці)."""
    httpx.post(
        _url("answerCallbackQuery"),
        data={"callback_query_id": callback_query_id, "text": text},
        timeout=30,
    )


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
