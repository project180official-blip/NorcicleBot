import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

import config
import db

BRAND = "NORCICLE SHOP"


def esc(s):
    return html.escape(str(s))


def header(title=None):
    lines = [f"✦ <b>{BRAND}</b> ✦", "Your Digital Destination"]
    if title:
        lines.append("")
        lines.append(title)
    return "\n".join(lines)


def fmt_price(n):
    return f"Rp{n:,}"


def force_join_page():
    channel = config.CHANNEL_USERNAME
    channel_link = f"https://t.me/{channel.lstrip('@')}"
    text = (
        f"{header()}\n\n"
        f"Before you start shopping, please <b>join our channel</b> first!\n\n"
        f"📢 Channel: {channel}\n\n"
        f"Click the button below to join, then click <b>✅ Joined</b>."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Join Channel", url=channel_link)],
            [InlineKeyboardButton("✅ Joined", callback_data="checkjoin")],
        ]
    )
    return text, keyboard


def product_line(p):
    avail = db.count_available(p["id"])
    ready = f"🟢 {avail} ready" if avail > 0 else "⏳ sold out"
    return (
        f"{p['emoji']} <b>{esc(p['name'])}</b>\n"
        f"   {fmt_price(p['price'])} · {ready}"
    )


def home_text(user_name=None):
    products = db.get_active_products()
    greeting = f"👋 Hello, <b>{esc(user_name)}</b>!" if user_name else "👋 Hello!"

    blocks = []
    for i, p in enumerate(products, 1):
        avail = db.count_available(p["id"])
        ready = f"🟢 {avail} ready" if avail > 0 else "⏳ sold out"
        blocks.append(
            f"<b>{i}.</b> {esc(p['name'])}\n"
            f"   {fmt_price(p['price'])} · {ready}"
        )
    hot_section = "\n\n".join(blocks) if blocks else "No products available at the moment."

    text = (
        f"{greeting}\n"
        f"What digital product are you looking for today?\n"
        f"🔥 Featured Products:\n\n"
        f"{hot_section}\n\n"
        f"Type the <b>number</b> or tap buttons below 👇"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Shop Now", callback_data="catalog")],
            [
                InlineKeyboardButton("🔥 Offers", callback_data="promo"),
                InlineKeyboardButton("📦 Check Stock", callback_data="stock"),
            ],
            [
                InlineKeyboardButton("🤝 Affiliate", callback_data="affiliate"),
                InlineKeyboardButton("🎧 Support", callback_data="contact"),
            ],
            [InlineKeyboardButton("↻ Refresh", callback_data="refresh")],
        ]
    )
    return text, keyboard


def promo_page():
    products = sorted(db.get_active_products(), key=lambda p: p["price"])
    if not products:
        text = f"{header('<b>🔥 Offers</b>')}\n\nNo active offers available."
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⌂ Home", callback_data="home")]]
        )
        return text, keyboard
    parts = [header("<b>🔥 Special Offers</b>")]
    blocks = []
    for p in products:
        blocks.append(product_line(p))
    parts.append("\n\n".join(blocks))
    text = "\n\n".join(parts) + "\n\nLimited stock available, shop now!"
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Shop Now", callback_data="catalog")],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
        ]
    )
    return text, keyboard


def catalog_text():
    products = db.get_active_products()
    if not products:
        text = f"{header('<b>🛍️ Catalog</b>')}\n\nNo products available at the moment."
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⌂ Home", callback_data="home")]]
        )
        return text, keyboard

    parts = [header("<b>🛍️ Select Product</b>")]
    blocks = []
    for i, p in enumerate(products, 1):
        avail = db.count_available(p["id"])
        ready = f"🟢 {avail} ready" if avail > 0 else "⏳ sold out"
        blocks.append(
            f"<b>{i}.</b> {esc(p['name'])}\n"
            f"   {fmt_price(p['price'])} · {ready}"
        )
    parts.append("\n\n".join(blocks))
    text = "\n\n".join(parts) + "\n\nType the <b>number</b> or tap buttons below 👇"

    rows = [
        [InlineKeyboardButton(f"{p['emoji']} {esc(p['name'])}", callback_data=f"product:{p['id']}")]
        for p in products
    ]
    rows.append(
        [
            InlineKeyboardButton("📦 Check Stock", callback_data="stock"),
            InlineKeyboardButton("⌂ Home", callback_data="home"),
        ]
    )
    return text, InlineKeyboardMarkup(rows)


def product_page(product, qty):
    avail = db.count_available(product["id"])
    total = product["price"] * qty
    sold_out = avail < 1

    text = (
        f"💎 <b>{esc(product['name'])}</b>\n\n"
        f"{esc(product['description'])}\n\n"
        f"💰 <b>{fmt_price(product['price'])}</b>\n"
        f"{'🟢 In Stock' if avail > 0 else '⏳ Sold Out'} · {avail} items\n\n"
        f"✨ Instant Delivery\n"
        f"⚡ Automated Processing\n\n"
        f"Select Quantity:\n\n"
        f"<b>Total:</b>\n"
        f"<b>{fmt_price(total)}</b>"
    )

    if sold_out:
        rows = [
            [InlineKeyboardButton("⏳ Sold Out", callback_data="noop")],
            [
                InlineKeyboardButton("‹ Back", callback_data="catalog"),
                InlineKeyboardButton("⌂ Home", callback_data="home"),
            ],
        ]
    else:
        rows = [
            [
                InlineKeyboardButton("−", callback_data=f"qtydec:{product['id']}"),
                InlineKeyboardButton(f"{qty}", callback_data="noop"),
                InlineKeyboardButton("+", callback_data=f"qtyinc:{product['id']}"),
            ],
            [InlineKeyboardButton("⚡ Checkout Now", callback_data=f"buy:{product['id']}")],
            [
                InlineKeyboardButton("‹ Back", callback_data="catalog"),
                InlineKeyboardButton("⌂ Home", callback_data="home"),
            ],
        ]
    return text, InlineKeyboardMarkup(rows)


def stock_page():
    products = db.get_active_products()
    parts = [header("<b>📦 Live Stock</b>")]
    if not products:
        parts.append("No products available.")
    for p in products:
        parts.append(product_line(p))
    text = "\n\n".join(parts)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Shop Now", callback_data="catalog")],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
        ]
    )
    return text, keyboard


def orders_page(user_id):
    rows = db.get_my_orders(user_id)
    parts = [header("<b>🧾 My Orders</b>")]
    if not rows:
        parts.append("No orders yet.\nStart shopping now! 🛍️")
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
            f"{esc(o['product_name'])} × {o['qty']}\n"
            f"   <code>{o['order_id']}</code>\n"
            f"   {fmt_price(o['total'])} · {icon} {o['status']}"
        )
    text = "\n\n".join(parts)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Shop Now", callback_data="catalog")],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
        ]
    )
    return text, keyboard


def contact_page():
    admin = db.get_setting("ADMIN_USERNAME", "admin")
    text = (
        f"{header('<b>🎧 Customer Support</b>')}\n\n"
        f"Need assistance or having issues?\n"
        f"Contact our admin: @{esc(admin)}\n\n"
        f"<b>Available Commands</b>\n"
        f"/start — Main Menu\n"
        f"/products — Browse Products\n"
        f"/promo — Special Offers\n"
        f"/stock — Live Stock\n"
        f"/orders — Order History\n"
        f"/help — Support & Help"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📩 Contact Admin", url=f"https://t.me/{admin}")],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
        ]
    )
    return text, keyboard


def loading_text(msg="Processing your order..."):
    return f"⏳ <b>{esc(msg)}</b>\n\nPlease wait a moment...", InlineKeyboardMarkup([])


def payment_method_page(order, usdt_amount=None):
    usdt_line = f"\n💲 Est. Crypto: <b>{usdt_amount:.2f} USDT</b>" if usdt_amount else ""
    text = (
        f"{header('<b>💳 Payment Method</b>')}\n\n"
        f"🛍️ {esc(order['product_name'])} × {order['qty']}\n"
        f"💰 Total: <b>{fmt_price(order['total'])}</b>{usdt_line}\n"
        f"🧾 Order ID: <code>{order['order_id']}</code>\n\n"
        f"Please select your payment method 👇"
    )
    buttons = [
        [
            InlineKeyboardButton("🆔 Binance Pay (ID)", callback_data=f"pay_binance:{order['order_id']}"),
            InlineKeyboardButton("💲 USDT (BEP20)", callback_data=f"pay_usdt:{order['order_id']}"),
        ],
        [InlineKeyboardButton("⌂ Home", callback_data="home")],
    ]
    return text, InlineKeyboardMarkup(buttons)


def binance_pay_page(order, usdt_amount):
    pay_id = config.BINANCE_PAY_ID
    text = (
        f"{header('<b>🟡 Binance Pay Payment</b>')}\n\n"
        f"🛍️ {esc(order['product_name'])} × {order['qty']}\n"
        f"🧾 Order ID: <code>{order['order_id']}</code>\n\n"
        f"💰 Total: <b>{fmt_price(order['total'])}</b>\n"
        f"💲 Exact Amount: <b>{usdt_amount:.2f} USDT</b>\n\n"
        f"📲 <b>Send to Binance ID:</b>\n"
        f"<code>{pay_id}</code>\n\n"
        f"<b>Transfer Steps:</b>\n"
        f"1. Open Binance App -> Pay / Send\n"
        f"2. Enter Binance ID: <code>{pay_id}</code>\n"
        f"3. Send exactly <b>{usdt_amount:.2f} USDT</b>\n"
        f"4. Add Order ID to notes: <code>{order['order_id']}</code>\n\n"
        f"After transferring, click <b>✅ I Have Paid</b> below 👇"
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
                    "✅ I Have Paid",
                    callback_data=f"confirm_pay:{order['order_id']}",
                )
            ],
            [InlineKeyboardButton("💲 Pay via BEP20 Wallet", callback_data=f"pay_usdt:{order['order_id']}")],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
        ]
    )
    return text, keyboard


def crypto_usdt_page(order, usdt_amount):
    wallet = config.CRYPTO_WALLET_USDT
    text = (
        f"{header('<b>💳 USDT Payment (BEP20)</b>')}\n\n"
        f"🛍️ {esc(order['product_name'])} × {order['qty']}\n"
        f"🧾 Order ID: <code>{order['order_id']}</code>\n\n"
        f"💰 Total: <b>{fmt_price(order['total'])}</b>\n"
        f"💲 Exact Amount: <b>{usdt_amount:.2f} USDT</b>\n\n"
        f"📩 <b>Wallet Address (BEP20 / BSC):</b>\n"
        f"<code>{wallet}</code>\n\n"
        f"⚠️ <b>IMPORTANT:</b>\n"
        f"> Send exactly <b>{usdt_amount:.2f} USDT</b>\n"
        f"> Ensure network is <b>BEP20 (BSC)</b>\n"
        f"> Do not send any other tokens!\n\n"
        f"After transferring, click <b>✅ I Have Paid</b> below 👇\n\n"
        f"Product will be delivered after admin verification. ✅"
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
                    "✅ I Have Paid",
                    callback_data=f"confirm_pay:{order['order_id']}",
                )
            ],
            [InlineKeyboardButton("🟡 Pay via Binance ID", callback_data=f"pay_binance:{order['order_id']}")],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
        ]
    )
    return text, keyboard


def test_payment_page(order):
    text = (
        f"{header('<b>🧪 Test Mode</b>')}\n\n"
        f"Payment is <b>simulated</b> — no real money required.\n\n"
        f"🛍️ {esc(order['product_name'])} × {order['qty']}\n"
        f"💰 <b>{fmt_price(order['total'])}</b>\n"
        f"🧾 Order ID: <code>{order['order_id']}</code>\n\n"
        f"Click the button below to simulate successful payment."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Pay Now (Simulate)", callback_data=f"paid:{order['order_id']}")],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
        ]
    )
    return text, keyboard


def pending_page(order):
    text = (
        f"{header('<b>⏳ Awaiting Payment</b>')}\n\n"
        f"🛍️ {esc(order['product_name'])} × {order['qty']}\n"
        f"💰 <b>{fmt_price(order['total'])}</b>\n"
        f"🧾 Order ID: <code>{order['order_id']}</code>\n\n"
        f"Complete your payment and check status."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "↻ Check Status", callback_data=f"paid:{order['order_id']}"
                )
            ],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
        ]
    )
    return text, keyboard


def awaiting_admin_page(order_id):
    text = (
        f"{header('<b>🕐 Awaiting Verification</b>')}\n\n"
        f"🧾 Order ID: <code>{esc(order_id)}</code>\n\n"
        f"Your payment confirmation has been submitted and is being verified by admin.\n"
        f"Product will be delivered automatically once approved. 🙏"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⌂ Home", callback_data="home")]]
    )
    return text, keyboard


def success_page(order_id):
    text = (
        f"{header('<b>✓ Payment Successful</b>')}\n\n"
        f"✓ <b>Payment Verified!</b>\n"
        f"🧾 Order ID: <code>{esc(order_id)}</code>\n\n"
        f"Your digital product has been delivered in the message above. 🎁\n"
        f"Thank you for your purchase!"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⌂ Home", callback_data="home")]]
    )
    return text, keyboard


def no_stock_paid_page(order_id):
    text = (
        f"{header('<b>⚠️ Payment Received</b>')}\n\n"
        f"✓ <b>Your payment was received.</b>\n"
        f"🧾 Order ID: <code>{esc(order_id)}</code>\n\n"
        f"However, this item is currently out of stock.\n"
        f"Admin will contact you directly for refund/replacement.\n"
        f"Thank you for your patience! 🙏"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⌂ Home", callback_data="home")]]
    )
    return text, keyboard


def error_page(message="An error occurred, please try again later."):
    text = f"{header('<b>Oops</b>')}\n\n⚠️ {esc(message)}"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⌂ Home", callback_data="home")]]
    )
    return text, keyboard


def soldout_page():
    text = (
        f"{header('<b>⏳ Sold Out</b>')}\n\n"
        f"Sorry, this product is currently out of stock.\n"
        f"Please check other available products."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Browse Catalog", callback_data="catalog")],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
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
        f"{header('<b>🔐 Admin Panel</b>')}\n\n"
        f"<b>Summary</b>\n"
        f"   Active Products: {len(products)}\n"
        f"   Available Stock: {total_stock}\n"
        f"   Total Orders   : {len(orders)} ({pending} pending, {completed} completed)\n\n"
        f"Manage products & stock directly in Google Sheets."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📦 Stock", callback_data="stock"),
                InlineKeyboardButton("🧾 Orders", callback_data="ordersadmin"),
            ],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
        ]
    )
    return text, keyboard


def admin_orders_page():
    rows = db.get_all_orders(limit=50)
    parts = [header("<b>🧾 All Orders</b>")]
    if not rows:
        parts.append("No orders yet.")
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
            f"{esc(o['product_name'])} × {o['qty']}\n"
            f"   <code>{o['order_id']}</code>\n"
            f"   {fmt_price(o['total'])} · {icon} {o['status']} · {o['telegram_id']}"
        )
    text = "\n\n".join(parts)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔐 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("⌂ Home", callback_data="home")],
        ]
    )
    return text, keyboard
