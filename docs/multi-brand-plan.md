# Multi-Brand, Multi-Store Plan

## Goal

Today every `Store` row is standalone — there is no concept of a retail brand
that owns multiple stores. The target model:

```text
Brand (e.g. "D-Mart")
  -> Store (D-Mart Andheri, D-Mart Powai, ...)
       -> Inventory (per store)
       -> Orders (per store)
```

Customer flow: pick a brand -> pick a store under that brand -> scan products
-> pay -> receipt on their phone. This document is the implementation plan
only; no code has been written yet.

## Open Decision (needs answer before Phase 2)

Is the product catalog shared across brands, or does each brand have its own
catalog/pricing?

- **Shared catalog** (simpler): `products` stays brand-agnostic; only
  `inventory` is per-store. Two brands selling "Lays Chips" share the same
  `product_id`, price, GST rates. Only stock levels differ per store.
- **Per-brand catalog**: `products` gets a `brand_id`, so D-Mart and a
  different brand can list the same physical item with different SKUs/prices.

Recommendation: start with **shared catalog** — it is the smaller change and
matches how `Product.brand` is already used today (a free-text manufacturer
brand, e.g. "Lays", not a retail-chain brand). Retail-chain brand becomes a
new concept scoped to `Store`, not `Product`.

## Phase 1 — Data Model

### New table: `ekart_prod.brands`

| column       | type          | notes                        |
|--------------|---------------|-------------------------------|
| brand_id     | UUID PK       | default uuid4                 |
| code         | string(20)    | unique, e.g. `DMART`           |
| name         | string(200)   | e.g. "D-Mart"                  |
| logo_url     | string, null  | for receipt/app branding       |
| is_active    | boolean       | default true                   |
| created_at   | datetime      |                                |
| updated_at   | datetime      |                                |

### Change: `ekart_prod.stores`

Add:

| column    | type    | notes                                          |
|-----------|---------|-------------------------------------------------|
| brand_id  | UUID FK | `brands.brand_id`, not null                     |

Update unique constraint: `code` should become unique **per brand**
(`UNIQUE(brand_id, code)`) instead of globally unique, since two brands may
reuse short codes.

### No change needed (Phase 1)

- `products`, `product_barcodes`, `inventory`, `orders`, `order_items`,
  `customers` — unchanged under the shared-catalog decision above.

### Files to touch

- `backend/models.py` — add `Brand` model, add `brand_id` FK + relationship
  on `Store`, update `Store.code` uniqueness.
- `docs/database.md` — document the new table and FK.

## Phase 2 — Migration Strategy

The project has no migration framework; tables are created via
`Base.metadata.create_all` on startup (see `docs/database.md`). For this
change specifically (adding a non-null FK to an existing table with data):

1. Introduce Alembic (`alembic init`), since `create_all` cannot add a
   NOT NULL column to a table that already has rows without a backfill step.
2. Migration steps:
   - Create `brands` table.
   - Insert a default brand row (e.g. code `DEFAULT`) so existing stores have
     somewhere to point.
   - Add `stores.brand_id` as nullable, backfill all existing rows to the
     default brand's id, then alter to NOT NULL.
   - Drop old global-unique constraint on `stores.code`, add
     `UNIQUE(brand_id, code)`.
3. This is the first migration in the repo — also wire `alembic upgrade head`
   into the backend startup docs (`docs/deployment.md`) so it's not skipped.

## Phase 3 — Backend API

### New router: `backend/routers/brands.py`

- `GET /api/v1/brands` — list active brands (id, code, name, logo_url).

### Update: `backend/routers/stores.py`

- `GET /api/v1/stores?brand_id={brand_id}` — filter stores by brand
  (required query param once frontend adopts brand selection).
- Response includes `brand_id`, `brand_name` for convenience.

### Update: `backend/schemas.py`

- Add `BrandResponse` schema.
- Add `brand_id` / `brand_name` to whatever store response schema exists.

### No change needed

- `backend/routers/products.py` (scan/list stay store-scoped, brand-agnostic
  under shared catalog).
- `backend/routers/orders.py` — orders already key off `store_id`; brand is
  reachable via `store.brand_id` if needed for receipts/reporting later.

## Phase 4 — Frontend

### New screen: `frontend/screens/BrandScreen.js`

- Fetches `GET /api/v1/brands`, shows a brand picker (logo + name).
- On selection, stores `brand_id` in `CartContext` and navigates to store
  selection (existing `HomeScreen` store list, now filtered by brand).

### Update: `frontend/services/CartContext.js`

- Add `brand` to global state (id, name), reset store/cart when brand
  changes.

### Update: `frontend/services/api.js`

- Add `getBrands()`.
- Update `getStores()` to accept `brandId` and pass it as a query param.

### Update: `frontend/App.js`

- Add `BrandScreen` as the new entry point in the stack, before store
  selection.

### Update: `frontend/screens/HomeScreen.js`

- Only render/fetch stores for the currently selected brand; show brand name
  in the header for context.

## Phase 5 — Receipts & Branding

- Receipt (`CheckoutScreen.js` display, and any WhatsApp/PDF receipt work
  referenced in `docs/enterprise-iot-architecture.md`) should show the
  brand name/logo, not just the store name, since the customer associates
  the purchase with the brand (e.g. "D-Mart").

## Phase 6 — Testing

No automated tests exist yet (`docs/testing.md`). Minimum coverage to add
alongside this change:

- Backend: brand list endpoint, store list filtered by brand, order creation
  still works with the new FK in place (regression).
- Manual: brand -> store -> scan -> checkout -> receipt end-to-end, using
  two seeded brands with distinct stores, to confirm store lists don't
  leak across brands.

## Rollout Order

1. Phase 1 + 2 (model + migration) — can ship with no visible behavior
   change if `brand_id` defaults existing stores to one default brand.
2. Phase 3 (backend API) — additive, non-breaking.
3. Phase 4 (frontend brand picker) — user-visible change.
4. Phase 5 (receipts/branding polish).
5. Phase 6 (tests) — ideally alongside 1–3, not deferred to the end.

## Out of Scope (for this plan)

- Per-brand user accounts / staff logins (no auth exists at all yet —
  separate effort per `docs/security.md`).
- Per-brand payment gateway configuration (payment is currently simulated).
- Cross-brand loyalty/points sharing.
