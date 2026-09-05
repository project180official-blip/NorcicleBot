import asyncio
import io
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from PIL import Image
from telegram import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.error import BadRequest

import config
import db
import sync
import ui

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

_NEVAPEDIA_LOCK = threading.Lock()
_nevapedia_last_call = 0.0

# Batas order yang belum dibayar per user: mencegah satu user mengunci semua
# stok dengan order PENDING kosong (reservasi stok bertahan ~24 jam).
MAX_PENDING_ORDERS_PER_USER = 3


def _generate_order_id():
    return "ORD-" + uuid.uuid4().hex[:10].upper()


def _make_unique_order_id():
    """Generate order id dengan retry bila bentrok dengan order yang sudah ada."""
    for _ in range(5):
        oid = _generate_order_id()
        if db.get_order(oid) is None:
            return oid
    raise RuntimeError("Gagal membuat order id yang unik")


def _nevapedia_throttle():
    global _nevapedia_last_call
    with _NEVAPEDIA_LOCK:
        elapsed = time.time() - _nevapedia_last_call
        if elapsed < 5.5:
            time.sleep(5.5 - elapsed)
        _nevapedia_last_call = time.time()


def nevapedia_create_invoice(order):
    try:
        _nevapedia_throttle()
        resp = requests.get(
            "https://app.nevapedia.com/api/invoice",
            params={
                "apikey": config.NEVAPEDIA_API_KEY,
                "amount": order["total"],
                "order_id": order["order_id"],
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            logger.warning("Nevapedia create invoice gagal: %s", data)
            return None
        return data
    except Exception as e:
        logger.error("Nevapedia create invoice error: %s", e)
        return None


def nevapedia_get_status(invoice_id):
    if not invoice_id:
        return "pending"
    try:
        _nevapedia_throttle()
        resp = requests.get(
            "https://app.nevapedia.com/api/invoice/status",
            params={
                "apikey": config.NEVAPEDIA_API_KEY,
                "invoice_id": invoice_id,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("status", "pending")).lower()
    except Exception as e:
        logger.warning("Nevapedia status check error: %s", e)
        return "error"


def nevapedia_is_paid(status):
    return status in ("paid", "success", "completed", "settled")


import hmac
import hashlib
import urllib.parse


def verify_binance_pay_transaction(order_id_target, expected_amount, tolerance_minutes=120):
    """Cek transaksi masuk di Binance Pay via API key."""
    if not config.BINANCE_API_KEY or not config.BINANCE_API_SECRET:
        return {"ok": False, "reason": "NO_API_KEYS"}
    
    timestamp = int(time.time() * 1000)
    # Cek transaksi dalam rentang beberapa jam terakhir
    start_time = timestamp - (tolerance_minutes * 60 * 1000)
    params = {
        "timestamp": timestamp,
        "startTime": start_time,
        "limit": 50
    }
    query_str = urllib.parse.urlencode(params)
    signature = hmac.new(
        config.BINANCE_API_SECRET.encode("utf-8"),
        query_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    url = f"https://api.binance.com/sapi/v1/pay/transactions?{query_str}&signature={signature}"
    headers = {"X-MBX-APIKEY": config.BINANCE_API_KEY}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if not resp.ok:
            logger.error("Binance Pay API error %s: %s", resp.status_code, resp.text)
            return {"ok": False, "reason": f"API_ERROR_{resp.status_code}"}
        
        data = resp.json()
        tx_list = data.get("data") or []
        
        # Cari transaksi masuk (deposit/receive) dengan order_id di note atau transaksi yang cocok nominalnya
        target_oid = str(order_id_target).strip().upper()
        for tx in tx_list:
            # tx status: SUCCESS, orderType: C2C / PAY
            note = str(tx.get("note") or "").upper()
            order_id_field = str(tx.get("orderId") or "").upper()
            amount = float(tx.get("amount") or 0)
            currency = str(tx.get("currency") or "").upper()
            
            # Cocokkan jika note mengandung order ID atau txID
            matched_id = target_oid in note or target_oid in order_id_field
            matched_amount = amount >= float(expected_amount) and currency in ("USDT", "BUSD", "USDC")
            
            if matched_id and matched_amount:
                return {
                    "ok": True,
                    "txId": tx.get("transactionId") or tx.get("orderId"),
                    "amount": amount,
                    "currency": currency
                }
        
        return {"ok": False, "reason": "TRANSACTION_NOT_FOUND"}
    except Exception as e:
        logger.error("Error verifying Binance Pay: %s", e)
        return {"ok": False, "reason": str(e)}
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "tether", "vs_currencies": "idr"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        rate = float(data["tether"]["idr"])
        if rate > 0:
            return rate
    except Exception as e:
        logger.warning("CoinGecko rate fetch failed: %s", e)

    try:
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "USDCIDR"},
            timeout=10,
        )
        resp.raise_for_status()
        rate = float(resp.json()["price"])
        if rate > 0:
            return rate
    except Exception as e:
        logger.warning("Binance rate fetch failed: %s", e)

    try:
        resp = requests.get(
            "https://indodax.com/api/ticker/usdtidr",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("ticker", {})
        rate = float(data.get("last", 0))
        if rate > 0:
            return rate
    except Exception as e:
        logger.warning("Indodax rate fetch failed: %s", e)

    return None


def calculate_usdt(total_rupiah):
    rate = fetch_usdt_idr_rate()
    if not rate or rate <= 0:
        return None
    return round(total_rupiah / rate, 2)


def _payment_poll_action(status, created_at, now, stale_hours=48):
    """Keputusan polling Nevapedia untuk satu order.

    Mengembalikan "complete" | "fail" | "retry":
    - paid        -> complete
    - terminal    -> fail
    - stale (tua) -> fail, KECUALI status "error" (transien) -> retry
    - selain itu  -> retry
    """
    if nevapedia_is_paid(status):
        return "complete"
    created_dt = None
    try:
        created_dt = datetime.fromisoformat(created_at)
    except (TypeError, ValueError):
        pass
    stale = bool(created_dt) and (now - created_dt).total_seconds() > stale_hours * 3600
    if status in ("canceled", "expired", "failed"):
        return "fail"
    if stale and status != "error":
        return "fail"
    return "retry"


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

    def log_message(self, *args):
        pass


def start_health_server():
    try:
        port = int(os.environ.get("PORT", "8000"))
        httpd = HTTPServer(("0.0.0.0", port), HealthHandler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        logger.info("Health server on port %s", port)
    except Exception as e:
        logger.warning("Tidak bisa start health server: %s", e)


async def keep_alive(context: ContextTypes.DEFAULT_TYPE):
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        return
    try:
        await asyncio.to_thread(requests.get, url, timeout=10)
    except Exception as e:
        logger.warning("Keep-alive ping gagal: %s", e)


def frame_qris_image(image_bytes, border_color=(20, 76, 249), border_ratio=0.06, corner_radius=24):
    """Lapisi gambar QRIS dengan bingkai tanpa mengubah isi QR.

    Isi QR (termasuk nominal) sudah ter-encode di dalam gambar asli oleh
    gateway — kita hanya menempelkannya di atas kanvas dengan border,
    sehingga kode QR tetap terbaca dan nominalnya tetap benar.
    """
    import io as _io

    raw = Image.open(_io.BytesIO(image_bytes)).convert("RGBA")
    raw_w, raw_h = raw.size
    pad = max(int(raw_w * border_ratio), 24)
    w = raw_w + pad * 2
    h = raw_h + pad * 2

    canvas = Image.new("RGBA", (w, h), border_color + (255,))
    mask = Image.new("L", (w, h), 0)
    from PIL import ImageDraw

    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=corner_radius, fill=255)
    canvas.paste(raw, (pad, pad))
    canvas.putalpha(mask)
    out = canvas.convert("RGB")

    buf = _io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def _sheet_write_url_ok(url):
    return bool(url) and url.startswith("https://script.google.com/macros/s/")


def _post_sheet(payload, retries=3):
    url = config.SHEET_WRITE_URL
    if not url:
        logger.warning(
            "SHEET_WRITE_URL kosong: write-back ke Google Sheets dilewati "
            "(order/stok tidak akan tercatat di sheet sampai env diisi). "
            "Cek env Render/SHEET_WRITE_URL."
        )
        return False
    if not _sheet_write_url_ok(url):
        logger.warning("SHEET_WRITE_URL tidak valid, dilewati: %s", url)
        return False
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                url,
                json={"secret": config.SHEET_WRITE_SECRET, **payload},
                timeout=15,
            )
            if resp.ok and "OK" in resp.text:
                return True
            last_err = f"HTTP {resp.status_code} — {resp.text[:120]}"
            logger.warning(
                "Write-back sheet tidak OK (attempt %s/%s): %s",
                attempt,
                retries,
                last_err,
            )
        except Exception as e:
            last_err = str(e)
            logger.warning(
                "Write-back sheet gagal (attempt %s/%s): %s", attempt, retries, e
            )
        time.sleep(1 * attempt)
    return False


def add_stock_to_sheet(product_id, items):
    url = config.SHEET_WRITE_URL
    if not url or not _sheet_write_url_ok(url):
        logger.warning("SHEET_WRITE_URL kosong/tidak valid: add_stock dilewati")
        return None
    try:
        resp = requests.post(
            url,
            json={
                "secret": config.SHEET_WRITE_SECRET,
                "add_stock": {"product_id": product_id, "items": items},
            },
            timeout=15,
        )
        body = resp.text.strip()
        logger.info("add_stock raw [%s]: %s", resp.status_code, body[:300])
        if resp.ok and "OK" in body and "INVALID" not in body and "ERROR" not in body:
            return {"added": len(items)}
        logger.warning("add_stock gagal: %s", body[:300])
    except Exception as e:
        logger.warning("add_stock error: %s", e)
    return None


def sync_sold_to_sheet(stock_ids, telegram_id):
    return _post_sheet(
        {
            "mark_sold": [
                {"stock_id": s, "sold_to": str(telegram_id)} for s in stock_ids
            ],
        },
        retries=5,
    )


def sync_order_to_sheet(order, stock_ids=None):
    return _post_sheet(
        {
            "orders": [
                {
                    "order_id": order["order_id"],
                    "telegram_id": str(order["telegram_id"]),
                    "username": order.get("username") or "",
                    "product_id": order["product_id"],
                    "qty": order["qty"],
                    "total": order["total"],
                    "status": order["status"],
                    "payment_id": order.get("payment_id") or "",
                    "created_at": order.get("created_at") or "",
                    "paid_at": order.get("paid_at") or "",
                    "stock_ids": ",".join(stock_ids) if stock_ids else "",
                }
            ],
        }
    )


def get_product(product_id):
    products = db.get_active_products()
    return next((p for p in products if p["id"] == product_id), None)


async def send_page(chat_id, text, keyboard):
    await app.bot.send_message(
        chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=keyboard
    )


async def _send_fallback(chat_id, text, keyboard):
    try:
        await app.bot.send_message(
            chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=keyboard
        )
    except Exception as e2:
        logger.error("Kirim pesan pengganti gagal: %s", e2)


async def safe_edit(chat_id, message_id, text, reply_markup=None):
    try:
        await app.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    except BadRequest as e:
        if "not modified" in str(e).lower():
            return
        logger.warning("Edit gagal, kirim pesan baru: %s", e)
        await _send_fallback(chat_id, text, reply_markup)
    except Exception as e:
        logger.warning("Edit gagal, kirim pesan baru: %s", e)
        await _send_fallback(chat_id, text, reply_markup)


async def render_home(chat_id, edit_message_id=None, user_name=None):
    text, kb = ui.home_text(user_name)
    if edit_message_id:
        await safe_edit(chat_id, edit_message_id, text, kb)
    elif config.BANNER_URL:
        try:
            await app.bot.send_photo(
                chat_id=chat_id,
                photo=config.BANNER_URL,
                caption=text,
                parse_mode="HTML",
                reply_markup=kb,
            )
        except Exception as e:
            logger.warning("Kirim banner gagal, fallback teks: %s", e)
            await send_page(chat_id, text, kb)
    else:
        await send_page(chat_id, text, kb)


async def render_catalog(chat_id, edit_message_id=None):
    text, kb = ui.catalog_text()
    if edit_message_id:
        await safe_edit(
            chat_id=chat_id,
            message_id=edit_message_id,
            text=text,
            reply_markup=kb,
        )
    else:
        await send_page(chat_id, text, kb)


async def render_product(chat_id, edit_message_id, product_id, qty):
    product = get_product(product_id)
    if not product:
        text, kb = ui.error_page("Produk tidak ditemukan.")
    else:
        avail = db.count_available(product_id)
        if avail < 1:
            text, kb = ui.soldout_page()
        else:
            if qty > avail:
                qty = avail
            text, kb = ui.product_page(product, qty)
    await safe_edit(
        chat_id=chat_id,
        message_id=edit_message_id,
        text=text,
        reply_markup=kb,
    )


async def check_member(bot, user_id):
    if not config.CHANNEL_USERNAME:
        return True
    try:
        member = await bot.get_chat_member(chat_id=config.CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning("check_member gagal (fail-open): %s", e)
        return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if args:
        payload = args[0]
        if payload.startswith("ref_"):
            referrer = payload[4:]
            if referrer.isdigit() and int(referrer) != user_id:
                db.set_referred(str(user_id), referrer)
    is_member = await check_member(app.bot, user_id)
    if not is_member:
        text, kb = ui.force_join_page()
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
        return
    await asyncio.to_thread(sync.sync_from_sheets, True)
    name = update.effective_user.first_name or update.effective_user.username
    await render_home(update.effective_chat.id, user_name=name)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_member = await check_member(app.bot, user_id)
    if not is_member:
        text, kb = ui.force_join_page()
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
        return
    await asyncio.to_thread(sync.sync_from_sheets)
    name = update.effective_user.first_name or update.effective_user.username
    await render_home(update.effective_chat.id, user_name=name)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, kb = ui.contact_page()
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def products_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.to_thread(sync.sync_from_sheets)
    text, kb = ui.catalog_text()
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def promo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.to_thread(sync.sync_from_sheets)
    text, kb = ui.promo_page()
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def stock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.to_thread(sync.sync_from_sheets)
    text, kb = ui.stock_page()
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, kb = ui.orders_page(update.effective_user.id)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


def is_admin(user_id):
    return config.ADMIN_CHAT_ID is not None and user_id == config.ADMIN_CHAT_ID


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Akses khusus admin. 🙅")
        return
    text, kb = ui.admin_panel()
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def admin_products_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Akses khusus admin. 🙅")
        return
    await asyncio.to_thread(sync.sync_from_sheets)
    text, kb = ui.catalog_text()
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def admin_stock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Akses khusus admin. 🙅")
        return
    await asyncio.to_thread(sync.sync_from_sheets)
    text, kb = ui.stock_page()
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def admin_orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Akses khusus admin. 🙅")
        return
    text, kb = ui.admin_orders_page()
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None or query.message is None:
        return
    try:
        await _handle_callback(update, context, query)
    except Exception as e:
        logger.exception("Unhandled error pada callback %s: %s", query.data, e)
        try:
            await query.answer("Terjadi kesalahan. Coba lagi ya.")
        except Exception:
            pass


async def _handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    chat_id = query.message.chat_id
    msg_id = query.message.message_id
    data = query.data

    if data == "checkjoin":
        is_member = await check_member(app.bot, query.from_user.id)
        if not is_member:
            await query.answer("You haven't joined the channel yet. Please join first!", show_alert=True)
            return
        await asyncio.to_thread(sync.sync_from_sheets, True)
        name = query.from_user.first_name or query.from_user.username
        await render_home(chat_id, msg_id, user_name=name)

    elif data == "home":
        is_member = await check_member(app.bot, query.from_user.id)
        if not is_member:
            await query.answer()
            text, kb = ui.force_join_page()
            await safe_edit(
                chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
            )
            return
        await asyncio.to_thread(sync.sync_from_sheets)
        name = query.from_user.first_name or query.from_user.username
        await render_home(chat_id, msg_id, user_name=name)

    elif data == "refresh":
        is_member = await check_member(app.bot, query.from_user.id)
        if not is_member:
            await query.answer()
            text, kb = ui.force_join_page()
            await safe_edit(
                chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
            )
            return
        await asyncio.to_thread(sync.sync_from_sheets, True)
        name = query.from_user.first_name or query.from_user.username
        await render_home(chat_id, msg_id, user_name=name)

    elif data == "promo":
        await asyncio.to_thread(sync.sync_from_sheets)
        text, kb = ui.promo_page()
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )

    elif data == "catalog":
        await asyncio.to_thread(sync.sync_from_sheets)
        await render_catalog(chat_id, msg_id)

    elif data == "stock":
        await asyncio.to_thread(sync.sync_from_sheets)
        text, kb = ui.stock_page()
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )

    elif data == "orders":
        text, kb = ui.orders_page(query.from_user.id)
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )

    elif data == "contact":
        text, kb = ui.contact_page()
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )

    elif data == "affiliate":
        text = affiliate_text(str(query.from_user.id))
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Home", callback_data="home")]]
        )
        await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)

    elif data == "admin":
        if not is_admin(query.from_user.id):
            await query.answer("Akses khusus admin.")
            return
        text, kb = ui.admin_panel()
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )

    elif data == "ordersadmin":
        if not is_admin(query.from_user.id):
            await query.answer("Akses khusus admin.")
            return
        text, kb = ui.admin_orders_page()
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )

    elif data.startswith("product:"):
        product_id = data.split(":", 1)[1]
        p = get_product(product_id)
        default_qty = 2 if p and (p.get("id") == "P0001" or "gemini" in str(p.get("name", "")).lower()) else 1
        context.user_data["qty"] = default_qty
        context.user_data["product_id"] = product_id
        await render_product(chat_id, msg_id, product_id, default_qty)

    elif data.startswith("qtydec:") or data.startswith("qtyinc:"):
        op, product_id = data.split(":", 1)
        p = get_product(product_id)
        min_qty = 2 if p and (p.get("id") == "P0001" or "gemini" in str(p.get("name", "")).lower()) else 1
        qty = context.user_data.get("qty", min_qty)
        if op == "qtydec":
            qty = max(min_qty, qty - 1)
        else:
            avail = db.count_available(product_id)
            qty = max(min_qty, min(avail, qty + 1))
        context.user_data["qty"] = qty
        context.user_data["product_id"] = product_id
        await render_product(chat_id, msg_id, product_id, qty)

    elif data.startswith("customqty:"):
        product_id = data.split(":", 1)[1]
        context.user_data["awaiting_qty_for"] = product_id
        context.user_data["product_id"] = product_id
        avail = db.count_available(product_id)
        text = (
            f"✏️ <b>Enter Custom Quantity</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Please type the number of items you want to buy (1 - {avail}) in the chat below 👇"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("« Cancel", callback_data=f"product:{product_id}")]
        ])
        await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)

    elif data.startswith("buy:"):
        product_id = data.split(":", 1)[1]
        qty = context.user_data.get("qty", 1)
        if not isinstance(qty, int) or qty < 1:
            qty = 1
        context.user_data["product_id"] = product_id
        context.user_data["qty"] = qty
        await do_checkout(query, context, chat_id, msg_id)

    elif data.startswith("paid:"):
        await paid_check(query, context, chat_id, msg_id)

    elif data.startswith("confirm_pay:"):
        order_id = data.split(":", 1)[1]
        await confirm_payment(query, context, order_id)

    elif data.startswith("admin_approve:"):
        order_id = data.split(":", 1)[1]
        await admin_approve(query, context, chat_id, msg_id, order_id)

    elif data.startswith("admin_reject:"):
        order_id = data.split(":", 1)[1]
        await admin_reject(query, context, chat_id, msg_id, order_id)

    elif data.startswith("pay_binance:"):
        order_id = data.split(":", 1)[1]
        await process_binance_payment(query, context, chat_id, msg_id, order_id)

    elif data.startswith("pay_usdt:"):
        order_id = data.split(":", 1)[1]
        await process_usdt_payment(query, context, chat_id, msg_id, order_id)

    elif data == "noop":
        pass

    await query.answer()


async def do_checkout(query, context, chat_id, msg_id):
    product_id = context.user_data.get("product_id")
    qty = context.user_data.get("qty", 1)
    if not isinstance(qty, int) or qty < 1:
        qty = 1
    product = get_product(product_id)
    if not product:
        text, kb = ui.error_page("Product not found.")
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )
        return
    
    is_gemini = product.get("id") == "P0001" or "gemini" in str(product.get("name", "")).lower()
    if is_gemini and qty < 2:
        text, kb = ui.error_page("Minimum order for Gemini AI Pro is 2 accounts.")
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )
        return
    if db.count_available(product_id) < qty:
        text, kb = ui.soldout_page()
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )
        return

    text, kb = ui.loading_text("Processing your order...")
    await safe_edit(
        chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
    )

    unit_price, total = ui.calculate_item_price(product, qty)
    user = query.from_user
    if db.count_available(product_id) < qty:
        text, kb = ui.soldout_page()
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )
        return
    if db.count_pending_for_user(user.id) >= MAX_PENDING_ORDERS_PER_USER:
        text, kb = ui.error_page(
            "You have too many unpaid pending orders. "
            "Please complete or wait for previous orders to expire."
        )
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )
        return
    order_id = _make_unique_order_id()
    db.create_order(order_id, user.id, user.username or "", product, qty, total)

    order = db.get_order(order_id)
    await asyncio.to_thread(sync_order_to_sheet, order)

    if config.TEST_MODE:
        text, kb = ui.test_payment_page(order)
        await safe_edit(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            reply_markup=kb,
        )
        await notify_admin(
            f"🔔 <b>NEW ORDER (TEST)</b>\n"
            f"🆔 Order: <code>{order_id}</code>\n"
            f"{product['emoji']} {ui.esc(product['name'])} x{qty}\n"
            f"💰 Total: <b>{ui.fmt_price(total)}</b>\n"
            f"👤 User: @{user.username or '-'} ({user.id})"
        )
        return

    if not db.reserve_stock(order_id, product_id, qty):
        db.set_order_status(order_id, "FAILED")
        await asyncio.to_thread(sync_order_to_sheet, db.get_order(order_id))
        text, kb = ui.soldout_page()
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )
        return

    try:
        usdt_amount = total
        text, kb = ui.payment_method_page(order, usdt_amount)
        await safe_edit(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
        )
        await notify_admin(
            f"🔔 <b>NEW ORDER</b>\n\n"
            f"🆔 Order: <code>{order_id}</code>\n"
            f"{product['emoji']} {ui.esc(product['name'])} x{qty}\n"
            f"💰 Total: <b>{ui.fmt_price(total)}</b> ({usdt_amount:.2f} USDT)\n"
            f"👤 User: @{user.username or '-'} ({user.id})"
        )
    except Exception as e:
        logger.error("Payment method selection error: %s", e)
        db.release_reservation(order_id)
        db.set_order_status(order_id, "FAILED")
        await asyncio.to_thread(sync_order_to_sheet, db.get_order(order_id))
        text, kb = ui.error_page("Payment creation failed. Admin will contact you.")
        try:
            await safe_edit(
                chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb
            )
        except Exception:
            await app.bot.send_message(
                chat_id=chat_id, text=text, reply_markup=kb
            )
        await notify_admin(
            f"⚠️ <b>PAYMENT CREATION FAILED</b>\n"
            f"🆔 Order: <code>{order_id}</code>\n"
            f"{ui.esc(product['name'])} x{qty}\n"
            f"💰 Total: {ui.fmt_price(total)}\n"
            f"👤 User: {user.id}\n"
            f"Error: {e}"
        )


async def process_binance_payment(query, context, chat_id, msg_id, order_id):
    order = db.get_order(order_id)
    if not order or str(order["telegram_id"]) != str(query.from_user.id):
        await query.answer("Order not found.")
        return

    total = order["total"]
    usdt_amount = float(total)

    try:
        text, kb = ui.binance_pay_page(order, usdt_amount)
        if config.BINANCE_QR_URL:
            try:
                await app.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception:
                pass
            await app.bot.send_photo(
                chat_id=chat_id,
                photo=config.BINANCE_QR_URL,
                caption=text,
                parse_mode="HTML",
                reply_markup=kb,
            )
        else:
            await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
    except Exception as e:
        logger.error("Binance payment error: %s", e)
        text, kb = ui.error_page("Failed to display Binance Pay page.")
        await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)


async def process_usdt_payment(query, context, chat_id, msg_id, order_id):
    order = db.get_order(order_id)
    if not order or str(order["telegram_id"]) != str(query.from_user.id):
        await query.answer("Order not found.")
        return

    product_id = order["product_id"]
    qty = order["qty"]
    total = order["total"]

    if not config.CRYPTO_WALLET_USDT:
        text, kb = ui.error_page("Crypto payment is not configured.")
        await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
        return

    usdt_amount = float(total)

    try:
        text, kb = ui.crypto_usdt_page(order, usdt_amount)
        await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
    except Exception as e:
        logger.error("Crypto payment error: %s", e)
        text, kb = ui.error_page("Failed to display crypto payment page.")
        await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)


async def paid_check(query, context, chat_id, msg_id):
    order_id = query.data.split(":", 1)[1]
    order = db.get_order(order_id)
    if not order:
        text, kb = ui.error_page("Order not found.")
        await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
        return
    if str(order["telegram_id"]) != str(query.from_user.id):
        text, kb = ui.error_page("This order does not belong to your account.")
        await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
        return

    if config.TEST_MODE and order["status"] not in (
        "COMPLETED", "PAID_BUT_OUT_OF_STOCK", "FAILED"
    ):
        await complete_order(order_id, "SIMULATED", context)
        order = db.get_order(order_id)

    elif order["status"] in ("PENDING", "FAILED") and config.PAYMENT_METHOD == "nevapedia":
        if not config.NEVAPEDIA_API_KEY:
            text, kb = ui.error_page("Payment gateway is not configured.")
            await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
            return
        try:
            status = await asyncio.to_thread(nevapedia_get_status, order.get("payment_id"))
            if nevapedia_is_paid(status):
                await complete_order(
                    order_id, order.get("payment_id") or order_id, context
                )
            elif status in ("canceled", "expired", "failed") and order["status"] == "PENDING":
                db.release_reservation(order_id)
                db.set_order_status(order_id, "FAILED")
                await asyncio.to_thread(sync_order_to_sheet, db.get_order(order_id))
        except Exception as e:
            logger.error("Status check error: %s", e)
            text, kb = ui.error_page("Failed to check payment status. Please try again.")
            await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
            return
        order = db.get_order(order_id)

    if not order:
        text, kb = ui.error_page("Order not found.")
    elif order["status"] == "COMPLETED":
        if not order.get("delivered"):
            contents = db.get_stock_contents_by_order(order_id)
            if contents:
                if await send_product_file(context, order, contents):
                    db.set_order_delivered(order_id)
        text, kb = ui.success_page(order_id)
    elif order["status"] in ("NO_STOCK", "PAID_BUT_OUT_OF_STOCK"):
        text, kb = ui.no_stock_paid_page(order_id)
    elif order["status"] == "AWAITING_ADMIN":
        text, kb = ui.awaiting_admin_page(order_id)
    elif order["status"] == "FAILED":
        text, kb = ui.error_page("Pembayaran gagal atau dibatalkan.")
    else:
        text, kb = ui.pending_page(order)
    try:
        await safe_edit(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb)
    except Exception:
        try:
            await app.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass
        await app.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=kb
        )


NETFLIX_VPN_TERMS = (
    "🟥 NETFLIX TUTORIAL: STREAMING WITH VPN\n\n"
    "HOW TO USE:\n"
    "1. Log in to the account as usual without connecting to VPN.\n"
    "2. Once logged in successfully, choose the movie/show you wish to watch.\n"
    "3. Turn on your VPN before clicking PLAY. "
    "Feel free to connect to any VPN server/region.\n"
    "4. Once video starts playing, you may turn off the VPN and continue watching. "
    "Leaving VPN on is also fine.\n\n"
    "If you cannot log in with the password, please use OTP login.\n\n"
    "📩 OTP INBOX ACCESS:\n"
    "https://mailku.online/mailbox\n\n"
    "⚠️ TERMS OF PURCHASE\n"
    "> Please understand the instructions before making a purchase.\n"
    "> No refunds if account is wiped, banned, or encounters issues post-purchase.\n"
    "> Ensure you have read and agreed to all conditions before buying.\n"
    "> PURCHASING = AGREEING to all terms & conditions.\n\n"
    "If you have questions regarding usage or login, feel free to contact support.\n\n"
)

GENERAL_TERMS = (
    "== TERMS & INSTRUCTIONS ==\n\n"
    "> Keep this file secure and do not share it with anyone.\n"
    "> Read activation instructions carefully before proceeding.\n"
    "> Ensure target account meets all specified product requirements.\n"
    "> Warranty applies strictly according to terms specified for each product.\n\n"
)

GOOGLE_AI_PRO_TERMS = (
    "📬 READ BEFORE ACTIVATION:\n"
    "* Verify your destination email account before clicking 'Activate'.\n"
    "* Do not activate on email accounts with an existing active Google Plus, Pro, or Ultra subscription.\n"
    "* Ensure you are signed into the target account during activation. Check top-right corner to verify active user.\n\n"
    "🛡️ TERMS & WARRANTY:\n"
    "> ➡️ 6-hour replacement guarantee to ensure activation link functions properly.\n"
    "> ➡️ Subscription activates instantly on your account upon completion.\n"
    "> ➡️ Store warranty ends once activation is verified successful.\n"
    "> ➡️ Guarantee applies strictly to the activation process.\n\n"
    "🆘 IMPORTANT NOTICE:\n"
    "> This plan is managed via Jio; subscription will terminate if the underlying SIM package expires. "
    "Therefore, this item carries zero warranty post-activation. "
    "However, as long as Jio SIM renewals are maintained, access remains active.\n\n"
    "⚠️ Note:\n"
    "> Redeem code is strictly single-use per account.\n"
)

LEONARDO_AI_TERMS = (
    "🎨 HOW TO LOGIN TO LEONARDO AI:\n"
    "1. Visit leonardo.ai\n"
    "2. Click 'Login with Canva'\n"
    "3. Enter the purchased email credential\n"
    "4. Proceed to OTP verification step\n"
    "5. Retrieve your OTP code at: https://bototp.site\n"
)


async def send_product_file(context, order, contents):
    file_text = (
        f"PAYMENT SUCCESSFUL\n"
        f"Order ID: {order['order_id']}\n"
        f"Product: {order['product_name']} x{order['qty']}\n"
        f"Total: {ui.fmt_price(order['total'])}\n"
        f"Timestamp: {db.utcnow().isoformat()}\n\n"
        f"== DIGITAL PRODUCT ITEMS ==\n\n"
    )
    for i, content in enumerate(contents, 1):
        file_text += f"Item {i}:\n{content}\n\n"
    file_text += GENERAL_TERMS
    if "google" in order["product_name"].lower() or "gemini" in order["product_name"].lower():
        file_text += GOOGLE_AI_PRO_TERMS
    if "netflix" in order["product_name"].lower() or "netflx" in order["product_name"].lower():
        file_text += NETFLIX_VPN_TERMS
    if "leonardo" in order["product_name"].lower():
        file_text += LEONARDO_AI_TERMS
    file_text += "Thank you for purchasing!\n"
    buf = io.BytesIO(file_text.encode("utf-8"))
    buf.name = f"product-{order['order_id']}.txt"
    await context.bot.send_document(
        chat_id=order["telegram_id"],
        document=InputFile(buf),
        caption=f"📂 Your digital product — Order <code>{order['order_id']}</code>",
        parse_mode="HTML",
    )


async def complete_order(order_id, payment_id, context):
    result = await asyncio.to_thread(
        db.complete_order_atomic, order_id, payment_id or order_id
    )
    status = result["status"]
    if status in ("ALREADY", "NOT_FOUND"):
        return status

    order = result["order"]
    contents = result["contents"]
    stock_ids = result["stock_ids"]

    order_sheet = db.get_order(order_id)
    if order_sheet:
        await asyncio.to_thread(
            sync_order_to_sheet, order_sheet, stock_ids or None
        )

    if status == "PAID_BUT_OUT_OF_STOCK":
        await notify_admin(
            f"⚠️ <b>ORDER OUT OF STOCK</b>\n"
            f"Order <code>{order_id}</code> dibayar tapi stok habis (sudah diklaim user lain). "
            f"Refund/manual resolution diperlukan.\n"
            f"👤 User: {order['telegram_id']}"
        )
        return status

    sold_ok = await asyncio.to_thread(
        sync_sold_to_sheet, stock_ids, order["telegram_id"]
    )
    if not sold_ok:
        await notify_admin(
            f"🚨 <b>WRITE-BACK STOK GAGAL</b>\n\n"
            f"Stok order <code>{order_id}</code> (ids: {', '.join(stock_ids)}) sudah "
            f"terjual di DB lokal tapi GAGAL disinkronkan ke Google Sheets.\n\n"
            f"⚠️ Jika server diredeploy sebelum stok ini di-sync manual ke sheet, "
            f"kredensial bisa dijual 2x. Harap cek & perbaiki sheet STOCK segera.\n"
            f"👤 User: {order['telegram_id']}"
        )

    if not config.TEST_MODE:
        referrer = db.get_referrer(str(order["telegram_id"]))
        if referrer and referrer != str(order["telegram_id"]):
            commission = int(round(order["total"] * config.AFFILIATE_PERCENT / 100))
            if commission > 0:
                db.credit_commission(
                    referrer,
                    str(order["telegram_id"]),
                    order_id,
                    order["product_name"],
                    commission,
                )
                await notify_affiliate(referrer, commission, order_id)

    intro = (
        f"✓ <b>Payment Successful!</b>\n\n"
        + ("🧪 <i>Test mode — simulated payment.</i>\n\n" if config.TEST_MODE else "")
        + f"🛍️ {ui.esc(order['product_name'])} x{order['qty']}\n"
        f"🧾 Order ID: <code>{order_id}</code>\n\n"
    )

    try:
        await context.bot.send_message(
            chat_id=order["telegram_id"],
            text=intro + "Your digital product is attached in the file below 👇",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Kirim intro produk gagal: %s", e)
    delivered = False
    try:
        await send_product_file(context, order, contents)
        delivered = True
        db.set_order_delivered(order_id)
    except Exception as e:
        logger.error("Kirim file produk gagal: %s", e)
    await notify_admin(
        f"✅ <b>ORDER COMPLETED</b>\n\n"
        f"🆔 Order <code>{order_id}</code>\n"
        f"🛒 {ui.esc(order['product_name'])} x{order['qty']}\n"
        f"💰 Total: <b>{ui.fmt_price(order['total'])}</b>\n"
        f"👤 User: {order['telegram_id']}\n"
        f"📦 Status: <b>COMPLETED</b>{' ⚠️ delivery failed' if not delivered else ''}"
    )
    await notify_channel(
        f"✅ <b>NEW PURCHASE</b>\n\n"
        f"🛒 {ui.esc(order['product_name'])} x{order['qty']}\n"
        f"💰 Total: <b>{ui.fmt_price(order['total'])}</b>\n"
        f"📦 Status: <b>COMPLETED</b>"
    )
    return "COMPLETED"


async def confirm_payment(query, context, order_id):
    order = db.get_order(order_id)
    if not order or str(order["telegram_id"]) != str(query.from_user.id):
        await query.answer("Order not found.")
        return
    if order["status"] != "PENDING":
        await query.answer("Order status has already updated.")
        return

    # 1. Jika API Key Binance sudah diisi, lakukan verifikasi otomatis
    if config.BINANCE_API_KEY and config.BINANCE_API_SECRET:
        await query.answer("Checking Binance Pay ledger... ⏳")
        verification = await asyncio.to_thread(
            verify_binance_pay_transaction, order_id, order["total"]
        )
        if verification.get("ok"):
            # Dana terverifikasi masuk di Binance! Langsung kirim produk
            await complete_order(order_id, verification.get("txId") or order_id, context)
            text, kb = ui.success_page(order_id)
            if query.message:
                if query.message.photo:
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    await app.bot.send_message(chat_id=query.message.chat_id, text=text, parse_mode="HTML", reply_markup=kb)
                else:
                    await safe_edit(chat_id=query.message.chat_id, message_id=query.message.message_id, text=text, reply_markup=kb)
            return
        elif verification.get("reason") == "TRANSACTION_NOT_FOUND":
            await query.answer("Transaction not found yet. Please make sure you included Order ID in notes!", show_alert=True)
            # Jangan langsung batalkan, beri tahu user untuk coba lagi atau submit ke admin

    # 2. Fallback: Verifikasi manual oleh admin jika belum ada API key atau belum terdeteksi
    db.set_order_status(order_id, "AWAITING_ADMIN")
    await asyncio.to_thread(sync_order_to_sheet, db.get_order(order_id))

    text, kb = ui.awaiting_admin_page(order_id)
    await query.answer("Payment confirmation submitted! ✅")

    if query.message:
        if query.message.photo:
            try:
                await query.message.delete()
            except Exception:
                pass
            await app.bot.send_message(
                chat_id=query.message.chat_id, text=text, parse_mode="HTML", reply_markup=kb
            )
        else:
            await safe_edit(chat_id=query.message.chat_id, message_id=query.message.message_id, text=text, reply_markup=kb)

    await notify_admin_pending_verification(order_id)


async def notify_admin_pending_verification(order_id):
    if config.ADMIN_CHAT_ID is None:
        return
    order = db.get_order(order_id)
    if not order:
        return
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve:{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject:{order_id}"),
            ]
        ]
    )
    text = (
        f"🕐 <b>PAYMENT AWAITING VERIFICATION</b>\n\n"
        f"🆔 Order: <code>{order_id}</code>\n"
        f"🛒 {ui.esc(order['product_name'])} x{order['qty']}\n"
        f"💰 Total: <b>{ui.fmt_price(order['total'])}</b>\n"
        f"👤 User: {order['telegram_id']}\n\n"
        f"Verify the incoming payment, then click <b>Approve</b> or <b>Reject</b>."
    )
    try:
        await app.bot.send_message(
            chat_id=config.ADMIN_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception as e:
        logger.error("Notif verifikasi admin gagal: %s", e)


async def admin_approve(query, context, chat_id, msg_id, order_id):
    if config.ADMIN_CHAT_ID is None or str(query.from_user.id) != str(config.ADMIN_CHAT_ID):
        await query.answer("Admin only.")
        return
    order = db.get_order(order_id)
    if not order:
        await query.answer("Order not found.")
        return
    if order["status"] != "AWAITING_ADMIN":
        await query.answer("Order is not awaiting verification.")
        return
    await complete_order(order_id, order_id, context)
    await query.answer("Approved.")
    try:
        await safe_edit(
            chat_id=chat_id,
            message_id=msg_id,
            text=f"✅ <b>Order approved.</b>\nProducts for <code>{order_id}</code> have been sent.",
            reply_markup=InlineKeyboardMarkup([]),
        )
    except Exception:
        pass


async def admin_reject(query, context, chat_id, msg_id, order_id):
    if config.ADMIN_CHAT_ID is None or str(query.from_user.id) != str(config.ADMIN_CHAT_ID):
        await query.answer("Admin only.")
        return
    order = db.get_order(order_id)
    if not order:
        await query.answer("Order not found.")
        return
    if order["status"] != "AWAITING_ADMIN":
        await query.answer("Order is not awaiting verification.")
        return
    db.release_reservation(order_id)
    db.set_order_status(order_id, "FAILED")
    await asyncio.to_thread(sync_order_to_sheet, db.get_order(order_id))
    try:
        await context.bot.send_message(
            chat_id=order["telegram_id"],
            text="❌ Your payment could not be verified. If you already transferred, please contact admin.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Notif reject ke user gagal: %s", e)
    await query.answer("Rejected.")
    try:
        await safe_edit(
            chat_id=chat_id,
            message_id=msg_id,
            text=f"❌ <b>Order rejected.</b>\n<code>{order_id}</code> was cancelled.",
            reply_markup=InlineKeyboardMarkup([]),
        )
    except Exception:
        pass


async def cleanup_reservations(context: ContextTypes.DEFAULT_TYPE):
    """Rutin lepas reservasi stok yang ditinggalkan (semua metode bayar)."""
    try:
        db.release_expired_reservations(max_age_hours=24)
    except Exception as e:
        logger.error("Cleanup reservasi gagal: %s", e)


async def check_payments(context: ContextTypes.DEFAULT_TYPE):
    if config.TEST_MODE or config.PAYMENT_METHOD != "nevapedia":
        return
    if not config.NEVAPEDIA_API_KEY:
        return
    now = db.utcnow()
    for order in db.get_pending_orders():
        try:
            status = await asyncio.to_thread(nevapedia_get_status, order.get("payment_id"))
            action = _payment_poll_action(status, order.get("created_at") or "", now)
            if action == "complete":
                await complete_order(
                    order["order_id"], order.get("payment_id") or order["order_id"], context
                )
            elif action == "fail":
                db.release_reservation(order["order_id"])
                db.set_order_status(order["order_id"], "FAILED")
                await asyncio.to_thread(
                    sync_order_to_sheet, db.get_order(order["order_id"])
                )
        except Exception as e:
            logger.error("Polling error %s: %s", order["order_id"], e)


async def notify_affiliate(referrer_uid, amount, order_id):
    text = (
        f"🎉 <b>Commission Received!</b>\n\n"
        f"Your referral completed a purchase.\n"
        f"🧾 Order: <code>{order_id}</code>\n"
        f"💰 Commission: <b>{ui.fmt_price(amount)}</b>\n\n"
        f"Check your balance with /affiliate"
    )
    try:
        await app.bot.send_message(
            chat_id=int(referrer_uid), text=text, parse_mode="HTML"
        )
    except Exception as e:
        logger.error("Notif komisi gagal: %s", e)


def affiliate_text(uid):
    link = (
        f"https://t.me/{bot_username}?start=ref_{uid}"
        if bot_username
        else "BOT_USERNAME not detected yet"
    )
    balance = db.get_wallet(uid)
    refs = db.count_referrals(uid)
    text = (
        f"🤝 <b>AFFILIATE PROGRAM</b>\n\n"
        f"Share your link below to earn "
        f"<b>{config.AFFILIATE_PERCENT}%</b> commission on every successful purchase!\n\n"
        f"🔗 <code>{link}</code>\n\n"
        f"📊 Referrals: <b>{refs}</b> users\n"
        f"💰 Commission balance: <b>{ui.fmt_price(balance)}</b>\n\n"
        f"Manual payout — please contact admin."
    )
    comms = db.get_commissions(uid, 5)
    if comms:
        text += "\n\n🧾 <b>Recent Commissions:</b>\n"
        for c in comms:
            status = "✅ paid" if c["status"] == "PAID" else "⏳ pending"
            text += f"• <code>{c['order_id']}</code> {ui.fmt_price(c['amount'])} · {status}\n"
    return text


async def affiliate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        affiliate_text(str(update.effective_user.id)), parse_mode="HTML"
    )


async def admin_affiliates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if config.ADMIN_CHAT_ID is None or str(update.effective_user.id) != str(config.ADMIN_CHAT_ID):
        await update.message.reply_text("Admin only.")
        return
    rows = db.get_all_wallets()
    if not rows:
        await update.message.reply_text("No recorded commissions yet.")
        return
    text = "🤝 <b>AFFILIATE & COMMISSION LEDGER</b>\n\n"
    for i, w in enumerate(rows, 1):
        text += (
            f"{i}. UID <code>{w['uid']}</code>\n"
            f"   👥 {w['referrals']} ref · 🧾 {w['total_comm']} comms · "
            f"💰 <b>{ui.fmt_price(w['balance'])}</b>\n"
        )
    text += "\nPayout: /payout &lt;uid&gt;"
    await update.message.reply_text(text, parse_mode="HTML")


async def admin_payout_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if config.ADMIN_CHAT_ID is None or str(update.effective_user.id) != str(config.ADMIN_CHAT_ID):
        await update.message.reply_text("Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Format: /payout <uid>")
        return
    uid = context.args[0]
    if not uid.isdigit():
        await update.message.reply_text("UID must be numbers.")
        return
    n = db.mark_payout(uid)
    await update.message.reply_text(f"✅ {n} commissions for UID <code>{ui.esc(uid)}</code> marked PAID.", parse_mode="HTML")
    if n and uid.isdigit():
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text="🎉 Your affiliate commission has been paid out by admin. Thank you! 💵",
            )
        except Exception as e:
            logger.error("Notif payout gagal: %s", e)


async def admin_addstock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Akses khusus admin. 🙅")
        return

    raw = update.message.text or ""
    lines = [l.strip() for l in raw.split("\n")]

    # Hapus command "/addstock" dari baris pertama, ambil product_id
    first = lines[0] if lines else ""
    parts = first.split(None, 1)
    if len(parts) < 2:
        await update.message.reply_text(
            "Format: /addstock PRODUCT_ID\ncontent1\ncontent2\n\n"
            "Contoh:\n"
            "<code>/addstock D001</code>\n"
            "<code>akun1@email.com</code>\n"
            "<code>akun2@email.com</code>",
            parse_mode="HTML",
        )
        return

    product_id = parts[1].strip()

    # Sisa baris = content items (trim, skip kosong)
    items = [l.strip() for l in lines[1:] if l.strip()]
    if not items:
        # Cek apakah ada content di baris yang sama setelah product_id
        remaining = parts[1].strip()
        if remaining and remaining != product_id:
            items = [remaining]

    if not items:
        await update.message.reply_text(
            "Tidak ada content stok. Kirim format:\n"
            "<code>/addstock PRODUCT_ID</code>\n"
            "<code>content1</code>\n"
            "<code>content2</code>",
            parse_mode="HTML",
        )
        return

    # Cek produk ada
    product = get_product(product_id)
    if not product:
        await update.message.reply_text(
            f"Produk <code>{ui.esc(product_id)}</code> tidak ditemukan.",
            parse_mode="HTML",
        )
        return

    await update.message.reply_text("⏳ Menambah stok ke Google Sheets...")

    result = await asyncio.to_thread(add_stock_to_sheet, product_id, items)
    if not result:
        await update.message.reply_text(
            "❌ Failed to add stock. Check SHEET_WRITE_URL or Apps Script."
        )
        return

    added = result.get("added", 0)

    await asyncio.to_thread(sync.sync_from_sheets, True)
    total = db.count_available(product_id)

    now_str = (datetime.now() + timedelta(hours=7)).strftime("%d/%m/%Y %H:%M")

    await update.message.reply_text(
        f"✅ <b>Stock added successfully!</b>\n\n"
        f"🛒 Product: {ui.esc(product['name'])} (<code>{product_id}</code>)\n"
        f"📦 Added: <b>{added}</b> items\n\n"
        f"Stock will update automatically on next /menu.",
        parse_mode="HTML",
    )

    admin_name = update.effective_user.first_name or update.effective_user.username or "Admin"
    await notify_channel(
        f"📦 <b>NEW RESTOCK</b>\n\n"
        f"🏷️ Produk: {ui.esc(product['name'])}\n"
        f"➕ Tambahan: <b>{added}</b> item\n"
        f"📊 Total stok: <b>{total}</b> item\n"
        f"📅 {now_str}"
    )


async def notify_admin(text):
    if not config.ADMIN_CHAT_ID:
        return
    if config.TEST_MODE:
        text = f"🧪 <b>MODE UJI COBA</b>\n\n{text}"
    try:
        await app.bot.send_message(
            chat_id=config.ADMIN_CHAT_ID, text=text, parse_mode="HTML"
        )
    except Exception as e:
        logger.error("Notifikasi admin gagal: %s", e)


async def notify_channel(text):
    if not config.CHANNEL_USERNAME:
        return
    try:
        await app.bot.send_message(
            chat_id=config.CHANNEL_USERNAME, text=text, parse_mode="HTML"
        )
    except Exception as e:
        logger.error("Notifikasi channel gagal: %s", e)


async def setup_commands(application):
    user_cmds = [
        BotCommand("start", "Start Bot"),
        BotCommand("products", "Browse Catalog"),
        BotCommand("stock", "Live Stock"),
        BotCommand("promo", "Special Offers"),
        BotCommand("orders", "My Orders"),
        BotCommand("join", "Join Channel"),
        BotCommand("support", "Support & Help"),
        BotCommand("affiliate", "Affiliate Program"),
    ]
    admin_cmds = user_cmds + [
        BotCommand("admin", "Admin Dashboard"),
        BotCommand("addstock", "Add Stock Items"),
        BotCommand("affiliates", "Affiliate Wallets"),
        BotCommand("payout", "Payout Commission"),
    ]
    try:
        await application.bot.set_my_commands(user_cmds, scope=BotCommandScopeDefault())
        if config.ADMIN_CHAT_ID is not None:
            await application.bot.set_my_commands(
                admin_cmds, scope=BotCommandScopeChat(chat_id=config.ADMIN_CHAT_ID)
            )
        logger.info("Command menu terpasang")
    except Exception as e:
        logger.error("Gagal setMyCommands: %s", e)


async def post_init(application):
    global bot_username
    try:
        me = await application.bot.get_me()
        bot_username = me.username or ""
    except Exception as e:
        logger.error("Gagal get_me untuk link afiliasi: %s", e)
    await setup_commands(application)


async def join_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel = (config.CHANNEL_USERNAME or "").strip().lstrip("@")
    if not channel:
        await update.message.reply_text("Channel is not configured.")
        return
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{channel}")]]
    )
    await update.message.reply_text(
        "Please join our channel for updates, discounts, and latest restocks 👇",
        reply_markup=kb,
    )


async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛟 <b>Need Assistance?</b>\n\n"
        "For questions, order issues, or product inquiries, please contact our support admin. "
        "We are happy to help! 🙏"
    )
    buttons = []
    if config.CHANNEL_USERNAME:
        buttons.append(
            [
                InlineKeyboardButton(
                    "📢 Join Channel", url=f"https://t.me/{config.CHANNEL_USERNAME.lstrip('@')}"
                )
            ]
        )
    admin_user = "levanyasya"
    if admin_user:
        buttons.append(
            [InlineKeyboardButton("💬 Contact Support", url=f"https://t.me/{admin_user}")]
        )
    elif config.ADMIN_CHAT_ID is not None:
        buttons.append(
            [InlineKeyboardButton("💬 Contact Support", url=f"tg://user?id={config.ADMIN_CHAT_ID}")]
        )
    if buttons:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await update.message.reply_text(text, parse_mode="HTML")


async def any_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    
    # 0. Debugger pembaca ID Custom Emoji animasi Telegram Premium
    if update.message and update.message.entities:
        for ent in update.message.entities:
            if ent.type == "custom_emoji" and ent.custom_emoji_id:
                await update.message.reply_text(
                    f"✨ <b>Custom Animated Emoji Detected!</b>\n"
                    f"🆔 <code>{ent.custom_emoji_id}</code>\n\n"
                    f"HTML Tag:\n"
                    f"<code>&lt;tg-emoji emoji-id=\"{ent.custom_emoji_id}\"&gt;⭐&lt;/tg-emoji&gt;</code>",
                    parse_mode="HTML"
                )
                return

    # 1. Cek jika user sedang mengetik custom quantity
    awaiting_pid = context.user_data.get("awaiting_qty_for")
    if awaiting_pid and text.isdigit():
        target_qty = int(text)
        product = get_product(awaiting_pid)
        if product:
            avail = db.count_available(awaiting_pid)
            is_gemini = product.get("id") == "P0001" or "gemini" in str(product.get("name", "")).lower()
            min_q = 2 if is_gemini else 1
            if target_qty < min_q:
                target_qty = min_q
            elif target_qty > avail:
                target_qty = max(min_q, avail)
            
            context.user_data["qty"] = target_qty
            context.user_data["product_id"] = awaiting_pid
            context.user_data.pop("awaiting_qty_for", None)
            
            text_msg, kb = ui.product_page(product, target_qty)
            await update.message.reply_text(text_msg, parse_mode="HTML", reply_markup=kb)
            return

    # 2. Cek jika user mengetik nomor produk atau jumlah qty saat melihat produk
    if text.isdigit():
        num = int(text)
        current_pid = context.user_data.get("product_id")
        
        # Jika user sedang di halaman produk dan mengetik angka -> set sebagai qty
        if current_pid:
            product = get_product(current_pid)
            if product:
                avail = db.count_available(current_pid)
                is_gemini = product.get("id") == "P0001" or "gemini" in str(product.get("name", "")).lower()
                min_q = 2 if is_gemini else 1
                set_qty = max(min_q, min(avail, num))
                context.user_data["qty"] = set_qty
                text_msg, kb = ui.product_page(product, set_qty)
                await update.message.reply_text(text_msg, parse_mode="HTML", reply_markup=kb)
                return

        # Jika user mengetik nomor indeks produk di catalog
        products = db.get_active_products()
        if 1 <= num <= len(products):
            product = products[num - 1]
            is_gemini = product.get("id") == "P0001" or "gemini" in str(product.get("name", "")).lower()
            default_qty = 2 if is_gemini else 1
            context.user_data["qty"] = default_qty
            context.user_data["product_id"] = product["id"]
            avail = db.count_available(product["id"])
            if avail < default_qty:
                from ui import soldout_page
                text_msg, kb = soldout_page()
                await update.message.reply_text(text_msg, parse_mode="HTML", reply_markup=kb)
            else:
                text_msg, kb = ui.product_page(product, default_qty)
                await update.message.reply_text(text_msg, parse_mode="HTML", reply_markup=kb)
            return

    await update.message.reply_text("Please use the menu buttons or type /start to shop. 🙂")


app = None
bot_username = ""


def main():
    global app
    if not config.TOKEN:
        logger.error(
            "TOKEN belum diset. Isi file .env (lihat .env.example) atau set env TOKEN."
        )
        return
    if config.ADMIN_CHAT_ID is None:
        logger.warning(
            "ADMIN_CHAT_ID belum diset. Fitur admin akan nonaktif."
        )
    db.init_db()
    sync.sync_from_sheets()
    db.release_expired_reservations(max_age_hours=24)
    sync.restore_inflight_orders()
    sync.restore_sold_stock()
    start_health_server()

    app = (
        Application.builder()
        .token(config.TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("products", products_cmd))
    app.add_handler(CommandHandler("promo", promo_cmd))
    app.add_handler(CommandHandler("stock", stock_cmd))
    app.add_handler(CommandHandler("orders", orders_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("join", join_cmd))
    app.add_handler(CommandHandler("support", support_cmd))
    app.add_handler(CommandHandler("affiliate", affiliate_cmd))
    app.add_handler(CommandHandler("addstock", admin_addstock_cmd))
    app.add_handler(CommandHandler("affiliates", admin_affiliates_cmd))
    app.add_handler(CommandHandler("payout", admin_payout_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("productsadmin", admin_products_cmd))
    app.add_handler(CommandHandler("stockadmin", admin_stock_cmd))
    app.add_handler(CommandHandler("ordersadmin", admin_orders_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, any_text))

    app.job_queue.run_repeating(check_payments, interval=60, first=30)
    app.job_queue.run_repeating(cleanup_reservations, interval=60, first=45)
    app.job_queue.run_repeating(keep_alive, interval=300, first=60)

    logger.info("Bot Digitalin Store berjalan (polling)...")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
