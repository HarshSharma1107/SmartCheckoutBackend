// =============================================================
// SmartCheckout — Device Token Storage
//
// Single source of truth for where the device access token lives on
// disk, shared by TerminalContext (which writes it on register/refresh)
// and api.js (which reads it to auto-attach the Authorization header to
// every request). Keeping the key in one place avoids the two modules
// drifting out of sync with each other.
// =============================================================

import * as SecureStore from "expo-secure-store";

export const DEVICE_ACCESS_TOKEN_KEY = "sc_access_token";

export async function getDeviceAccessToken() {
  return SecureStore.getItemAsync(DEVICE_ACCESS_TOKEN_KEY);
}
