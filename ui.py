import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

import config
import db

BRAND = "NOLE SHOP"


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
EMOJI_GAMMA = '<tg-emoji emoji-id="5848290240627740402">🎬</tg-emoji>'
EMOJI_RUNWAY = '<tg-emoji emoji-id="5848290240627740402">🎬</tg-emoji>'
EMOJI_HIGGSFIELD = '<tg-emoji emoji-id="5848290240627740402">🎬</tg-emoji>'
EMOJI_LOVABLE = '<tg-emoji emoji-id="5848290240627740402">🎬</tg-emoji>'
EMOJI_PERPLEXITY = '<tg-emoji emoji-id="5848290240627740402">🎬</tg-emoji>'
EMOJI_DUOLINGO = '<tg-emoji emoji-id="6023922371168047961">🦜</tg-emoji>'
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
        f"{EMOJI_STAR} <b>{BRAND}</b>\n\n"
        f"🔐 <b>Almost there!</b>\n\n"
        f"Join the channel first to unlock the store.\n\n"
        f"👉 <b>{channel}</b>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Join Now", url=channel_link)],
            [InlineKeyboardButton("✅ I'm In, Let's Go!", callback_data="checkjoin")],
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
    if "gamma" in name:
        return EMOJI_GAMMA
    if "runway" in name:
        return EMOJI_RUNWAY
    if "higgsfield" in name:
        return EMOJI_HIGGSFIELD
    if "lovable" in name:
        return EMOJI_LOVABLE
    if "perplexity" in name:
        return EMOJI_PERPLEXITY
    if "duolingo" in name:
        return EMOJI_DUOLINGO
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
    if "gamma" in name:
        return "5848290240627740402"
    if "runway" in name:
        return "5848290240627740402"
    if "higgsfield" in name:
        return "5848290240627740402"
    if "lovable" in name:
        return "5848290240627740402"
    if "perplexity" in name:
        return "5848290240627740402"
    if "duolingo" in name:
        return "6023922371168047961"
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
    if "gamma" in name:
        return "🎬"
    if "runway" in name:
        return "🎬"
    if "higgsfield" in name:
        return "🎬"
    if "lovable" in name:
        return "🎬"
    if "perplexity" in name:
        return "🎬"
    if "duolingo" in name:
        return "🦜"
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
    stock_badge = f"🟢 {avail}" if avail > 0 else "🔴 Sold Out"
    icon = get_product_icon(p)
    price_display = fmt_price(p['price'])
    return f"{icon} <b>{esc(p['name'])}</b>  {price_display}  {stock_badge}"


def home_text(user_name=None, user_id=None):
    products = db.get_active_products()
    balance_val = db.get_wallet(str(user_id)) if user_id else 0.0
    user_greeting = f"<b>{esc(user_name)}</b>" if user_name else "there"

    text = (
        f"<b>NOLE SHOP</b>\n"
        f"<i>Your go-to digital store.</i>\n\n"
        f"Hey {user_greeting}, what are you copping today?\n\n"
        f"Balance: <b>{fmt_price(balance_val)}</b>"
    )

    rows = []
    for p in products:
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail}" if avail > 0 else "🔴"
        emoji_id = get_product_emoji_id(p)
        price_tag = fmt_price(p['price'])
        btn = InlineKeyboardButton(
            f"{p['name']}  {price_tag}  {stock_badge}",
            callback_data=f"product:{p['id']}",
            api_kwargs={"icon_custom_emoji_id": emoji_id, "style": "success"}
        )
        rows.append([btn])

    rows.append([
        InlineKeyboardButton("💳 Top Up", callback_data="topup"),
        InlineKeyboardButton("🧾 Orders", callback_data="orders"),
    ])
    rows.append([
        InlineKeyboardButton("📦 Stock", callback_data="stock"),
        InlineKeyboardButton("💬 Support", callback_data="contact"),
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
    ])

    return text, InlineKeyboardMarkup(rows)


def promo_page():
    products = sorted(db.get_active_products(), key=lambda p: p["price"], reverse=True)
    if not products:
        text = f"🔥 <b>DEALS & PROMOS</b>\n\nNo active promos right now. Check back soon!"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Back", callback_data="home")]]
        )
        return text, keyboard

    items = [product_line(p) for p in products]
    text = (
        f"🔥 <b>HOT DEALS</b>\n\n"
        f"{chr(10).join(items)}"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Browse All Products", callback_data="catalog")],
            [InlineKeyboardButton("« Back", callback_data="home")],
        ]
    )
    return text, keyboard


def catalog_text():
    products = db.get_active_products()
    if not products:
        text = f"🛍️ <b>CATALOG</b>\n\nNothing available right now. Check back soon!"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Back", callback_data="home")]]
        )
        return text, keyboard

    items_list = []
    for i, p in enumerate(products, 1):
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail}" if avail > 0 else "🔴 Sold Out"
        icon = get_product_icon(p)
        price_tag = fmt_price(p['price'])
        items_list.append(f"{i}. {icon} <b>{esc(p['name'])}</b>  {price_tag}  {stock_badge}")

    text = f"🛍️ <b>CATALOG</b>\n\n{chr(10).join(items_list)}\n\n<i>Tap to order:</i>"

    rows = []
    for p in products:
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail}" if avail > 0 else "🔴"
        emoji_id = get_product_emoji_id(p)
        price_tag = fmt_price(p['price'])
        btn = InlineKeyboardButton(
            f"{p['name']}  {price_tag}  {stock_badge}",
            callback_data=f"product:{p['id']}",
            api_kwargs={"icon_custom_emoji_id": emoji_id, "style": "success"}
        )
        rows.append([btn])

    rows.append([
        InlineKeyboardButton("📦 Stock", callback_data="stock"),
        InlineKeyboardButton("« Menu", callback_data="home"),
    ])
    return text, InlineKeyboardMarkup(rows)


def product_page(product, qty):
    avail = db.count_available(product["id"])
    unit_price, total = calculate_item_price(product, qty)
    sold_out = avail < 1

    stock_badge = f"🟢 {avail} in stock" if avail > 0 else "🔴 Out of stock"
    icon = get_product_icon(product)

    desc = esc(product['description']).strip()
    if desc.startswith("✨"):
        desc = desc.lstrip("✨").strip()

    text = (
        f"{icon} <b>{esc(product['name'])}</b>\n\n"
        f"{desc}\n\n"
        f"💰 <b>{fmt_price(unit_price)}</b>  {stock_badge}\n"
        f"⚡ Instant delivery\n\n"
        f"🛒 <b>{qty}x = {fmt_price(total)}</b>"
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
            f"🔥 Order Now • {fmt_price(total)}",
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
        items.append("No products right now. Check back soon!")
    for p in products:
        items.append(product_line(p))

    text = f"📦 <b>STOCK</b>\n\n{chr(10).join(items)}"
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Browse Catalog", callback_data="catalog")],
            [InlineKeyboardButton("« Back", callback_data="home")],
        ]
    )
    return text, keyboard


def orders_page(user_id):
    rows = db.get_my_orders(user_id)
    if not rows:
        text = f"🧾 <b>ORDERS</b>\n\nNo orders yet."
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
                f"{icon} {p_icon} <b>{esc(o['product_name'])}</b> x{o['qty']}  <b>{fmt_price(o['total'])}</b>\n"
                f"   <code>{o['order_id']}</code>  {o['status']}"
            )
        text = f"🧾 <b>ORDERS</b>\n\n{chr(10).join(items)}"

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Shop Again", callback_data="catalog")],
            [InlineKeyboardButton("« Back", callback_data="home")],
        ]
    )
    return text, keyboard


def contact_page():
    admin = "nolejass"
    text = (
        f"💬 <b>SUPPORT</b>\n\n"
        f"Admin: @{esc(admin)}\n\n"
        f"<b>Commands:</b>\n"
        f"<code>/start</code>  Main Menu\n"
        f"<code>/products</code>  Catalog\n"
        f"<code>/stock</code>  Live Stock\n"
        f"<code>/orders</code>  Order History\n"
        f"<code>/support</code>  Contact Admin"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Chat Admin (@nolejass)", url=f"https://t.me/{admin}")],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard


def loading_text(msg="Processing your order..."):
    return f"⏳ <b>{esc(msg)}</b>\n\n<i>Give us a sec...</i>", InlineKeyboardMarkup([])


def payment_method_page(order, usdt_amount=None, user_balance=0.0):
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    icon = get_product_icon({"name": order['product_name'], "id": order.get('product_id', '')})
    bal_str = fmt_price(user_balance)
    text = (
        f"<b>Checkout</b>\n\n"
        f"Item: {icon} <b>{esc(order['product_name'])}</b>\n"
        f"Qty: {order['qty']}x\n"
        f"Total: <b>{fmt_price(order['total'])}</b> ({amt:.2f} USDT)\n"
        f"Balance: <b>{bal_str}</b>\n"
        f"Order ID: <code>{order['order_id']}</code>\n\n"
        f"Pick your payment method:"
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
        f"💳 <b>TOP UP</b>\n\n"
        f"Balance: <b>{bal_str}</b>\n\n"
        f"<i>Pick an amount:</i>"
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
        f"💳 <b>DEPOSIT  {fmt_price(amt)}</b>\n\n"
        f"ID: <code>{deposit['deposit_id']}</code>\n"
        f"Amount: <b>{amt:.2f} USDT</b>\n\n"
        f"<b>Binance Pay:</b>\n"
        f"<code>{pay_id}</code>\n\n"
        f"<b>USDT BEP20:</b>\n"
        f"<code>{wallet}</code>\n\n"
        f"<i>Done? Tap below and send your Transaction ID.</i>"
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
        f"🟡 <b>BINANCE PAY</b>\n\n"
        f"{icon} <b>{esc(order['product_name'])}</b> x{order['qty']}\n"
        f"Amount: <b>{amt:.2f} USDT</b>\n"
        f"Order: <code>{order['order_id']}</code>\n\n"
        f"<b>Pay ID:</b>\n"
        f"<code>{pay_id}</code>\n\n"
        f"<i>Sent? Tap below.</i>"
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
        f"🌐 <b>USDT BEP20</b>\n\n"
        f"{icon} <b>{esc(order['product_name'])}</b> x{order['qty']}\n"
        f"Amount: <b>{amt:.2f} USDT</b>\n"
        f"Order: <code>{order['order_id']}</code>\n\n"
        f"<b>Wallet:</b>\n"
        f"<code>{wallet}</code>\n\n"
        f"⚠️ BNB Smart Chain (BEP20) only\n\n"
        f"<i>Sent? Tap below.</i>"
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
        f"<i>Complete your payment, then tap below to check your status.</i>"
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
        f"⚡ <b>VERIFYING PAYMENT</b>\n\n"
        f"Order: <code>{esc(order_id)}</code>\n\n"
        f"<i>Got your proof. Hang tight, your account is on the way.</i>"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back to Menu", callback_data="home")]]
    )
    return text, keyboard


def success_page(order_id):
    text = (
        f"{EMOJI_VERIFIED} <b>ORDER COMPLETE</b>\n\n"
        f"{EMOJI_CHECK} Payment confirmed\n"
        f"Order: <code>{esc(order_id)}</code>\n\n"
        f"Your account is in the message above.\n"
        f"Thanks for shopping with <b>{BRAND}</b>. {EMOJI_HEART}"
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
        f"Your payment went through but the stock ran dry at the exact same moment.\n"
        f"Admin's been notified and we'll get you a replacement or full refund ASAP.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back to Menu", callback_data="home")]]
    )
    return text, keyboard


def error_page(message="Something went wrong. Please try again."):
    text = (
        f"⚠️ <b>HOLD UP!</b>\n"
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
        f"This one just ran out. But we've got more heat in the catalog!\n\n"
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
        f"{EMOJI_VERIFIED} <b>{BRAND} ADMIN</b>\n\n"
        f"Products: <b>{len(products)}</b>\n"
        f"Stock: <b>{total_stock}</b>\n"
        f"Orders: <b>{len(orders)}</b>  ({pending} pending  {completed} done)"
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
        text = f"🧾 <b>TRANSACTIONS</b>\n\nNo transactions yet."
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
                f"{icon} <code>{o['order_id']}</code>  <b>{fmt_price(o['total'])}</b>\n"
                f"   {esc(o['product_name'])} x{o['qty']}  {o['status']}  UID:<code>{o['telegram_id']}</code>"
            )
        text = f"🧾 <b>TRANSACTIONS</b>\n\n{chr(10).join(items)}"

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔐 Admin Console", callback_data="admin")],
            [InlineKeyboardButton("« Back to Menu", callback_data="home")],
        ]
    )
    return text, keyboard
