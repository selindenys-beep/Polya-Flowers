"""Обробка реального фото товару: акуратна композиція на гарному фоні + підпис.

ВАЖЛИВО: ми покращуємо СПРАВЖНЄ фото букета (а не генеруємо вигаданий),
щоб клієнт отримав саме те, що бачить на зображенні.

Поточна реалізація (MVP) — локальна, без зовнішніх API: масштабування,
м'який градієнтний фон-підкладка та текстовий підпис. Пізніше сюди можна
додати якісне видалення фону (rembg / remove.bg / OpenAI) — інтерфейс не зміниться.
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

CANVAS = (1080, 1350)  # вертикальний формат, зручний для Telegram/Instagram


def _gradient_background(size: tuple[int, int]) -> Image.Image:
    """М'який теплий градієнт як фон-підкладка."""
    w, h = size
    top, bottom = (250, 244, 247), (233, 222, 236)  # ніжні пастельні тони
    bg = Image.new("RGB", size)
    px = bg.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return bg


def process(photo_bytes: bytes, caption: str | None = None) -> bytes:
    """Повертає JPEG-байти обробленого зображення для попереднього перегляду/публікації."""
    product = Image.open(io.BytesIO(photo_bytes)).convert("RGB")

    canvas = _gradient_background(CANVAS)
    max_w, max_h = int(CANVAS[0] * 0.86), int(CANVAS[1] * 0.74)
    product.thumbnail((max_w, max_h), Image.LANCZOS)
    x = (CANVAS[0] - product.width) // 2
    y = int(CANVAS[1] * 0.06)
    canvas.paste(product, (x, y))

    if caption:
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 40)
        except OSError:
            font = ImageFont.load_default()
        first_line = caption.strip().splitlines()[0][:60]
        tw = draw.textlength(first_line, font=font)
        draw.text(((CANVAS[0] - tw) / 2, int(CANVAS[1] * 0.86)), first_line,
                  fill=(90, 60, 80), font=font)

    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=90)
    return out.getvalue()
