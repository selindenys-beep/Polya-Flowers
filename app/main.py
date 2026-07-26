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

from fastapi import FastAPI, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from app.services import image_service, sheets_service, telegram_service, text_service

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
):
    """Обробляє фото + генерує підпис. Повертає прев'ю (base64) і текст."""
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Потрібен вхід")

    raw = await photo.read()
    caption = text_service.generate_caption(description, price)
    processed = image_service.process(raw, caption)

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

    tg = telegram_service.publish_product(item["image"], caption, product_id)
    post_url = ""
    try:
        chat = str(tg["result"]["chat"]["id"]).replace("-100", "")
        post_url = f"https://t.me/c/{chat}/{tg['result']['message_id']}"
    except (KeyError, TypeError):
        pass

    sheets_service.append_sale(
        product_id, item["description"], item["price"], caption, post_url
    )
    _PENDING.pop(product_id, None)
    return {"ok": True, "post_url": post_url}
