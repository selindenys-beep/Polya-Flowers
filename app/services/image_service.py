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

# Промт для сцени навколо виробу + брендинг. Сам виріб має лишитись незмінним.
BACKGROUND_PROMPT = (
    "The input is a photo of a REAL HANDMADE flower made from chenille / pipe cleaners. "
    "Create one elegant vertical product poster while keeping the handmade flower EXACTLY as in the "
    "input — identical colors, exact same petals, shape, texture and fine details. "
    "CRITICAL: do NOT change or shift the flower's COLORS or shades in any way — the customer chose "
    "that exact shade, so every petal color must stay pixel-accurate to the input. "
    "Do NOT redraw, restyle, recolor, beautify, smooth or replace the flower. "
    "Only build a beautiful scene around it and add text.\n\n"
    "SCENE: place the flower as the hero, slightly above center, on a soft luxurious light-lavender "
    "silk/satin fabric backdrop with gentle folds and soft natural light. Tastefully decorate around it "
    "(not covering it): a few delicate sprigs of white baby's breath (gypsophila), a few stems of dried "
    "lavender in the corners, and a light scattering of small pearl beads. Elegant, soft, feminine, "
    "premium florist-boutique aesthetic, dreamy and clean.\n\n"
    "TEXT (render it crisp and spelled EXACTLY, no typos, in soft elegant purple tones, not covering the flower):\n"
    "  - top center, graceful calligraphy script, large: Polya Flowers\n"
    "  - just below, elegant script, medium: Handmade\n"
    "  - under it, small letter-spaced capitals with a tiny heart: WITH LOVE\n\n"
    "Portrait orientation, high quality, cohesive lavender color palette."
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
