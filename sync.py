import csv
import io
import logging
import re
import threading
import time

import requests

import config
import db

logger = logging.getLogger(__name__)

SYNC_LOCK = threading.Lock()
_last_sync_done = 0.0
_SYNC_TTL_SECONDS = 20.0


def fetch_csv(url):
    # Coba gviz URL dulu, jika mengembalikan format sheet yang salah coba export URL
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    r.encoding = "utf-8"
    rows = list(csv.DictReader(io.StringIO(r.text)))
    return rows


def _parse_price(raw):
    s = str(raw or "").strip().replace("$", "").replace(",", "")
    match = re.search(r"[-+]?\d*\.?\d+", s)
    if match:
        try:
            val = float(match.group())
            return int(val) if val.is_integer() else val
        except ValueError:
            return 0
    return 0


def restore_inflight_orders():
    """Import ulang order yang masih berjalan dari sheet ORDERS.

    Berguna saat disk ephemeral (SQLite) terhapus oleh redeploy: order
    PENDING/AWAITING_ADMIN/PAID_BUT_OUT_OF_STOCK dipulihkan dari sheet
    sehingga admin masih bisa approve dan user masih bisa cek status.
    """
    try:
        rows = fetch_csv(config.ORDERS_URL)
    except Exception as e:
        logger.error("Gagal baca ORDERS sheet: %s", e)
        return
    restored = 0
    for row in rows:
        oid = str(row.get("ORDER_ID", "")).strip()
        status = str(row.get("STATUS", "")).strip().upper()
        if not oid:
            continue
        if status not in ("PENDING", "AWAITING_ADMIN", "PAID_BUT_OUT_OF_STOCK"):
            continue
        if db.get_order(oid):
            continue
        pid = str(row.get("PRODUCT_ID", "")).strip()
        pname = str(row.get("PRODUCT_NAME", "")).strip() or pid
        try:
            prod = next(
                (p for p in db.get_active_products() if p["id"] == pid), None
            )
            if prod:
                pname = prod["name"]
        except Exception:
            pass
        db.create_order(
            oid,
            str(row.get("TELEGRAM_ID", "")).strip(),
            str(row.get("USERNAME", "")).strip(),
            {
                "id": pid,
                "name": pname,
                "emoji": "",
                "price": _parse_price(row.get("TOTAL", "")),
                "status": "ACTIVE",
                "description": "",
            },
            max(1, _parse_price(row.get("QTY", ""))),
            _parse_price(row.get("TOTAL", "")),
        )
        db.set_order_status(oid, status, payment_id=row.get("PAYMENT_ID", "") or None, paid_at=row.get("PAID_AT", "") or None)
        restored += 1
    if restored:
        logger.info("Order dipulihkan dari sheet: %s", restored)


def restore_sold_stock():
    """Rekonstruksi status SOLD dari sheet ORDERS (kolom STOCK_IDS).

    Dipanggil SETELAH sync_from_sheets(). Menutup celah penjualan-ganda saat
    disk ephemeral terhapus oleh redeploy: jika write-back STOCK (mark_sold)
    gagal tapi write-back ORDERS berhasil, stok yang sudah terjual akan
    di-import ulang sebagai AVAILABLE dan bisa dijual 2x. Dengan memetakan
    stock_id -> order COMPLETED dari kolom STOCK_IDS, baris itu dikunci SOLD
    lagi.

    Aman pada restart normal: baris RESERVED (milik order yang masih hidup)
    tidak disentuh, dan baris SOLD yang sudah punya pemilik tidak ditimpa.
    Iterasi dibalik (terbaru duluan) sehingga bila ada konflik historis,
    order yang paling akhir menang.
    """
    try:
        rows = fetch_csv(config.ORDERS_URL)
    except Exception as e:
        logger.error("Gagal baca ORDERS untuk restore stok SOLD: %s", e)
        return 0
    restored = 0
    enriched = 0
    for row in reversed(rows):
        oid = str(row.get("ORDER_ID", "")).strip()
        status = str(row.get("STATUS", "")).strip().upper()
        if status != "COMPLETED" or not oid:
            continue
        stock_ids = [
            s.strip()
            for s in str(row.get("STOCK_IDS", "")).replace(";", ",").split(",")
            if s.strip()
        ]
        if not stock_ids:
            continue
        sold_to = str(row.get("TELEGRAM_ID", "")).strip()
        paid_at = str(row.get("PAID_AT", "")).strip()
        now = db.utcnow().isoformat()
        conn = db.get_conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for sid in stock_ids:
                cur = conn.execute(
                    "UPDATE stock SET status='SOLD', sold_to=?, sold_order_id=?, sold_at=? "
                    "WHERE stock_id=? AND status NOT IN ('SOLD','RESERVED')",
                    (sold_to, oid, paid_at or now, sid),
                )
                restored += cur.rowcount
                if not cur.rowcount:
                    cur = conn.execute(
                        "UPDATE stock SET sold_order_id=?, sold_at=? "
                        "WHERE stock_id=? AND status='SOLD' "
                        "AND (sold_order_id IS NULL OR sold_order_id='')",
                        (oid, paid_at or now, sid),
                    )
                    enriched += cur.rowcount
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    if restored or enriched:
        logger.info(
            "Stok SOLD dipulihkan dari ORDERS sheet: %d dikunci, %d dienrich",
            restored,
            enriched,
        )
    return restored


def sync_from_sheets(force=False):
    """Sinkron dari Google Sheets (PRODUCTS, STOCK, SETTINGS) ke SQLite lokal.

    - Dibatasi TTL (_SYNC_TTL_SECONDS): tap beruntun di menu tidak perlu
      memicu 4 request HTTP penuh setiap kali; refresh/checkjoin/start memakai
      force=True supaya tetap segar.
    - Memakai lock non-blocking: bila ada sinkronisasi sedang berjalan,
      panggilan berikutnya dianggap sudah memuaskan (data < TTL tua), sehingga
      burst update tidak menumpuk di event loop.
    """
    global _last_sync_done
    now = time.monotonic()
    if not force and _last_sync_done and (now - _last_sync_done) < _SYNC_TTL_SECONDS:
        return True
    if not SYNC_LOCK.acquire(blocking=False):
        return True
    try:
        _last_sync_done = time.monotonic()
        for row in fetch_csv(config.PRODUCTS_URL):
            # Cek jika baris 1 adalah header tergabung (misal: 'ID P0001', 'PRICE 0.8')
            first_key_id = next((k for k in row.keys() if k and k.strip().upper().startswith("ID")), None)
            if first_key_id and len(first_key_id.split(None, 1)) > 1:
                # Daftarkan produk dari nama header baris 1 jika belum ada
                h_id = first_key_id.split(None, 1)[1].strip()
                h_name = next((k.split(None, 1)[1].strip() for k in row.keys() if k and k.strip().upper().startswith("NAME") and len(k.split(None, 1)) > 1), h_id)
                h_emoji = next((k.split(None, 1)[1].strip() for k in row.keys() if k and k.strip().upper().startswith("EMOJI") and len(k.split(None, 1)) > 1), "📦")
                h_price = next((k.split(None, 1)[1].strip() for k in row.keys() if k and k.strip().upper().startswith("PRICE") and len(k.split(None, 1)) > 1), 0)
                h_status = next((k.split(None, 1)[1].strip() for k in row.keys() if k and k.strip().upper().startswith("STATUS") and len(k.split(None, 1)) > 1), "ACTIVE")
                h_desc = next((k.split(None, 1)[1].strip() for k in row.keys() if k and k.strip().upper().startswith("DESC") and len(k.split(None, 1)) > 1), h_name)
                db.upsert_product({
                    "id": h_id,
                    "name": h_name,
                    "emoji": h_emoji,
                    "price": _parse_price(h_price),
                    "status": h_status.upper(),
                    "description": h_desc,
                })

            raw_id = row.get("ID")
            if not raw_id and first_key_id:
                raw_id = row.get(first_key_id)
            if not raw_id:
                continue

            name = row.get("NAME") or ""
            emoji = row.get("EMOJI") or "📦"
            price_raw = row.get("PRICE") or 0
            status = row.get("STATUS") or "ACTIVE"
            desc = row.get("DESCRIPTION") or ""

            for k, v in row.items():
                if not k:
                    continue
                ku = k.strip().upper()
                if ku.startswith("NAME") and not name:
                    name = v
                elif ku.startswith("EMOJI") and emoji == "📦":
                    emoji = v or "📦"
                elif ku.startswith("PRICE"):
                    if v is not None and str(v).strip() != "":
                        price_raw = v
                elif ku.startswith("STATUS") and status == "ACTIVE":
                    status = v or "ACTIVE"
                elif ku.startswith("DESC") and not desc:
                    desc = v

            db.upsert_product(
                {
                    "id": str(raw_id).strip(),
                    "name": str(name).strip(),
                    "emoji": str(emoji).strip(),
                    "price": _parse_price(price_raw),
                    "status": str(status).strip().upper(),
                    "description": str(desc).strip(),
                }
            )
        stock_rows = fetch_csv(config.STOCK_URL)
        if stock_rows:
            # Cek jika baris 1 adalah header tergabung (misal: 'STOCK_ID S0001', 'PRODUCT_ID P0001')
            first_s_id = next((k for k in stock_rows[0].keys() if k and k.strip().upper().startswith("STOCK_ID") or (k and k.strip().upper().startswith("STOCK"))), None)
            if first_s_id and len(first_s_id.split(None, 1)) > 1:
                h_sid = first_s_id.split(None, 1)[1].strip()
                h_pid = next((k.split(None, 1)[1].strip() for k in stock_rows[0].keys() if k and (k.strip().upper().startswith("PRODUCT_ID") or k.strip().upper().startswith("PRODUCT")) and len(k.split(None, 1)) > 1), "")
                h_content = next((k.split(None, 1)[1].strip() for k in stock_rows[0].keys() if k and k.strip().upper().startswith("CONTENT") and len(k.split(None, 1)) > 1), "")
                h_status = next((k.split(None, 1)[1].strip() for k in stock_rows[0].keys() if k and k.strip().upper().startswith("STATUS") and len(k.split(None, 1)) > 1), "AVAILABLE")
                h_sold_to = next((k.split(None, 1)[1].strip() for k in stock_rows[0].keys() if k and k.strip().upper().startswith("SOLD_TO") and len(k.split(None, 1)) > 1), "")
                db.upsert_stock_row({
                    "stock_id": h_sid,
                    "product_id": h_pid,
                    "content": h_content,
                    "status": h_status.upper(),
                    "sold_to": h_sold_to,
                })

        for row in stock_rows:
            raw_sid = row.get("STOCK_ID")
            raw_pid = row.get("PRODUCT_ID")
            raw_content = row.get("CONTENT") or ""
            raw_status = row.get("STATUS") or "AVAILABLE"
            raw_sold_to = row.get("SOLD_TO") or ""

            for k, v in row.items():
                if not k:
                    continue
                ku = k.strip().upper()
                if (ku.startswith("STOCK_ID") or ku.startswith("STOCK")) and not raw_sid:
                    raw_sid = v
                elif (ku.startswith("PRODUCT_ID") or ku.startswith("PRODUCT")) and not raw_pid:
                    raw_pid = v
                elif ku.startswith("CONTENT") and not raw_content:
                    raw_content = v
                elif ku.startswith("STATUS") and raw_status == "AVAILABLE":
                    raw_status = v or "AVAILABLE"
                elif ku.startswith("SOLD_TO") and not raw_sold_to:
                    raw_sold_to = v

            if not raw_sid:
                continue

            db.upsert_stock_row(
                {
                    "stock_id": str(raw_sid).strip(),
                    "product_id": str(raw_pid or "").strip(),
                    "content": str(raw_content or ""),
                    "status": str(raw_status or "").strip().upper(),
                    "sold_to": str(raw_sold_to or ""),
                }
            )
        
        kept = set()
        if stock_rows:
            first_s_id = next((k for k in stock_rows[0].keys() if k and (k.strip().upper().startswith("STOCK_ID") or k.strip().upper().startswith("STOCK"))), None)
            if first_s_id and len(first_s_id.split(None, 1)) > 1:
                kept.add(first_s_id.split(None, 1)[1].strip())
        for row in stock_rows:
            for k, v in row.items():
                if k and (k.strip().upper().startswith("STOCK_ID") or k.strip().upper().startswith("STOCK")) and v:
                    kept.add(str(v).strip())
                    break
        available = db.count_all_available()
        if kept and available > max(10, len(kept) * 2):
            logger.warning(
                "STOCK sheet mencurigakan (hanya %d baris vs %d stok lokal) — lewati penghapusan",
                len(kept),
                available,
            )
        else:
            db.delete_stock_not_in(kept)
        for row in fetch_csv(config.SETTINGS_URL):
            if row.get("KEY"):
                db.set_setting(str(row["KEY"]).strip(), row.get("VALUE", ""))
        logger.info("Sinkronisasi dari spreadsheet selesai")
        return True
    except Exception as e:
        logger.error("Gagal sinkronisasi: %s", e)
        return False
    finally:
        SYNC_LOCK.release()
