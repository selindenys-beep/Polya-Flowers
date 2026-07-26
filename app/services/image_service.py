"""Обробка реального фото товару.

ВАЖЛИВО: ми покращуємо СПРАВЖНЄ фото виробу (а не генеруємо вигаданий),
щоб клієнт отримав саме те, що бачить на зображенні.

Поточна реалізація (без видалення фону): приводимо фото до єдиного вертикального
формату на м'якій пастельній підкладці. Підпис у фото НЕ вписуємо — він іде окремим
текстом посту. Заміна фону (вирізання квітки) додається окремо (див. remove_background).
"""
from __future__ import annotations

import io

from PIL import Image

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
    """Повертає JPEG-байти обробленого фото для перегляду/публікації."""
    product = Image.open(io.BytesIO(photo_bytes)).convert("RGB")

    canvas = _gradient_background(CANVAS)
    max_w, max_h = int(CANVAS[0] * 0.9), int(CANVAS[1] * 0.9)
    product.thumbnail((max_w, max_h), Image.LANCZOS)
    x = (CANVAS[0] - product.width) // 2
    y = (CANVAS[1] - product.height) // 2
    canvas.paste(product, (x, y))

    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=90)
    return out.getvalue()
