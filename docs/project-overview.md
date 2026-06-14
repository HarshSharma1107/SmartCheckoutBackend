# Project Overview

SmartCheckout is a barcode-scanning retail checkout application. It lets a shopper or cashier choose a store, enter customer details, scan product barcodes, manage a cart, select a payment method, submit an order, and view a digital receipt.

## Stack

- Backend: FastAPI, async SQLAlchemy 2.x, Pydantic v2, PostgreSQL through `asyncpg`
- Frontend: React Native, Expo, `expo-camera`, React Navigation
- Database schema: `ekart_prod`
- Configuration: `.env` files with `DATABASE_URL` for backend and `EXPO_PUBLIC_API_URL` for frontend

## Repository Layout

```text
backend/
  config.py
  database.py
  main.py
  models.py
  schemas.py
  utils.py
  routers/
    health.py
    orders.py
    products.py
    stores.py
frontend/
  App.js
  app.json
  package.json
  app/
  screens/
  services/
docs/
README.md
requirements.txt
```

## Core User Journey

1. Open the mobile app.
2. Enter customer name and phone.
3. Select an active store loaded from the backend.
4. Grant camera permission.
5. Scan a barcode.
6. Add an in-stock product to cart.
7. Adjust quantities up to available stock.
8. Select payment method.
9. Create an order.
10. View receipt.

## Current Implementation Status

Implemented:

- Store listing
- Product listing and product lookup
- Barcode scanning lookup
- Cart state and quantity controls
- Order creation
- Order receipt response
- Basic health endpoint

Not yet implemented:

- Authentication and cashier identity
- Real payment gateway
- Inventory ledger transactions
- Database migrations
- Automated tests
- Product image handling
- Offline sync
