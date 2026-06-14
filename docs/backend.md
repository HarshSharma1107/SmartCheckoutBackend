# Backend

## Technology

- FastAPI
- SQLAlchemy async ORM
- Pydantic v2
- PostgreSQL with `asyncpg`
- `python-dotenv`

Dependencies are currently listed in root `requirements.txt`.

## Application Entry

`backend/main.py` creates the FastAPI app:

- Title: `SmartCheckout API`
- Version: `1.0.0`
- CORS: allows all origins, credentials, methods, and headers
- Routers: health, products, orders, stores
- Startup: creates ORM tables

## Database Session Pattern

`backend/database.py` creates an async session factory and exposes `get_db()`.

`get_db()`:

- yields an `AsyncSession`
- commits after successful request
- rolls back on exception

Some handlers also call `commit()` explicitly. This currently works, but transaction ownership should be standardized.

## Routers

### Health

`GET /health` returns service status.

### Products

Product routes handle:

- Barcode scan
- Product detail
- Product list

They query barcode, product, inventory, and category models directly.

### Stores

Store route lists active stores.

### Orders

Order routes handle:

- Creating orders
- Fetching orders by ID

Order creation validates stock before writing records, calculates GST, creates/reuses customers by phone, and decrements inventory.

## Utilities

`generate_order_number()` format:

```text
ORD-YYYYMMDD-XXXXXX
```

`format_order()` converts ORM order objects into `OrderResponse`.

## Business Rules

- Products must be active.
- Discontinued products cannot be scanned successfully.
- Inventory availability is based on `qty_on_hand - qty_reserved`.
- Checkout rejects insufficient stock with `409`.
- Checkout immediately completes payment.
- Discounts and round-off are modeled but not actively applied.

## Known Backend Gaps

- No authentication.
- No authorization.
- No migrations.
- No tests.
- No inventory transaction ledger.
- CORS is fully open.
- Invalid `store_id` on scan/product lookup is silently ignored instead of rejected.
- `customers` class name is lowercase, unlike other ORM model classes.
- PostgreSQL enum types use `create_type=False`; database bootstrap must create them.
- `print(engine)` runs at import time in `database.py`.
