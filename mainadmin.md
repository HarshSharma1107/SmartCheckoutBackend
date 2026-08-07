# SmartCheckout Admin Panel — Build Spec

> **⚠️ Superseded (2026-07-30):** The architecture described below (admin
> panel calls this backend directly, "does not get its own backend project")
> is no longer current. All `/api/v1/admin/...` and `/api/v1/reports/...`
> routes have been moved out of this repo into a dedicated FastAPI service at
> `C:\Users\ASUS\OneDrive\Desktop\smartChekoutAdmin\SmartCheckoutAdmin\backend`
> (package `admin_backend`), which shares this repo's database but is
> deployed and run separately. This repo now only serves the client-facing
> checkout app and physical devices. See that service's own `README.md` for
> current admin API docs. The rest of this file is kept for historical
> context only.

This file is the single source of truth for building the SmartCheckout admin
panel. It is written to be **self-contained** — usable from a completely
empty directory with no other project files present — so every URL, path,
and example payload below is explicit rather than "see the source file."

## 0. Reference URLs & Locations (read this first)

| What | Value |
|---|---|
| Backend production URL (use this as the API base URL) | `https://smartcheckoutbackend.onrender.com` |
| Backend source repo (GitHub) | `https://github.com/HarshSharma1107/SmartCheckoutBackend.git` |
| Backend source repo (local machine, absolute path) | `C:\Users\ASUS\OneDrive\Desktop\Ekart\SmartCheckoutBackend` |
| Backend framework / language | FastAPI, Python 3, async SQLAlchemy 2.0 + asyncpg |
| Database | PostgreSQL, schema name `ekart_prod` |
| Existing customer-facing checkout app (do NOT modify) | `frontend/` folder inside the backend repo above — a separate Expo app |
| This admin panel | A brand-new, separate Expo project. Put it in its own empty directory (per the user's plan) — it only needs network access to the backend URL above, it does not need to live inside the backend repo. |

**Important for whoever builds this:** section 6 below ("Backend Gaps")
requires adding new endpoints to the *existing* FastAPI backend, which
lives in the repo path/URL above — not in this new admin-panel directory.
If you (the AI building this) have filesystem access to that local path,
edit the backend files there directly, in the same style as the existing
routers. If you only have this markdown file and no access to that path,
say so explicitly before inventing backend code from scratch — clone
`https://github.com/HarshSharma1107/SmartCheckoutBackend.git` first so you
are editing the real project instead of guessing its structure.

## 1. Purpose

One admin panel, usable on **web and mobile**, for store/brand admins and a
super admin to:

- Log in with role-based access (`SUPER_ADMIN` vs `STORE_ADMIN`)
- Manage brands and stores
- Provision physical checkout devices: view pairing requests, assign a
  device to a store (auto-creates/reuses a terminal), deactivate devices
- View and deactivate terminals
- Manage products, categories, and barcodes (catalogue)
- View and adjust per-store inventory
- View sales/device-health reports (backend currently returns stub data —
  see Gaps section)
- (SUPER_ADMIN only) create further admin accounts

This is a **separate app** from the existing customer-facing checkout app.
Do not modify the existing `frontend/` app — build the admin panel as its
own project in its own directory, talking to the same backend over HTTPS.

## 2. Tech Stack (must match)

- **Frontend**: React Native + **Expo** (same major stack as the existing
  checkout app — Expo SDK 54, `expo-router` for file-based routing), built
  so it runs as:
  - a mobile app (Android/iOS) via Expo Go / EAS build, **and**
  - a web app via `expo start --web` (React Native Web) — this is why Expo
    was chosen over plain React Native: one codebase, two targets.
  - State: React Context or Zustand.
  - Key packages the existing app already uses, for consistency:
    `expo` ~54.x, `expo-router` ~6.x, `expo-secure-store` ~15.x,
    `@react-native-async-storage/async-storage`, `react` 19.1.0,
    `react-native` 0.81.x, `react-dom` 19.1.0 (needed for `expo start --web`).
- **Backend**: FastAPI (Python), already implemented at the repo path/URL
  in section 0. The admin panel is a pure HTTP API consumer — it does
  **not** get its own backend project. New endpoints (see Gaps) get added
  to that same FastAPI app, in the same style as its existing routers.
- **Database**: PostgreSQL, schema `ekart_prod`. No new tables are needed
  except where noted in Gaps.

## 3. Backend Conventions (apply to any new endpoint)

- **Base URL**: `https://smartcheckoutbackend.onrender.com` in production.
  For local dev against a backend run with `uvicorn backend.main:app
  --reload`, use `http://localhost:8000` (or the machine's LAN IP if
  testing from a phone on the same network, e.g. `http://192.168.1.100:8000`).
- **Response envelope**: every admin/terminal-provisioning endpoint returns:
  ```json
  {"success": true,  "data": { ... }, "error": null}
  {"success": false, "data": null,    "error": {"code": "FORBIDDEN", "message": "Not authorized for this brand"}}
  ```
  The admin panel's API client must unwrap `data` on success and read
  `error.message` on failure. Some errors instead come back as FastAPI's
  default shape `{"detail": "..."}` or `{"detail": {"code","message"}}` —
  handle all three shapes so a thrown error always has readable text.
- **Auth**: `Authorization: Bearer <token>` header on every admin-prefixed
  endpoint.
  - Admin login (`POST /api/v1/admin/auth/login`) returns a JWT
    (`access_token`, `expires_in` seconds — currently `3600` = 1 hour, no
    refresh endpoint exists for admins yet, so re-login on 401/expiry).
  - JWT claims include `role` (`SUPER_ADMIN` | `STORE_ADMIN`) and `brand_id`
    (`null` for `SUPER_ADMIN`, a specific brand UUID for `STORE_ADMIN`) —
    but don't decode the JWT client-side for this; the login response
    already returns `role`/`brand_id`/`admin_id` in plain JSON.
  - `STORE_ADMIN` accounts are scoped to one brand: any endpoint that
    filters/creates by `brand_id` restricts a `STORE_ADMIN` to their own
    brand server-side (403 otherwise) — the UI should also hide/disable
    cross-brand actions for `STORE_ADMIN`, but the backend is the real
    enforcement.
- **CORS** is currently wide open (`allow_origins=["*"]`) on the backend,
  so the web build can call the API directly from the browser with no
  proxy needed.

## 4. Existing Backend API Reference (verified — already implemented, ready to call today)

All paths below are relative to the base URL in section 3
(e.g. `https://smartcheckoutbackend.onrender.com/api/v1/admin/auth/login`).

### 4.1 Admin Auth

**`POST /api/v1/admin/auth/bootstrap`** — no auth required.
One-time only: works only while the `admin_users` table is empty, to
create the first `SUPER_ADMIN`. Always 409s once any admin exists.
```json
// Request
{"email": "owner@example.com", "password": "at-least-8-chars", "full_name": "Harsh Sharma", "brand_id": null}
// Response (data)
{"access_token": "eyJ...", "expires_in": 3600, "admin_id": "uuid", "role": "SUPER_ADMIN", "brand_id": null}
```

**`POST /api/v1/admin/auth/login`** — no auth required.
```json
// Request
{"email": "owner@example.com", "password": "at-least-8-chars"}
// Response (data) — same shape as bootstrap
{"access_token": "eyJ...", "expires_in": 3600, "admin_id": "uuid", "role": "SUPER_ADMIN", "brand_id": null}
```

**`POST /api/v1/admin/auth/users`** — Bearer token, SUPER_ADMIN only.
Creates another admin account. If `brand_id` is given, the new account is
`STORE_ADMIN` scoped to it; otherwise it's another `SUPER_ADMIN`.
```json
// Request
{"email": "store1@example.com", "password": "at-least-8-chars", "full_name": "Store One Manager", "brand_id": "brand-uuid-here"}
// Response (data)
{"admin_id": "uuid", "role": "STORE_ADMIN"}
```

### 4.2 Brands & Stores

**`GET /api/v1/brands`** — no auth. Public list of active brands.
```json
// Response (data)
[{"brand_id": "uuid", "code": "DEFAULT", "name": "Default Brand", "logo_url": null, "is_active": true}]
```

**`POST /api/v1/admin/brands`** — Bearer, SUPER_ADMIN only. 409 if `code` exists.
```json
// Request
{"code": "ACME", "name": "Acme Retail", "logo_url": null}
// Response (data)
{"brand_id": "uuid", "code": "ACME", "name": "Acme Retail", "logo_url": null, "is_active": true}
```

**`GET /api/v1/admin/stores?brand_id=<optional-uuid>`** — Bearer.
`SUPER_ADMIN` sees all (or filtered by `brand_id` query param);
`STORE_ADMIN` is forced to their own brand regardless of the query param.
```json
// Response (data)
[{"store_id": "uuid", "brand_id": "uuid", "brand_name": "Acme Retail", "code": "STORE1", "name": "Acme MG Road", "city": "Bengaluru", "is_active": true}]
```

**`POST /api/v1/admin/stores`** — Bearer. `STORE_ADMIN` may only create for
their own `brand_id` (403 otherwise). 409 if the store code already exists
for that brand.
```json
// Request
{"brand_id": "uuid", "code": "STORE1", "name": "Acme MG Road", "city": "Bengaluru"}
// Response (data) — same shape as the list item above
```

### 4.3 Device Provisioning

This is the core "assign stores to devices" flow the whole system is
built around. Devices are phones running the checkout app; terminals are
logical checkout lanes at a store; a device is assigned to a **terminal**
(not directly to a store) — this is what lets a broken/reinstalled phone
be swapped without losing that terminal's order history.

**`GET /api/v1/admin/devices?status=unassigned|assigned|offline|disabled`**
(status filter optional) — Bearer. `STORE_ADMIN` sees only devices whose
current store is in their brand.
```json
// Response (data)
[{
  "device_id": "uuid",
  "device_name": "realme 8 Pro",
  "manufacturer": "realme",
  "model": "RMX3081",
  "os_version": "13",
  "app_version": "1.0.0",
  "status": "ASSIGNED",
  "terminal_code": "SC-000123",
  "store_name": "Acme MG Road",
  "last_seen_at": "2026-07-24T18:45:16.349Z",
  "is_online": true,
  "registered_at": "2026-07-18T20:41:12.508Z"
}]
```
`is_online` = last heartbeat within 90 seconds; a device drops to the
`offline` bucket if no heartbeat in 5 minutes; it never leaves `ASSIGNED`
status just for going offline.

**`POST /api/v1/admin/devices/{device_id}/assign-store`** — Bearer.
Requires the **pairing code** currently shown on the physical device's
pending screen (a 6-digit code, 15-minute TTL, generated by the device's
own `/api/v1/devices/register` call). Auto-creates a terminal for the
store if none exists yet, otherwise reuses the store's first active
terminal — so re-assigning a reinstalled/replacement phone to the *same*
store lands it back on the same terminal, preserving its order history.
```json
// Request
{"store_id": "uuid", "pairing_code": "482913", "notes": "Replacement for lost phone"}
// Response (data)
{
  "assignment_id": "uuid",
  "terminal_id": "uuid",
  "terminal_code": "SC-000123",
  "assigned_at": "2026-07-25T10:09:15.65Z",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 900
}
```
The `access_token`/`refresh_token` in the response are tokens *for the
device*, not the admin — the admin UI can just ignore them; they exist so
this same call could hand them back to the physical device if ever needed.

**`POST /api/v1/admin/devices/{device_id}/deactivate`** — Bearer.
```json
// Request
{"reason": "Phone lost"}
// Response (data)
{"deactivated": true}
```
Revokes the device's active assignment, sets its status to `DISABLED`,
and kills its refresh token so it can't silently regain access.

**`POST /api/v1/admin/terminals/{terminal_id}/deactivate`** — Bearer.
```json
// Request
{"reason": "Lane permanently closed"}
// Response (data)
{"deactivated": true}
```
Retires a terminal; any device holding it is freed back to `UNASSIGNED`
(not disabled — the phone itself is fine) so it naturally re-enters the
pairing-code flow next time it registers.

### 4.4 Reports (Bearer required on all four; all currently return stub/empty data — build the UI, expect empty results until Gaps §6 is done)

- `GET /api/v1/reports/sales?store_id=&date_from=&date_to=&group_by=terminal|product|hour`
  → `{"store_id","date_from","date_to","group_by","rows": []}`
- `GET /api/v1/reports/device-health?brand_id=&store_id=`
  → `{"brand_id","store_id","devices": []}`
- `GET /api/v1/reports/customer/{customer_id}/purchases`
  → `{"customer_id","orders": []}`
- `GET /api/v1/reports/terminal/{terminal_id}/summary`
  → `{"terminal_id","summary": {}}`

### 4.5 Read-only, no-auth endpoints (not for admin catalogue management, just noting they exist)

- `GET /api/v1/products` → `{"count": n, "products": [{"product_id","sku","name","mrp"}]}`
- `GET /api/v1/products/{product_id}?store_id=` → full product + stock detail
- `GET /api/v1/orders/{order_id}` → full order detail
- `GET /api/v1/stores?brand_id=` → public active store list

There is **no create/edit endpoint for products today** — see Gaps §6.

## 5. Data Model Reference (Postgres schema `ekart_prod`)

- **Brand**: `brand_id (uuid pk), code (unique str), name, logo_url, is_active, created_at, updated_at`
- **Store**: `store_id (uuid pk), brand_id→Brand, code (unique per brand), name, city, is_active`
- **Category**: `category_id (uuid pk), name, parent_id→self (nullable), is_active`
- **Product**: `product_id (uuid pk), sku (unique), name, description, brand (free-text string, unrelated to the Brand table), category_id→Category, mrp (numeric 10,2), cost_price (numeric 10,2, nullable), cgst_rate (numeric 5,2), sgst_rate (numeric 5,2), is_active, is_discontinued, created_at, updated_at`
- **ProductBarcode**: `barcode_id (uuid pk), product_id→Product, barcode_value, barcode_type (default "EAN13"), is_primary, is_active, created_at`
- **Inventory**: `inventory_id (uuid pk), product_id→Product, store_id→Store, qty_on_hand (int), qty_reserved (int), last_updated`. Available quantity is always **derived**: `max(0, qty_on_hand - qty_reserved)` — never let the UI write to "available" directly, only to `qty_on_hand`.
- **Device**: `device_id (uuid pk), local_install_id (uuid, unique when set), device_type, device_name, manufacturer, model, os_version, app_version, platform, status (UNASSIGNED|ASSIGNED|DISABLED), pairing_code, pairing_code_expires_at, refresh_token_hash, last_seen_at, created_at, updated_at`
- **Terminal**: `terminal_id (uuid pk), store_id→Store, terminal_code (unique per store), label, is_active, deactivated_at, created_at`
- **DeviceTerminalAssignment**: `assignment_id (uuid pk), device_id→Device, terminal_id→Terminal, assigned_by (admin_id, nullable), assigned_at, revoked_at (nullable), revoke_reason (nullable)` — at most one active (`revoked_at IS NULL`) row per device and per terminal at any time.
- **AdminUser**: `admin_id (uuid pk), email (unique), password_hash, full_name, role (SUPER_ADMIN|STORE_ADMIN), brand_id→Brand (null for SUPER_ADMIN), is_active, last_login_at, created_at`
- **customers**: `customer_id (uuid pk), name, phone, email, date_of_birth, loyalty_points, tier, is_active, ...` (used by checkout, not admin-managed today)

## 6. Backend Gaps — build these into the backend repo (section 0 path/URL) before or alongside the UI

The existing backend has **no product/inventory/category CRUD** despite
the models existing (confirmed by reading every router file — only
read-only, no-auth product endpoints exist). Whatever admin tool was used
to add products before now was not part of this backend, so it must be
rebuilt here.

Add a new router `backend/routers/admin_catalog.py` in the backend repo,
mounted in `backend/main.py`, following the exact conventions already used
in `backend/routers/admin_devices.py` and `backend/routers/brands.py`:
`AdminPrincipal = Depends(require_admin)` for auth, `require_brand_access`
where relevant, the `ok(...)` response envelope from `backend/api_response.py`,
new Pydantic request/response models alongside the existing ones in
`backend/schemas_terminal.py` (or a new `backend/schemas_catalog.py`).

New endpoints to add (all under `/api/v1/admin/...`, Bearer auth):

- `GET /api/v1/admin/categories` — list categories.
- `POST /api/v1/admin/categories` — create `{name, parent_id?}`.
- `GET /api/v1/admin/products?category_id=&search=` — list/search products.
  Note: products are not brand-scoped today (no `brand_id` column on
  Product) — this endpoint is open to any admin role; flag to the user if
  per-brand catalogue isolation turns out to matter later.
- `POST /api/v1/admin/products` — create `{sku, name, description?, brand?, category_id, mrp, cost_price?, cgst_rate, sgst_rate}`.
- `PATCH /api/v1/admin/products/{product_id}` — edit any of the above, or `is_active`/`is_discontinued`.
- `POST /api/v1/admin/products/{product_id}/barcodes` — add `{barcode_value, barcode_type?, is_primary?}`.
- `DELETE /api/v1/admin/products/{product_id}/barcodes/{barcode_id}` — or soft-delete via `is_active=false`.
- `GET /api/v1/admin/inventory?store_id=` — list inventory rows for a store, joined with product name/SKU.
- `PATCH /api/v1/admin/inventory/{inventory_id}` — adjust stock. Prefer a
  `{"delta": <int>}` body (add/remove stock) over an absolute `qty_on_hand`
  overwrite, and lock the row with `with_for_update()` — same pattern
  `admin_devices.py`'s `assign_store` already uses for concurrency safety.
- `GET /api/v1/admin/terminals?store_id=` — list terminals for a store
  (today terminals can only be deactivated by ID, never listed).
- `GET /api/v1/admin/admins` — list admin accounts (creation already
  exists via `POST /api/v1/admin/auth/users`, but nothing lists them).

Do **not** touch `enterprise_products.py`, `enterprise_orders.py`,
`enterprise_customers.py`, Celery, MQTT, or S3 config in that repo — those
are unused scaffolding for a larger future architecture, out of scope here.

## 7. Admin Panel Screens

1. **Login** — email/password → `POST /api/v1/admin/auth/login`, store the
   JWT (SecureStore on native, web-safe fallback on Expo web — see §8),
   keep `role`/`brand_id`/`admin_id` from the plain JSON response.
2. **Dashboard** — quick counts: devices by status, stores, low-stock
   products (once the inventory endpoint exists). Simple cards, nothing
   fancy.
3. **Devices** — list with status filter tabs (Unassigned / Assigned /
   Offline / Disabled), online indicator dot. Tapping an unassigned device
   opens an "Assign to store" form: pick store (dropdown from
   `GET /api/v1/admin/stores`), enter the pairing code shown on the
   physical device's pending screen, optional notes. Assigned devices show
   a "Deactivate" action with a required reason field.
4. **Terminals** — list per store (once the list endpoint exists), each
   showing its current device (if any) and a "Deactivate terminal" action.
5. **Stores** — list (filtered to brand for `STORE_ADMIN`), "Create store"
   form (`brand_id` locked to the admin's own brand for `STORE_ADMIN`).
6. **Brands** — `SUPER_ADMIN` only. List + "Create brand" form.
7. **Products** — list/search, "Add product" form, edit existing (price,
   tax rates, active/discontinued toggle), manage barcodes per product.
8. **Inventory** — pick a store, see its stock table (SKU, name, on-hand,
   reserved, available), inline "adjust stock" action.
9. **Admin Users** — `SUPER_ADMIN` only. List existing admins, "Create
   admin" form (email/password/full name, optional brand → STORE_ADMIN).
10. **Reports** — Sales / Device Health tabs calling the existing stub
    endpoints; render "no data yet" gracefully since they return empty
    arrays/objects today.

## 8. Non-functional Requirements

- **Token storage**: use `expo-secure-store` on native and fall back to
  `localStorage` (or `AsyncStorage`, which is web-safe) when
  `Platform.OS === "web"`, since `expo-secure-store` has no web
  implementation.
- **Role-aware UI**: hide/disable Brands and Admin Users screens (and any
  cross-brand store dropdown) for `STORE_ADMIN`. Always still rely on the
  backend's `require_brand_access` for real enforcement — UI hiding is
  just polish, not security.
- **Error handling**: unwrap the `{success, data, error}` envelope in one
  central API client, handling the FastAPI-default `{"detail": ...}` shape
  too, so every screen just gets a thrown `Error` with a readable
  `.message` on failure.
- **Responsive layout**: the same screens must work on a phone-sized
  mobile view and a wide browser window — use flex layouts, avoid fixed
  pixel widths, test both `expo start --web` and a device build before
  calling a screen done.
- **Pairing-code UX**: make the "assign device to store" flow prominent —
  it's the single most important admin action in this whole product (a
  store admin does this every time a phone is reinstalled or replaced).

## 9. Suggested Build Order

1. Backend: in the backend repo (section 0 path/URL), add the Gaps §6
   endpoints (products/categories/barcodes/inventory/terminals-list/
   admins-list). Test each with `curl` against
   `https://smartcheckoutbackend.onrender.com` (or a local `uvicorn` run)
   before building UI against it.
2. Admin app scaffold: new Expo + expo-router project, API client with
   token storage + envelope unwrapping, Login screen.
3. Devices + Terminals + Stores screens (the core provisioning workflow).
4. Products + Inventory screens.
5. Brands + Admin Users screens (SUPER_ADMIN-only).
6. Reports screens (wired to the existing stub endpoints).
7. Web build pass: `expo start --web`, fix any RN-Web layout issues.

---

## Prompt to give the AI

Copy everything below into a fresh conversation with the coding AI (Claude
Code or similar), with this `mainadmin.md` file present in whatever
directory that conversation starts in:

```
Read mainadmin.md fully before doing anything else — it is the complete,
verified spec for what I need built, including exact production/repo URLs
in section 0. Don't guess at the backend's structure or API — everything
you need is either in this file directly (exact endpoint paths, request/
response JSON examples, data model) or reachable via the repo path/URL
in section 0.

The backend already exists and is deployed — it lives at:
- Local path (if you have filesystem access to it): C:\Users\ASUS\OneDrive\Desktop\Ekart\SmartCheckoutBackend
- GitHub: https://github.com/HarshSharma1107/SmartCheckoutBackend.git
- Production API base URL: https://smartcheckoutbackend.onrender.com

Build in this order:

1. Backend gaps (section 6 of mainadmin.md): add the missing admin CRUD
   endpoints for categories, products, product barcodes, inventory, a
   terminals-list endpoint, and an admin-users-list endpoint, in the
   backend repo above — as a new `backend/routers/admin_catalog.py`,
   mounted in `backend/main.py`, following the exact same patterns already
   used in `backend/routers/admin_devices.py` and `backend/routers/
   brands.py`. If you don't have filesystem access to the local path, clone
   the GitHub repo first so you're editing the real project. Do not touch
   enterprise_orders.py, enterprise_products.py, enterprise_customers.py,
   Celery, MQTT, or S3 config in that repo — those are unused scaffolding,
   out of scope.

2. A brand-new Expo app for the admin panel in the current (separate)
   directory — same major stack as the existing checkout app (Expo SDK 54,
   expo-router), built to run both as a mobile app and as a web app via
   `expo start --web`, talking to the production API base URL above (make
   it configurable via an env var, not hardcoded).

3. Implement every screen listed in section 7 of mainadmin.md, wired to
   the real endpoints in sections 4 and 6, respecting the auth/role rules
   in sections 3 and 8, and the response-envelope/error-handling
   conventions in section 8.

Work through it milestone by milestone per section 9's build order, and
tell me clearly at each step what you built and what's left. Ask me before
making any product decision that isn't already specified in mainadmin.md
(e.g. exact visual design, additional fields I didn't mention) rather than
guessing.
```
