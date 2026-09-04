import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

import config
import db

BRAND = "Norcicle Store"


def esc(s):
    return html.escape(str(s))


def header(title=None):
    if title:
        return f"<b>{BRAND}</b> • {title}"
    return f"<b>{BRAND}</b>"


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
        f"{header('Join Channel')}\n\n"
        f"Please join our official channel to continue shopping:\n\n"
        f"📢 <b>Channel:</b> {channel}\n\n"
        f"After joining, tap <b>Verify & Continue</b> below."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Join Channel", url=channel_link)],
            [InlineKeyboardButton("✅ Verify & Continue", callback_data="checkjoin")],
        ]
    )
    return text, keyboard


def product_line(p):
    avail = db.count_available(p["id"])
    stock_badge = f"🟢 {avail} in stock" if avail > 0 else "🔴 Sold out"
    return f"{p['emoji']} <b>{esc(p['name'])}</b>\nPrice: <b>{fmt_price(p['price'])}</b> • {stock_badge}"


def home_text(user_name=None):
    products = db.get_active_products()
    name = f", <b>{esc(user_name)}</b>" if user_name else ""

    text = (
        f"👋 Welcome to <b>{BRAND}</b>{name}!\n\n"
        f"⚡ <b>Instant Delivery • 24/7 Automated</b>\n"
        f"💎 High-Quality Digital Subscriptions & Accounts\n\n"
        f"Select a product directly below to purchase 👇"
    )

    rows = []
    # Baris tombol produk langsung (1 atau 2 kolom)
    for p in products:
        avail = db.count_available(p["id"])
        stock_badge = f"🟢 {avail}" if avail > 0 else "🔴 0"
        rows.append([
            InlineKeyboardButton(
                f"{p['emoji']} {esc(p['name'])} • {fmt_price(p['price'])} ({stock_badge})",
                callback_data=f"product:{p['id']}"
            )
        ])

    # Menu utility di bawah produk
    rows.append([
        InlineKeyboardButton("📦 Live Stock", callback_data="stock"),
        InlineKeyboardButton("🧾 My Orders", callback_data="orders"),
    ])
    rows.append([
        InlineKeyboardButton("🤝 Affiliate", callback_data="affiliate"),
        InlineKeyboardButton("💬 Support", callback_data="contact"),
    ])
    rows.append([
        InlineKeyboardButton("↻ Refresh Menu", callback_data="refresh"),
    ])

    return text, InlineKeyboardMarkup(rows)


def promo_page():
    products = sorted(db.get_active_products(), key=lambda p: p["price"])
    if not products:
        text = f"{header('Special Offers')}\n\nNo active offers right now."
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Back to Home", callback_data="home")]]
        )
        return text, keyboard
    
    items = [product_line(p) for p in products]
    text = (
        f"{header('Special Offers')}\n\n"
        f"{chr(10).join(items)}\n\n"
        f"Grab your digital products before stock runs out!"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Order Now", callback_data="catalog")],
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
        ]
    )
    return text, keyboard


def catalog_text():
    products = db.get_active_products()
    if not products:
        text = f"{header('Catalog')}\n\nNo products available at the moment."
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« Back to Home", callback_data="home")]]
        )
        return text, keyboard

    text = (
        f"{header('Product Catalog')}\n\n"
        f"Select a product to view details & buy:"
    )

    rows = []
    for p in products:
        avail = db.count_available(p["id"])
        stock_text = f"({avail} ready)" if avail > 0 else "(Sold out)"
        rows.append([
            InlineKeyboardButton(
                f"{p['emoji']} {esc(p['name'])} - {fmt_price(p['price'])} {stock_text}",
                callback_data=f"product:{p['id']}"
            )
        ])
    rows.append(
        [
            InlineKeyboardButton("📦 Live Stock", callback_data="stock"),
            InlineKeyboardButton("« Back to Home", callback_data="home"),
        ]
    )
    return text, InlineKeyboardMarkup(rows)


def product_page(product, qty):
    avail = db.count_available(product["id"])
    total = product["price"] * qty
    sold_out = avail < 1

    stock_badge = f"🟢 In Stock ({avail} available)" if avail > 0 else "🔴 Out of Stock"

    text = (
        f"{product['emoji']} <b>{esc(product['name'])}</b>\n\n"
        f"📝 <b>Description:</b>\n{esc(product['description'])}\n\n"
        f"💵 <b>Price:</b> {fmt_price(product['price'])}\n"
        f"📦 <b>Stock:</b> {stock_badge}\n"
        f"⚡ <b>Delivery:</b> Instant via Telegram\n\n"
        f"Selected Quantity: <b>{qty}</b>\n"
        f"Total Price: <b>{fmt_price(total)}</b>"
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
            [InlineKeyboardButton(f"⚡ Buy Now • {fmt_price(total)}", callback_data=f"buy:{product['id']}")],
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
        items.append("No stock data available.")
    for p in products:
        items.append(product_line(p))
    
    text = (
        f"{header('Live Stock')}\n\n"
        f"{chr(10).join(items)}\n\n"
        f"Stock updates in real-time."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Browse Catalog", callback_data="catalog")],
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
        ]
    )
    return text, keyboard


def orders_page(user_id):
    rows = db.get_my_orders(user_id)
    if not rows:
        text = f"{header('My Orders')}\n\nYou haven't placed any orders yet."
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
                f"🧾 <code>{o['order_id']}</code>\n"
                f"   {esc(o['product_name'])} × {o['qty']} • <b>{fmt_price(o['total'])}</b>\n"
                f"   Status: {icon} <b>{o['status']}</b>"
            )
        text = f"{header('My Orders')}\n\n" + "\n\n".join(items)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Shop Now", callback_data="catalog")],
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
        ]
    )
    return text, keyboard


def contact_page():
    admin = db.get_setting("ADMIN_USERNAME", "admin")
    text = (
        f"{header('Customer Support')}\n\n"
        f"Need assistance or have any questions?\n"
        f"Contact our admin directly: @{esc(admin)}\n\n"
        f"<b>Commands:</b>\n"
        f"/start — Main Menu\n"
        f"/products — Catalog\n"
        f"/stock — Live Stock\n"
        f"/orders — Order History\n"
        f"/support — Support Admin"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{admin}")],
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
        ]
    )
    return text, keyboard


def loading_text(msg="Processing your order..."):
    return f"⏳ <b>{esc(msg)}</b>\n\nPlease wait a moment...", InlineKeyboardMarkup([])


def payment_method_page(order, usdt_amount=None):
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    text = (
        f"{header('Checkout & Payment')}\n\n"
        f"📦 <b>Item:</b> {esc(order['product_name'])}\n"
        f"🔢 <b>Quantity:</b> {order['qty']}\n"
        f"💰 <b>Total Due:</b> <b>{fmt_price(order['total'])}</b> (<b>{amt:.2f} USDT</b>)\n"
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n\n"
        f"Please choose your payment method below:"
    )
    buttons = [
        [
            InlineKeyboardButton("🟡 Binance Pay (ID)", callback_data=f"pay_binance:{order['order_id']}"),
            InlineKeyboardButton("🌐 USDT (BEP20)", callback_data=f"pay_usdt:{order['order_id']}"),
        ],
        [InlineKeyboardButton("« Cancel Order", callback_data="home")],
    ]
    return text, InlineKeyboardMarkup(buttons)


def binance_pay_page(order, usdt_amount=None):
    pay_id = config.BINANCE_PAY_ID
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    text = (
        f"{header('Binance Pay Payment')}\n\n"
        f"📦 <b>Item:</b> {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 <b>Exact Amount:</b> <b>{amt:.2f} USDT</b>\n"
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n\n"
        f"📲 <b>Send to Binance ID:</b>\n"
        f"<code>{pay_id}</code>\n\n"
        f"<b>How to Pay:</b>\n"
        f"1. Open your Binance App ➔ Pay / Send\n"
        f"2. Input Binance ID: <code>{pay_id}</code>\n"
        f"3. Send exactly <b>{amt:.2f} USDT</b>\n"
        f"4. Add your Order ID in notes: <code>{order['order_id']}</code>\n\n"
        f"Click <b>I Have Paid</b> below after transferring 👇"
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
            [InlineKeyboardButton("🌐 Pay via USDT BEP20", callback_data=f"pay_usdt:{order['order_id']}")],
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
        ]
    )
    return text, keyboard


def crypto_usdt_page(order, usdt_amount=None):
    wallet = config.CRYPTO_WALLET_USDT
    amt = float(usdt_amount if usdt_amount is not None else order['total'])
    text = (
        f"{header('USDT (BEP20) Payment')}\n\n"
        f"📦 <b>Item:</b> {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 <b>Exact Amount:</b> <b>{amt:.2f} USDT</b>\n"
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n\n"
        f"📩 <b>Wallet Address (BEP20 / BSC):</b>\n"
        f"<code>{wallet}</code>\n\n"
        f"⚠️ <b>Important:</b>\n"
        f"• Network: <b>BNB Smart Chain (BEP20)</b> only\n"
        f"• Send exact amount: <b>{amt:.2f} USDT</b>\n\n"
        f"Click <b>I Have Paid</b> below after transferring 👇"
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
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
        ]
    )
    return text, keyboard


def test_payment_page(order):
    text = (
        f"{header('Test Mode')}\n\n"
        f"This is a simulated transaction.\n\n"
        f"📦 {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 Total: <b>{fmt_price(order['total'])}</b>\n"
        f"🧾 Order ID: <code>{order['order_id']}</code>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Simulate Success", callback_data=f"paid:{order['order_id']}")],
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
        ]
    )
    return text, keyboard


def pending_page(order):
    text = (
        f"{header('Payment Pending')}\n\n"
        f"📦 {esc(order['product_name'])} x{order['qty']}\n"
        f"💰 Total: <b>{fmt_price(order['total'])}</b>\n"
        f"🧾 Order ID: <code>{order['order_id']}</code>\n\n"
        f"Please complete your transfer and check status."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "↻ Check Payment Status", callback_data=f"paid:{order['order_id']}"
                )
            ],
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
        ]
    )
    return text, keyboard


def awaiting_admin_page(order_id):
    text = (
        f"{header('Verification in Progress')}\n\n"
        f"🧾 Order ID: <code>{esc(order_id)}</code>\n\n"
        f"Your payment has been submitted for admin verification.\n"
        f"Your product will be delivered automatically upon confirmation. 🙏"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back to Home", callback_data="home")]]
    )
    return text, keyboard


def success_page(order_id):
    text = (
        f"{header('Payment Successful')}\n\n"
        f"✅ <b>Order Completed!</b>\n"
        f"🧾 Order ID: <code>{esc(order_id)}</code>\n\n"
        f"Your digital product has been sent in the message above. 🎁\n"
        f"Thank you for shopping with us!"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back to Home", callback_data="home")]]
    )
    return text, keyboard


def no_stock_paid_page(order_id):
    text = (
        f"{header('Stock Depleted')}\n\n"
        f"✅ Payment confirmed: <code>{esc(order_id)}</code>\n\n"
        f"Unfortunately, stock ran out during checkout.\n"
        f"Admin will contact you shortly for refund or replacement."
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back to Home", callback_data="home")]]
    )
    return text, keyboard


def error_page(message="An error occurred, please try again later."):
    text = f"{header('Notice')}\n\n⚠️ {esc(message)}"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back to Home", callback_data="home")]]
    )
    return text, keyboard


def soldout_page():
    text = (
        f"{header('Out of Stock')}\n\n"
        f"Sorry, this product is currently out of stock.\n"
        f"Please check back later or explore other products."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Browse Catalog", callback_data="catalog")],
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
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
        f"{header('Admin Panel')}\n\n"
        f"📊 <b>Summary:</b>\n"
        f"• Active Products: {len(products)}\n"
        f"• Total Ready Stock: {total_stock}\n"
        f"• Orders: {len(orders)} ({pending} pending, {completed} completed)"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📦 Stock List", callback_data="stock"),
                InlineKeyboardButton("🧾 Orders Log", callback_data="ordersadmin"),
            ],
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
        ]
    )
    return text, keyboard


def admin_orders_page():
    rows = db.get_all_orders(limit=50)
    if not rows:
        text = f"{header('All Orders')}\n\nNo orders yet."
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
                f"🧾 <code>{o['order_id']}</code> • <b>{fmt_price(o['total'])}</b>\n"
                f"   {esc(o['product_name'])} x{o['qty']} • {icon} {o['status']} • UID: <code>{o['telegram_id']}</code>"
            )
        text = f"{header('All Orders')}\n\n" + "\n\n".join(items)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔐 Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("« Back to Home", callback_data="home")],
        ]
    )
    return text, keyboard
