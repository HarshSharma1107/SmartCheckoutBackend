# SmartCheckout — Full-Stack Retail System

Barcode-scanning smart checkout system.  
**Backend:** FastAPI + PostgreSQL | **Frontend:** React Native (Expo)

---

## Project Structure

```
smartcheckout/
├── backend/
│   ├── main.py              # FastAPI app — all routes, models, and DB logic
│   └── requirements.txt
└── frontend/
    ├── App.js               # Root navigation
    ├── app.json             # Expo config + camera permissions
    ├── package.json
    ├── services/
    │   ├── api.js           # All API calls in one place
    │   └── CartContext.js   # Global cart state (useReducer)
    └── screens/
        ├── HomeScreen.js    # Customer name + phone + store selection
        ├── ScannerScreen.js # Camera + real-time barcode detection ← CORE
        ├── CartScreen.js    # Cart view with quantity controls
        └── CheckoutScreen.js # Payment selection + receipt/payslip
```

---

## Backend Setup

### 1. Create a PostgreSQL database

```bash
createdb smartcheckout
```

### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Set environment variables

```bash
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/smartcheckout"
```

Or create a `.env` file:
```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/smartcheckout
```

### 4. Run the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server auto-creates tables and seeds 8 demo products with real EAN-13 barcodes on first startup.

### 5. Verify

```
GET http://localhost:8000/health
GET http://localhost:8000/api/v1/products
GET http://localhost:8000/api/v1/scan/8901030000018
```

---

## Frontend Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Set your backend URL

Edit `services/api.js`:
```js
// Replace with your machine's local IP (NOT localhost — the phone needs to reach your machine)
const BASE_URL = "http://192.168.1.100:8000";
```

Find your IP:
- **macOS/Linux:** `ifconfig | grep inet`
- **Windows:** `ipconfig`

### 3. Run

```bash
npx expo start
```

Scan the QR code with **Expo Go** (iOS/Android).

---

## API Reference

### Scan a barcode
```
GET /api/v1/scan/{barcode}?store_id={uuid}
```
Returns product details + live stock, or `found: false` with an error message.

### Get product by ID
```
GET /api/v1/products/{product_id}
```

### Create order (checkout)
```
POST /api/v1/orders
{
  "customer_name": "Rahul Sharma",
  "customer_phone": "9876543210",
  "store_id": "...",
  "payment_method": "UPI",
  "items": [
    { "product_id": "...", "quantity": 2 }
  ]
}
```
Returns full order with calculated GST, totals, and receipt data.

### List stores
```
GET /api/v1/stores
```

---

## Demo Barcodes (pre-seeded)

Scan these in the app (or test via API):

| Barcode          | Product              | MRP     |
|------------------|----------------------|---------|
| `8901030000018`  | Surf Excel 1kg       | ₹135.00 |
| `8901764000018`  | Amul Milk 500ml      | ₹32.00  |
| `8904004100017`  | Parle-G 800g         | ₹55.00  |
| `6294003592560`  | Dettol 500ml         | ₹175.00 |
| `8901725000018`  | Tata Salt 1kg        | ₹28.00  |
| `8901058001112`  | Maggi 70g            | ₹14.00  |
| `8906001500018`  | Fortune Oil 1L       | ₹145.00 |
| `8901314102010`  | Colgate 200g         | ₹115.00 |

You can also print these barcodes and scan them physically with the camera.

---

## Key Design Decisions

### Scanner (ScannerScreen.js)

- Uses `expo-camera` `CameraView` with `onBarcodeScanned` callback
- **Debounce:** 1500ms cooldown per barcode to prevent duplicate API calls
- **State guard:** API call blocked if already in `loading` or `result` state
- **Viewfinder overlay:** CSS mask approach — four transparent rectangles create the scan-area cutout
- **Corner brackets + laser line:** animated with `Animated.loop` for visual feedback
- **Flash toggle:** `enableTorch` prop on `CameraView`
- **Scan types:** EAN-13, EAN-8, UPC-A, UPC-E, Code128, Code39, QR

### Cart (CartContext.js)

- `useReducer` with pure reducer — no Zustand/Redux needed at this scale
- `qty_available` cap enforced on increment
- Derived values (`subtotal`, `taxTotal`, `grandTotal`) computed on every render — no stale state
- `orderPayload` convenience getter builds the exact POST body

### Backend (main.py)

- Single-file FastAPI for simplicity; split into routers for production
- **Async SQLAlchemy** throughout — no blocking DB calls
- **Auto-seed** on startup if DB is empty — zero manual setup
- **Decimal arithmetic** everywhere — no float rounding bugs on GST
- **Stock validation** before order creation — returns 409 if insufficient

---

## Production Hardening (next steps)

- [ ] Add Redis for barcode/inventory caching (`GET /scan` goes Redis-first)
- [ ] Add `inventory_transactions` ledger writes on every order
- [ ] JWT auth on all endpoints (cashier login)
- [ ] Kafka event on `order.completed` → loyalty points, analytics
- [ ] Replace mock payment with Razorpay SDK integration
- [ ] Add product images (S3 + CDN)
- [ ] Offline mode: SQLite cache on device, sync on reconnect
