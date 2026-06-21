from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .database import engine, Base
from .routers import (
    admin_devices,
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

# Include enterprise routers before legacy routers where paths overlap.
app.include_router(health.router)
app.include_router(devices.router)
app.include_router(admin_devices.router)
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
    # await seed_demo_data()
