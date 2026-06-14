# Coding Standards

## General

- Prefer small, focused modules.
- Keep business rules close to the service or route that owns them until shared reuse is clear.
- Update documentation when architecture, API contracts, database relationships, or workflows change.

## Backend

- Use async SQLAlchemy APIs consistently.
- Use SQLAlchemy expressions instead of raw SQL unless there is a strong reason.
- Use Pydantic schemas for request and response boundaries.
- Use `Decimal` for money and tax calculations.
- Return explicit HTTP status codes for business errors.
- Avoid import-time side effects such as printing engine objects.
- Keep ORM model class names in PascalCase.
- Add migrations for schema changes before production use.

## Frontend

- Keep backend communication in `frontend/services/api.js`.
- Keep shared cart/customer/store state in `CartContext`.
- Validate user input before navigation or checkout.
- Keep derived totals deterministic and easy to compare with backend totals.
- Use environment variables for host-specific backend URLs.

## API Contracts

- Do not change endpoint response shapes without updating `docs/api.md`.
- Keep frontend request payloads aligned with `backend/schemas.py`.
- Add explicit error behavior for invalid identifiers.

## Database

- Document every new table, relationship, constraint, and index in `docs/database.md`.
- Prefer unique constraints for natural uniqueness such as barcode, SKU, store code, and inventory product/store pairs.
- Add indexes for query paths used by endpoints.

## Testing

- Add tests for business rules before broad refactors.
- Cover stock validation, tax calculation, and checkout side effects.
- Keep regression tests around API response shapes used by the mobile app.
