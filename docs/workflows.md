# Workflows

## Customer Shopping Workflow

1. Customer opens app.
2. Home screen checks `/health`.
3. Home screen loads `/api/v1/stores`.
4. Customer enters name and phone.
5. Customer selects a store.
6. Customer starts scanning.

## Barcode Scan Workflow

1. App requests camera permission.
2. `CameraView` detects barcode.
3. Scanner debounce prevents duplicate rapid processing.
4. App calls `/api/v1/scan/{barcode}` with current `store_id`.
5. Backend checks active barcode.
6. Backend checks active, non-discontinued product.
7. Backend checks inventory and category.
8. App shows product card or error card.
9. Customer adds product to cart or dismisses result.

## Cart Workflow

1. Product is added with quantity `1`.
2. If product already exists, quantity increments up to `qty_available`.
3. Customer can increase, decrease, or remove product.
4. Totals are derived in `CartContext`.

## Checkout Workflow

1. Customer opens cart and proceeds to checkout.
2. Customer selects payment method.
3. Frontend submits `POST /api/v1/orders`.
4. Backend validates customer, store, products, and stock.
5. Backend creates or reuses customer by phone.
6. Backend creates completed, paid order.
7. Backend creates order items.
8. Backend decrements inventory.
9. Backend returns receipt.
10. Frontend clears cart and displays receipt.

## ETL Jobs

No ETL jobs were found.

## Cron Jobs

No cron jobs were found.

## Pipelines

No CI/CD or data pipelines were found.

## External Integrations

Current external integrations are development/runtime dependencies only:

- PostgreSQL
- Expo camera APIs

No payment gateway, analytics, loyalty, message queue, or inventory sync integration is currently implemented.
