# SmartCheckout

SmartCheckout is a barcode-scanning retail checkout system.

- Backend: FastAPI, async SQLAlchemy, PostgreSQL
- Frontend: React Native with Expo and `expo-camera`
- Core flow: select customer/store, scan barcode, add products to cart, checkout, show receipt

## Repository Structure

```text
backend/
  main.py              # FastAPI app setup, CORS, router registration
  config.py            # Environment configuration
  database.py          # Async SQLAlchemy engine/session dependency
  models.py            # PostgreSQL ORM models under ekart_prod schema
  schemas.py           # Pydantic request/response models
  utils.py             # Order number and response formatting helpers
  routers/
    health.py
    products.py
    stores.py
    orders.py
frontend/
  App.js               # React Navigation stack and CartProvider
  services/
    api.js             # Backend API client
    CartContext.js     # Shared cart/customer/store state
  screens/
    HomeScreen.js
    ScannerScreen.js
    CartScreen.js
    CheckoutScreen.js
docs/
  architecture.md
  database.md
  api.md
  frontend.md
  backend.md
  deployment.md
  security.md
  testing.md
  workflows.md
  integrations.md
  coding-standards.md
  troubleshooting.md
  project-overview.md
```

## Backend Setup

Create a PostgreSQL database and ensure the backend can connect to it.

```bash
pip install -r requirements.txt
```

Set the database URL:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/smartcheckout
```

Run the API from the repository root:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Run enterprise migrations:

```bash
alembic upgrade head
```

Verify:

```text
GET http://localhost:8000/health
GET http://localhost:8000/api/v1/stores
GET http://localhost:8000/api/v1/products
```

## Frontend Setup

```bash
cd frontend
npm install
npm start
```

Set the backend URL for the app:

```bash
EXPO_PUBLIC_API_URL=http://<your-machine-lan-ip>:8000
```

Use a LAN IP for physical devices. `localhost` usually only works from the same machine.

## Production Foundation

The repo now includes a first-pass Smart eKart production foundation:

- Alembic migration scaffold in `migrations/`
- Enterprise device/admin/order/customer/reporting/webhook routers under `backend/routers/`
- Celery app and invoice/WhatsApp task scaffolds under `backend/tasks/`
- GST invoice template in `backend/templates/invoice.html`
- MQTT/offline cache/Zustand kiosk scaffolds under `frontend/services/`
- Local infrastructure in `docker-compose.yml`

Start local infrastructure:

```bash
docker compose up --build
```

To run backend and Expo frontend together for phone testing:

```bash
copy .env.example .env
```

Edit `.env` and set `LAN_IP` to your laptop IP on the same Wi-Fi as your phone.

```bash
docker compose up --build api frontend
```

Open Expo Go on your phone and scan the QR code printed by the `frontend` container logs. The app will call:

```text
http://<LAN_IP>:8000
```

Do not use `api:8000` or `localhost:8000` inside the phone app; those only work inside Docker or on the laptop itself.

To lock a cart/kiosk to one store, set this in `frontend/.env`:

```env
EXPO_PUBLIC_LOCKED_STORE_ID=<store_uuid>
```

Get the value from:

```text
GET /api/v1/stores
```

When this is set, the app auto-selects that store and hides the store picker from customers.

## Raspberry Pi Provisioning Summary

1. Flash Raspberry Pi OS and install the kiosk app/agent.
2. First boot generates a device fingerprint and CSR.
3. Agent calls `POST /api/v1/devices/register`.
4. Admin assigns device to a terminal through `POST /api/v1/admin/devices/{device_id}/assign`.
5. Cart activates with `POST /api/v1/devices/activate`.
6. Runtime calls use device bearer token now; production must add mTLS plus signed JWT validation.

## Environment Variables

Backend:

- `DATABASE_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `MQTT_BROKER_URL`
- `S3_BUCKET_INVOICES`
- `WHATSAPP_GRAPH_VERSION`

Frontend:

- `EXPO_PUBLIC_API_URL`

## API Summary

- `GET /health`
- `GET /api/v1/stores`
- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}?store_id={uuid}`
- `GET /api/v1/scan/{barcode}?store_id={uuid}`
- `POST /api/v1/orders`
- `GET /api/v1/orders/{order_id}`

See `docs/api.md` for request and response contracts.
See `docs/production-implementation.md` for the production foundation status.

## Business Rules

- Products must be active and not discontinued to scan successfully.
- Available inventory is `qty_on_hand - qty_reserved`, floored at zero.
- Cart quantities are capped by scanned product availability.
- Checkout validates store, products, item quantities, and stock.
- Orders are currently marked `COMPLETED` and `PAID` immediately.
- Payment methods are labels only; no payment gateway is integrated yet.

## Project Knowledge

This repo uses a documentation-first project memory system. Start with:

1. `CLAUDE.md`
2. `docs/project-overview.md`
3. `docs/architecture.md`
4. `docs/database.md`
5. `docs/api.md`
6. `docs/security.md`

Update the relevant docs whenever architecture, business rules, API contracts, database design, workflows, or deployment behavior changes.

## Current Gaps

- No automated tests are present.
- No database migration tool is configured.
- No authentication or authorization is implemented.
- CORS is currently permissive.
- Payment is simulated.
- Inventory ledger/audit tables are not implemented.
