import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

import config
import db

BRAND = "NORCICLE"


def esc(s):
    return html.escape(str(s))


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
        f"👑 <b>{BRAND} OFFICIAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📢 <b>Channel Access Required</b>\n"
        f"Join our official channel to get access to the store, exclusive drops, and discounts:\n\n"
        f"👉 <b>{channel}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Join Channel", url=channel_link)],
            [InlineKeyboardButton("✅ Verify Membership", callback_data="checkjoin")],
        ]
    )
    return text, keyboard


def calculate_item_price(product, qty):
    pid = str(product.get("id", "")).upper()
    pname = str(product.get("name", "")).lower()
    base_price = float(product.get("price", 0))

    # Tiered pricing khusus Gemini AI (1 pcs = $0.9, min 5 pcs = $0.8)
    if pid == "P0001" or "gemini" in pname:
        unit_price = 0.8 if qty >= 5 else 0.9
        return unit_price, round(unit_price * qty, 2)

    return base_price, round(base_price * qty, 2)


def product_line(p):
    avail = db.count_available(p["id"])
    stock_badge = f"🟢 {avail} Ready" if avail > 0 else "🔴 Out of Stock"
    pname = str(p.get("name", "")).lower()
    if p.get("id") == "P0001" or "gemini" in pname:
        price_display = "$0.90 ($0.80 for 5+)"
    else:
        price_display = fmt_price(p['price'])
    return f"• {p['emoji']} <b>{esc(p['name'])}</b>\n  └ 💵 <b>{price_display}</b>  |  {stock_badge}"


def home_text(user_name=None):
    products = db.get_active_products()
    name_str = f", <b>{esc(user_name)}</b>" if user_name else ""

    text = (
        f"👑 <b>WELCOME TO {BRAND} STORE</b>{name_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <i>Instant Delivery • 100% Automated • 24/7</i>\n"
        f"💎 <i>High-Quality Digital Accounts & Subscriptions</i>\n\n"
        f"<i>Select a product or menu below to get started:</i>"
    )

    rows = []
    # Baris tombol produk langsung rapi
    for i, p in enumerate(products, 1):
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail}" if avail > 0 else "🔴 0"
        pname = str(p.get("name", "")).lower()
        if p.get("id") == "P0001" or "gemini" in pname:
            price_tag = "$0.90 ($0.80 for 5+)"
        else:
            price_tag = fmt_price(p['price'])
        rows.append([
            InlineKeyboardButton(
                f"{p['emoji']} {esc(p['name'])} — {price_tag} ({stock_badge})",
                callback_data=f"product:{p['id']}"
            )
        ])

    # Navigasi Menu
    rows.append([
        InlineKeyboardButton("📦 Live Stock", callback_data="stock"),
        InlineKeyboardButton("🧾 My Orders", callback_data="orders"),
    ])
    rows.append([
        InlineKeyboardButton("🤝 Affiliate (5%)", callback_data="affiliate"),
        InlineKeyboardButton("💬 Support Desk", callback_data="contact"),
    ])
    rows.append([
        InlineKeyboardButton("🔄 Refresh Menu", callback_data="refresh"),
    ])

    return text, InlineKeyboardMarkup(rows)


def promo_page():
    products = sorted(db.get_active_products(), key=lambda p: p["price"])
    if not products:
        text = (
            f"🔥 <b>SPECIAL OFFERS & PROMOS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"No special promos active right now.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Return to Menu", callback_data="home")]]
        )
        return text, keyboard
    
    items = [product_line(p) for p in products]
    text = (
        f"🔥 <b>SPECIAL OFFERS & DEALS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{chr(10).join(items)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <i>Limited stocks available. Grab yours now!</i>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Open Catalog", callback_data="catalog")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def catalog_text():
    products = db.get_active_products()
    if not products:
        text = (
            f"🛍️ <b>PRODUCT CATALOG</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"No products currently in stock.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Return to Menu", callback_data="home")]]
        )
        return text, keyboard

    items_list = []
    for i, p in enumerate(products, 1):
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail} Ready" if avail > 0 else "🔴 Out of Stock"
        pname = str(p.get("name", "")).lower()
        if p.get("id") == "P0001" or "gemini" in pname:
            price_tag = "$0.90 ($0.80 for 5+)"
        else:
            price_tag = fmt_price(p['price'])
        items_list.append(
            f"<b>{i}. {p['emoji']} {esc(p['name'])}</b>\n"
            f"   └ 💵 <b>{price_tag}</b>  |  {stock_badge}"
        )

    text = (
        f"🛍️ <b>PRODUCT CATALOG</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{chr(10).join(items_list)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Select a product to view details & purchase:</i>"
    )

    rows = []
    for i, p in enumerate(products, 1):
        rows.append([
            InlineKeyboardButton(
                f"🛍️ Buy #{i}: {esc(p['name'])}",
                callback_data=f"product:{p['id']}"
            )
        ])
    rows.append(
        [
            InlineKeyboardButton("📦 Live Stock", callback_data="stock"),
            InlineKeyboardButton("« Return to Menu", callback_data="home"),
        ]
    )
    return text, InlineKeyboardMarkup(rows)


def product_page(product, qty):
    avail = db.count_available(product["id"])
    unit_price, total = calculate_item_price(product, qty)
    sold_out = avail < 1

    stock_badge = f"🟢 In Stock ({avail} available)" if avail > 0 else "🔴 Out of Stock"
    
    pname = str(product.get("name", "")).lower()
    promo_badge = ""
    if product.get("id") == "P0001" or "gemini" in pname:
        promo_badge = "\n🎁 <i>Tier Pricing: 1-4 pcs = $0.90 | 5+ pcs = $0.80/ea</i>"

    text = (
        f"{product['emoji']} <b>{esc(product['name'])}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📖 <b>Description:</b>\n"
        f"{esc(product['description'])}\n"
        f"{promo_badge}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>Unit Price:</b> <b>{fmt_price(unit_price)}</b>\n"
        f"📦 <b>Status    :</b> {stock_badge}\n"
        f"⚡ <b>Delivery  :</b> Instant Delivery (.txt credential)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔢 <b>Selected Quantity:</b> <b>{qty}x</b>\n"
        f"💰 <b>Total Payable     :</b> <b>{fmt_price(total)}</b>\n\n"
        f"💡 <i>Tip: You can use [-] / [+] or send a number directly in chat to set custom quantity.</i>"
    )

    if sold_out:
        rows = [
            [InlineKeyboardButton("🔴 Out of Stock", callback_data="noop")],
            [
                InlineKeyboardButton("« Catalog", callback_data="catalog"),
                InlineKeyboardButton("« Home", callback_data="home"),
            ],
        ]
    else:
        rows = [
            [
                InlineKeyboardButton("➖", callback_data=f"qtydec:{product['id']}"),
                InlineKeyboardButton(f"Qty: {qty}", callback_data="noop"),
                InlineKeyboardButton("➕", callback_data=f"qtyinc:{product['id']}"),
            ],
            [
                InlineKeyboardButton("✏️ Enter Custom Qty", callback_data=f"customqty:{product['id']}"),
            ],
            [InlineKeyboardButton(f"⚡ Order Now • {fmt_price(total)}", callback_data=f"buy:{product['id']}")],
            [
                InlineKeyboardButton("« Catalog", callback_data="catalog"),
                InlineKeyboardButton("« Home", callback_data="home"),
            ],
        ]
    return text, InlineKeyboardMarkup(rows)


def stock_page():
    products = db.get_active_products()
    items = []
    if not products:
        items.append("No active products found.")
    for p in products:
        items.append(product_line(p))
    
    text = (
        f"📦 <b>LIVE VAULT STOCK</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{chr(10).join(items)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 <i>Inventory updates in real-time from server.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Browse Catalog", callback_data="catalog")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def orders_page(user_id):
    rows = db.get_my_orders(user_id)
    if not rows:
        text = (
            f"🧾 <b>ORDER HISTORY</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"You don't have any purchase logs yet.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        items = []
        for o in rows:
            icon = {
                "PENDING": "⏳",
                "PAID": "💳",
                "COMPLETED": "✅",
                "FAILED": "❌",
                "PAID_BUT_OUT_OF_STOCK": "⚠️",
                "AWAITING_ADMIN": "🕐",
            }.get(o["status"], "•")
            items.append(
                f"🧾 <b>Order:</b> <code>{o['order_id']}</code>\n"
                f"   └ {esc(o['product_name'])} x{o['qty']} • <b>{fmt_price(o['total'])}</b>\n"
                f"   └ Status: {icon} <b>{o['status']}</b>"
            )
        text = (
            f"🧾 <b>MY ORDERS & TRANSACTIONS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{chr(10).join(items)}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Order Products", callback_data="catalog")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def contact_page():
    admin = db.get_setting("ADMIN_USERNAME", config.ADMIN_USERNAME) or config.ADMIN_USERNAME
    text = (
        f"💬 <b>CUSTOMER SUPPORT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Need help with your order or have a custom inquiry?\n\n"
        f"👤 <b>Official Admin:</b> @{esc(admin)}\n\n"
        f"<b>Available Shortcut Commands:</b>\n"
        f"• <code>/start</code> — Main Menu\n"
        f"• <code>/products</code> — Product Catalog\n"
        f"• <code>/stock</code> — Live Stock Vault\n"
        f"• <code>/orders</code> — Transaction History\n"
        f"• <code>/support</code> — Direct Support Desk\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Open Chat with Admin", url=f"https://t.me/{admin}")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def loading_text(msg="Processing your order..."):
    return f"⏳ <b>{esc(msg)}</b>\n\n<i>Please wait a moment...</i>", InlineKeyboardMarkup([])


def payment_method_page(order, usdt_amount=None):
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    text = (
        f"💳 <b>CHECKOUT & SETTLEMENT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛍️ <b>Product :</b> {esc(order['product_name'])}\n"
        f"🔢 <b>Quantity:</b> {order['qty']}x\n"
        f"💰 <b>Total Due:</b> <b>{fmt_price(order['total'])}</b> (<b>{amt:.2f} USDT</b>)\n"
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Select your crypto payment channel below:"
    )
    buttons = [
        [
            InlineKeyboardButton("🟡 Binance Pay (Pay ID)", callback_data=f"pay_binance:{order['order_id']}"),
            InlineKeyboardButton("🌐 USDT (BEP20 / BSC)", callback_data=f"pay_usdt:{order['order_id']}"),
        ],
        [InlineKeyboardButton("« Cancel & Return", callback_data="home")],
    ]
    return text, InlineKeyboardMarkup(buttons)


def binance_pay_page(order, usdt_amount=None):
    pay_id = config.BINANCE_PAY_ID
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    text = (
        f"🟡 <b>BINANCE PAY SETTLEMENT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛍️ <b>Item    :</b> {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 <b>Amount  :</b> <b>{amt:.2f} USDT</b> (Send exact)\n"
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📲 <b>Binance Pay ID:</b>\n"
        f"👉 <code>{pay_id}</code>\n\n"
        f"<b>Payment Steps:</b>\n"
        f"1. <b>Scan QR Code</b> above or open Binance Pay\n"
        f"2. Input Binance ID: <code>{pay_id}</code>\n"
        f"3. Enter exact amount: <b>{amt:.2f} USDT</b>\n"
        f"4. Add Order ID to notes: <code>{order['order_id']}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Tap the button below after completing your transfer:</i>"
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
                    "✅ I Have Transferred",
                    callback_data=f"confirm_pay:{order['order_id']}",
                )
            ],
            [InlineKeyboardButton("🌐 Switch to USDT BEP20", callback_data=f"pay_usdt:{order['order_id']}")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def crypto_usdt_page(order, usdt_amount=None):
    wallet = config.CRYPTO_WALLET_USDT
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    text = (
        f"🌐 <b>USDT (BEP20 / BSC) PAYMENT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛍️ <b>Item    :</b> {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 <b>Amount  :</b> <b>{amt:.2f} USDT</b> (Exact)\n"
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📩 <b>Deposit Wallet Address:</b>\n"
        f"👉 <code>{wallet}</code>\n\n"
        f"⚠️ <b>Network Checklist:</b>\n"
        f"• Network: <b>BNB Smart Chain (BEP20)</b>\n"
        f"• Do not send through other chains (ERC20/TRC20)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Tap the button below after broadcasting transfer:</i>"
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
                    "✅ I Have Transferred",
                    callback_data=f"confirm_pay:{order['order_id']}",
                )
            ],
            [InlineKeyboardButton("🟡 Switch to Binance Pay", callback_data=f"pay_binance:{order['order_id']}")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def test_payment_page(order):
    text = (
        f"🧪 <b>TEST MODE SIMULATION</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛍️ {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 Total: <b>{fmt_price(order['total'])}</b>\n"
        f"🧾 Order ID: <code>{order['order_id']}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Simulate Success", callback_data=f"paid:{order['order_id']}")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def pending_page(order):
    text = (
        f"⏳ <b>PAYMENT PENDING</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛍️ {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 Total: <b>{fmt_price(order['total'])}</b>\n"
        f"🧾 Order ID: <code>{order['order_id']}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Please complete your payment and refresh status.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔄 Check Payment Status", callback_data=f"paid:{order['order_id']}"
                )
            ],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def awaiting_admin_page(order_id):
    text = (
        f"🕐 <b>VERIFICATION IN PROGRESS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🧾 <b>Order ID:</b> <code>{esc(order_id)}</code>\n\n"
        f"Your transfer confirmation has been submitted.\n"
        f"Admin is verifying the transaction ledger.\n\n"
        f"⚡ <i>Your credentials will be delivered automatically upon confirmation!</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Return to Menu", callback_data="home")]]
    )
    return text, keyboard


def success_page(order_id):
    text = (
        f"🎉 <b>ORDER COMPLETED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>Payment Verified Successfully</b>\n"
        f"🧾 <b>Order ID:</b> <code>{esc(order_id)}</code>\n\n"
        f"📦 Your digital credentials file has been delivered above.\n"
        f"Thank you for shopping with <b>{BRAND}</b>!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Return to Menu", callback_data="home")]]
    )
    return text, keyboard


def no_stock_paid_page(order_id):
    text = (
        f"⚠️ <b>STOCK DEPLETED NOTICE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Payment Received: <code>{esc(order_id)}</code>\n\n"
        f"Stock ran out right before your confirmation completed.\n"
        f"Admin has been notified and will process immediate replacement or refund.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Return to Menu", callback_data="home")]]
    )
    return text, keyboard


def error_page(message="An error occurred, please try again later."):
    text = (
        f"⚠️ <b>NOTICE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{esc(message)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Return to Menu", callback_data="home")]]
    )
    return text, keyboard


def soldout_page():
    text = (
        f"⏳ <b>OUT OF STOCK</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"This product is currently sold out.\n"
        f"Please check back soon or browse our other available products.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Browse Catalog", callback_data="catalog")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
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
        f"🔐 <b>{BRAND} ADMIN CONSOLE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>Store Metrics:</b>\n"
        f"• Active Products : <b>{len(products)}</b>\n"
        f"• Total Vault Stock: <b>{total_stock} items</b>\n"
        f"• Total Orders    : <b>{len(orders)}</b> ({pending} pending, {completed} completed)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📦 Vault Stock", callback_data="stock"),
                InlineKeyboardButton("🧾 Orders Log", callback_data="ordersadmin"),
            ],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def admin_orders_page():
    rows = db.get_all_orders(limit=50)
    if not rows:
        text = (
            f"🧾 <b>ALL TRANSACTIONS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"No order logs recorded.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        items = []
        for o in rows:
            icon = {
                "PENDING": "⏳",
                "PAID": "💳",
                "COMPLETED": "✅",
                "FAILED": "❌",
                "PAID_BUT_OUT_OF_STOCK": "⚠️",
                "AWAITING_ADMIN": "🕐",
            }.get(o["status"], "•")
            items.append(
                f"• <code>{o['order_id']}</code> | <b>{fmt_price(o['total'])}</b>\n"
                f"  └ {esc(o['product_name'])} x{o['qty']} • {icon} {o['status']} (UID: <code>{o['telegram_id']}</code>)"
            )
        text = (
            f"🧾 <b>ALL TRANSACTIONS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{chr(10).join(items)}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔐 Admin Console", callback_data="admin")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard
