# Production Implementation Pass

This document tracks the implementation response to the production Smart eKart specification.

## Added In This Pass

- Alembic scaffolding and enterprise foundation migration:
  - `brands`
  - `stores`
  - `terminals`
  - `devices`
  - `device_terminal_assignments`
  - `customers`
  - `orders`
  - `order_items`
  - `audit_logs`
  - `device_heartbeats`
  - `whatsapp_messages`
- Pydantic v2 request/response schemas in `backend/schemas_enterprise.py`.
- Consistent response helpers and error codes.
- Device APIs:
  - `POST /api/v1/devices/register`
  - `POST /api/v1/devices/activate`
  - `POST /api/v1/devices/{device_id}/heartbeat`
  - `GET /api/v1/devices/{device_id}/config`
- Admin device APIs:
  - `POST /api/v1/admin/devices/{device_id}/assign`
  - `POST /api/v1/admin/devices/{device_id}/revoke`
- Enterprise product barcode API:
  - `GET /api/v1/products/barcode/{barcode_value}`
- Enterprise order APIs:
  - `POST /api/v1/orders`
  - `POST /api/v1/orders/{order_id}/items`
  - `DELETE /api/v1/orders/{order_id}/items/{item_id}`
  - `PATCH /api/v1/orders/{order_id}/items/{item_id}`
  - `POST /api/v1/orders/{order_id}/checkout`
  - `POST /api/v1/orders/{order_id}/payment-confirmation`
  - `GET /api/v1/orders/{order_id}`
  - `GET /api/v1/orders/{order_id}/invoice`
  - `POST /api/v1/orders/{order_id}/resend-invoice`
- Inventory reservation behavior:
  - Add item reserves inventory with row lock.
  - Delete item releases reservation and recalculates totals.
  - Patch item adjusts reservation delta and recalculates totals.
  - Payment confirmation commits reserved inventory to sale transactions.
- `inventory_transactions` and `idempotency_keys` tables in the foundation migration.
- `X-Idempotency-Key` support for add-item scanner retries.
- Customer/reporting/webhook route scaffolds.
- Celery app and task modules for invoice and WhatsApp pipelines.
- GST invoice Jinja2 template.
- WhatsApp Cloud API template payload builder.
- MQTT topic helpers.
- Expo kiosk-side Zustand stores for cart, device, connectivity, and customer state.
- SQLite offline cache schema and helpers.
- Docker Compose for API, PostgreSQL, Redis, Mosquitto, Celery, and Grafana.

## Still Required Before Production

- Real mTLS client certificate verification.
- Real JWT signing/verification and revocation.
- Payment gateway integration and HMAC verification.
- Meta WhatsApp media upload/send and signature verification.
- S3/MinIO upload for invoice PDFs.
- Full delete/update item reservation logic for edge cases like partial refunds and post-payment returns.
- Alembic reconciliation with the existing prototype ORM tables.
- Admin users/RBAC tables.
- Product catalog enterprise extensions: suppliers, warehouses, product batches.
- Prometheus metrics and Grafana dashboards.
- MQTT TLS and per-device ACLs.
- Full React Native kiosk screen implementation.

## Compatibility Note

The current prototype ORM already defines `stores`, `customers`, `orders`, and `order_items` with a different shape. The enterprise migration is intended as the production target schema. Before applying it to a database that has already been created by `Base.metadata.create_all`, create a dedicated migration path or rebuild the development database.
