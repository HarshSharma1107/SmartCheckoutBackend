import logging
import uuid
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from .config import DEFAULT_BRAND_CODE, DEFAULT_BRAND_NAME, JWT_SECRET
from .database import engine, Base
from .errors import ErrorCode
from .routers import (
    brands,
    devices,
    enterprise_customers,
    enterprise_orders,
    enterprise_products,
    health,
    orders,
    products,
    stores,
    webhooks,
)
# from .utils import seed_demo_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SCHEMA_NAME = "ekart_prod"


async def ensure_database_primitives(conn):
    await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}"))
    await conn.execute(
        text(
            f"""
            DO $$
            BEGIN
                CREATE TYPE {SCHEMA_NAME}.order_status_enum AS ENUM (
                    'PENDING',
                    'AWAITING_PAYMENT',
                    'COMPLETED',
                    'FAILED',
                    'CANCELLED',
                    'REFUND_PENDING',
                    'REFUNDED'
                );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    await conn.execute(
        text(
            f"""
            DO $$
            BEGIN
                CREATE TYPE {SCHEMA_NAME}.payment_status_enum AS ENUM (
                    'PENDING',
                    'PAID',
                    'FAILED',
                    'PARTIALLY_REFUNDED',
                    'REFUNDED'
                );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    await conn.execute(
        text(
            f"""
            DO $$
            BEGIN
                CREATE TYPE {SCHEMA_NAME}.payment_method_enum AS ENUM (
                    'CASH',
                    'UPI',
                    'CARD',
                    'WALLET',
                    'BNPL'
                );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    await conn.execute(text(f"CREATE SEQUENCE IF NOT EXISTS {SCHEMA_NAME}.terminal_code_seq START 1"))


async def ensure_default_brand_and_backfill_stores(conn):
    """Patch the pre-existing `stores` table with `brand_id`.

    Must run after `Base.metadata.create_all` so `stores`/`brands` exist.
    On a brand-new database this is a no-op (the ORM model already creates
    `stores.brand_id` correctly); on a database that predates the multi-brand
    feature, this adds the column, backfills existing stores to one default
    brand, and tightens the constraints. No Alembic migration is invoked
    anywhere in this project's actual deploy path (see Procfile/render.yaml),
    so schema evolution happens here, the same way enum types already do.
    """
    default_brand_id = uuid.uuid4()
    now = datetime.utcnow()
    await conn.execute(
        text(
            f"""
            INSERT INTO {SCHEMA_NAME}.brands (brand_id, code, name, is_active, created_at, updated_at)
            VALUES (:brand_id, :code, :name, TRUE, :created_at, :updated_at)
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {
            "brand_id": default_brand_id,
            "code": DEFAULT_BRAND_CODE,
            "name": DEFAULT_BRAND_NAME,
            "created_at": now,
            "updated_at": now,
        },
    )
    result = await conn.execute(
        text(f"SELECT brand_id FROM {SCHEMA_NAME}.brands WHERE code = :code"),
        {"code": DEFAULT_BRAND_CODE},
    )
    default_brand_id = result.scalar_one()

    await conn.execute(text(f"ALTER TABLE {SCHEMA_NAME}.stores ADD COLUMN IF NOT EXISTS brand_id UUID"))
    await conn.execute(
        text(f"UPDATE {SCHEMA_NAME}.stores SET brand_id = :brand_id WHERE brand_id IS NULL"),
        {"brand_id": default_brand_id},
    )
    await conn.execute(text(f"ALTER TABLE {SCHEMA_NAME}.stores ALTER COLUMN brand_id SET NOT NULL"))

    fk_exists = await conn.execute(
        text(
            "SELECT 1 FROM pg_constraint WHERE conname = 'stores_brand_id_fkey' "
            f"AND conrelid = '{SCHEMA_NAME}.stores'::regclass"
        )
    )
    if not fk_exists.scalar():
        await conn.execute(
            text(
                f"ALTER TABLE {SCHEMA_NAME}.stores ADD CONSTRAINT stores_brand_id_fkey "
                f"FOREIGN KEY (brand_id) REFERENCES {SCHEMA_NAME}.brands(brand_id)"
            )
        )

    # Old single-column unique constraint predates multi-brand support and
    # would block two brands from reusing the same short store code.
    await conn.execute(text(f"ALTER TABLE {SCHEMA_NAME}.stores DROP CONSTRAINT IF EXISTS stores_code_key"))

    composite_unique_exists = await conn.execute(
        text(
            "SELECT 1 FROM pg_constraint WHERE conname = 'uq_stores_brand_code' "
            f"AND conrelid = '{SCHEMA_NAME}.stores'::regclass"
        )
    )
    if not composite_unique_exists.scalar():
        await conn.execute(
            text(f"ALTER TABLE {SCHEMA_NAME}.stores ADD CONSTRAINT uq_stores_brand_code UNIQUE (brand_id, code)")
        )


async def ensure_product_expiry_column(conn):
    """Patch the pre-existing `products` table with `expiry_date`.

    Same reasoning as `ensure_default_brand_and_backfill_stores` above:
    `Base.metadata.create_all` only creates missing tables, it never adds
    columns to a table that already exists, and this project doesn't run
    Alembic in its actual deploy path. Nullable, single-value (not
    per-batch) expiry date - a scan of an expired product is rejected in
    routers/products.py.
    """
    await conn.execute(text(f"ALTER TABLE {SCHEMA_NAME}.products ADD COLUMN IF NOT EXISTS expiry_date DATE"))


async def ensure_products_brand_id_nullable(conn):
    """`products.brand_id` is a leftover NOT NULL column from an earlier
    "enterprise" catalog migration that the current, simplified `Product`
    ORM model never maps or sets. Left NOT NULL, it silently breaks any
    product INSERT done through this ORM (both the admin panel's
    create-product endpoint and any future one here). This model doesn't
    support per-brand product catalogs today, so relax the constraint
    instead of mapping a column nothing sets.
    """
    await conn.execute(text(f"ALTER TABLE {SCHEMA_NAME}.products ALTER COLUMN brand_id DROP NOT NULL"))


async def ensure_orders_device_and_idempotency_columns(conn):
    """Patch the pre-existing `orders` table with `device_id` and
    `idempotency_key` (same reasoning as the other `ensure_*` functions in
    this file: `create_all` never adds columns to a table that already
    exists). `device_id` records which authenticated device actually made
    the sale (see routers/orders.py create_order, which now derives the
    order's store/terminal from this device's own assignment rather than
    trusting client input); `idempotency_key` lets a retried/double-tapped
    checkout from the same device replay to the original order instead of
    creating a duplicate.
    """
    await conn.execute(
        text(
            f"ALTER TABLE {SCHEMA_NAME}.orders "
            f"ADD COLUMN IF NOT EXISTS device_id UUID REFERENCES {SCHEMA_NAME}.devices(device_id)"
        )
    )
    await conn.execute(text(f"ALTER TABLE {SCHEMA_NAME}.orders ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(100)"))
    await conn.execute(
        text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_device_idempotency_key "
            f"ON {SCHEMA_NAME}.orders (device_id, idempotency_key) WHERE idempotency_key IS NOT NULL"
        )
    )


async def ensure_indexes(conn):
    """Indexes for the scan/checkout hot path that predate this pass -
    `create_all` only creates indexes declared on tables it's creating for
    the first time, so a live database that already has these tables needs
    them added explicitly, same as the column patches above."""
    await conn.execute(
        text(f"CREATE INDEX IF NOT EXISTS ix_product_barcodes_barcode_value ON {SCHEMA_NAME}.product_barcodes (barcode_value)")
    )
    await conn.execute(
        text(f"CREATE INDEX IF NOT EXISTS ix_inventory_store_product ON {SCHEMA_NAME}.inventory (store_id, product_id)")
    )
    await conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_orders_store_id ON {SCHEMA_NAME}.orders (store_id)"))
    await conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON {SCHEMA_NAME}.order_items (order_id)"))


app = FastAPI(
    title="SmartCheckout API",
    version="1.0.0",
    description="Production-ready retail checkout system"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # Every client here (the checkout app, physical devices) authenticates
    # with a Bearer token, never cookies - allow_credentials=True combined
    # with a wildcard origin was both unnecessary and, per the CORS spec,
    # not something browsers actually honor together.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


_FIELD_ERROR_CODES = {
    "customer_phone": ErrorCode.INVALID_PHONE,
    "customer_email": ErrorCode.INVALID_EMAIL,
}


@app.exception_handler(RequestValidationError)
async def format_validation_errors(request: Request, exc: RequestValidationError):
    """FastAPI's default 422 body is `{"detail": [{"loc": [...], "msg": ...}, ...]}`
    - an array, not the `{code, message}` shape every other error response in
    this API uses. frontend/services/api.js's error parser only understands
    a string or a `{code,message}` object for `detail`, so against that array
    it fell through to a generic "Request failed (HTTP 422)" and silently
    discarded whatever friendly text a validator (e.g. the phone/email
    checks in schemas.py) actually raised. Reshape to the standard envelope
    here, once, so every validation error across the whole API - not just
    phone/email - reaches the user as readable text.
    """
    errors = exc.errors()
    message = "Invalid request."
    code = ErrorCode.VALIDATION_ERROR
    if errors:
        first = errors[0]
        raw_msg = first.get("msg", message)
        # Pydantic v2 prefixes a validator's raised ValueError text with
        # "Value error, " - strip that back off to get the original message.
        message = raw_msg[len("Value error, "):] if raw_msg.startswith("Value error, ") else raw_msg
        loc = first.get("loc") or ()
        field = loc[-1] if loc else None
        code = _FIELD_ERROR_CODES.get(field, ErrorCode.VALIDATION_ERROR)
    return JSONResponse(status_code=422, content={"detail": {"code": str(code), "message": message}})


@app.exception_handler(Exception)
async def log_unhandled_exceptions(request: Request, exc: Exception):
    """Without this, an unhandled exception anywhere in the app falls
    through to Starlette's default handler, which returns a bare
    `Internal Server Error` *plain-text* body (not JSON) and logs nothing
    anywhere the app's own logging config would capture - the client sees
    only "HTTP 500" with zero way to correlate it to a backend log line.
    Log the full traceback with request context here, and return a
    same-shaped JSON error body so callers (see frontend/services/api.js)
    get a parseable {detail} instead of falling into its "non-JSON
    response" fallback path.
    """
    logger.exception(
        "unhandled_exception method=%s path=%s client=%s",
        request.method, request.url.path, request.client.host if request.client else None,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# NOTE: enterprise_orders and orders both mount under /api/v1/orders.
# They no longer share any exact (path, method) pair - enterprise's
# create/get order routes live under /api/v1/orders/cart(/{order_id}) -
# so inclusion order here no longer affects which handler wins. Keep it
# that way: two routers claiming the identical path+method is a silent
# bug (Starlette dispatches to whichever was registered first, but
# FastAPI's generated OpenAPI docs display whichever was registered
# last, so the docs and the actual runtime behavior can disagree - this
# is exactly what caused the "Missing device bearer token" checkout bug).
app.include_router(health.router)
app.include_router(devices.router)
app.include_router(brands.router)
app.include_router(enterprise_products.router)
app.include_router(enterprise_orders.router)
app.include_router(enterprise_customers.router)
app.include_router(webhooks.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(stores.router)


@app.get("/api/v1/ready")
async def ready():
    return {"status": "ready", "checks": {"api": "ok"}}

@app.on_event("startup")
async def startup():
    if JWT_SECRET == "dev-insecure-secret-change-me":
        logger.critical(
            "JWT_SECRET is unset and using the insecure development default - "
            "every device/session token is forgeable. Set a real JWT_SECRET "
            "env var before this instance handles production traffic."
        )
    async with engine.begin() as conn:
        await ensure_database_primitives(conn)
        await conn.run_sync(Base.metadata.create_all)
        await ensure_default_brand_and_backfill_stores(conn)
        await ensure_product_expiry_column(conn)
        await ensure_products_brand_id_nullable(conn)
        await ensure_orders_device_and_idempotency_columns(conn)
        await ensure_indexes(conn)
    # await seed_demo_data()
