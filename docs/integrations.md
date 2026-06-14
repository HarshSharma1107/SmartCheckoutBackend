# Integrations

## PostgreSQL

The backend requires PostgreSQL through `DATABASE_URL` using the `postgresql+asyncpg://` SQLAlchemy URL format.

Important requirements:

- Database must be reachable from the backend process.
- Schema `ekart_prod` must exist or be creatable.
- Enum types referenced with `create_type=False` must exist before table creation.

## Expo Camera

The frontend uses `expo-camera` for barcode scanning.

The app requests camera permission and supports:

- EAN-13
- EAN-8
- UPC-A
- UPC-E
- Code128
- QR
- Code39

## Payment

No real payment gateway is integrated. Payment method selection is a UI/backend label, and orders are immediately marked paid.

Potential future integration:

- Razorpay or another payment provider
- Webhook verification
- Idempotent order/payment state transitions

## Caching

No caching layer is implemented.

Potential future integration:

- Redis for barcode/product/inventory lookup caching

## Messaging and Analytics

No queue or analytics integration is implemented.

Potential future integration:

- Kafka or another broker for `order.completed`
- Loyalty points service
- Sales analytics pipeline
