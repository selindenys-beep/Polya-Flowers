"""Генерація тексту опису/підпису українською через Claude Sonnet."""
from __future__ import annotations

from anthropic import Anthropic

from app import config

_SYSTEM = (
    "Ти — копірайтер невеликого сімейного магазину квітів ручної роботи «Polya Flowers». "
    "Пишеш українською мовою, тепло, елегантно й лаконічно. "
    "Твоє завдання — за коротким описом і ціною скласти привабливий підпис до посту в Telegram. "
    "Формат: 1–2 короткі речення про букет + доречні емодзі (помірно) + окремим рядком ціна. "
    "Без вигаданих характеристик, яких немає в описі. Без хештегів, якщо про них не просять."
)


def generate_caption(description: str, price: str | None = None) -> str:
    """Повертає готовий підпис українською. Якщо ключ не налаштований — простий фолбек."""
    if not config.ANTHROPIC_API_KEY:
        parts = [description.strip() or "Ніжний букет ручної роботи 💐"]
        if price:
            parts.append(f"Ціна: {price}")
        return "\n".join(parts)

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    user_prompt = f"Опис товару: {description or '(без опису)'}\nЦіна: {price or '(не вказана)'}"
    message = client.messages.create(
        model=config.CLAUDE_TEXT_MODEL,
        max_tokens=400,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in message.content if block.type == "text").strip()
