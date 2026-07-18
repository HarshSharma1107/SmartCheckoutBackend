// =============================================================
// SmartCheckout — Terminal Context
// Owns device provisioning state: registration, pairing code, assigned
// store/brand, and token lifecycle. See docs/terminal-provisioning-plan.md.
//
// Status values:
//   checking  - resolving cached tokens / first registration call in flight
//   pending   - registered but not yet assigned to a store (show pairing code)
//   assigned  - has an active terminal; storeId/brandId are populated
//   disabled  - an admin deactivated this device
//   error     - could not reach the backend
// =============================================================

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";
import * as SecureStore from "expo-secure-store";
import { getOrCreateInstallId, collectDeviceInfo } from "./deviceIdentity";
import { registerDevice, getDeviceMe, sendHeartbeat, refreshDeviceToken } from "./api";

const ACCESS_TOKEN_KEY = "sc_access_token";
const REFRESH_TOKEN_KEY = "sc_refresh_token";
const HEARTBEAT_INTERVAL_MS = 30_000;
const POLL_INTERVAL_MS = 20_000;

const TerminalContext = createContext(null);

export function TerminalProvider({ children }) {
  const [status, setStatus] = useState("checking");
  const [pairingCode, setPairingCode] = useState(null);
  const [pairingCodeExpiresAt, setPairingCodeExpiresAt] = useState(null);
  const [terminal, setTerminal] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const accessTokenRef = useRef(null);
  const pollTimer = useRef(null);
  const heartbeatTimer = useRef(null);

  const loadMe = useCallback(async (accessToken) => {
    const me = await getDeviceMe(accessToken);
    if (me.status === "ASSIGNED") {
      setTerminal({
        terminalId: me.terminal_id,
        terminalCode: me.terminal_code,
        storeId: me.store_id,
        storeName: me.store_name,
        brandId: me.brand_id,
        brandName: me.brand_name,
      });
      setStatus("assigned");
      return true;
    }
    return false;
  }, []);

  const registerOrPoll = useCallback(async () => {
    try {
      const installId = await getOrCreateInstallId();
      const info = await collectDeviceInfo();
      const data = await registerDevice({ local_install_id: installId, ...info });

      if (data.status === "DISABLED") {
        setStatus("disabled");
        return;
      }

      if (data.status === "ASSIGNED") {
        accessTokenRef.current = data.access_token;
        await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, data.access_token);
        await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, data.refresh_token);
        const ok = await loadMe(data.access_token);
        if (!ok) setStatus("pending");
        return;
      }

      setPairingCode(data.pairing_code);
      setPairingCodeExpiresAt(data.pairing_code_expires_at);
      setStatus("pending");
    } catch (err) {
      setErrorMessage(err.message || "Could not reach the server");
      setStatus("error");
    }
  }, [loadMe]);

  // Boot: try cached tokens first so an already-provisioned device goes
  // straight to "assigned" without waiting on a network round trip's worth
  // of registration bookkeeping.
  useEffect(() => {
    (async () => {
      const cachedAccess = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
      if (cachedAccess) {
        accessTokenRef.current = cachedAccess;
        try {
          const ok = await loadMe(cachedAccess);
          if (ok) return;
        } catch {
          // Cached token rejected (expired/revoked) - fall through to
          // register, which also clears local state server-side truth wins.
        }
        await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
        await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
        accessTokenRef.current = null;
      }
      await registerOrPoll();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Poll for assignment while pending.
  useEffect(() => {
    if (status !== "pending") return undefined;
    pollTimer.current = setInterval(registerOrPoll, POLL_INTERVAL_MS);
    return () => clearInterval(pollTimer.current);
  }, [status, registerOrPoll]);

  // Heartbeat while assigned; pause when the app is backgrounded so an idle
  // kiosk phone doesn't burn battery/data.
  useEffect(() => {
    if (status !== "assigned") return undefined;

    const beat = async () => {
      if (AppState.currentState !== "active") return;
      try {
        await sendHeartbeat(accessTokenRef.current);
      } catch (err) {
        if (err.status === 401) {
          const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
          if (!refreshToken) return;
          try {
            const rotated = await refreshDeviceToken(refreshToken);
            accessTokenRef.current = rotated.access_token;
            await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, rotated.access_token);
            await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, rotated.refresh_token);
          } catch (refreshErr) {
            if (refreshErr.status === 401 || refreshErr.status === 403) {
              // The server actually rejected the refresh token (device was
              // deactivated/reassigned while running) - drop back to the
              // pending flow so it doesn't keep operating on a revoked
              // identity.
              await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
              await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
              accessTokenRef.current = null;
              setTerminal(null);
              setStatus("checking");
              await registerOrPoll();
            }
            // Otherwise (status 0 = network unreachable, or a 5xx) this was
            // transient, not a rejection - leave cached tokens and terminal
            // state alone. The next heartbeat tick retries on its own.
          }
        }
      }
    };

    beat();
    heartbeatTimer.current = setInterval(beat, HEARTBEAT_INTERVAL_MS);
    return () => clearInterval(heartbeatTimer.current);
  }, [status, registerOrPoll]);

  const retry = useCallback(() => {
    setErrorMessage(null);
    setStatus("checking");
    registerOrPoll();
  }, [registerOrPoll]);

  return (
    <TerminalContext.Provider
      value={{ status, pairingCode, pairingCodeExpiresAt, terminal, errorMessage, retry }}
    >
      {children}
    </TerminalContext.Provider>
  );
}

export function useTerminal() {
  const ctx = useContext(TerminalContext);
  if (!ctx) throw new Error("useTerminal must be used within TerminalProvider");
  return ctx;
}
