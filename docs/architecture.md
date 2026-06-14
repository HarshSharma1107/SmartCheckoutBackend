# Architecture

## High-Level Design

SmartCheckout is a two-tier application:

- Mobile client: React Native Expo app for customer/store entry, scanning, cart, checkout, and receipt.
- API server: FastAPI service that owns product, barcode, store, inventory, customer, and order data.
- Database: PostgreSQL using async SQLAlchemy ORM models under schema `ekart_prod`.

```text
Expo app
  -> frontend/services/api.js
  -> FastAPI routers
  -> async SQLAlchemy session
  -> PostgreSQL ekart_prod schema
```

## Backend Modules

- `backend/main.py`: creates FastAPI app, configures permissive CORS, mounts routers, creates tables on startup.
- `backend/database.py`: creates async engine/session factory and dependency-managed sessions.
- `backend/models.py`: SQLAlchemy models and enum definitions.
- `backend/schemas.py`: Pydantic API schemas.
- `backend/utils.py`: order number generation and response formatting.
- `backend/routers/health.py`: `/health`.
- `backend/routers/products.py`: product list, product detail, barcode scan.
- `backend/routers/stores.py`: active store list.
- `backend/routers/orders.py`: create order and fetch order.

## Frontend Modules

- `frontend/App.js`: stack navigation and `CartProvider`.
- `frontend/services/api.js`: fetch wrapper and API functions.
- `frontend/services/CartContext.js`: global cart/customer/store state and derived totals.
- `frontend/screens/HomeScreen.js`: customer and store selection.
- `frontend/screens/ScannerScreen.js`: camera permission, barcode detection, scan result.
- `frontend/screens/CartScreen.js`: cart review and quantity controls.
- `frontend/screens/CheckoutScreen.js`: payment method, order creation, receipt display.

## Service Communication

The frontend calls the backend through `BASE_URL` in `frontend/services/api.js`.

Default:

```text
process.env.EXPO_PUBLIC_API_URL || http://192.168.1.100:8000
```

The phone or emulator must be able to reach that host. `localhost` usually only works from the same machine, not a physical phone.

## Data Flow

Barcode scan:

```text
CameraView detects barcode
  -> scanBarcode(barcode, storeId)
  -> GET /api/v1/scan/{barcode}?store_id={storeId}
  -> product_barcodes
  -> products
  -> inventory
  -> categories
  -> product response with qty_available and GST rates
```

Checkout:

```text
CartContext items/customer/store
  -> CheckoutScreen builds payload
  -> POST /api/v1/orders
  -> validate store
  -> find or create customer by phone
  -> validate products and inventory
  -> calculate subtotal, CGST, SGST, grand total
  -> create order and order_items
  -> decrement inventory.qty_on_hand
  -> return formatted receipt
```

## Business Flow

The application currently treats payment as accepted at order creation time. The backend sets:

- `Order.status = COMPLETED`
- `Order.payment_status = PAID`
- `Order.completed_at = now`

This means payment methods are labels only until a real payment provider is integrated.

## Deployment Flow

Local development requires:

1. PostgreSQL database reachable through `DATABASE_URL`.
2. Backend run with Uvicorn.
3. Frontend run with Expo.
4. Frontend `EXPO_PUBLIC_API_URL` or hardcoded fallback pointing to the backend host reachable by the device.

No Docker, Kubernetes, or CI/CD configuration was found.

## ER Diagram References

No generated ER diagram file exists yet. The relationships are documented in `docs/database.md`; generate an ERD from `backend/models.py` or PostgreSQL metadata when the schema stabilizes.
