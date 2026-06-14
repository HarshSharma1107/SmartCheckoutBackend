# Frontend

## Technology

The frontend is an Expo React Native app.

Important dependencies:

- `expo`
- `expo-camera`
- `react`
- `react-native`
- `@react-navigation/native`
- `@react-navigation/native-stack`

Note: React Navigation packages are imported in source. Confirm they are present in `package-lock.json` or install them if a fresh install fails.

## App Structure

- `frontend/App.js`: wraps the app in `CartProvider` and defines stack routes.
- `frontend/services/api.js`: central API client.
- `frontend/services/CartContext.js`: global state.
- `frontend/screens/HomeScreen.js`: customer/store entry.
- `frontend/screens/ScannerScreen.js`: camera scanning and product result.
- `frontend/screens/CartScreen.js`: cart review and quantity controls.
- `frontend/screens/CheckoutScreen.js`: payment method, order creation, receipt.

## Navigation

Stack routes:

- `Home`
- `Scanner`
- `Cart`
- `Checkout`

Headers are hidden and each screen renders its own header controls.

## State Management

`CartContext` uses `useReducer`.

State:

```js
{
  items: [],
  customer: null,
  storeId: null
}
```

Actions:

- `SET_CUSTOMER`
- `SET_STORE`
- `ADD_ITEM`
- `UPDATE_QUANTITY`
- `REMOVE_ITEM`
- `CLEAR_CART`

Derived values:

- `itemCount`
- `subtotal`
- `taxTotal`
- `grandTotal`
- `orderPayload`

## API Client

`frontend/services/api.js` defines:

- `scanBarcode(barcode, storeId)`
- `getProduct(productId, storeId)`
- `listProducts()`
- `listStores()`
- `createOrder(payload)`
- `getOrder(orderId)`
- `healthCheck()`

Backend URL:

```js
process.env.EXPO_PUBLIC_API_URL || "http://192.168.1.100:8000"
```

## Scanner Behavior

`ScannerScreen` uses `CameraView` from `expo-camera`.

Barcode types:

- `ean13`
- `ean8`
- `upc_a`
- `upc_e`
- `code128`
- `qr`
- `code39`

Important guards:

- Same barcode debounce: 1500 ms.
- API calls are disabled while loading, showing a result, or showing an error.
- Product can be added only if `product.in_stock` is true.

## Checkout Behavior

Checkout supports UI selection for:

- `CASH`
- `UPI`
- `CARD`
- `WALLET`

The backend also defines `BNPL`, but the current frontend does not expose it.

After successful order creation, the cart is cleared and a receipt is shown.

## Known Issues

- Some UI text in source appears mojibake-encoded for rupee symbols, arrows, and icons when read in this environment.
- `orderPayload` in `CartContext` defaults `payment_method` to `CASH`, but `CheckoutScreen` builds its own payload using the selected payment method.
- Default backend URL must be changed for each development network unless `EXPO_PUBLIC_API_URL` is set.
