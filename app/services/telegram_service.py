"""Публікація товару в Telegram-групу з кнопками під постом."""
from __future__ import annotations

import httpx

from app import config

_API = "https://api.telegram.org/bot{token}/{method}"


def _url(method: str) -> str:
    return _API.format(token=config.TELEGRAM_BOT_TOKEN, method=method)


def _preset_rows(selected) -> list:
    """Рядки для стандартних кнопок: pay / ask / delivery / site."""
    bot = config.TELEGRAM_BOT_USERNAME
    rows = []
    if "pay" in selected:
        rows.append([{"text": "💳 Оплатити", "url": f"https://t.me/{bot}?start=pay"}])
    second = []
    if "ask" in selected:
        second.append({"text": "❓ Задати питання", "url": f"https://t.me/{bot}?start=ask"})
    if "delivery" in selected:
        second.append({"text": "🚚 Доставка", "url": f"https://t.me/{bot}?start=delivery"})
    if second:
        rows.append(second)
    if "site" in selected:
        rows.append([{"text": "🌐 Перейти на сайт", "url": config.SITE_URL}])
    return rows


def build_keyboard(product_id: str = "", custom: list | None = None,
                   presets=("pay", "ask", "delivery", "site")) -> dict | None:
    """Клавіатура: власні кнопки (custom = [{text,url}]) + стандартні (presets).

    Повертає None, якщо кнопок немає (щоб пост був без клавіатури).
    """
    inline = []
    for b in (custom or []):
        text, url = (b.get("text") or "").strip(), (b.get("url") or "").strip()
        if text and url:
            inline.append([{"text": text, "url": url}])
    inline += _preset_rows(set(presets or ()))
    return {"inline_keyboard": inline} if inline else None


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


def publish_product(photo_bytes: bytes | None, caption: str,
                    product_id: str = "", keyboard: dict | None = "__default__") -> list[dict]:
    """Публікує в усі цілі (група/канал). З фото (sendPhoto) або без (sendMessage).

    keyboard: dict із кнопками; None — без кнопок; "__default__" — стандартні 4 кнопки.
    Повертає список відповідей Telegram API.
    """
    targets = config.telegram_targets()
    if not config.TELEGRAM_BOT_TOKEN or not targets:
        raise RuntimeError("Не налаштовано TELEGRAM_BOT_TOKEN або ціль публікації "
                           "(TELEGRAM_GROUP_CHAT_ID / TELEGRAM_CHANNEL_CHAT_ID)")
    if keyboard == "__default__":
        keyboard = build_keyboard(product_id)

    import json as _json
    markup = _json.dumps(keyboard) if keyboard else None
    results = []
    for chat_id in targets:
        if photo_bytes:
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            if markup:
                data["reply_markup"] = markup
            resp = httpx.post(_url("sendPhoto"), data=data,
                              files={"photo": ("product.jpg", photo_bytes, "image/jpeg")}, timeout=60)
        else:
            data = {"chat_id": chat_id, "text": caption, "parse_mode": "HTML",
                    "disable_web_page_preview": False}
            if markup:
                data["reply_markup"] = markup
            resp = httpx.post(_url("sendMessage"), data=data, timeout=60)
        resp.raise_for_status()
        results.append(resp.json())
    return results
