# Security

## Current Posture

SmartCheckout is currently a prototype-level API and mobile app. It should not be exposed to untrusted networks without hardening.

## Authentication Strategy

Not implemented.

Recommended:

- Add cashier/admin login.
- Use short-lived access tokens and refresh tokens.
- Associate orders with authenticated cashier or terminal identity.

## Authorization Strategy

Not implemented.

Recommended:

- Role-based permissions for cashier, store manager, inventory admin, and system admin.
- Restrict order creation to authorized terminals/users.
- Restrict product/inventory management endpoints when added.

## Secret Management

Current:

- Backend reads `DATABASE_URL` from environment.
- `.env` is ignored by `.gitignore`.

Recommended:

- Use environment-specific secret stores in deployment.
- Never commit `.env`, database passwords, payment keys, or local MCP/settings files.

## Threat Model

Assets:

- Customer name and phone.
- Product and pricing data.
- Inventory levels.
- Order and payment status.
- Database credentials.

Threats:

- Unauthenticated order creation.
- Inventory tampering through repeated or malicious checkout requests.
- Customer data exposure.
- Overly permissive CORS.
- SQL or ORM misuse in future raw-query changes.
- Payment spoofing because payment is currently simulated.

## Security Checklist

- SQL injection: current code uses SQLAlchemy expressions; keep this pattern.
- XSS: mobile app renders native text, but sanitize any future web or rich text surfaces.
- CSRF: less relevant for native clients, but required if browser sessions are introduced.
- SSRF: no outbound URL fetching found.
- RCE: no dynamic code execution found.
- Broken authentication: authentication is absent and must be added before exposure.
- Sensitive data exposure: customer phone is returned in order receipts; protect API access and logs.
- CORS: currently `allow_origins=["*"]`; restrict in production.
- Rate limiting: not implemented.
- Audit logging: not implemented.

## Payment Security

Payment methods are labels only. Orders are marked `PAID` immediately. Do not treat this as real payment confirmation.

Before integrating a gateway:

- Verify provider signatures/webhooks.
- Store provider transaction references.
- Use idempotency keys.
- Model pending, failed, and refunded states accurately.
