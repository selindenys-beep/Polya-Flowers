"""Сповіщення адмінам через окремий бот-нотифікатор (@Polya_Flowers_Notice_bot).

Надсилає повідомлення на всі NOTIFY_CHAT_IDS про події:
натискання «Оплатити» у боті, «Купити» на сайті, заповнення форми зворотного звʼязку.
"""
from __future__ import annotations

import httpx

from app import config


def _send(text: str) -> None:
    if not config.NOTIFY_BOT_TOKEN or not config.NOTIFY_CHAT_IDS:
        return
    url = f"https://api.telegram.org/bot{config.NOTIFY_BOT_TOKEN}/sendMessage"
    for chat_id in config.NOTIFY_CHAT_IDS:
        try:
            httpx.post(url, data={"chat_id": chat_id, "text": text,
                                  "disable_web_page_preview": True}, timeout=20)
        except Exception as e:  # noqa: BLE001 — сповіщення не має ламати основний потік
            print(f"[notify_service] send failed to {chat_id}: {e}")


def _client_lines(username: str = "", tg_id="", name: str = "", phone: str = "") -> str:
    lines = []
    if name:
        lines.append(f"👤 Ім'я: {name}")
    if phone:
        lines.append(f"📞 Телефон: {phone}")
    if username:
        lines.append(f"🔗 Username: {username}")
    if tg_id:
        lines.append(f"🆔 ID: {tg_id}")
    return "\n".join(lines) if lines else "ℹ️ Даних про клієнта немає"


def notify_bot_pay(tg_id="", username: str = "", name: str = "", phone: str = "") -> None:
    _send("💳 Натиснули «Оплатити» у Telegram-боті!\n\n"
          + _client_lines(username, tg_id, name, phone))


def notify_site_buy(product: str = "", price: str = "", color: str = "",
                    scent: str = "", phone: str = "") -> None:
    details = [f"🌸 Товар: {product}" if product else ""]
    if price:
        details.append(f"💰 Ціна: {price}")
    if color:
        details.append(f"🎨 Колір: {color}")
    if scent:
        details.append(f"🧴 Аромат: {scent}")
    if phone:
        details.append(f"📞 Телефон: {phone}")
    body = "\n".join(d for d in details if d)
    _send("🛒 Нове замовлення з САЙТУ (натиснули «Купити»)!\n\n" + body)


def notify_feedback(name: str = "", phone: str = "") -> None:
    _send("✉️ Нова заявка з форми «Зв'язатися зі мною» (сайт)!\n\n"
          + _client_lines(name=name, phone=phone))
