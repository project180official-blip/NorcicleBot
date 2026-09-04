import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

import config
import db

BRAND = "NORCICLE TERMINAL"


def esc(s):
    return html.escape(str(s))


def header(title=None):
    lines = [
        f"⚡ <code>[ {BRAND} // v2.0 ]</code>",
        "<code>─── [● SYSTEM ONLINE] ───</code>"
    ]
    if title:
        lines.append("")
        lines.append(f"◈ <b>{title}</b>")
    return "\n".join(lines)


def fmt_price(n):
    try:
        val = float(n or 0)
        if val.is_integer():
            return f"${int(val)}"
        return f"${val:.2f}"
    except (ValueError, TypeError):
        return f"${n}"


def force_join_page():
    channel = config.CHANNEL_USERNAME
    channel_link = f"https://t.me/{channel.lstrip('@')}"
    text = (
        f"{header('AUTHENTICATION REQUIRED')}\n\n"
        f"<code>ACCESS GATE:</code> Channel membership required.\n\n"
        f"🛰️ <b>Network Node:</b> <code>{channel}</code>\n\n"
        f"Connect to the network node below and click <b>[ VERIFY ACCESS ]</b>."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛰️ Connect Node", url=channel_link)],
            [InlineKeyboardButton("⚡ [ VERIFY ACCESS ]", callback_data="checkjoin")],
        ]
    )
    return text, keyboard


def product_line(p):
    avail = db.count_available(p["id"])
    status = f"<code>[● {avail} READY]</code>" if avail > 0 else "<code>[○ SOLD OUT]</code>"
    return (
        f"<code>┌─</code> {p['emoji']} <b>{esc(p['name'])}</b>\n"
        f"<code>└─▸</code> <b>{fmt_price(p['price'])}</b>  {status}"
    )


def home_text(user_name=None):
    products = db.get_active_products()
    user_tag = f"<code>{esc(user_name)}</code>" if user_name else "<code>ANONYMOUS</code>"

    blocks = []
    for i, p in enumerate(products, 1):
        avail = db.count_available(p["id"])
        status = f"<code>[● {avail} IN STOCK]</code>" if avail > 0 else "<code>[○ SOLD OUT]</code>"
        blocks.append(
            f"<code>[{i:02d}]</code> {p['emoji']} <b>{esc(p['name'])}</b>\n"
            f"      <code>PRICE :</code> <b>{fmt_price(p['price'])}</b>\n"
            f"      <code>STATUS:</code> {status}"
        )
    feed = "\n\n".join(blocks) if blocks else "<code>[ NO ACTIVE FEEDS DETECTED ]</code>"

    text = (
        f"⚡ <code>[ {BRAND} // TERMINAL ]</code>\n"
        f"<code>USER // {user_tag}</code>\n"
        f"<code>STATUS // AUTHENTICATED [●]</code>\n\n"
        f"<code>─── [ LIVE CATALOG FEED ] ───</code>\n\n"
        f"{feed}\n\n"
        f"<code>─── [ SELECT COMMAND ] ───</code>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚡ [ EXECUTE ORDER ]", callback_data="catalog")],
            [
                InlineKeyboardButton("🔥 Hot Offers", callback_data="promo"),
                InlineKeyboardButton("📦 Live Vault", callback_data="stock"),
            ],
            [
                InlineKeyboardButton("🤝 Affiliate Node", callback_data="affiliate"),
                InlineKeyboardButton("🛰️ Support Desk", callback_data="contact"),
            ],
            [InlineKeyboardButton("↻ Sync Feed", callback_data="refresh")],
        ]
    )
    return text, keyboard


def promo_page():
    products = sorted(db.get_active_products(), key=lambda p: p["price"])
    if not products:
        text = f"{header('SPECIAL DEALS')}\n\n<code>[ NO ACTIVE PROMOTIONS ]</code>"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Return Terminal", callback_data="home")]]
        )
        return text, keyboard
    parts = [header("PROMO DEALS // HIGH PRIORITY")]
    blocks = [product_line(p) for p in products]
    parts.append("\n\n".join(blocks))
    text = "\n\n".join(parts) + "\n\n<code>⚡ Limited allocation available. Execute below:</code>"
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚡ [ EXECUTE ORDER ]", callback_data="catalog")],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard


def catalog_text():
    products = db.get_active_products()
    if not products:
        text = f"{header('PRODUCT CATALOG')}\n\n<code>[ NO PRODUCTS LOADED ]</code>"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Return Terminal", callback_data="home")]]
        )
        return text, keyboard

    parts = [header("SELECT PRODUCT ITEM")]
    blocks = []
    for i, p in enumerate(products, 1):
        avail = db.count_available(p["id"])
        status = f"<code>[● {avail} READY]</code>" if avail > 0 else "<code>[○ SOLD]</code>"
        blocks.append(
            f"<code>[{i:02d}]</code> {p['emoji']} <b>{esc(p['name'])}</b>\n"
            f"      <code>PRICE:</code> <b>{fmt_price(p['price'])}</b>  {status}"
        )
    parts.append("\n\n".join(blocks))
    text = "\n\n".join(parts) + "\n\n<code>Select target product below:</code>"

    rows = [
        [InlineKeyboardButton(f"⚡ {p['emoji']} {esc(p['name'])}", callback_data=f"product:{p['id']}")]
        for p in products
    ]
    rows.append(
        [
            InlineKeyboardButton("📦 Live Vault", callback_data="stock"),
            InlineKeyboardButton("« Return Terminal", callback_data="home"),
        ]
    )
    return text, InlineKeyboardMarkup(rows)


def product_page(product, qty):
    avail = db.count_available(product["id"])
    total = product["price"] * qty
    sold_out = avail < 1

    status_tag = f"<code>[● {avail} UNITS READY]</code>" if avail > 0 else "<code>[○ OUT OF STOCK]</code>"

    text = (
        f"⚡ <code>[ PRODUCT DETAIL // {product['id']} ]</code>\n\n"
        f"{product['emoji']} <b>{esc(product['name'])}</b>\n\n"
        f"<code>DESCRIPTION:</code>\n"
        f"> {esc(product['description'])}\n\n"
        f"<code>┌─ UNIT PRICE :</code> <b>{fmt_price(product['price'])}</b>\n"
        f"<code>├─ VAULT INVENTORY :</code> {status_tag}\n"
        f"<code>├─ DELIVERY   :</code> <b>INSTANT DEPLOY [●]</b>\n"
        f"<code>└─ QUANTITY   :</code> <b>{qty}x</b>\n\n"
        f"<code>TOTAL PAYABLE // </code><b>{fmt_price(total)}</b>"
    )

    if sold_out:
        rows = [
            [InlineKeyboardButton("🚫 [ OUT OF STOCK ]", callback_data="noop")],
            [
                InlineKeyboardButton("« Catalog", callback_data="catalog"),
                InlineKeyboardButton("« Terminal", callback_data="home"),
            ],
        ]
    else:
        rows = [
            [
                InlineKeyboardButton("[-]", callback_data=f"qtydec:{product['id']}"),
                InlineKeyboardButton(f"Qty: {qty}", callback_data="noop"),
                InlineKeyboardButton("[+]", callback_data=f"qtyinc:{product['id']}"),
            ],
            [InlineKeyboardButton("⚡ [ PROCEED CHECKOUT ]", callback_data=f"buy:{product['id']}")],
            [
                InlineKeyboardButton("« Catalog", callback_data="catalog"),
                InlineKeyboardButton("« Terminal", callback_data="home"),
            ],
        ]
    return text, InlineKeyboardMarkup(rows)


def stock_page():
    products = db.get_active_products()
    parts = [header("LIVE VAULT INVENTORY")]
    if not products:
        parts.append("<code>[ NO INVENTORY DATA ]</code>")
    for p in products:
        parts.append(product_line(p))
    text = "\n\n".join(parts)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚡ [ EXECUTE ORDER ]", callback_data="catalog")],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard


def orders_page(user_id):
    rows = db.get_my_orders(user_id)
    parts = [header("ORDER LOGS")]
    if not rows:
        parts.append("<code>[ NO TRANSACTION LOGS FOUND ]</code>")
    for o in rows:
        icon = {
            "PENDING": "⏳",
            "PAID": "💳",
            "COMPLETED": "✓",
            "FAILED": "❌",
            "PAID_BUT_OUT_OF_STOCK": "⛔",
            "AWAITING_ADMIN": "🕐",
        }.get(o["status"], "❓")
        parts.append(
            f"<code>┌─ TX:</code> <code>{o['order_id']}</code>\n"
            f"<code>├─ ITEM:</code> {esc(o['product_name'])} x{o['qty']}\n"
            f"<code>└─ TOTAL:</code> <b>{fmt_price(o['total'])}</b> <code>[{icon} {o['status']}]</code>"
        )
    text = "\n\n".join(parts)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚡ [ EXECUTE ORDER ]", callback_data="catalog")],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard


def contact_page():
    admin = db.get_setting("ADMIN_USERNAME", "admin")
    text = (
        f"{header('SUPPORT DESK // ENCRYPTED COMMS')}\n\n"
        f"<code>NODE ADMIN //</code> @{esc(admin)}\n\n"
        f"<code>─── [ TERMINAL COMMANDS ] ───</code>\n"
        f"<code>/start</code>    - Launch main terminal\n"
        f"<code>/products</code> - Open product catalog\n"
        f"<code>/stock</code>    - Query vault inventory\n"
        f"<code>/promo</code>    - Special deal feeds\n"
        f"<code>/orders</code>   - Query order logs\n"
        f"<code>/support</code>  - Open support comms"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛰️ Connect Admin Comms", url=f"https://t.me/{admin}")],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard


def loading_text(msg="Processing crypto gateway request..."):
    return f"⚡ <code>[ {esc(msg)} ]</code>\n\n<code>Connecting to blockchain network...</code>", InlineKeyboardMarkup([])


def payment_method_page(order, usdt_amount=None):
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    text = (
        f"{header('CRYPTO SETTLEMENT GATEWAY')}\n\n"
        f"<code>ORDER ID //</code> <code>{order['order_id']}</code>\n"
        f"<code>ITEM     //</code> {esc(order['product_name'])} x{order['qty']}\n"
        f"<code>VALUE    //</code> <b>{fmt_price(order['total'])}</b> (<b>{amt:.2f} USDT</b>)\n\n"
        f"<code>Select Web3 settlement channel:</code>"
    )
    buttons = [
        [
            InlineKeyboardButton("🟡 Binance Pay (Pay ID)", callback_data=f"pay_binance:{order['order_id']}"),
            InlineKeyboardButton("🌐 USDT (BEP20 / BSC)", callback_data=f"pay_usdt:{order['order_id']}"),
        ],
        [InlineKeyboardButton("« Abort Order", callback_data="home")],
    ]
    return text, InlineKeyboardMarkup(buttons)


def binance_pay_page(order, usdt_amount=None):
    pay_id = config.BINANCE_PAY_ID
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    text = (
        f"{header('BINANCE PAY SETTLEMENT')}\n\n"
        f"<code>ORDER ID //</code> <code>{order['order_id']}</code>\n"
        f"<code>ITEM     //</code> {esc(order['product_name'])} x{order['qty']}\n"
        f"<code>AMOUNT   //</code> <b>{amt:.2f} USDT</b> (Exact)\n\n"
        f"📲 <b>TARGET BINANCE ID:</b>\n"
        f"<code>{pay_id}</code>\n\n"
        f"<code>TRANSACTION GUIDE:</code>\n"
        f"1. Open Binance App ➔ Pay / Send\n"
        f"2. Input Binance ID: <code>{pay_id}</code>\n"
        f"3. Send exact: <b>{amt:.2f} USDT</b>\n"
        f"4. Add note/remark: <code>{order['order_id']}</code>\n\n"
        f"Click <b>[ CONFIRM TRANSFER ]</b> once completed 👇"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📋 Copy Binance ID",
                    copy_text=CopyTextButton(text=pay_id),
                )
            ],
            [
                InlineKeyboardButton(
                    "⚡ [ CONFIRM TRANSFER ]",
                    callback_data=f"confirm_pay:{order['order_id']}",
                )
            ],
            [InlineKeyboardButton("🌐 Switch to BEP20 Wallet", callback_data=f"pay_usdt:{order['order_id']}")],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard


def crypto_usdt_page(order, usdt_amount=None):
    wallet = config.CRYPTO_WALLET_USDT
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    text = (
        f"{header('USDT BEP20 ON-CHAIN GATEWAY')}\n\n"
        f"<code>ORDER ID //</code> <code>{order['order_id']}</code>\n"
        f"<code>ITEM     //</code> {esc(order['product_name'])} x{order['qty']}\n"
        f"<code>AMOUNT   //</code> <b>{amt:.2f} USDT</b>\n\n"
        f"📩 <b>CONTRACT / WALLET (BSC / BEP20):</b>\n"
        f"<code>{wallet}</code>\n\n"
        f"⚠️ <code>NETWORK NOTICE:</code>\n"
        f"• Exact transfer: <b>{amt:.2f} USDT</b>\n"
        f"• Network: <b>BNB Smart Chain (BEP20)</b>\n"
        f"• Instant deployment upon admin ledger validation.\n\n"
        f"Click <b>[ CONFIRM TRANSFER ]</b> once broadcasted 👇"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📋 Copy Wallet Address",
                    copy_text=CopyTextButton(text=wallet),
                )
            ],
            [
                InlineKeyboardButton(
                    "⚡ [ CONFIRM TRANSFER ]",
                    callback_data=f"confirm_pay:{order['order_id']}",
                )
            ],
            [InlineKeyboardButton("🟡 Switch to Binance Pay", callback_data=f"pay_binance:{order['order_id']}")],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard


def test_payment_page(order):
    text = (
        f"{header('TESTNET SIMULATION')}\n\n"
        f"<code>SIMULATED PAYMENT NODE</code>\n\n"
        f"<code>ORDER ID //</code> <code>{order['order_id']}</code>\n"
        f"<code>ITEM     //</code> {esc(order['product_name'])} x{order['qty']}\n"
        f"<code>TOTAL    //</code> <b>{fmt_price(order['total'])}</b>\n\n"
        f"Execute simulated transaction below:"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚡ [ SIMULATE SUCCESS ]", callback_data=f"paid:{order['order_id']}")],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard


def pending_page(order):
    text = (
        f"{header('SETTLEMENT PENDING')}\n\n"
        f"<code>ORDER ID //</code> <code>{order['order_id']}</code>\n"
        f"<code>ITEM     //</code> {esc(order['product_name'])} x{order['qty']}\n"
        f"<code>TOTAL    //</code> <b>{fmt_price(order['total'])}</b>\n\n"
        f"<code>Awaiting transaction confirmation on the network...</code>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "↻ Query Status", callback_data=f"paid:{order['order_id']}"
                )
            ],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard


def awaiting_admin_page(order_id):
    text = (
        f"{header('TRANSACTION IN VERIFICATION')}\n\n"
        f"<code>ORDER ID //</code> <code>{esc(order_id)}</code>\n\n"
        f"<code>Transaction broadcast registered.</code>\n"
        f"<code>Validator node is currently reviewing the ledger.</code>\n"
        f"<code>Auto-dispatch will trigger immediately upon verification. 🙏</code>"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Return Terminal", callback_data="home")]]
    )
    return text, keyboard


def success_page(order_id):
    text = (
        f"{header('TRANSACTION COMPLETED')}\n\n"
        f"<code>[● LEDGER VALIDATED & SETTLED]</code>\n"
        f"<code>ORDER ID //</code> <code>{esc(order_id)}</code>\n\n"
        f"🎁 <b>Digital payload has been deployed above.</b>\n"
        f"Thank you for transacting with us."
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Return Terminal", callback_data="home")]]
    )
    return text, keyboard


def no_stock_paid_page(order_id):
    text = (
        f"{header('VAULT DEPLETED // REFUND PENDING')}\n\n"
        f"<code>PAYMENT CONFIRMED:</code> <code>{esc(order_id)}</code>\n\n"
        f"<code>Target vault inventory was depleted by concurrent order.</code>\n"
        f"<code>Admin is issuing immediate manual refund/dispatch.</code>"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Return Terminal", callback_data="home")]]
    )
    return text, keyboard


def error_page(message="An error occurred, please try again later."):
    text = f"{header('EXECUTION ERROR')}\n\n⚠️ <code>{esc(message)}</code>"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Return Terminal", callback_data="home")]]
    )
    return text, keyboard


def soldout_page():
    text = (
        f"{header('VAULT DEPLETED')}\n\n"
        f"<code>Selected item is currently out of stock.</code>\n"
        f"<code>Please select alternative available assets.</code>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚡ [ VIEW CATALOG ]", callback_data="catalog")],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard


def admin_panel():
    products = db.get_active_products()
    total_stock = sum(db.count_available(p["id"]) for p in products)
    orders = db.get_all_orders(limit=50)
    pending = sum(1 for o in orders if o["status"] == "PENDING")
    completed = sum(1 for o in orders if o["status"] == "COMPLETED")

    text = (
        f"{header('ADMIN ROOT CONSOLE')}\n\n"
        f"<code>METRICS SUMMARY:</code>\n"
        f"<code>├─ ACTIVE ASSETS :</code> {len(products)}\n"
        f"<code>├─ VAULT ITEMS   :</code> {total_stock}\n"
        f"<code>└─ TRANSACTIONS  :</code> {len(orders)} ({pending} pend, {completed} done)\n\n"
        f"<code>Connected to Google Sheets database ledger.</code>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📦 Vault Stock", callback_data="stock"),
                InlineKeyboardButton("🧾 Orders Log", callback_data="ordersadmin"),
            ],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard


def admin_orders_page():
    rows = db.get_all_orders(limit=50)
    parts = [header("GLOBAL TRANSACTION LEDGER")]
    if not rows:
        parts.append("<code>[ NO TRANSACTIONS LOGGED ]</code>")
    for o in rows:
        icon = {
            "PENDING": "⏳",
            "PAID": "💳",
            "COMPLETED": "✓",
            "FAILED": "❌",
            "PAID_BUT_OUT_OF_STOCK": "⛔",
            "AWAITING_ADMIN": "🕐",
        }.get(o["status"], "❓")
        parts.append(
            f"<code>┌─ TX:</code> <code>{o['order_id']}</code>\n"
            f"<code>├─ ITEM:</code> {esc(o['product_name'])} x{o['qty']}\n"
            f"<code>└─ USER:</code> <code>{o['telegram_id']}</code> ➔ <b>{fmt_price(o['total'])}</b> <code>[{icon} {o['status']}]</code>"
        )
    text = "\n\n".join(parts)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔐 Admin Console", callback_data="admin")],
            [InlineKeyboardButton("« Return Terminal", callback_data="home")],
        ]
    )
    return text, keyboard
