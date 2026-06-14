# AI Agent Prompt: Build Smart eKart Admin Panel

You are a senior full-stack engineer. Build a production-ready admin panel for the Smart eKart project.

## Project Context

Repository:

```text
SmartCheckoutBackend/
  backend/      FastAPI backend
  frontend/     Expo React Native customer/cart app
  docs/         project documentation
```

Important docs to read first:

```text
CLAUDE.md
README.md
docs/project-overview.md
docs/architecture.md
docs/database.md
docs/api.md
docs/security.md
docs/workflows.md
docs/enterprise-iot-architecture.md
docs/production-implementation.md
```

Current backend stack:

```text
FastAPI
PostgreSQL
SQLAlchemy async
Alembic
Redis/Celery scaffolding
MQTT scaffolding
```

Current production mapping target:

```text
Brand -> Store -> Terminal -> Device assignment
```

More precisely:

```text
brands
  -> stores
      -> terminals
          <- device_terminal_assignments
              <- devices
```

The customer/cart app should not allow customer store switching in production. Store must be derived from:

```text
device -> active assignment -> terminal -> store -> brand
```

## Existing Backend Tables

The enterprise migration is:

```text
migrations/versions/20260612_0001_enterprise_foundation.py
```

It creates:

```text
ekart_prod.brands
ekart_prod.stores
ekart_prod.terminals
ekart_prod.devices
ekart_prod.device_terminal_assignments
ekart_prod.customers
ekart_prod.orders
ekart_prod.order_items
ekart_prod.inventory_transactions
ekart_prod.audit_logs
ekart_prod.device_heartbeats
ekart_prod.whatsapp_messages
ekart_prod.idempotency_keys
```

Existing device/admin backend routes:

```text
POST /api/v1/devices/register
POST /api/v1/devices/activate
POST /api/v1/devices/{device_id}/heartbeat
GET  /api/v1/devices/{device_id}/config

POST /api/v1/admin/devices/{device_id}/assign
POST /api/v1/admin/devices/{device_id}/revoke
```

Current admin auth is a placeholder:

```text
Authorization: Bearer test-admin-token
X-Admin-Id: 00000000-0000-0000-0000-000000000000
```

Do not pretend this is production auth. Add real admin auth only if requested; otherwise keep the placeholder compatible with the current backend.

## Goal

Build an admin panel that lets store/admin users manage:

1. Brands
2. Stores
3. Terminals
4. Devices/kiosks
5. Device-terminal assignments
6. Activation codes
7. Revoke/reassign workflows
8. Device heartbeat/status
9. Audit history

The main business workflow:

```text
Admin creates/selects brand
Admin creates/selects store
Admin creates terminal for store
Device registers through backend
Admin sees unprovisioned device
Admin assigns device to terminal
Admin generates activation code
Technician enters activation code on cart
Device becomes ACTIVE
Admin can later revoke or reassign
```

## Required Admin Panel Features

### Dashboard

Show:

- total brands
- total stores
- active terminals
- active devices
- unassigned devices
- offline devices
- devices in maintenance
- recent audit events

### Brands Page

CRUD:

- create brand
- edit brand
- activate/deactivate brand

Fields:

```text
brand_id
name
slug
logo_url
gstin
support_email
whatsapp_phone_number_id
invoice_template_id
is_active
created_at
```

Do not show raw WhatsApp access token after save.

### Stores Page

CRUD:

- create store under brand
- edit store
- activate/deactivate store

Fields:

```text
store_id
brand_id
code
name
address_line1
city
state
pincode
gstin
store_type
timezone
is_active
created_at
```

### Terminals Page

CRUD:

- create terminal under store
- edit terminal label/type/status
- deactivate terminal

Fields:

```text
terminal_id
store_id
terminal_code
label
terminal_type
is_active
created_at
```

Important explanation:

```text
terminal_code = stable business code, e.g. TERM-DEL-001
label = human-readable location/name, e.g. Billing Counter 3 or Smart Cart 12
```

### Devices Page

Show list:

```text
device_id
device_serial
hostname
model
os_version
app_version
status
last_seen_at
last_ip
firmware_version
active assignment if any
```

Filters:

- UNPROVISIONED
- PROVISIONED
- ACTIVE
- SUSPENDED
- DECOMMISSIONED
- Unassigned
- Offline

### Device Detail Page

Show:

- device profile
- active assignment
- assignment history
- heartbeat history
- audit log

Actions:

- assign to terminal
- revoke current assignment
- generate activation code
- suspend device
- mark maintenance

### Assignment Workflow

Admin chooses:

```text
brand -> store -> terminal -> device
```

Rules:

- a device can have only one active assignment
- a terminal can have only one active device
- assigning a device should revoke its old active assignment first
- old assignments must remain in history
- orders must never be rewritten

Use existing API if available:

```http
POST /api/v1/admin/devices/{device_id}/assign
```

Request:

```json
{
  "terminal_id": "uuid",
  "notes": "Initial assignment"
}
```

Headers:

```http
Authorization: Bearer test-admin-token
X-Admin-Id: 00000000-0000-0000-0000-000000000000
```

### Revoke Workflow

Use existing API:

```http
POST /api/v1/admin/devices/{device_id}/revoke
```

Request:

```json
{
  "reason": "Moved to another store"
}
```

After revoke:

- current assignment should have `revoked_at`
- device status should become `PROVISIONED`
- audit log should be written

### Activation Code Workflow

Current backend does not yet have:

```text
POST /api/v1/admin/devices/{device_id}/activation-code
```

Implement this endpoint if building backend too.

Expected behavior:

- generate random 8-character code
- save to `devices.activation_code`
- save expiry in `devices.activation_code_expires_at`
- default expiry: 15 minutes
- write audit log `DEVICE_ACTIVATION_CODE_GENERATED`

Suggested request:

```http
POST /api/v1/admin/devices/{device_id}/activation-code
```

```json
{
  "expires_in_minutes": 15
}
```

Suggested response:

```json
{
  "success": true,
  "data": {
    "device_id": "uuid",
    "activation_code": "A7K9P2Q1",
    "expires_at": "2026-06-15T10:30:00Z"
  },
  "error": null
}
```

## Required Backend Admin APIs If Missing

If direct table access is not acceptable, add FastAPI admin routes:

```text
GET    /api/v1/admin/brands
POST   /api/v1/admin/brands
PATCH  /api/v1/admin/brands/{brand_id}

GET    /api/v1/admin/stores
POST   /api/v1/admin/stores
PATCH  /api/v1/admin/stores/{store_id}

GET    /api/v1/admin/terminals
POST   /api/v1/admin/terminals
PATCH  /api/v1/admin/terminals/{terminal_id}

GET    /api/v1/admin/devices
GET    /api/v1/admin/devices/{device_id}
POST   /api/v1/admin/devices/{device_id}/assign
POST   /api/v1/admin/devices/{device_id}/revoke
POST   /api/v1/admin/devices/{device_id}/activation-code

GET    /api/v1/admin/audit-logs
GET    /api/v1/admin/device-heartbeats
```

All responses should use:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

Errors:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Readable message"
  }
}
```

## Suggested Frontend Stack

If creating a separate web admin:

```text
React + Vite
TypeScript preferred
TanStack Query
React Hook Form
Zod validation
Tailwind or simple CSS modules
```

If staying inside current repo:

```text
admin/
  package.json
  src/
    api/
    pages/
    components/
```

Admin UI should be dense and operational, not a marketing landing page.

## UX Requirements

Use pages:

```text
/dashboard
/brands
/stores
/terminals
/devices
/devices/:device_id
/assignments
/audit
```

Important UI states:

- loading
- empty table
- API error
- validation error
- success toast
- confirm revoke modal
- assignment conflict message

## Manual SQL Fallback

If admin panel is not ready, manual bootstrap can be done with SQL:

```sql
SELECT store_id, code, name FROM ekart_prod.stores;

INSERT INTO ekart_prod.terminals (
  store_id,
  terminal_code,
  label,
  terminal_type,
  is_active
)
VALUES (
  '<store_id>',
  'TERM-001',
  'Smart Cart 1',
  'SMART_CART',
  true
)
RETURNING terminal_id;
```

Register device through API:

```http
POST /api/v1/devices/register
```

Assign device:

```sql
INSERT INTO ekart_prod.device_terminal_assignments (
  device_id,
  terminal_id,
  assigned_by
)
VALUES (
  '<device_id>',
  '<terminal_id>',
  '00000000-0000-0000-0000-000000000000'
);
```

Generate activation code manually:

```sql
UPDATE ekart_prod.devices
SET activation_code = '12345678',
    activation_code_expires_at = NOW() + INTERVAL '15 minutes'
WHERE device_id = '<device_id>';
```

Activate device:

```http
POST /api/v1/devices/activate
```

```json
{
  "device_id": "<device_id>",
  "activation_code": "12345678"
}
```

## Acceptance Criteria

The admin panel is complete when:

1. Admin can create/select brand and store.
2. Admin can create a terminal under a store.
3. Admin can see registered devices.
4. Admin can assign a device to a terminal.
5. Admin can revoke/reassign without deleting history.
6. Admin can generate activation code.
7. Device activation returns brand/store/terminal config.
8. Device detail page shows heartbeat and assignment history.
9. Audit events are visible.
10. Customer cart app can lock store based on assigned device config or `EXPO_PUBLIC_LOCKED_STORE_ID`.

## Important Warning

Do not use phone IP, laptop IP, MAC address, or Wi-Fi network as store identity.

Correct production identity:

```text
device certificate / device_id -> assignment -> terminal -> store
```

