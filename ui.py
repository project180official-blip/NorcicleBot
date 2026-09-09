import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

import config
import db

BRAND = "COSMO SHOP"


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
EMOJI_CLAUDE = '<tg-emoji emoji-id="5899837428797020489">😒</tg-emoji>'
EMOJI_HBO = '<tg-emoji emoji-id="5298588152485651370">📺</tg-emoji>'
EMOJI_CAPCUT = '<tg-emoji emoji-id="5474521476197536994">🖤</tg-emoji>'
EMOJI_NETFLIX = '<tg-emoji emoji-id="5355165443143252480">📺</tg-emoji>'
EMOJI_CHATGPT = '<tg-emoji emoji-id="5796185041717433060">😺</tg-emoji>'
EMOJI_GROK = '<tg-emoji emoji-id="5902340522852227618">😐</tg-emoji>'
EMOJI_NOTION = '<tg-emoji emoji-id="5364199932620194408">📱</tg-emoji>'
EMOJI_FIGMA = '<tg-emoji emoji-id="5411160533804014808">🟣</tg-emoji>'
EMOJI_LEONARDO = '<tg-emoji emoji-id="5332348708556133142">👍</tg-emoji>'
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
        f"{EMOJI_STAR} <b>{BRAND}</b> {EMOJI_VERIFIED}\n"
        f"────────────────────\n\n"
        f"🔒 <b>One more step!</b>\n\n"
        f"Join our official channel to unlock the store, exclusive drops, and stock updates:\n\n"
        f"👉 <b>{channel}</b>\n\n"
        f"Already in? Hit the button below.\n"
        f"────────────────────"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Join Channel", url=channel_link)],
            [InlineKeyboardButton("✅ Done, Let Me In!", callback_data="checkjoin")],
        ]
    )
    return text, keyboard


def calculate_item_price(product, qty):
    pid = str(product.get("id", "")).upper()
    pname = str(product.get("name", "")).lower()
    base_price = float(product.get("price", 0))

    if pid == "P0001" or "gemini" in pname:
        if qty >= 10:
            unit_price = 0.5
        elif qty >= 5:
            unit_price = 0.7
        elif qty >= 2:
            unit_price = 0.8
        else:
            unit_price = 0.9
        return unit_price, round(unit_price * qty, 2)

    return base_price, round(base_price * qty, 2)


def get_product_icon(product):
    name = str(product.get("name", "")).lower()
    pid = str(product.get("id", "")).upper()
    if "notion" in name or pid == "P0010":
        return EMOJI_NOTION
    if "figma" in name or pid == "P0011":
        return EMOJI_FIGMA
    if "leonardo" in name or pid == "P0012":
        return EMOJI_LEONARDO
    if "claude" in name or pid == "P0006":
        return EMOJI_CLAUDE
    if "chatgpt" in name or "gpt" in name or pid in ("P0007", "P0009"):
        return EMOJI_CHATGPT
    if "grok" in name or pid == "P0008":
        return EMOJI_GROK
    if "gemini" in name or pid == "P0001":
        return EMOJI_GEMINI
    if "hbo" in name or "max" in name:
        return EMOJI_HBO
    if "capcut" in name or pid == "P0003":
        return EMOJI_CAPCUT
    if "netflix" in name or pid == "P0005":
        return EMOJI_NETFLIX
    return EMOJI_DEFAULT_PROD


def get_product_emoji_id(product):
    name = str(product.get("name", "")).lower()
    pid = str(product.get("id", "")).upper()
    if "notion" in name or pid == "P0010":
        return "5364199932620194408"
    if "figma" in name or pid == "P0011":
        return "5411160533804014808"
    if "leonardo" in name or pid == "P0012":
        return "5332348708556133142"
    if "claude" in name or pid == "P0006":
        return "5899837428797020489"
    if "chatgpt" in name or "gpt" in name or pid in ("P0007", "P0009"):
        return "5796185041717433060"
    if "grok" in name or pid == "P0008":
        return "5902340522852227618"
    if "gemini" in name or pid == "P0001":
        return "5951817721468424817"
    if "hbo" in name or "max" in name:
        return "5298588152485651370"
    if "capcut" in name or pid == "P0003":
        return "5474521476197536994"
    if "netflix" in name or pid == "P0005":
        return "5355165443143252480"
    return "5472246178617765188"


def get_product_btn_icon(product):
    name = str(product.get("name", "")).lower()
    pid = str(product.get("id", "")).upper()
    if "notion" in name or pid == "P0010":
        return "📝"
    if "figma" in name or pid == "P0011":
        return "🎨"
    if "leonardo" in name or pid == "P0012":
        return "🖌️"
    if "claude" in name or pid == "P0006":
        return "🧠"
    if "chatgpt" in name or "gpt" in name or pid in ("P0007", "P0009"):
        return "🤖"
    if "grok" in name or pid == "P0008":
        return "⚡"
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
        price_display = "$0.90 ($0.80 for 2+ | $0.50 for 10+)"
    else:
        price_display = fmt_price(p['price'])
    return f"{icon} <b>{esc(p['name'])}</b>\n   └ {price_display} • {stock_badge}"


def home_text(user_name=None, user_id=None):
    products = db.get_active_products()
    balance_val = db.get_wallet(str(user_id)) if user_id else 0.0
    user_greeting = f"<b>{esc(user_name)}</b>" if user_name else "there"

    text = (
        f"✦ <b>{BRAND}</b> ✦\n\n"
        f"Hey, {user_greeting}! 👋\n"
        f"Premium digital accounts — affordable prices, delivered instantly & automatically.\n\n"
        f"💳 Your balance: <b>{fmt_price(balance_val)}</b>\n\n"
        f"Pick something below:"
    )

    rows = []
    for p in products:
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail}" if avail > 0 else "🔴 Sold Out"
        pname = str(p.get("name", "")).lower()
        emoji_id = get_product_emoji_id(p)
        if p.get("id") == "P0001" or "gemini" in pname:
            price_tag = "$0.80"
        else:
            price_tag = fmt_price(p['price'])

        btn = InlineKeyboardButton(
            f"{p['name']} • {price_tag} [{stock_badge}]",
            callback_data=f"product:{p['id']}",
            api_kwargs={"icon_custom_emoji_id": emoji_id, "style": "success"}
        )
        rows.append([btn])

    rows.append([
        InlineKeyboardButton("💳 Top Up", callback_data="topup"),
        InlineKeyboardButton("📦 Stock", callback_data="stock"),
        InlineKeyboardButton("🧾 Orders", callback_data="orders"),
    ])
    rows.append([
        InlineKeyboardButton("💬 Support", callback_data="contact"),
        InlineKeyboardButton("🤝 Affiliate", callback_data="affiliate"),
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
    ])

    return text, InlineKeyboardMarkup(rows)


def promo_page():
    products = sorted(db.get_active_products(), key=lambda p: p["price"], reverse=True)
    if not products:
        text = (
            f"🔥 <b>DEALS & PROMOS</b>\n"
            f"────────────────────\n\n"
            f"No active promos right now.\n"
            f"Check back soon!\n\n"
            f"────────────────────"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Back to Menu", callback_data="home")]]
        )
        return text, keyboard

    items = [product_line(p) for p in products]
    text = (
        f"🔥 <b>BEST DEALS FOR YOU</b>\n"
        f"────────────────────\n\n"
        f"{chr(10).join(items)}\n\n"
        f"────────────────────\n"
        f"⚡ <i>Limited stock — don't sleep on it!</i>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Browse All Products", callback_data="catalog")],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def catalog_text():
    products = db.get_active_products()
    if not products:
        text = (
            f"🛍️ <b>PRODUCT CATALOG</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Nothing in stock right now. Check back soon!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Back to Menu", callback_data="home")]]
        )
        return text, keyboard

    items_list = []
    for i, p in enumerate(products, 1):
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail} available" if avail > 0 else "🔴 Out of Stock"
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
        f"<i>Tap a product to see details & order:</i>"
    )

    rows = []
    for p in products:
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail}" if avail > 0 else "🔴 Sold Out"
        pname = str(p.get("name", "")).lower()
        emoji_id = get_product_emoji_id(p)
        if p.get("id") == "P0001" or "gemini" in pname:
            price_tag = "$0.80"
        else:
            price_tag = fmt_price(p['price'])

        btn = InlineKeyboardButton(
            f"{p['name']} • {price_tag} [{stock_badge}]",
            callback_data=f"product:{p['id']}",
            api_kwargs={"icon_custom_emoji_id": emoji_id, "style": "success"}
        )
        rows.append([btn])

    rows.append(
        [
            InlineKeyboardButton("📦 Live Stock", callback_data="stock"),
            InlineKeyboardButton("« Main Menu", callback_data="home"),
        ]
    )
    return text, InlineKeyboardMarkup(rows)


def product_page(product, qty):
    avail = db.count_available(product["id"])
    unit_price, total = calculate_item_price(product, qty)
    sold_out = avail < 1

    stock_badge = f"🟢 {avail} in stock" if avail > 0 else "🔴 Out of stock"
    pname = str(product.get("name", "")).lower()
    icon = get_product_icon(product)

    tier_block = ""
    if product.get("id") == "P0001" or "gemini" in pname:
        tier_block = (
            f"\n💡 Bulk Pricing:\n"
            f"• 1 pcs: $0.90\n"
            f"• 2–4 pcs: $0.80/ea\n"
            f"• 5–9 pcs: $0.70/ea\n"
            f"• 10+ pcs: $0.50/ea\n"
        )

    desc = esc(product['description']).strip()
    if desc.startswith("✨"):
        desc = desc.lstrip("✨").strip()

    text = (
        f"{icon} <b>{esc(product['name'])}</b>\n\n"
        f"{desc}\n"
        f"{tier_block}\n"
        f"💰 Price: <b>{fmt_price(unit_price)}</b>\n"
        f"📦 Stock: {stock_badge}\n"
        f"⚡ Delivery: Instant & Automated\n\n"
        f"🛒 Total: <b>{qty}x = {fmt_price(total)}</b>"
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
        buy_btn = InlineKeyboardButton(
            f"⚡ Order Now • {fmt_price(total)}",
            callback_data=f"buy:{product['id']}",
            api_kwargs={"icon_custom_emoji_id": "5222184635659747645", "style": "success"}
        )
        rows = [
            [
                InlineKeyboardButton("➖", callback_data=f"qtydec:{product['id']}"),
                InlineKeyboardButton(f"Qty: {qty}", callback_data="noop"),
                InlineKeyboardButton("➕", callback_data=f"qtyinc:{product['id']}"),
            ],
            [
                InlineKeyboardButton("✏️ Custom Qty", callback_data=f"customqty:{product['id']}"),
            ],
            [buy_btn],
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
        f"📦 <b>LIVE STOCK</b> {EMOJI_VERIFIED}\n"
        f"────────────────────\n\n"
        f"{chr(10).join(items)}\n\n"
        f"────────────────────\n"
        f"{EMOJI_LIGHTNING} <i>Updated in real-time from our servers.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Browse Catalog", callback_data="catalog")],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def orders_page(user_id):
    rows = db.get_my_orders(user_id)
    if not rows:
        text = (
            f"🧾 <b>ORDER HISTORY</b>\n"
            f"────────────────────\n\n"
            f"No orders yet — go grab something! 🛍️\n\n"
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
            f"🧾 <b>YOUR ORDERS</b>\n"
            f"────────────────────\n\n"
            f"{chr(10).join(items)}\n\n"
            f"────────────────────"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Shop Again", callback_data="catalog")],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def contact_page():
    admin = "urcosmoxyz"
    text = (
        f"💬 <b>NEED HELP?</b>\n"
        f"────────────────────\n\n"
        f"Got an issue with your order or just wanna ask something?\n"
        f"Our admin's got you covered.\n\n"
        f"👤 <b>Official Admin:</b> @{esc(admin)}\n\n"
        f"<b>Quick Commands:</b>\n"
        f"• <code>/start</code> — Main Menu\n"
        f"• <code>/products</code> — Product Catalog\n"
        f"• <code>/stock</code> — Live Stock\n"
        f"• <code>/orders</code> — Order History\n"
        f"• <code>/support</code> — Contact Admin\n\n"
        f"────────────────────"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Chat Admin (@urcosmoxyz)", url=f"https://t.me/{admin}")],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def loading_text(msg="Processing your order..."):
    return f"⏳ <b>{esc(msg)}</b>\n\n<i>Hang tight...</i>", InlineKeyboardMarkup([])


def payment_method_page(order, usdt_amount=None, user_balance=0.0):
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    icon = get_product_icon({"name": order['product_name'], "id": order.get('product_id', '')})
    bal_str = fmt_price(user_balance)
    text = (
        f"<b>Checkout</b>\n\n"
        f"Product: {icon} <b>{esc(order['product_name'])}</b>\n"
        f"Quantity: {order['qty']}x\n"
        f"Total: <b>{fmt_price(order['total'])}</b> ({amt:.2f} USDT)\n"
        f"Balance: <b>{bal_str}</b>\n"
        f"Order ID: <code>{order['order_id']}</code>\n\n"
        f"How do you want to pay?"
    )
    buttons = []
    if float(user_balance) >= float(order['total']):
        pay_bal_btn = InlineKeyboardButton(f"⚡ Pay with Balance ({bal_str})", callback_data=f"pay_balance:{order['order_id']}")
        try:
            setattr(pay_bal_btn, "style", "success")
            setattr(pay_bal_btn, "icon_custom_emoji_id", "5417924076503062111")
        except Exception:
            pass
        buttons.append([pay_bal_btn])

    b1 = InlineKeyboardButton("Binance Pay (Pay ID)", callback_data=f"pay_binance:{order['order_id']}", api_kwargs={"style": "success"})
    b2 = InlineKeyboardButton("USDT (BEP20 / BSC)", callback_data=f"pay_usdt:{order['order_id']}", api_kwargs={"style": "success"})
    buttons.append([b1, b2])
    buttons.append([InlineKeyboardButton("« Cancel & Go Back", callback_data="home")])
    return text, InlineKeyboardMarkup(buttons)


def topup_menu(user_balance=0.0):
    bal_str = fmt_price(user_balance)
    text = (
        f"💳 <b>TOP UP BALANCE</b>\n"
        f"────────────────────\n\n"
        f"💰 <b>Current Balance:</b> <b>{bal_str}</b>\n\n"
        f"Top up once, buy anytime — no need to transfer every order.\n\n"
        f"────────────────────\n"
        f"<i>Pick an amount or enter a custom one:</i>"
    )
    rows = [
        [
            InlineKeyboardButton("+$5.00", callback_data="dep:5"),
            InlineKeyboardButton("+$10.00", callback_data="dep:10"),
            InlineKeyboardButton("+$25.00", callback_data="dep:25"),
        ],
        [
            InlineKeyboardButton("+$50.00", callback_data="dep:50"),
            InlineKeyboardButton("+$100.00", callback_data="dep:100"),
        ],
        [
            InlineKeyboardButton("✏️ Custom Amount", callback_data="custom_dep"),
        ],
        [
            InlineKeyboardButton("« Back to Menu", callback_data="home"),
        ]
    ]
    return text, InlineKeyboardMarkup(rows)


def deposit_pay_page(deposit):
    amt = float(deposit['amount'])
    pay_id = config.BINANCE_PAY_ID
    wallet = config.CRYPTO_WALLET_USDT
    text = (
        f"💳 <b>DEPOSIT • {fmt_price(amt)}</b>\n"
        f"────────────────────\n\n"
        f"🆔 <b>Deposit ID:</b> <code>{deposit['deposit_id']}</code>\n"
        f"💰 <b>Amount Due:</b> <b>{amt:.2f} USDT</b> (exact amount only)\n\n"
        f"<b>1. Via Binance Pay:</b>\n"
        f"👉 Pay ID: <code>{pay_id}</code>\n\n"
        f"<b>2. Via USDT (BEP20 / BSC):</b>\n"
        f"👉 Address: <code>{wallet}</code>\n\n"
        f"────────────────────\n"
        f"<i>Done transferring? Tap below and paste your Transaction ID:</i>"
    )
    btn = InlineKeyboardButton("✅ I've Transferred", callback_data=f"confirm_dep:{deposit['deposit_id']}")
    try:
        setattr(btn, "style", "success")
        setattr(btn, "icon_custom_emoji_id", "5411309092427834175")
    except Exception:
        pass
    rows = [
        [btn],
        [InlineKeyboardButton("« Cancel Deposit", callback_data="home")]
    ]
    return text, InlineKeyboardMarkup(rows)


def binance_pay_page(order, usdt_amount=None):
    pay_id = config.BINANCE_PAY_ID
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    icon = get_product_icon({"name": order['product_name'], "id": order.get('product_id', '')})
    text = (
        f"🟡 <b>BINANCE PAY</b>\n"
        f"────────────────────\n\n"
        f"{icon} <b>Item    :</b> {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 <b>Amount  :</b> <b>{amt:.2f} USDT</b> (exact amount only)\n"
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n\n"
        f"────────────────────\n"
        f"📲 <b>Binance Pay ID:</b>\n"
        f"👉 <code>{pay_id}</code>\n\n"
        f"<b>How to Pay:</b>\n"
        f"1. Open Binance Pay or scan the QR\n"
        f"2. Send <b>{amt:.2f} USDT</b> to Pay ID: <code>{pay_id}</code>\n"
        f"3. Tap below & paste your <b>Transaction ID</b> from the receipt\n\n"
        f"────────────────────\n"
        f"<i>Transfer done? Hit the button below!</i>"
    )
    pay_btn = InlineKeyboardButton(
        "✅ I've Transferred",
        callback_data=f"confirm_pay:{order['order_id']}",
        api_kwargs={"icon_custom_emoji_id": "5411309092427834175", "style": "success"}
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📋 Copy Binance ID",
                    copy_text=CopyTextButton(text=pay_id),
                )
            ],
            [pay_btn],
            [InlineKeyboardButton("🌐 Switch to USDT BEP20", callback_data=f"pay_usdt:{order['order_id']}")],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def crypto_usdt_page(order, usdt_amount=None):
    wallet = config.CRYPTO_WALLET_USDT
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    icon = get_product_icon({"name": order['product_name'], "id": order.get('product_id', '')})
    text = (
        f"🌐 <b>USDT PAYMENT (BEP20 / BSC)</b>\n"
        f"────────────────────\n\n"
        f"{icon} <b>Item    :</b> {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 <b>Amount  :</b> <b>{amt:.2f} USDT</b> (exact amount only)\n"
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n\n"
        f"────────────────────\n"
        f"📩 <b>Wallet Address:</b>\n"
        f"👉 <code>{wallet}</code>\n\n"
        f"⚠️ <b>Important:</b>\n"
        f"• Network: <b>BNB Smart Chain (BEP20)</b>\n"
        f"• Do NOT send via other networks (ERC20/TRC20)\n\n"
        f"────────────────────\n"
        f"<i>Transfer done? Hit the button below!</i>"
    )
    pay_btn2 = InlineKeyboardButton(
        "✅ I've Transferred",
        callback_data=f"confirm_pay:{order['order_id']}",
        api_kwargs={"icon_custom_emoji_id": "5411309092427834175", "style": "success"}
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📋 Copy Wallet Address",
                    copy_text=CopyTextButton(text=wallet),
                )
            ],
            [pay_btn2],
            [InlineKeyboardButton("🟡 Switch to Binance Pay", callback_data=f"pay_binance:{order['order_id']}")],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
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
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def pending_page(order):
    text = (
        f"⏳ <b>AWAITING PAYMENT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛍️ {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 Total: <b>{fmt_price(order['total'])}</b>\n"
        f"🧾 Order ID: <code>{order['order_id']}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Complete your payment then check the status below.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔄 Check Payment Status", callback_data=f"paid:{order['order_id']}"
                )
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def awaiting_admin_page(order_id):
    text = (
        f"⚡ <b>VERIFYING YOUR PAYMENT</b>\n"
        f"────────────────────\n\n"
        f"🧾 <b>Order ID:</b> <code>{esc(order_id)}</code>\n\n"
        f"We've received your transaction details and are matching it with the payment network.\n\n"
        f"🚀 <i>Once confirmed, your digital account will be delivered here automatically!</i>\n"
        f"────────────────────"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back to Menu", callback_data="home")]]
    )
    return text, keyboard


def success_page(order_id):
    text = (
        f"{EMOJI_VERIFIED} <b>ORDER COMPLETE!</b>\n"
        f"────────────────────\n\n"
        f"{EMOJI_CHECK} <b>Payment Confirmed</b>\n"
        f"🧾 <b>Order ID:</b> <code>{esc(order_id)}</code>\n\n"
        f"📦 Your digital account has been delivered above.\n"
        f"Thanks for shopping with <b>{BRAND}</b>! {EMOJI_HEART}\n\n"
        f"────────────────────"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back to Menu", callback_data="home")]]
    )
    return text, keyboard


def no_stock_paid_page(order_id):
    text = (
        f"⚠️ <b>STOCK RAN OUT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Payment received: <code>{esc(order_id)}</code>\n\n"
        f"Stock ran out right as your order was confirmed.\n"
        f"Admin has been notified and will arrange a replacement or refund ASAP.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back to Menu", callback_data="home")]]
    )
    return text, keyboard


def error_page(message="Something went wrong — please try again."):
    text = (
        f"⚠️ <b>OOPS!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{esc(message)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back to Menu", callback_data="home")]]
    )
    return text, keyboard


def soldout_page():
    text = (
        f"😔 <b>OUT OF STOCK</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"This one's sold out right now.\n"
        f"Check back later or browse what else we've got!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ See Other Products", callback_data="catalog")],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
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
        f"📊 <b>Store Overview:</b>\n"
        f"• Active Products : <b>{len(products)}</b>\n"
        f"• Total Stock     : <b>{total_stock} items</b>\n"
        f"• Total Orders    : <b>{len(orders)}</b> ({pending} pending, {completed} completed)\n\n"
        f"────────────────────"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📦 Live Stock", callback_data="stock"),
                InlineKeyboardButton("🧾 Orders Log", callback_data="ordersadmin"),
            ],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def admin_orders_page():
    rows = db.get_all_orders(limit=50)
    if not rows:
        text = (
            f"🧾 <b>ALL TRANSACTIONS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"No transactions recorded yet.\n\n"
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
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard
