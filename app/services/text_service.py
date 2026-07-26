"""Генерація опису/підпису українською через Claude Sonnet (з баченням фото)."""
from __future__ import annotations

import base64
import io

from anthropic import Anthropic
from PIL import Image

from app import config

_SYSTEM = (
    "Ти — копірайтер невеликого сімейного магазину квітів ручної роботи «Polya Flowers». "
    "Пишеш українською мовою: тепло, елегантно, живо й лаконічно. "
    "Тобі показують ФОТО справжнього виробу ручної роботи. Уважно роздивись його "
    "(тип квітки/букета, кольори, матеріал, настрій) і напиши готовий привабливий підпис "
    "до посту в Telegram.\n"
    "Формат: 2–3 короткі речення, що описують саме те, що на фото, + доречні емодзі 💐 (помірно) "
    "+ окремим рядком ціна (якщо надана).\n"
    "Важливо: описуй лише те, що реально бачиш на фото. Не вигадуй складу чи розмірів, яких не видно. "
    "НЕ проси надіслати додаткові деталі — одразу дай завершений гарний підпис."
)


def _image_block(photo_bytes: bytes) -> dict:
    """Готує зображення для Claude (перекодовуємо в JPEG для сумісності)."""
    img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    img.thumbnail((1024, 1024), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    data = base64.b64encode(buf.getvalue()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}


def generate_caption(description: str, price: str | None = None, photo_bytes: bytes | None = None) -> str:
    """Повертає готовий підпис українською на основі фото та (за наявності) опису/ціни."""
    if not config.ANTHROPIC_API_KEY:
        parts = [description.strip() or "Ніжна квітка ручної роботи 💐"]
        if price:
            parts.append(f"Ціна: {price}")
        return "\n".join(parts)

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    hint = (
        f"Побажання майстрині до опису: {description}\n" if description.strip() else ""
    ) + f"Ціна: {price or '(не вказана)'}"

    content: list[dict] = []
    if photo_bytes:
        content.append(_image_block(photo_bytes))
    content.append({"type": "text", "text": hint + "\n\nНапиши підпис до цього товару."})

    message = client.messages.create(
        model=config.CLAUDE_TEXT_MODEL,
        max_tokens=500,
        system=_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(b.text for b in message.content if b.type == "text").strip()
