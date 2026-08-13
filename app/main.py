"""Polya Flowers — дашборд і публікація товарів.

Потік роботи доньки:
  1. Завантажує фото букета, додає опис і ціну → «Обробити».
  2. Система покращує фото (гарний фон) і генерує підпис (Claude Sonnet).
  3. Бачить результат. Якщо подобається → «Публікація».
  4. Пост із кнопками (оплата / питання / доставка) йде в Telegram-групу
     та зберігається в Google Sheets.
"""
from __future__ import annotations

import base64
import secrets
import uuid

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from app.services import (
    chat_service,
    image_service,
    sheets_service,
    telegram_service,
    text_service,
)

app = FastAPI(title="Polya Flowers")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Проста in-memory сесія входу (для MVP достатньо; пізніше можна винести у сховище).
_SESSIONS: set[str] = set()
# Тимчасове сховище оброблених зображень до моменту публікації.
_PENDING: dict[str, dict] = {}


def _is_authed(request: Request) -> bool:
    if not config.DASHBOARD_PASSWORD:
        return True  # якщо пароль не заданий — дашборд відкритий (локальна розробка)
    return request.cookies.get("session") in _SESSIONS


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "missing_secrets": config.missing_secrets()}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
def login(response: Response, password: str = Form(...)):
    if config.DASHBOARD_PASSWORD and password == config.DASHBOARD_PASSWORD:
        token = secrets.token_urlsafe(24)
        _SESSIONS.add(token)
        resp = JSONResponse({"ok": True})
        resp.set_cookie("session", token, httponly=True, samesite="lax")
        return resp
    raise HTTPException(status_code=401, detail="Невірний пароль")


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not _is_authed(request):
        return templates.TemplateResponse("login.html", {"request": request, "error": None})
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "missing_secrets": config.missing_secrets()},
    )


@app.post("/api/process")
async def api_process(
    request: Request,
    photo: UploadFile,
    description: str = Form(""),
    price: str = Form(""),
    skip_image: str = Form(""),
):
    """Обробляє фото + генерує підпис. Повертає прев'ю (base64) і текст.

    skip_image (готове фото): не змінюємо фон — беремо зображення як є,
    лише генеруємо підпис.
    """
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Потрібен вхід")

    raw = await photo.read()
    caption = text_service.generate_caption(description, price, raw)
    processed = image_service.passthrough(raw) if skip_image else image_service.process(raw)

    product_id = uuid.uuid4().hex[:10]
    _PENDING[product_id] = {
        "image": processed,
        "caption": caption,
        "description": description,
        "price": price,
    }
    return {
        "product_id": product_id,
        "caption": caption,
        "image_base64": base64.b64encode(processed).decode(),
    }


@app.post("/api/publish")
async def api_publish(request: Request, product_id: str = Form(...), caption: str = Form(...)):
    """Публікує підготовлений товар у Telegram і зберігає в Google Sheets."""
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Потрібен вхід")

    item = _PENDING.get(product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Товар не знайдено або сесія застаріла")

    results = telegram_service.publish_product(item["image"], caption, product_id)
    post_url = _best_post_url(results)

    sheets_service.append_sale(
        product_id, item["description"], item["price"], caption, post_url
    )
    _PENDING.pop(product_id, None)
    return {"ok": True, "post_url": post_url}


def _best_post_url(results: list[dict]) -> str:
    """Будує посилання на пост: спершу публічний канал (t.me/username/N),
    інакше приватний формат t.me/c/<id>/N. Повертає перший, що вдалося."""
    private = ""
    for r in results:
        res = r.get("result", {})
        chat = res.get("chat", {})
        mid = res.get("message_id")
        if not mid:
            continue
        if chat.get("username"):
            return f"https://t.me/{chat['username']}/{mid}"
        if not private:
            cid = str(chat.get("id", "")).replace("-100", "")
            private = f"https://t.me/c/{cid}/{mid}"
    return private


@app.get("/api/sheets")
def api_sheets(request: Request):
    """Повертає всі аркуші Google Sheets для відображення у вкладках дашборда."""
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Потрібен вхід")
    try:
        return {"ok": True, "sheets": sheets_service.read_all()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "sheets": []}


# ─────────────────────────────────────────────────────────────
# Telegram webhook — сюди Telegram надсилає всі оновлення (повідомлення, кнопки).
# Бот відповідає клієнтам через Claude Haiku (chat_service).
# ─────────────────────────────────────────────────────────────
@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Миттєво відповідає Telegram 200, а обробку робить у фоні.

    Так Telegram не чекає (і не ретраїть) під час «пробудження» безкоштовного
    Render чи виклику Claude — клієнт усе одно отримає відповідь.
    """
    update = await request.json()
    background_tasks.add_task(_process_update, update)
    return {"ok": True}


def _process_update(update: dict) -> None:
    # Новий підписник каналу (Telegram) → рядок у Google Sheets.
    cm = update.get("chat_member")
    if cm:
        new = cm.get("new_chat_member", {})
        old = cm.get("old_chat_member", {})
        joined = (old.get("status") in ("left", "kicked")
                  and new.get("status") in ("member", "administrator", "creator"))
        if joined:
            u = new.get("user", {})
            uname = "@" + u["username"] if u.get("username") else ""
            fullname = " ".join(x for x in [u.get("first_name"), u.get("last_name")] if x)
            sheets_service.log_channel_subscriber(u.get("id", ""), uname, fullname)
        return
    if "my_chat_member" in update:  # зміни статусу самого бота — ігноруємо
        return

    # Підстраховка: якщо десь лишились старі callback-кнопки — просто підтвердити.
    if "callback_query" in update:
        telegram_service.answer_callback(update["callback_query"]["id"])
        return

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return

    chat = msg["chat"]
    is_private = chat.get("type") == "private"
    tg_id, username, name, phone = _extract_user(msg)

    # Клієнт поділився контактом → зберігаємо телефон у переписку.
    if "contact" in msg:
        phone = msg["contact"].get("phone_number", phone)
        sheets_service.log_message(tg_id, username, name, phone,
                                   "[поділився контактом]", "", "контакт")
        telegram_service.send_message(
            chat["id"], "Дякуємо! 💐 Ми зберегли ваш контакт і звʼяжемось за потреби."
        )
        return

    if "text" not in msg:
        return
    text = msg["text"]

    # 1) Діп-лінк із кнопок під товаром: /start pay | ask | delivery.
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) > 1 else ""

        # Оплата: фіксуємо натискання і даємо кнопку переходу на monobank.
        if payload == "pay":
            sheets_service.log_payment_click(tg_id, username, name, phone)
            pay_url = config.MONOBANK_JAR_URL or config.PUBLIC_BASE_URL
            telegram_service.send_message(
                chat["id"],
                "Дякуємо за замовлення! 💐 Натисніть кнопку нижче, щоб перейти до оплати "
                "(підтримується Apple Pay / Google Pay та картка).",
                reply_markup={"inline_keyboard": [[{"text": "💳 Перейти до оплати", "url": pay_url}]]},
            )
            return

        if payload == "delivery":
            answer = chat_service.DELIVERY_INFO
            question, kind = "🚚 Доставка (кнопка)", "доставка"
        elif payload == "ask":
            answer = "Вітаємо у Polya Flowers! 💐 Напишіть, будь ласка, ваше запитання — і ми відповімо."
            question, kind = "❓ Задати питання (кнопка)", "запит"
        else:
            answer = ("Вітаємо у Polya Flowers! 🌸 Ми робимо квіти ручної роботи. "
                      "Запитуйте про букети, доставку чи оплату — залюбки допоможемо.")
            question, kind = "/start", "старт"
        telegram_service.send_message(chat["id"], answer)
        sheets_service.log_message(tg_id, username, name, phone, question, answer, kind)
        return

    # 2) Звичайні повідомлення. У приваті відповідаємо завжди; у групі —
    # лише коли згадали бота або відповіли на його повідомлення (щоб не спамити).
    mentioned = "@" + config.TELEGRAM_BOT_USERNAME in text
    replied_to_bot = bool(msg.get("reply_to_message", {}).get("from", {}).get("is_bot"))
    if not (is_private or mentioned or replied_to_bot):
        return

    question = text.replace("@" + config.TELEGRAM_BOT_USERNAME, "").strip()
    reply = chat_service.generate_reply(question)
    telegram_service.send_message(chat["id"], reply, reply_to=msg["message_id"])
    sheets_service.log_message(tg_id, username, name, phone, question, reply, "повідомлення")


def _extract_user(msg: dict) -> tuple:
    """Витягує (Telegram ID, нікнейм, ім'я, телефон) з повідомлення."""
    frm = msg.get("from", {})
    tg_id = frm.get("id", "")
    username = "@" + frm["username"] if frm.get("username") else ""
    name = " ".join(x for x in [frm.get("first_name"), frm.get("last_name")] if x)
    phone = (msg.get("contact") or {}).get("phone_number", "")
    return tg_id, username, name, phone
