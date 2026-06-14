# SmartCheckout Project Memory

This file is the persistent engineering context entry point for SmartCheckout. Future AI agents and engineers should read it before making recommendations or code changes.

## Context Loading Order

1. `~/.claude/CLAUDE.md` if present
2. `CLAUDE.md`
3. `README.md`
4. `docs/project-overview.md`
5. `docs/architecture.md`
6. `docs/database.md`
7. `docs/api.md`
8. `docs/security.md`
9. `docs/workflows.md`
10. Task-specific files

At the time this file was created, `~/.claude/CLAUDE.md` was not present on this machine.

## Project Summary

SmartCheckout is a full-stack retail checkout prototype:

- Backend: FastAPI, async SQLAlchemy, PostgreSQL via `asyncpg`
- Frontend: React Native with Expo and `expo-camera`
- Core flow: customer/store selection, barcode scan, product lookup with inventory, cart management, checkout, order receipt
- Database schema: PostgreSQL schema `ekart_prod`

## Key Source Files

- Backend app entry: `backend/main.py`
- Backend database config: `backend/database.py`, `backend/config.py`
- Backend ORM models: `backend/models.py`
- Backend request/response schemas: `backend/schemas.py`
- Backend routers: `backend/routers/*.py`
- Frontend app entry/navigation: `frontend/App.js`
- Frontend API client: `frontend/services/api.js`
- Frontend cart state: `frontend/services/CartContext.js`
- Frontend screens: `frontend/screens/*.js`

## Current Known Architecture

The backend exposes `/health` and `/api/v1/*` endpoints. `main.py` mounts routers for health, products, stores, and orders. On startup, it creates missing tables from SQLAlchemy metadata.

The frontend is a stack-navigated Expo app. It uses a global cart context to hold customer, store, cart items, derived totals, and checkout payload helpers.

## Current Known Business Rules

- A scan returns a product only if an active barcode maps to an active, non-discontinued product.
- Inventory availability is `max(0, qty_on_hand - qty_reserved)`.
- Cart quantity cannot exceed `qty_available` from the scanned product response.
- Checkout requires a valid store, at least one item, customer name, and customer phone with at least 10 digits.
- Existing customers are reused by phone; otherwise a new customer is created.
- Orders are marked `COMPLETED` and `PAID` immediately.
- GST is calculated from product CGST and SGST rates using decimal arithmetic in the backend.
- Inventory `qty_on_hand` is decremented after order item creation.

## Documentation Map

- `docs/project-overview.md`: product and repository overview
- `docs/architecture.md`: system design, flows, module map
- `docs/database.md`: schema, relationships, constraints, indexes
- `docs/api.md`: endpoint contracts and error behavior
- `docs/frontend.md`: React Native app structure and state
- `docs/backend.md`: FastAPI structure and backend rules
- `docs/deployment.md`: local run and deployment considerations
- `docs/security.md`: current security posture and hardening checklist
- `docs/testing.md`: current gaps and recommended test plan
- `docs/workflows.md`: checkout, scanning, and operational workflows
- `docs/integrations.md`: external dependencies and integration points
- `docs/coding-standards.md`: project coding conventions
- `docs/troubleshooting.md`: common issues and fixes
- `docs/enterprise-iot-architecture.md`: target production architecture for Raspberry Pi devices, provisioning, terminal assignment, offline sync, audit, APIs, and WhatsApp invoices
- `docs/production-implementation.md`: implementation status for the production Smart eKart foundation

## Important Gaps

- No automated tests were found.
- No migration system was found; tables are created from ORM metadata at startup.
- No authentication or authorization is implemented.
- CORS currently allows all origins.
- Payment is simulated by immediate `PAID` status; no gateway integration exists.
- README appears partly stale: it references `backend/requirements.txt`, but dependencies are currently in root `requirements.txt`.
