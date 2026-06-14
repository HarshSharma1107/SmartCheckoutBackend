import * as SQLite from "expo-sqlite";

const db = SQLite.openDatabaseSync("smart_ekart.db");

export function initOfflineCache() {
  db.execSync(`
    CREATE TABLE IF NOT EXISTS device_config (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS product_cache (
      barcode TEXT NOT NULL,
      store_id TEXT NOT NULL,
      payload TEXT NOT NULL,
      expires_at TEXT NOT NULL,
      PRIMARY KEY (barcode, store_id)
    );
    CREATE TABLE IF NOT EXISTS offline_outbox (
      outbox_id TEXT PRIMARY KEY,
      event_type TEXT NOT NULL,
      payload TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'PENDING',
      attempts INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
  `);
}

export function cacheProduct({ barcode, storeId, payload, ttlSeconds = 60 }) {
  const expiresAt = new Date(Date.now() + ttlSeconds * 1000).toISOString();
  db.runSync(
    `INSERT OR REPLACE INTO product_cache (barcode, store_id, payload, expires_at)
     VALUES (?, ?, ?, ?)`,
    [barcode, storeId, JSON.stringify(payload), expiresAt]
  );
}

export function getCachedProduct(barcode, storeId) {
  const row = db.getFirstSync(
    `SELECT payload FROM product_cache
     WHERE barcode = ? AND store_id = ? AND expires_at > ?`,
    [barcode, storeId, new Date().toISOString()]
  );
  return row ? JSON.parse(row.payload) : null;
}

export function enqueueOfflineEvent(eventType, payload) {
  const now = new Date().toISOString();
  const id = `${eventType}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  db.runSync(
    `INSERT INTO offline_outbox (outbox_id, event_type, payload, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?)`,
    [id, eventType, JSON.stringify(payload), now, now]
  );
  return id;
}
