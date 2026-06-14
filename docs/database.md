# Database

## Database Technology

The backend uses PostgreSQL through SQLAlchemy async ORM and `asyncpg`.

Configuration:

- Environment variable: `DATABASE_URL`
- SQLAlchemy engine: `create_async_engine(DATABASE_URL, pool_pre_ping=True)`
- Schema name in models: `ekart_prod`

Tables are created on FastAPI startup with:

```python
Base.metadata.create_all
```

No migration framework was found.

## Tables

### `ekart_prod.categories`

- `category_id`: UUID primary key
- `name`: string, required
- `parent_id`: nullable self-reference to `categories.category_id`
- `is_active`: boolean

Relationships:

- One category has many products.
- Category can reference a parent category.

### `ekart_prod.products`

- `product_id`: UUID primary key
- `sku`: unique string, required
- `name`: string, required
- `description`: nullable text
- `brand`: nullable string
- `category_id`: foreign key to categories
- `mrp`: numeric(10,2), required
- `cost_price`: nullable numeric(10,2)
- `cgst_rate`: numeric(5,2)
- `sgst_rate`: numeric(5,2)
- `is_active`: boolean
- `is_discontinued`: boolean
- `created_at`, `updated_at`: datetime

Relationships:

- Many products belong to one category.
- One product has many barcodes.
- One product has many inventory rows.
- One product can appear in many order items.

### `ekart_prod.product_barcodes`

- `barcode_id`: UUID primary key
- `product_id`: foreign key to products
- `barcode_value`: string, required
- `barcode_type`: string, default `EAN13`
- `is_primary`: boolean
- `is_active`: boolean
- `created_at`: datetime

Current model does not declare a unique constraint on `barcode_value`; the scan endpoint reads the first active match.

### `ekart_prod.stores`

- `store_id`: UUID primary key
- `code`: unique string, required
- `name`: string, required
- `city`: nullable string
- `is_active`: boolean

Relationships:

- One store has many inventory rows.
- Orders reference a store.

### `ekart_prod.inventory`

- `inventory_id`: UUID primary key
- `product_id`: foreign key to products
- `store_id`: foreign key to stores
- `qty_on_hand`: integer
- `qty_reserved`: integer
- `last_updated`: datetime

Computed property:

```text
qty_available = max(0, qty_on_hand - qty_reserved)
```

Current model does not declare a uniqueness constraint for `(product_id, store_id)`.

### `ekart_prod.customers`

- `customer_id`: UUID primary key
- `name`: string, required
- `phone`: string, required
- `email`: string, required by model, currently inserted as empty string
- `date_of_birth`: datetime default
- `loyalty_points`: integer
- `tier`: string, default `STANDARD`
- `is_active`: boolean
- `deleted_at`: nullable datetime
- `created_at`, `updated_at`: datetime

Current checkout lookup reuses customers by phone. The model does not declare `phone` unique.

### `ekart_prod.orders`

- `order_id`: UUID primary key
- `order_number`: unique string, required
- `customer_id`: nullable foreign key to customers
- `store_id`: foreign key to stores
- `status`: enum `order_status_enum`
- `subtotal`, `discount_total`, `cgst_total`, `sgst_total`, `round_off`, `grand_total`: numeric(12,2)
- `payment_method`: enum `payment_method_enum`
- `payment_status`: enum `payment_status_enum`
- `payment_ref`: nullable string
- `cashier_id`: nullable UUID
- `terminal_id`: nullable string
- `ordered_at`, `completed_at`, `updated_at`: datetime

### `ekart_prod.order_items`

- `item_id`: UUID primary key
- `order_id`: foreign key to orders
- `product_id`: foreign key to products
- `quantity`: integer, required
- `unit_price`, `mrp`, `discount_amount`: numeric
- `cgst_rate`, `cgst_amount`, `sgst_rate`, `sgst_amount`: numeric
- `line_total`: numeric(12,2), required
- `created_at`: datetime

### `ekart_prod.inventory_transactions` Target Table

The enterprise foundation migration adds an inventory transaction ledger for reservation and sale events:

- `transaction_id`: UUID primary key
- `product_id`: UUID
- `store_id`: foreign key to stores
- `order_id`: nullable foreign key to orders
- `order_item_id`: nullable UUID
- `transaction_type`: string such as `RESERVE`, `RELEASE`, `RESERVATION_ADJUSTMENT`, `SALE`
- `quantity_delta`: signed integer
- `qty_on_hand_after`: integer snapshot
- `qty_reserved_after`: integer snapshot
- `reason`: text
- `actor_type`, `actor_id`
- `created_at`

The current order API writes this ledger when cart items reserve/release inventory and when payment confirmation commits a sale.

### `ekart_prod.idempotency_keys` Target Table

The enterprise foundation migration adds request idempotency storage:

- `idempotency_key`: primary key
- `scope`: operation scope, for example `order-item-add:{order_id}`
- `request_hash`: reserved for stricter duplicate validation
- `response`: JSONB response envelope
- `created_at`
- `expires_at`

`POST /api/v1/orders/{order_id}/items` reads `X-Idempotency-Key` to avoid duplicate scanner inserts during rapid retries.

## Enums

The ORM references PostgreSQL enums with `create_type=False`:

- `order_status_enum`: `PENDING`, `AWAITING_PAYMENT`, `COMPLETED`, `FAILED`, `CANCELLED`, `REFUND_PENDING`, `REFUNDED`
- `payment_status_enum`: `PENDING`, `PAID`, `FAILED`, `PARTIALLY_REFUNDED`, `REFUNDED`
- `payment_method_enum`: `CASH`, `UPI`, `CARD`, `WALLET`, `BNPL`

Because `create_type=False` is set, these enum types must already exist in PostgreSQL before table creation unless created elsewhere.

## Query Patterns

- Scan by `product_barcodes.barcode_value` and `is_active`.
- Product detail by `products.product_id` and `is_active`.
- Product list by `products.is_active`.
- Store list by `stores.is_active`.
- Order creation validates inventory by `(product_id, store_id)`.
- Order retrieval eager-loads customer and order item products.

## Recommended Indexes

Confirm these exist in the database:

- `product_barcodes(barcode_value)` preferably unique for active barcode values.
- `inventory(product_id, store_id)` preferably unique.
- `products(sku)` unique already represented in ORM.
- `stores(code)` unique already represented in ORM.
- `customers(phone)` for checkout lookup.
- `orders(order_number)` unique already represented in ORM.
- `order_items(order_id)`.

## Migration History

No Alembic or migration directory was found. Startup table creation is convenient for prototypes but should be replaced by controlled migrations before production.
