// =============================================================
// SmartCheckout — Device Identity
// Generates and persists the permanent install UUID used to identify
// this physical device to the backend. See
// docs/terminal-provisioning-plan.md section 6.1.
// =============================================================

import * as SecureStore from "expo-secure-store";
import * as Device from "expo-device";
import * as Application from "expo-application";
import { Platform } from "react-native";

const INSTALL_ID_KEY = "sc_local_install_id";

function generateUuidV4() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Reads the install UUID from secure (Keystore-backed) storage, generating
 * and persisting one on first launch. This identifies the app install, not
 * the person using it - the backend never trusts it alone for
 * authorization, only for idempotent registration.
 */
export async function getOrCreateInstallId() {
  let id = await SecureStore.getItemAsync(INSTALL_ID_KEY);
  if (!id) {
    id = generateUuidV4();
    await SecureStore.setItemAsync(INSTALL_ID_KEY, id);
  }
  return id;
}

export async function collectDeviceInfo() {
  return {
    device_name: Device.deviceName || null,
    manufacturer: Device.manufacturer || null,
    model: Device.modelName || null,
    os_version: Device.osVersion || null,
    app_version: Application.nativeApplicationVersion || null,
    platform: Platform.OS,
  };
}
