# Troubleshooting

## Backend Cannot Connect to Database

Check:

- `DATABASE_URL` is set.
- URL uses `postgresql+asyncpg://`.
- Database host and port are reachable.
- Database user has privileges.
- Schema `ekart_prod` and required enum types exist.

## Startup Fails on Enum Types

The ORM enums use `create_type=False`, so PostgreSQL enum types may need to be created manually before `Base.metadata.create_all`.

Required enum names:

- `ekart_prod.order_status_enum`
- `ekart_prod.payment_status_enum`
- `ekart_prod.payment_method_enum`

## Frontend Cannot Reach Backend

Check:

- Backend is running on `0.0.0.0:8000`.
- Phone/emulator can reach the backend machine.
- `EXPO_PUBLIC_API_URL` points to the machine LAN IP, not `localhost`.
- Firewall allows inbound traffic to port `8000`.

## Store List Is Empty

Check:

- `/health` responds.
- `/api/v1/stores` returns data.
- `stores.is_active` is true for expected stores.
- Database seed data exists.

## Barcode Not Found

Check:

- Barcode exists in `product_barcodes.barcode_value`.
- Barcode row has `is_active = true`.
- Product exists, has `is_active = true`, and `is_discontinued = false`.
- Scanner is reading the exact barcode value expected.

## Product Shows Out of Stock

Check:

- Inventory row exists for product and selected store.
- `qty_on_hand > qty_reserved`.
- `store_id` passed by frontend is the intended store.

## Checkout Fails With Insufficient Stock

The backend rechecks stock at checkout time. A product that was available during scan can fail checkout if inventory changed before order creation.

Check:

- Current inventory row for `(product_id, store_id)`.
- Cart quantity.
- Concurrent orders.

## Receipt Totals Differ From Cart Preview

The backend is the source of truth for order totals. Compare:

- Product `selling_price` in frontend scan response.
- Product `mrp`, `cgst_rate`, and `sgst_rate` in database.
- Frontend calculation in `CartContext`.
- Backend calculation in `backend/routers/orders.py`.
