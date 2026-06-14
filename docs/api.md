# API

Base URL in local development is typically:

```text
http://<backend-host>:8000
```

Most application endpoints are under `/api/v1`.

## Error Standards

The backend uses FastAPI `HTTPException` for error cases. Common shapes:

```json
{ "detail": "Error message" }
```

Validation errors use FastAPI/Pydantic's default validation response.

## Health

### `GET /health`

Response:

```json
{
  "status": "ok",
  "service": "SmartCheckout API",
  "version": "1.0.0"
}
```

## Products

### `GET /api/v1/scan/{barcode}?store_id={uuid}`

Looks up an active barcode and returns product details with live inventory.

Behavior:

- Empty barcode returns `400`.
- Unknown barcode returns `found: false`.
- Inactive or discontinued product returns `found: false`.
- Invalid `store_id` is ignored by current code, so inventory can fall back to the first inventory row for the product.

Success response:

```json
{
  "found": true,
  "barcode": "8901030000018",
  "product": {
    "product_id": "uuid",
    "sku": "SKU",
    "name": "Product name",
    "brand": "Brand",
    "mrp": 135.0,
    "selling_price": 135.0,
    "cgst_rate": 9.0,
    "sgst_rate": 9.0,
    "tax_rate": 18.0,
    "qty_available": 10,
    "category_name": "Category",
    "in_stock": true
  },
  "error": null
}
```

Not found response:

```json
{
  "found": false,
  "barcode": "unknown",
  "product": null,
  "error": "Product not found. Barcode not in catalogue."
}
```

### `GET /api/v1/products/{product_id}?store_id={uuid}`

Returns one active product with available stock.

Errors:

- `400` for invalid product UUID.
- `404` if product is not found.

### `GET /api/v1/products`

Returns active products in a compact list.

Response:

```json
{
  "count": 1,
  "products": [
    {
      "product_id": "uuid",
      "sku": "SKU",
      "name": "Product name",
      "mrp": 135.0
    }
  ]
}
```

## Stores

### `GET /api/v1/stores`

Returns active stores.

Response:

```json
[
  {
    "store_id": "uuid",
    "code": "STORE01",
    "name": "Main Store",
    "city": "Bengaluru"
  }
]
```

## Orders

### `POST /api/v1/orders`

Creates an order, marks it paid/completed, creates order items, and decrements inventory.

Request:

```json
{
  "customer_name": "Rahul Sharma",
  "customer_phone": "9876543210",
  "store_id": "uuid",
  "payment_method": "UPI",
  "items": [
    { "product_id": "uuid", "quantity": 2 }
  ]
}
```

Validation:

- `customer_name` must not be empty.
- `customer_phone` must contain at least 10 digits.
- `store_id` must be a valid UUID and existing store.
- `items` must not be empty.
- Item quantity must be at least 1.
- Each product must exist and be active.
- Available inventory must be enough for requested quantity.

Errors:

- `400` invalid store or product UUID, empty order.
- `404` store or product not found.
- `409` insufficient stock.

Response:

```json
{
  "order_id": "uuid",
  "order_number": "ORD-20260612-ABC123",
  "customer_name": "Rahul Sharma",
  "customer_phone": "9876543210",
  "status": "COMPLETED",
  "subtotal": 270.0,
  "discount_total": 0.0,
  "cgst_total": 24.3,
  "sgst_total": 24.3,
  "grand_total": 318.6,
  "payment_method": "UPI",
  "payment_status": "PAID",
  "ordered_at": "2026-06-12T00:00:00",
  "completed_at": "2026-06-12T00:00:00",
  "items": []
}
```

### `GET /api/v1/orders/{order_id}`

Returns an order receipt by UUID.

Errors:

- `400` invalid UUID.
- `404` order not found.

## Authentication Flow

No authentication is currently implemented. All endpoints are public to any client that can reach the API.

## Enterprise Production API Surface

The first production foundation pass adds the following `/api/v1` endpoints with consistent response envelopes:

```json
{ "success": true, "data": {}, "error": null }
```

```json
{ "success": false, "data": null, "error": { "code": "ERROR_CODE", "message": "Message" } }
```

Device endpoints:

- `POST /api/v1/devices/register`
- `POST /api/v1/devices/activate`
- `POST /api/v1/devices/{device_id}/heartbeat`
- `GET /api/v1/devices/{device_id}/config`

Admin device endpoints:

- `POST /api/v1/admin/devices/{device_id}/assign`
- `POST /api/v1/admin/devices/{device_id}/revoke`

Product endpoint:

- `GET /api/v1/products/barcode/{barcode_value}?store_id={uuid}`

Enterprise order endpoints:

- `POST /api/v1/orders`
- `POST /api/v1/orders/{order_id}/items`
- `DELETE /api/v1/orders/{order_id}/items/{item_id}`
- `PATCH /api/v1/orders/{order_id}/items/{item_id}`
- `POST /api/v1/orders/{order_id}/checkout`
- `POST /api/v1/orders/{order_id}/payment-confirmation`
- `GET /api/v1/orders/{order_id}`
- `GET /api/v1/orders/{order_id}/invoice`
- `POST /api/v1/orders/{order_id}/resend-invoice`

Customer endpoints:

- `POST /api/v1/customers/lookup`
- `POST /api/v1/customers/verify-phone`
- `POST /api/v1/customers/verify-otp`

Webhook endpoints:

- `POST /api/v1/webhooks/payment`
- `POST /api/v1/webhooks/whatsapp`

Reporting endpoints:

- `GET /api/v1/reports/sales`
- `GET /api/v1/reports/device-health`
- `GET /api/v1/reports/customer/{customer_id}/purchases`
- `GET /api/v1/reports/terminal/{terminal_id}/summary`

Monitoring endpoints:

- `GET /api/v1/health`
- `GET /api/v1/ready`

Current caveat: the auth dependencies are local-development placeholders. Production still needs real mTLS certificate verification, JWT signature validation, webhook HMAC verification, and RBAC.
