"""Обробка реального фото товару: заміна фону через OpenAI gpt-image-1.

ВАЖЛИВО: ми покращуємо СПРАВЖНЄ фото виробу — модель отримує інструкцію
залишити саму квітку/букет НЕЗМІННИМ (кольори, форма, деталі) і замінити лише
тло на гарне студійне. Якщо OpenAI недоступний — тихий фолбек: фото на м'якій
пастельній підкладці (без заміни фону).
"""
from __future__ import annotations

import base64
import io

from openai import OpenAI
from PIL import Image

from app import config

CANVAS = (1080, 1350)  # вертикальний формат для фолбеку

# Промт для заміни фону. Сформульований так, щоб зберегти сам виріб незмінним.
BACKGROUND_PROMPT = (
    "Replace ONLY the background behind this handmade flower with a soft, elegant, "
    "slightly blurred pastel studio backdrop (gentle light pink and lavender tones, "
    "like a cozy florist boutique, with soft natural light and subtle bokeh). "
    "Keep the handmade flower itself completely unchanged and photorealistic: exact same "
    "colors, shape, petals, texture and details. Do not add or remove anything from the flower. "
    "Center the flower nicely. High quality, clean, professional product photo."
)


def _simple_composite(photo_bytes: bytes) -> bytes:
    """Фолбек: фото на м'якій градієнтній підкладці, без заміни фону."""
    product = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    w, h = CANVAS
    top, bottom = (250, 244, 247), (233, 222, 236)
    canvas = Image.new("RGB", CANVAS)
    px = canvas.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px_row = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(w):
            px[x, y] = px_row
    product.thumbnail((int(w * 0.9), int(h * 0.9)), Image.LANCZOS)
    canvas.paste(product, ((w - product.width) // 2, (h - product.height) // 2))
    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=90)
    return out.getvalue()


def _openai_replace_background(photo_bytes: bytes) -> bytes:
    """Заміна фону через gpt-image-1. Кидає виняток, якщо не вдалося."""
    img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    img.thumbnail((1024, 1024), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.name = "flower.png"
    buf.seek(0)

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.images.edit(
        model="gpt-image-1",
        image=buf,
        prompt=BACKGROUND_PROMPT,
        size="1024x1536",
        quality="medium",  # баланс якість/вартість (~кілька центів за фото)
    )
    return base64.b64decode(resp.data[0].b64_json)


def process(photo_bytes: bytes, caption: str | None = None) -> bytes:
    """Повертає JPEG/PNG-байти обробленого фото. Пробує OpenAI, інакше — фолбек."""
    if config.OPENAI_API_KEY:
        try:
            return _openai_replace_background(photo_bytes)
        except Exception as e:  # noqa: BLE001 — не валимо публікацію через фон
            print(f"[image_service] OpenAI fallback: {e}")
    return _simple_composite(photo_bytes)
