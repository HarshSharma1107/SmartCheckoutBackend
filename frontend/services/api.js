// =============================================================
// SmartCheckout — API Service Layer
// All backend communication in one place.
// =============================================================

const BASE_URL = process.env.EXPO_PUBLIC_API_URL || "https://smartcheckoutbackend.onrender.com";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const config = {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  };

  try {
    const res = await fetch(url, config);
    const data = await res.json();

    if (!res.ok) {
      // FastAPI's default error shape is {detail: {code, message}} or
      // {detail: "string"}; the terminal-provisioning endpoints also use
      // {success:false, error:{code,message}}. Handle all three so the
      // thrown message is always readable text, not "[object Object]".
      const detail = data.detail ?? data.error;
      const message = typeof detail === "string" ? detail : detail?.message || "Request failed";
      throw new ApiError(message, res.status);
    }
    // Terminal-provisioning endpoints wrap payloads as {success, data, error}.
    return data && typeof data === "object" && "data" in data && "success" in data ? data.data : data;
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

// =============================================================
// TERMINAL PROVISIONING
// See docs/terminal-provisioning-plan.md for the full flow.
// =============================================================

/**
 * Idempotent by local_install_id - safe to call repeatedly while polling
 * for admin assignment, and safe to call again after a reinstall.
 */
export async function registerDevice(payload) {
  return request("/api/v1/devices/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getDeviceMe(accessToken) {
  return request("/api/v1/devices/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export async function sendHeartbeat(accessToken, appVersion = null) {
  return request("/api/v1/devices/heartbeat", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ app_version: appVersion }),
  });
}

export async function refreshDeviceToken(refreshToken) {
  return request("/api/v1/devices/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}
