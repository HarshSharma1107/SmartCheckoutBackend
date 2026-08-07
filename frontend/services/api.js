// =============================================================
// SmartCheckout — API Service Layer
// All backend communication in one place.
// =============================================================

import { getDeviceAccessToken } from "./deviceToken";

const BASE_URL = process.env.EXPO_PUBLIC_API_URL || "https://smartcheckoutbackend.onrender.com";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };

  // Auto-attach the device bearer token to every request that doesn't
  // already specify its own Authorization header (e.g. a one-off admin
  // token). This is the single place it happens - call sites never need
  // to remember to thread a token through, which is exactly the gap that
  // caused "Missing device bearer token" on checkout: whichever endpoint
  // ends up requiring device auth next won't need special-casing here.
  if (!headers.Authorization) {
    const deviceToken = await getDeviceAccessToken();
    if (deviceToken) headers.Authorization = `Bearer ${deviceToken}`;
  }

  const config = { ...options, headers };

  let res;
  try {
    res = await fetch(url, config);
  } catch (err) {
    console.error(`[api] ${config.method || "GET"} ${url} - fetch failed:`, err.message);
    throw new ApiError("Network error — check your connection", 0);
  }

  // Read the body as text first: error responses aren't guaranteed to be
  // JSON (e.g. a raw 500 from an unhandled backend exception, or a Cloudflare/
  // Render gateway page during a cold start), and calling res.json() straight
  // away would throw and get misreported as a network error instead of the
  // real status.
  const rawBody = await res.text();
  let data = null;
  try {
    data = rawBody ? JSON.parse(rawBody) : null;
  } catch {
    console.error(`[api] ${config.method || "GET"} ${url} - non-JSON response (HTTP ${res.status}):`, rawBody.slice(0, 500));
    throw new ApiError(`Server error (HTTP ${res.status})`, res.status);
  }

  if (!res.ok) {
    // FastAPI's default error shape is {detail: {code, message}} or
    // {detail: "string"}; the terminal-provisioning endpoints also use
    // {success:false, error:{code,message}}. Handle all three so the
    // thrown message is always readable text, not "[object Object]".
    const detail = data?.detail ?? data?.error;
    const message = typeof detail === "string" ? detail : detail?.message || `Request failed (HTTP ${res.status})`;
    console.error(`[api] ${config.method || "GET"} ${url} - HTTP ${res.status}:`, message);
    throw new ApiError(message, res.status);
  }
  // Terminal-provisioning endpoints wrap payloads as {success, data, error}.
  return data && typeof data === "object" && "data" in data && "success" in data ? data.data : data;
}

// =============================================================
// BARCODE / PRODUCT
// =============================================================

/**
 * Core scan call. Called immediately when barcode is detected.
 * Returns product details + live stock, or error if not found.
 */
export async function scanBarcode(barcode) {
  // No store_id param - the backend derives the store from the
  // authenticated device's own active terminal assignment.
  return request(`/api/v1/scan/${encodeURIComponent(barcode)}`);
}

export async function getProduct(productId) {
  return request(`/api/v1/products/${productId}`);
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
