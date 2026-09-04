// Apps Script khusus write-back: menandai stok SOLD + siapa pembelinya (sold_to)
// di Google Sheets, dipanggil oleh bot.py lewat POST ke endpoint web app.
//
// CARA SETUP (sekali saja, tanpa menjalankan fungsi apa pun):
// 1. Buka https://script.google.com  ->  tombol "+ New project"
// 2. Hapus isi Code.gs, ganti dengan SEMUA kode file ini, lalu save (Ctrl+S)
// 3. Set WRITE_SECRET lewat menu bawaan editor:
//    - Klik ikon "Project Settings" (⚙️) di sidebar kiri
//    - Scroll ke bawah ke "Script properties"
//    - Klik "Add script property"
//      Key   : WRITE_SECRET
//      Value : <ganti dengan secret rahasia yang kuat, jangan dipakai contoh di bawah>
//    - Tambahkan juga script property kedua:
//      Key   : SPREADSHEET_ID
//      Value : <ID spreadsheet tujuan (lihat URL sheet)>
//    - Klik "Save script properties"
// 4. Deploy -> New deployment -> Type: Web app
//    - Execute as : Me
//    - Who has access : Anyone  <-- WAJIB "Anyone", bukan "Only myself"
//    - Deploy, lalu copy URL https://script.google.com/macros/s/xxxxx/exec
// 5. Buka URL itu di browser: harus tampil "Digitalin Store write-back OK".
//    URL itu menjadi SHEET_WRITE_URL di .env (lokal) dan di env Render.

const SHEET_STOCK = 'STOCK';

// ID spreadsheet diambil dari Script Properties (key SPREADSHEET_ID).
// JANGAN hardcode di file ini: file ter-commit ke git dan STOCK sheet
// (yang berisi kredensial produk) bisa dibaca siapa pun via URL gviz publik.
function getSpreadsheetId() {
  const id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) {
    throw new Error('SPREADSHEET_ID belum di-set di Script Properties');
  }
  return id;
}

// Endpoint yang dipanggil bot.py dengan body:
// {"secret": "...", "mark_sold": [{"stock_id": "S0001", "sold_to": "12345"}]}
// atau
// {"secret": "...", "orders": [{"order_id":"ORD-...", "telegram_id":"123",
//   "username":"","product_id":"D0001","qty":1,"total":10000,
//   "status":"PENDING","payment_id":"","created_at":"...","paid_at":""}]}
// atau
// {"secret": "...", "add_stock": {"product_id": "D0001", "items": ["akun1", "akun2"]}}
function doPost(e) {
  try {
    // Rate limiting sederhana: maks 600 request / 60 detik untuk semua source.
    const cache = CacheService.getScriptCache();
    let n = Number(cache.get('rate') || 0);
    if (n > 600) {
      return HtmlService.createHtmlOutput('RATE_LIMIT');
    }
    cache.put('rate', String(n + 1), 60);

    const body = JSON.parse(e.postData.contents);
    const secret = PropertiesService.getScriptProperties().getProperty('WRITE_SECRET');
    if (!body.secret || body.secret !== secret) {
      return HtmlService.createHtmlOutput('INVALID');
    }
    if (Array.isArray(body.mark_sold)) {
      markRowsSold(body.mark_sold);
      return HtmlService.createHtmlOutput('OK');
    }
    if (Array.isArray(body.orders)) {
      upsertOrders(body.orders);
      return HtmlService.createHtmlOutput('OK');
    }
    if (body.add_stock && typeof body.add_stock === 'object') {
      var result = addStock(body.add_stock);
      return HtmlService.createHtmlOutput('OK:' + JSON.stringify(result));
    }
    return HtmlService.createHtmlOutput('INVALID');
  } catch (err) {
    console.error(err);
    return HtmlService.createHtmlOutput('ERROR');
  }
}

function doGet() {
  return HtmlService.createHtmlOutput('Digitalin Store write-back OK');
}

// Menandai baris stok menjadi SOLD dan mengisi kolom SOLD_TO.
// Asumsi kolom: A=STOCK_ID, B=PRODUCT_ID, C=CONTENT, D=STATUS, E=SOLD_TO
function markRowsSold(rows) {
  const sheet = SpreadsheetApp.openById(getSpreadsheetId()).getSheetByName(SHEET_STOCK);
  const data = sheet.getDataRange().getValues();
  const index = {};
  for (let i = 1; i < data.length; i++) {
    index[String(data[i][0]).trim()] = i + 1;
  }
  for (const r of rows) {
    const sid = String(r.stock_id).trim();
    if (!/^[A-Za-z0-9_-]{1,32}$/.test(sid)) continue;
    const row = index[sid];
    if (!row) continue;
    sheet.getRange(row, 4).setValue('SOLD');
    sheet.getRange(row, 5).setValue(String(r.sold_to).slice(0, 64));
  }
}

// Menambah stok baru ke sheet STOCK.
// Body: {"product_id": "D0001", "items": ["akun1", "akun2"]}
// Mengembalikan: {"added": 2, "stock_ids": ["S0015", "S0016"]}
function addStock(data) {
  const productId = String(data.product_id || '').trim();
  const items = Array.isArray(data.items) ? data.items : [];
  if (!productId || !items.length) {
    return { added: 0, stock_ids: [] };
  }

  const sheet = SpreadsheetApp.openById(getSpreadsheetId()).getSheetByName(SHEET_STOCK);
  const dataRange = sheet.getDataRange();
  const rows = dataRange.getValues();

  // Cari stock ID terakhir (format: SXXXX)
  let maxNum = 0;
  for (let i = 1; i < rows.length; i++) {
    const sid = String(rows[i][0] || '').trim();
    const match = sid.match(/^S(\d+)$/i);
    if (match) {
      const num = parseInt(match[1], 10);
      if (num > maxNum) maxNum = num;
    }
  }

  // Generate stock ID baru
  const addedIds = [];
  for (let i = 0; i < items.length; i++) {
    const content = String(items[i] || '').trim();
    if (!content) continue;
    maxNum++;
    const newId = 'S' + String(maxNum).padStart(4, '0');
    sheet.appendRow([newId, productId, content, 'AVAILABLE', '']);
    addedIds.push(newId);
  }

  return { added: addedIds.length, stock_ids: addedIds };
}

// Mencatat/memperbarui order di sheet ORDERS.
// Asumsi kolom: A=ORDER_ID, B=TELEGRAM_ID, C=USERNAME, D=PRODUCT_ID,
// E=QTY, F=TOTAL, G=STATUS, H=PAYMENT_ID, I=CREATED_AT, J=PAID_AT,
// K=STOCK_IDS (daftar stock_id yang dilepas, dipisah koma; dipakai bot untuk
// rekonstruksi status SOLD setelah redeploy).
// Kalau ORDER_ID sudah ada -> update STATUS/PAYMENT_ID/PAID_AT/STOCK_IDS saja.
// Kalau belum ada -> tambahkan baris baru.
function upsertOrders(rows) {
  const sheet = SpreadsheetApp.openById(getSpreadsheetId()).getSheetByName('ORDERS');
  const data = sheet.getDataRange().getValues();
  const idx = {};
  for (let i = 1; i < data.length; i++) {
    idx[String(data[i][0]).trim()] = i + 1;
  }
  for (const o of rows) {
    const r = idx[String(o.order_id).trim()];
    if (r) {
      if (o.status) sheet.getRange(r, 7).setValue(String(o.status));
      if (o.payment_id) sheet.getRange(r, 8).setValue(String(o.payment_id));
      if (o.paid_at) sheet.getRange(r, 10).setValue(String(o.paid_at));
      if (o.stock_ids) sheet.getRange(r, 11).setValue(String(o.stock_ids));
    } else {
      sheet.appendRow([
        o.order_id || '',
        o.telegram_id || '',
        o.username || '',
        o.product_id || '',
        o.qty || '',
        o.total || '',
        o.status || 'PENDING',
        o.payment_id || '',
        o.created_at || '',
        o.paid_at || '',
        o.stock_ids || ''
      ]);
    }
  }
}

// Alat reset untuk mode uji coba: kembalikan baris SOLD -> AVAILABLE.
// Isi argumen opsional: "S0001,S0002" (dipisah koma). Kosongkan = reset SEMUA baris SOLD.
// Hasilnya ditampilkan di Execution log.
function resetStock(ids) {
  const sheet = SpreadsheetApp.openById(getSpreadsheetId()).getSheetByName(SHEET_STOCK);
  const data = sheet.getDataRange().getValues();
  const only = String(ids || '')
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s);
  let n = 0;
  for (let i = 1; i < data.length; i++) {
    const status = String(data[i][3]).trim().toUpperCase();
    if (status !== 'SOLD') continue;
    const sid = String(data[i][0]).trim();
    if (only.length && !only.includes(sid)) continue;
    sheet.getRange(i + 1, 4).setValue('AVAILABLE');
    sheet.getRange(i + 1, 5).setValue('');
    n++;
  }
  console.log('Reset selesai: ' + n + ' baris direset.');
}

// Fungsi inisialisasi untuk membuat 4 sheet otomatis dengan header lengkap.
// Jalankan fungsi setupSheets() sekali di Apps Script editor.
function setupSheets() {
  const ss = SpreadsheetApp.openById(getSpreadsheetId());
  
  // 1. PRODUCTS
  let shProd = ss.getSheetByName('PRODUCTS');
  if (!shProd) shProd = ss.insertSheet('PRODUCTS');
  if (shProd.getLastRow() === 0) {
    shProd.appendRow(['ID', 'NAME', 'EMOJI', 'PRICE', 'STATUS', 'DESCRIPTION']);
    shProd.appendRow(['P0001', 'Produk Contoh', '📦', 10000, 'ACTIVE', 'Deskripsi produk contoh']);
  }

  // 2. STOCK
  let shStock = ss.getSheetByName('STOCK');
  if (!shStock) shStock = ss.insertSheet('STOCK');
  if (shStock.getLastRow() === 0) {
    shStock.appendRow(['STOCK_ID', 'PRODUCT_ID', 'CONTENT', 'STATUS', 'SOLD_TO']);
    shStock.appendRow(['S0001', 'P0001', 'AKUN-CONTOH-1', 'AVAILABLE', '']);
  }

  // 3. SETTINGS
  let shSet = ss.getSheetByName('SETTINGS');
  if (!shSet) shSet = ss.insertSheet('SETTINGS');
  if (shSet.getLastRow() === 0) {
    shSet.appendRow(['KEY', 'VALUE']);
    shSet.appendRow(['STORE_NAME', 'Norcicle Shop']);
    shSet.appendRow(['BOT_USERNAME', 'NorcicleBot']);
    shSet.appendRow(['ADMIN_USERNAME', 'saldihere']);
    shSet.appendRow(['CURRENCY', 'IDR']);
  }

  // 4. ORDERS
  let shOrders = ss.getSheetByName('ORDERS');
  if (!shOrders) shOrders = ss.insertSheet('ORDERS');
  if (shOrders.getLastRow() === 0) {
    shOrders.appendRow(['ORDER_ID', 'TELEGRAM_ID', 'USERNAME', 'PRODUCT_ID', 'QTY', 'TOTAL', 'STATUS', 'PAYMENT_ID', 'CREATED_AT', 'PAID_AT', 'STOCK_IDS']);
  }

  // Hapus Sheet1 default jika masih ada dan kosong
  const defaultSheet = ss.getSheetByName('Sheet1') || ss.getSheetByName('Sheet 1');
  if (defaultSheet && ss.getSheets().length > 1) {
    try { ss.deleteSheet(defaultSheet); } catch(e) {}
  }

  console.log('Setup 4 sheets selesai!');
}

// Opsional: cek akses ke spreadsheet (cukup jalankan sekali supaya
// editor meminta izin akses Google Sheets). WRITE_SECRET di-set lewat
// Project Settings -> Script properties, BUKAN lewat fungsi ini.
function initProps() {
  SpreadsheetApp.openById(getSpreadsheetId());
  return 'OK';
}
