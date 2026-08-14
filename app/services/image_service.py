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

# Жорстке збереження самого виробу (застосовується завжди).
PRESERVE = (
    "The input is a photo of REAL HANDMADE flowers made from chenille / pipe cleaners "
    "(sometimes in a basket, a box or a bouquet). "
    "You MUST keep the product itself 100% UNCHANGED and photorealistic: exact same flowers, "
    "exact same COLORS and shades (do not recolor or shift any hue at all), exact same petal shapes, "
    "count, texture and arrangement. If flowers are in a basket, box or vase — keep that basket/box/vase "
    "EXACTLY as is too. Do NOT redraw, restyle, recolor, beautify, smooth, add or remove any flower. "
    "Intervene MINIMALLY: change ONLY the background behind the product and add the requested text. "
    "Portrait orientation, high quality."
)

# Фірмова сцена (за замовчуванням) — за референсом бренду.
BRAND_SCENE = (
    "\n\nSCENE: place the product as the hero, on a soft luxurious PINK silk/satin fabric backdrop "
    "with gentle folds, soft dreamy light and subtle bokeh sparkles. Tastefully decorate around it "
    "(never covering the flowers): delicate sprigs of white baby's breath (gypsophila), a few stems of "
    "purple lavender in the corners, and a light scattering of small white pearl beads. "
    "Elegant, soft, feminine, premium florist-boutique aesthetic.\n\n"
    "TEXT (render crisp, spelled EXACTLY, no typos, in deep elegant purple, not covering the flowers):\n"
    "  - top center, large graceful calligraphy script: Polya Flowers\n"
    "  - below, elegant script between two short dashes: Handmade\n"
    "  - under it, small letter-spaced capitals: WITH LOVE, then a tiny purple heart\n"
    "  - at the very bottom center, small letter-spaced capitals: MADE WITH CARE\n"
    "Cohesive soft-pink and purple palette."
)

# Проста сцена, коли фірмовий стиль вимкнено (без брендового тексту).
SIMPLE_SCENE = (
    "\n\nSCENE: place the product on a soft, elegant, slightly blurred pastel backdrop "
    "(gentle pink and lavender tones) with soft natural light. No text unless requested."
)

BACKGROUND_PROMPT = PRESERVE + BRAND_SCENE  # сумісність зі старим кодом


def build_prompt(brand_style: bool = True, wishes: str = "") -> str:
    """Складає промт: PRESERVE + (побажання користувача АБО фірмова/проста сцена)."""
    wishes = (wishes or "").strip()
    if wishes:
        return PRESERVE + "\n\nADDITIONAL REQUEST (background and text only): " + wishes
    return PRESERVE + (BRAND_SCENE if brand_style else SIMPLE_SCENE)


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


def _openai_replace_background(photo_bytes: bytes, prompt: str) -> bytes:
    """Заміна фону через gpt-image-1 за заданим промтом. Кидає виняток, якщо не вдалося."""
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
        prompt=prompt,
        size="1024x1536",
    )
    return base64.b64decode(resp.data[0].b64_json)


def passthrough(photo_bytes: bytes) -> bytes:
    """Готове фото: використовуємо як є (лише нормалізуємо у JPEG), без заміни фону."""
    img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=92)
    return out.getvalue()


def process(photo_bytes: bytes, brand_style: bool = True, wishes: str = "") -> bytes:
    """Обробляє фото: фірмовий стиль АБО власні побажання. Фолбек — підкладка."""
    if config.OPENAI_API_KEY:
        try:
            return _openai_replace_background(photo_bytes, build_prompt(brand_style, wishes))
        except Exception as e:  # noqa: BLE001 — не валимо публікацію через фон
            print(f"[image_service] OpenAI fallback: {e}")
    return _simple_composite(photo_bytes)
