# Testing

## Current State

No automated tests were found in the repository.

## Recommended Backend Tests

Use `pytest` with async support.

Core coverage:

- `GET /health` returns service metadata.
- `GET /api/v1/stores` returns only active stores.
- `GET /api/v1/products` returns only active products.
- `GET /api/v1/scan/{barcode}`:
  - found barcode
  - unknown barcode
  - inactive barcode
  - discontinued product
  - store-specific inventory
  - invalid `store_id` behavior
- `POST /api/v1/orders`:
  - valid order
  - invalid store ID
  - missing store
  - empty items
  - invalid product ID
  - inactive product
  - insufficient stock
  - customer reuse by phone
  - inventory decrement
  - GST totals
- `GET /api/v1/orders/{order_id}`:
  - valid order
  - invalid UUID
  - missing order

## Recommended Frontend Tests

Use React Native Testing Library where practical.

Core coverage:

- Cart reducer behavior.
- Quantity caps at available stock.
- Customer and store validation.
- API error display on Home, Scanner, and Checkout.
- Checkout payload construction.

## Manual Test Checklist

Backend:

```text
GET /health
GET /api/v1/stores
GET /api/v1/products
GET /api/v1/scan/{known_barcode}?store_id={store_id}
POST /api/v1/orders
GET /api/v1/orders/{order_id}
```

Frontend:

- App starts in Expo.
- Store list loads.
- Camera permission prompt works.
- Known barcode displays product.
- Out-of-stock product cannot be added.
- Cart quantity controls work.
- Checkout creates order and shows receipt.

## Regression Risks

- GST calculation mismatch between frontend preview and backend receipt.
- Inventory race conditions during concurrent checkout.
- Silent invalid `store_id` fallback during scan.
- Enum bootstrap failure in fresh PostgreSQL database.
