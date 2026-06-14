<sqlalchemy.ext.asyncio.engine.AsyncEngine object at 0x0000027526975ED0>
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 20260612_0001

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE EXTENSION IF NOT EXISTS "ltree";

CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE SCHEMA IF NOT EXISTS ekart_prod;

CREATE TABLE IF NOT EXISTS ekart_prod.brands (
            brand_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            logo_url TEXT,
            whatsapp_phone_number_id VARCHAR(50),
            whatsapp_access_token TEXT,
            invoice_template_id VARCHAR(50),
            gstin VARCHAR(15),
            support_email VARCHAR(200),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

CREATE TABLE IF NOT EXISTS ekart_prod.stores (
            store_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brand_id UUID NOT NULL REFERENCES ekart_prod.brands(brand_id),
            code VARCHAR(30) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            address_line1 TEXT,
            city VARCHAR(100),
            state VARCHAR(100),
            pincode VARCHAR(10),
            gstin VARCHAR(15),
            store_type VARCHAR(50) DEFAULT 'SUPERMARKET',
            timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

CREATE INDEX IF NOT EXISTS idx_stores_brand ON ekart_prod.stores(brand_id);

CREATE TABLE IF NOT EXISTS ekart_prod.terminals (
            terminal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            store_id UUID NOT NULL REFERENCES ekart_prod.stores(store_id),
            terminal_code VARCHAR(50) NOT NULL,
            label VARCHAR(100),
            terminal_type VARCHAR(30) DEFAULT 'SMART_CART',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(store_id, terminal_code)
        );

CREATE INDEX IF NOT EXISTS idx_terminals_store ON ekart_prod.terminals(store_id);

CREATE TABLE IF NOT EXISTS ekart_prod.devices (
            device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            device_serial VARCHAR(100) UNIQUE NOT NULL,
            hardware_mac MACADDR,
            cpu_serial VARCHAR(64),
            hostname VARCHAR(100),
            model VARCHAR(100) DEFAULT 'Raspberry Pi 4 Model B',
            os_version VARCHAR(50),
            app_version VARCHAR(20),
            status VARCHAR(20) DEFAULT 'UNPROVISIONED',
            activation_code VARCHAR(8),
            activation_code_expires_at TIMESTAMPTZ,
            certificate_fingerprint TEXT,
            last_seen_at TIMESTAMPTZ,
            last_ip INET,
            firmware_version VARCHAR(20),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

CREATE INDEX IF NOT EXISTS idx_devices_status ON ekart_prod.devices(status);

CREATE INDEX IF NOT EXISTS idx_devices_serial ON ekart_prod.devices(device_serial);

CREATE TABLE IF NOT EXISTS ekart_prod.device_terminal_assignments (
            assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            device_id UUID NOT NULL REFERENCES ekart_prod.devices(device_id),
            terminal_id UUID NOT NULL REFERENCES ekart_prod.terminals(terminal_id),
            assigned_by UUID NOT NULL,
            assigned_at TIMESTAMPTZ DEFAULT NOW(),
            revoked_at TIMESTAMPTZ,
            revoke_reason TEXT,
            is_active BOOLEAN GENERATED ALWAYS AS (revoked_at IS NULL) STORED
        );

CREATE UNIQUE INDEX IF NOT EXISTS idx_dta_unique_active_device
        ON ekart_prod.device_terminal_assignments(device_id)
        WHERE revoked_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_dta_unique_active_terminal
        ON ekart_prod.device_terminal_assignments(terminal_id)
        WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_dta_device ON ekart_prod.device_terminal_assignments(device_id);

CREATE TABLE IF NOT EXISTS ekart_prod.customers (
            customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brand_id UUID NOT NULL REFERENCES ekart_prod.brands(brand_id),
            phone VARCHAR(20) NOT NULL,
            phone_verified BOOLEAN DEFAULT FALSE,
            name VARCHAR(200),
            email VARCHAR(200),
            whatsapp_opt_in BOOLEAN DEFAULT FALSE,
            loyalty_points INT DEFAULT 0,
            tier VARCHAR(20) DEFAULT 'STANDARD',
            date_of_birth DATE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(brand_id, phone)
        );

CREATE INDEX IF NOT EXISTS idx_customers_brand_phone ON ekart_prod.customers(brand_id, phone);

CREATE TABLE IF NOT EXISTS ekart_prod.orders (
            order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_number VARCHAR(60) UNIQUE NOT NULL,
            brand_id UUID NOT NULL REFERENCES ekart_prod.brands(brand_id),
            store_id UUID NOT NULL REFERENCES ekart_prod.stores(store_id),
            terminal_id UUID NOT NULL REFERENCES ekart_prod.terminals(terminal_id),
            device_id UUID NOT NULL REFERENCES ekart_prod.devices(device_id),
            customer_id UUID REFERENCES ekart_prod.customers(customer_id),
            session_token VARCHAR(64),
            status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
            subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
            discount_total NUMERIC(12,2) DEFAULT 0,
            coupon_code VARCHAR(50),
            loyalty_points_redeemed INT DEFAULT 0,
            cgst_total NUMERIC(12,2) DEFAULT 0,
            sgst_total NUMERIC(12,2) DEFAULT 0,
            round_off NUMERIC(5,2) DEFAULT 0,
            grand_total NUMERIC(12,2) NOT NULL DEFAULT 0,
            payment_method VARCHAR(30),
            payment_gateway VARCHAR(30),
            payment_ref VARCHAR(100),
            payment_status VARCHAR(30) DEFAULT 'PENDING',
            paid_at TIMESTAMPTZ,
            invoice_number VARCHAR(60) UNIQUE,
            invoice_pdf_url TEXT,
            invoice_sent_at TIMESTAMPTZ,
            whatsapp_msg_id VARCHAR(100),
            started_at TIMESTAMPTZ DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            abandoned_at TIMESTAMPTZ,
            metadata JSONB DEFAULT '{}'::JSONB
        );

CREATE INDEX IF NOT EXISTS idx_orders_store ON ekart_prod.orders(store_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_terminal ON ekart_prod.orders(terminal_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON ekart_prod.orders(customer_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_status ON ekart_prod.orders(status);

CREATE INDEX IF NOT EXISTS idx_orders_number ON ekart_prod.orders(order_number);

CREATE TABLE IF NOT EXISTS ekart_prod.order_items (
            item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id UUID NOT NULL REFERENCES ekart_prod.orders(order_id) ON DELETE CASCADE,
            product_id UUID NOT NULL,
            barcode_scanned VARCHAR(50),
            batch_id UUID,
            quantity INT NOT NULL CHECK (quantity > 0),
            unit_price NUMERIC(10,2) NOT NULL,
            mrp NUMERIC(10,2) NOT NULL,
            discount_amount NUMERIC(10,2) DEFAULT 0,
            cgst_rate NUMERIC(5,2) DEFAULT 0,
            cgst_amount NUMERIC(10,2) DEFAULT 0,
            sgst_rate NUMERIC(5,2) DEFAULT 0,
            sgst_amount NUMERIC(10,2) DEFAULT 0,
            line_total NUMERIC(12,2) NOT NULL,
            scanned_at TIMESTAMPTZ DEFAULT NOW()
        );

CREATE INDEX IF NOT EXISTS idx_order_items_order ON ekart_prod.order_items(order_id);

CREATE INDEX IF NOT EXISTS idx_order_items_product ON ekart_prod.order_items(product_id);

CREATE TABLE IF NOT EXISTS ekart_prod.inventory_transactions (
            transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID NOT NULL,
            store_id UUID NOT NULL REFERENCES ekart_prod.stores(store_id),
            order_id UUID REFERENCES ekart_prod.orders(order_id),
            order_item_id UUID,
            transaction_type VARCHAR(40) NOT NULL,
            quantity_delta INT NOT NULL,
            qty_on_hand_after INT,
            qty_reserved_after INT,
            reason TEXT,
            actor_type VARCHAR(20) DEFAULT 'system',
            actor_id UUID,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

CREATE INDEX IF NOT EXISTS idx_inventory_txn_product_store
        ON ekart_prod.inventory_transactions(product_id, store_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_inventory_txn_order
        ON ekart_prod.inventory_transactions(order_id, created_at DESC);

CREATE TABLE IF NOT EXISTS ekart_prod.idempotency_keys (
            idempotency_key VARCHAR(128) PRIMARY KEY,
            scope VARCHAR(80) NOT NULL,
            request_hash TEXT,
            response JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL
        );

CREATE INDEX IF NOT EXISTS idx_idempotency_expires
        ON ekart_prod.idempotency_keys(expires_at);

CREATE TABLE IF NOT EXISTS ekart_prod.audit_logs (
            log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(80) NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            entity_id UUID NOT NULL,
            brand_id UUID REFERENCES ekart_prod.brands(brand_id),
            store_id UUID REFERENCES ekart_prod.stores(store_id),
            actor_id UUID,
            actor_type VARCHAR(20),
            payload JSONB,
            ip_address INET,
            occurred_at TIMESTAMPTZ DEFAULT NOW()
        );

CREATE INDEX IF NOT EXISTS idx_audit_entity
        ON ekart_prod.audit_logs(entity_type, entity_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_brand ON ekart_prod.audit_logs(brand_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS ekart_prod.device_heartbeats (
            heartbeat_id UUID DEFAULT gen_random_uuid(),
            device_id UUID NOT NULL REFERENCES ekart_prod.devices(device_id),
            terminal_id UUID REFERENCES ekart_prod.terminals(terminal_id),
            store_id UUID REFERENCES ekart_prod.stores(store_id),
            ip_address INET,
            signal_strength INT,
            cpu_temp NUMERIC(5,2),
            ram_used_mb INT,
            disk_used_pct INT,
            app_version VARCHAR(20),
            uptime_seconds BIGINT,
            recorded_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (heartbeat_id, recorded_at)
        ) PARTITION BY RANGE (recorded_at);

CREATE TABLE IF NOT EXISTS ekart_prod.whatsapp_messages (
            message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brand_id UUID NOT NULL REFERENCES ekart_prod.brands(brand_id),
            order_id UUID REFERENCES ekart_prod.orders(order_id),
            customer_id UUID REFERENCES ekart_prod.customers(customer_id),
            phone_to VARCHAR(20) NOT NULL,
            template_name VARCHAR(100) NOT NULL,
            wa_message_id VARCHAR(100),
            status VARCHAR(20) DEFAULT 'PENDING',
            error_code VARCHAR(20),
            error_message TEXT,
            payload JSONB,
            sent_at TIMESTAMPTZ,
            delivered_at TIMESTAMPTZ,
            read_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

CREATE INDEX IF NOT EXISTS idx_wa_order ON ekart_prod.whatsapp_messages(order_id);

CREATE INDEX IF NOT EXISTS idx_wa_status ON ekart_prod.whatsapp_messages(status, created_at DESC);

INSERT INTO alembic_version (version_num) VALUES ('20260612_0001') RETURNING alembic_version.version_num;

COMMIT;

