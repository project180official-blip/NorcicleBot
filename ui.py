import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

import config
import db

BRAND = "NORCICLE"


# Custom Animated Emoji IDs (Telegram Premium)
EMOJI_STORE = '<tg-emoji emoji-id="5938274774756103272">🏪</tg-emoji>'
EMOJI_STAR = '<tg-emoji emoji-id="5224257782013769471">⭐</tg-emoji>'
EMOJI_VERIFIED = '<tg-emoji emoji-id="5411309092427834175">✅</tg-emoji>'
EMOJI_CLOCK = '<tg-emoji emoji-id="5927066722589742879">⏰</tg-emoji>'
EMOJI_MONEY = '<tg-emoji emoji-id="5417924076503062111">💰</tg-emoji>'
EMOJI_CART = '<tg-emoji emoji-id="5271783639548441015">🛒</tg-emoji>'
EMOJI_LIGHTNING = '<tg-emoji emoji-id="5222184635659747645">⚡</tg-emoji>'
EMOJI_DOLLAR = '<tg-emoji emoji-id="5224301028039491729">💲</tg-emoji>'
EMOJI_CHECK = '<tg-emoji emoji-id="5222314103153917906">✅</tg-emoji>'
EMOJI_HEART = '<tg-emoji emoji-id="5273813153329719141">❤️</tg-emoji>'

# Dedicated Animated Product Logos
EMOJI_GEMINI = '<tg-emoji emoji-id="5951817721468424817">🤖</tg-emoji>'
EMOJI_HBO = '<tg-emoji emoji-id="5298588152485651370">📺</tg-emoji>'
EMOJI_CAPCUT = '<tg-emoji emoji-id="5474521476197536994">🖤</tg-emoji>'
EMOJI_NETFLIX = '<tg-emoji emoji-id="5355165443143252480">📺</tg-emoji>'
EMOJI_DEFAULT_PROD = '<tg-emoji emoji-id="5472246178617765188">🎨</tg-emoji>'


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
        f"{EMOJI_STAR} <b>{BRAND} OFFICIAL</b> {EMOJI_VERIFIED}\n"
        f"────────────────────\n\n"
        f"📢 <b>Access Verification Required</b>\n"
        f"Join our official update channel to unlock the store, exclusive drops, and stock updates:\n\n"
        f"👉 <b>{channel}</b>\n\n"
        f"────────────────────"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Join Official Channel", url=channel_link)],
            [InlineKeyboardButton("⚡ Verify Access", callback_data="checkjoin")],
        ]
    )
    return text, keyboard


def calculate_item_price(product, qty):
    pid = str(product.get("id", "")).upper()
    pname = str(product.get("name", "")).lower()
    base_price = float(product.get("price", 0))

    # Tiered pricing khusus Gemini AI:
    # 2 - 4 pcs: $0.80
    # 5 - 9 pcs: $0.70
    # >= 10 pcs: $0.50
    if pid == "P0001" or "gemini" in pname:
        if qty >= 10:
            unit_price = 0.5
        elif qty >= 5:
            unit_price = 0.7
        else:
            unit_price = 0.8
        return unit_price, round(unit_price * qty, 2)

    return base_price, round(base_price * qty, 2)


def get_product_icon(product):
    name = str(product.get("name", "")).lower()
    pid = str(product.get("id", "")).upper()
    if "gemini" in name or pid == "P0001":
        return EMOJI_GEMINI
    if "hbo" in name or "max" in name:
        return EMOJI_HBO
    if "capcut" in name or pid == "P0003":
        return EMOJI_CAPCUT
    if "netflix" in name or pid == "P0005":
        return EMOJI_NETFLIX
    return EMOJI_DEFAULT_PROD


def get_product_btn_icon(product):
    name = str(product.get("name", "")).lower()
    pid = str(product.get("id", "")).upper()
    if "gemini" in name or pid == "P0001":
        return "✨"
    if "hbo" in name or "max" in name:
        return "🎬"
    if "capcut" in name or pid == "P0003":
        return "✂️"
    if "netflix" in name or pid == "P0005":
        return "🍿"
    return "💎"


def product_line(p):
    avail = db.count_available(p["id"])
    stock_badge = f"🟢 {avail} Ready" if avail > 0 else "🔴 Out of Stock"
    pname = str(p.get("name", "")).lower()
    icon = get_product_icon(p)
    if p.get("id") == "P0001" or "gemini" in pname:
        price_display = "$0.80 ($0.70 for 5+ | $0.50 for 10+)"
    else:
        price_display = fmt_price(p['price'])
    return f"{icon} <b>{esc(p['name'])}</b>\n   └ {price_display} • {stock_badge}"


def home_text(user_name=None):
    products = db.get_active_products()
    name_str = f", <b>{esc(user_name)}</b>" if user_name else ""

    text = (
        f"{EMOJI_STORE} <b>{BRAND} OFFICIAL STORE</b>{name_str} {EMOJI_VERIFIED}\n"
        f"────────────────────\n"
        f"{EMOJI_CLOCK} <i>Instant Automated 24/7 Delivery</i>\n"
        f"{EMOJI_MONEY} <i>Direct Wholesale Digital Subscriptions</i>\n\n"
        f"<b>{EMOJI_CART} Select a product below to purchase:</b>"
    )

    rows = []
    # 1 baris per produk tombol penuh, jelas, dan langsung diklik user
    for p in products:
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail} Ready" if avail > 0 else "🔴 Sold Out"
        pname = str(p.get("name", "")).lower()
        btn_icon = get_product_btn_icon(p)
        if p.get("id") == "P0001" or "gemini" in pname:
            price_tag = "$0.80"
        else:
            price_tag = fmt_price(p['price'])

        rows.append([
            InlineKeyboardButton(
                f"{btn_icon} {p['name']} • {price_tag} [{stock_badge}]",
                callback_data=f"product:{p['id']}"
            )
        ])

    # Navigasi Menu
    rows.append([
        InlineKeyboardButton("📦 Live Vault", callback_data="stock"),
        InlineKeyboardButton("🧾 Orders Log", callback_data="orders"),
    ])
    rows.append([
        InlineKeyboardButton("🤝 Affiliate (5%)", callback_data="affiliate"),
        InlineKeyboardButton("💬 Support Desk", callback_data="contact"),
    ])
    rows.append([
        InlineKeyboardButton("🔄 Refresh Store", callback_data="refresh"),
    ])

    return text, InlineKeyboardMarkup(rows)


def promo_page():
    products = sorted(db.get_active_products(), key=lambda p: p["price"])
    if not products:
        text = (
            f"🔥 <b>SPECIAL OFFERS & PROMOS</b>\n"
            f"────────────────────\n\n"
            f"No special promos active right now.\n\n"
            f"────────────────────"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Return to Menu", callback_data="home")]]
        )
        return text, keyboard
    
    items = [product_line(p) for p in products]
    text = (
        f"🔥 <b>SPECIAL OFFERS & DEALS</b>\n"
        f"────────────────────\n\n"
        f"{chr(10).join(items)}\n\n"
        f"────────────────────\n"
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
        icon = get_product_icon(p)
        if p.get("id") == "P0001" or "gemini" in pname:
            price_tag = "$0.80 ($0.70 for 5+ | $0.50 for 10+)"
        else:
            price_tag = fmt_price(p['price'])
        items_list.append(
            f"<b>{i}. {icon} {esc(p['name'])}</b>\n"
            f"   └ {price_tag} • {stock_badge}"
        )

    text = (
        f"🛍️ <b>PRODUCT CATALOG</b>\n"
        f"────────────────────\n\n"
        f"{chr(10).join(items_list)}\n\n"
        f"────────────────────\n"
        f"<i>Select an item to view details & purchase:</i>"
    )

    rows = []
    for p in products:
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail} Ready" if avail > 0 else "🔴 Sold Out"
        pname = str(p.get("name", "")).lower()
        btn_icon = get_product_btn_icon(p)
        if p.get("id") == "P0001" or "gemini" in pname:
            price_tag = "$0.80"
        else:
            price_tag = fmt_price(p['price'])

        rows.append([
            InlineKeyboardButton(
                f"{btn_icon} {p['name']} • {price_tag} [{stock_badge}]",
                callback_data=f"product:{p['id']}"
            )
        ])

    rows.append(
        [
            InlineKeyboardButton("📦 Live Vault", callback_data="stock"),
            InlineKeyboardButton("« Main Menu", callback_data="home"),
        ]
    )
    return text, InlineKeyboardMarkup(rows)


def product_page(product, qty):
    avail = db.count_available(product["id"])
    unit_price, total = calculate_item_price(product, qty)
    sold_out = avail < 1

    stock_badge = f"🟢 In Stock ({avail} available)" if avail > 0 else "🔴 Out of Stock"
    
    pname = str(product.get("name", "")).lower()
    icon = get_product_icon(product)
    promo_badge = ""
    if product.get("id") == "P0001" or "gemini" in pname:
        promo_badge = f"\n{EMOJI_STAR} <i>Wholesale Tiers: 2-4 pcs = $0.80 | 5-9 pcs = $0.70 | 10+ pcs = $0.50</i>\n⚠️ <b>Min. Purchase: 2 pcs</b>"

    text = (
        f"{icon} <b>{esc(product['name'])}</b> {EMOJI_VERIFIED}\n"
        f"────────────────────\n\n"
        f"📖 <b>Description:</b>\n"
        f"{esc(product['description'])}\n"
        f"{promo_badge}\n\n"
        f"────────────────────\n"
        f"💵 <b>Unit Price :</b> <b>{fmt_price(unit_price)}</b>\n"
        f"📦 <b>Vault Stock:</b> {stock_badge}\n"
        f"{EMOJI_CLOCK} <b>Fulfillment:</b> Instant Automated 24/7\n"
        f"────────────────────\n\n"
        f"🔢 <b>Quantity   :</b> <b>{qty}x</b>\n"
        f"💰 <b>Total Due  :</b> <b>{fmt_price(total)}</b>\n\n"
        f"💡 <i>Tip: Adjust with [-] / [+] or send a number directly in chat.</i>"
    )

    if sold_out:
        rows = [
            [InlineKeyboardButton("🔴 Out of Stock", callback_data="noop")],
            [
                InlineKeyboardButton("« Catalog", callback_data="catalog"),
                InlineKeyboardButton("« Menu", callback_data="home"),
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
                InlineKeyboardButton("✏️ Custom Quantity", callback_data=f"customqty:{product['id']}"),
            ],
            [InlineKeyboardButton(f"🟢 ⚡ Order Now • {fmt_price(total)}", callback_data=f"buy:{product['id']}")],
            [
                InlineKeyboardButton("« Catalog", callback_data="catalog"),
                InlineKeyboardButton("« Menu", callback_data="home"),
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
        f"📦 <b>LIVE VAULT INVENTORY</b> {EMOJI_VERIFIED}\n"
        f"────────────────────\n\n"
        f"{chr(10).join(items)}\n\n"
        f"────────────────────\n"
        f"{EMOJI_LIGHTNING} <i>Inventory updates in real-time from secure server.</i>"
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
            f"────────────────────\n\n"
            f"You don't have any purchase logs yet.\n\n"
            f"────────────────────"
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
            p_icon = get_product_icon({"name": o['product_name']})
            items.append(
                f"🧾 <b>Order:</b> <code>{o['order_id']}</code>\n"
                f"   └ {p_icon} {esc(o['product_name'])} x{o['qty']} • <b>{fmt_price(o['total'])}</b>\n"
                f"   └ Status: {icon} <b>{o['status']}</b>"
            )
        text = (
            f"🧾 <b>MY ORDERS & TRANSACTIONS</b>\n"
            f"────────────────────\n\n"
            f"{chr(10).join(items)}\n\n"
            f"────────────────────"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Order Products", callback_data="catalog")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def contact_page():
    admin = "norciclesupport"
    text = (
        f"💬 <b>CUSTOMER SUPPORT</b>\n"
        f"────────────────────\n\n"
        f"Need help with your order or have a custom inquiry?\n\n"
        f"👤 <b>Official Support:</b> @{esc(admin)}\n\n"
        f"<b>Shortcut Commands:</b>\n"
        f"• <code>/start</code> — Main Menu\n"
        f"• <code>/products</code> — Product Catalog\n"
        f"• <code>/stock</code> — Live Vault\n"
        f"• <code>/orders</code> — Purchase History\n"
        f"• <code>/support</code> — Direct Support Desk\n\n"
        f"────────────────────"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Contact Support (@norciclesupport)", url=f"https://t.me/{admin}")],
            [InlineKeyboardButton("« Return to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def loading_text(msg="Processing your order..."):
    return f"⏳ <b>{esc(msg)}</b>\n\n<i>Please wait a moment...</i>", InlineKeyboardMarkup([])


def payment_method_page(order, usdt_amount=None):
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    icon = get_product_icon({"name": order['product_name'], "id": order.get('product_id', '')})
    text = (
        f"{EMOJI_VERIFIED} <b>SECURE CHECKOUT</b>\n"
        f"────────────────────\n\n"
        f"{icon} <b>Item     :</b> {esc(order['product_name'])}\n"
        f"🔢 <b>Quantity :</b> {order['qty']}x\n"
        f"💰 <b>Total Due:</b> <b>{fmt_price(order['total'])}</b> (<b>{amt:.2f} USDT</b>)\n"
        f"🧾 <b>Order ID :</b> <code>{order['order_id']}</code>\n\n"
        f"────────────────────\n"
        f"Select your preferred crypto payment channel below:"
    )
    buttons = [
        [
            InlineKeyboardButton("🟢 🟡 Binance Pay (Pay ID)", callback_data=f"pay_binance:{order['order_id']}"),
            InlineKeyboardButton("🟢 🌐 USDT (BEP20 / BSC)", callback_data=f"pay_usdt:{order['order_id']}"),
        ],
        [InlineKeyboardButton("« Cancel & Return", callback_data="home")],
    ]
    return text, InlineKeyboardMarkup(buttons)


def binance_pay_page(order, usdt_amount=None):
    pay_id = config.BINANCE_PAY_ID
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    icon = get_product_icon({"name": order['product_name'], "id": order.get('product_id', '')})
    text = (
        f"🟡 <b>BINANCE PAY SETTLEMENT</b>\n"
        f"────────────────────\n\n"
        f"{icon} <b>Item    :</b> {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 <b>Amount  :</b> <b>{amt:.2f} USDT</b> (Send exact)\n"
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n\n"
        f"────────────────────\n"
        f"📲 <b>Binance Pay ID:</b>\n"
        f"👉 <code>{pay_id}</code>\n\n"
        f"<b>Payment Steps:</b>\n"
        f"1. <b>Scan QR Code</b> above or open Binance Pay\n"
        f"2. Input Binance ID: <code>{pay_id}</code>\n"
        f"3. Enter exact amount: <b>{amt:.2f} USDT</b>\n"
        f"4. Add Order ID to notes: <code>{order['order_id']}</code>\n\n"
        f"────────────────────\n"
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
                    "🟢 ✅ I Have Transferred",
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
    icon = get_product_icon({"name": order['product_name'], "id": order.get('product_id', '')})
    text = (
        f"🌐 <b>USDT (BEP20 / BSC) PAYMENT</b>\n"
        f"────────────────────\n\n"
        f"{icon} <b>Item    :</b> {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 <b>Amount  :</b> <b>{amt:.2f} USDT</b> (Exact)\n"
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n\n"
        f"────────────────────\n"
        f"📩 <b>Deposit Wallet Address:</b>\n"
        f"👉 <code>{wallet}</code>\n\n"
        f"⚠️ <b>Network Checklist:</b>\n"
        f"• Network: <b>BNB Smart Chain (BEP20)</b>\n"
        f"• Do not send through other chains (ERC20/TRC20)\n\n"
        f"────────────────────\n"
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
                    "🟢 ✅ I Have Transferred",
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
        f"{EMOJI_VERIFIED} <b>ORDER COMPLETED!</b>\n"
        f"────────────────────\n\n"
        f"{EMOJI_CHECK} <b>Payment Verified Successfully</b>\n"
        f"🧾 <b>Order ID:</b> <code>{esc(order_id)}</code>\n\n"
        f"📦 Your digital credentials file has been delivered above.\n"
        f"Thank you for shopping with <b>{BRAND}</b>! {EMOJI_HEART}\n\n"
        f"────────────────────"
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
        f"{EMOJI_VERIFIED} <b>{BRAND} ADMIN CONSOLE</b>\n"
        f"────────────────────\n\n"
        f"📊 <b>Store Metrics:</b>\n"
        f"• Active Products : <b>{len(products)}</b>\n"
        f"• Total Vault Stock: <b>{total_stock} items</b>\n"
        f"• Total Orders    : <b>{len(orders)}</b> ({pending} pending, {completed} completed)\n\n"
        f"────────────────────"
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
