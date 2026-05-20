// =============================================================
// SmartCheckout — API Service Layer
// All backend communication in one place.
// =============================================================

const BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://192.168.1.100:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const config = {
    headers: { "Content-Type": "application/json" },
    ...options,
  };

  try {
    const res = await fetch(url, config);
    const data = await res.json();

    if (!res.ok) {
      throw new ApiError(data.detail || "Request failed", res.status);
    }
    return data;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError("Network error — check your connection", 0);
  }
}

// =============================================================
// BARCODE / PRODUCT
// =============================================================

/**
 * Core scan call. Called immediately when barcode is detected.
 * Returns product details + live stock, or error if not found.
 */
export async function scanBarcode(barcode, storeId = null) {
  const params = storeId ? `?store_id=${storeId}` : "";
  return request(`/api/v1/scan/${encodeURIComponent(barcode)}${params}`);
}

export async function getProduct(productId, storeId = null) {
  const params = storeId ? `?store_id=${storeId}` : "";
  return request(`/api/v1/products/${productId}${params}`);
}

export async function listProducts() {
  return request("/api/v1/products");
}

// =============================================================
// STORES
// =============================================================

export async function listStores() {
  return request("/api/v1/stores");
}

// =============================================================
// ORDERS
// =============================================================

/**
 * Submit the final cart as an order.
 * @param {Object} payload - { customer_name, customer_phone, store_id, items, payment_method }
 */
export async function createOrder(payload) {
  return request("/api/v1/orders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getOrder(orderId) {
  return request(`/api/v1/orders/${orderId}`);
}

// =============================================================
// HEALTH
// =============================================================

export async function healthCheck() {
  return request("/health");
}
