import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TOKEN", "").strip()

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "").strip()
PRODUCTS_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=PRODUCTS&headers=1"
STOCK_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=STOCK&headers=1"
SETTINGS_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=SETTINGS&headers=1"
ORDERS_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=ORDERS&headers=1"

PAYMENT_METHOD = os.environ.get("PAYMENT_METHOD", "crypto").strip().lower()

BINANCE_PAY_ID = os.environ.get("BINANCE_PAY_ID", "356095638").strip()
BINANCE_QR_URL = os.environ.get("BINANCE_QR_URL", "https://i.ibb.co.com/Lh9133Lg/Whats-App-Image-2026-09-04-at-7-38-02-PM.jpg").strip()
CRYPTO_WALLET_USDT = os.environ.get("CRYPTO_WALLET_USDT", "0x5a3f4b292bd4269b82191ffae4dd14f1d0a75756").strip()

AFFILIATE_PERCENT = int(os.environ.get("AFFILIATE_PERCENT", "5") or 0)

NEVAPEDIA_API_KEY = os.environ.get("NEVAPEDIA_API_KEY", "").strip()

QRIS_IMAGE_URL = os.environ.get("QRIS_IMAGE_URL", "").strip()

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "Norcicle").strip().lstrip("@")

_admin_raw = os.environ.get("ADMIN_CHAT_ID", "").strip()
try:
    ADMIN_CHAT_ID = int(_admin_raw) if _admin_raw else None
except ValueError:
    ADMIN_CHAT_ID = None

SHEET_WRITE_URL = os.environ.get("SHEET_WRITE_URL", "").strip()
SHEET_WRITE_SECRET = os.environ.get("SHEET_WRITE_SECRET", "").strip()

TEST_MODE = os.environ.get("TEST_MODE", "false").lower() in ("1", "true", "yes")

CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@DigitalinUpdate")

# Banner welcome /start. Isi URL gambar publik ATAU file_id foto Telegram
# (biarkan kosong jika tidak ingin banner).
BANNER_URL = os.environ.get(
    "BANNER_URL",
    "https://i.ibb.co.com/VWJw3H7z/Chat-GPT-Image-Sep-4-2026-06-34-34-PM.png",
).strip()
