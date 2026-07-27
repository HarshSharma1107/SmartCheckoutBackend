import uuid
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .config import DEFAULT_BRAND_CODE, DEFAULT_BRAND_NAME
from .database import engine, Base
from .routers import (
    admin_auth,
    admin_catalog,
    admin_devices,
    admin_terminals,
    brands,
    devices,
    enterprise_customers,
    enterprise_orders,
    enterprise_products,
    health,
    orders,
    products,
    reports,
    stores,
    webhooks,
)
# from .utils import seed_demo_data

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


app = FastAPI(
    title="SmartCheckout API",
    version="1.0.0",
    description="Production-ready retail checkout system"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(admin_devices.router)
app.include_router(admin_terminals.router)
app.include_router(admin_auth.router)
app.include_router(admin_catalog.router)
app.include_router(brands.router)
app.include_router(enterprise_products.router)
app.include_router(enterprise_orders.router)
app.include_router(enterprise_customers.router)
app.include_router(reports.router)
app.include_router(webhooks.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(stores.router)


@app.get("/api/v1/ready")
async def ready():
    return {"status": "ready", "checks": {"api": "ok"}}

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await ensure_database_primitives(conn)
        await conn.run_sync(Base.metadata.create_all)
        await ensure_default_brand_and_backfill_stores(conn)
    # await seed_demo_data()
