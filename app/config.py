"""Централізоване читання секретів із змінних оточення.

Локально значення беруться з файлу .env (через python-dotenv).
На Render — із розділу Environment. У код секрети НЕ вписуються.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # підхопить .env локально; на Render просто нічого не зробить


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# --- Anthropic (Claude) ---
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
CLAUDE_CHAT_MODEL = _get("CLAUDE_CHAT_MODEL", "claude-haiku-4-5-20251001")
CLAUDE_TEXT_MODEL = _get("CLAUDE_TEXT_MODEL", "claude-sonnet-5")

# --- OpenAI ---
OPENAI_API_KEY = _get("OPENAI_API_KEY")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN")
TELEGRAM_GROUP_CHAT_ID = _get("TELEGRAM_GROUP_CHAT_ID")
TELEGRAM_CHANNEL_CHAT_ID = _get("TELEGRAM_CHANNEL_CHAT_ID")
TELEGRAM_BOT_USERNAME = _get("TELEGRAM_BOT_USERNAME", "Polya_flowers_bot")


def telegram_targets() -> list[str]:
    """Куди публікувати товар. Наразі — лише КАНАЛ (група вимкнена).
    Якщо канал не заданий — фолбек на групу."""
    if TELEGRAM_CHANNEL_CHAT_ID:
        return [TELEGRAM_CHANNEL_CHAT_ID]
    return [TELEGRAM_GROUP_CHAT_ID] if TELEGRAM_GROUP_CHAT_ID else []

# --- Google Sheets (через Apps Script Web App) ---
# URL розгорнутого веб-застосунку Apps Script + спільний токен для захисту.
SHEETS_WEBHOOK_URL = _get("SHEETS_WEBHOOK_URL")
SHEETS_WEBHOOK_TOKEN = _get("SHEETS_WEBHOOK_TOKEN")

# --- Сайт ---
SITE_URL = _get("SITE_URL", "https://polyaflowers.com/")

# --- Оплата ---
MONOBANK_JAR_URL = _get("MONOBANK_JAR_URL")

# --- Дашборд ---
DASHBOARD_PASSWORD = _get("DASHBOARD_PASSWORD")

# --- Загальне ---
PUBLIC_BASE_URL = _get("PUBLIC_BASE_URL", "http://localhost:8000")


def missing_secrets() -> list[str]:
    """Повертає список ще не налаштованих секретів — для діагностики на дашборді."""
    checks = {
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_GROUP_CHAT_ID": TELEGRAM_GROUP_CHAT_ID,
        "SHEETS_WEBHOOK_URL": SHEETS_WEBHOOK_URL,
        "MONOBANK_JAR_URL": MONOBANK_JAR_URL,
    }
    return [name for name, value in checks.items() if not value]
