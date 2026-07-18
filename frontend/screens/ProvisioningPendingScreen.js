// =============================================================
// ProvisioningPendingScreen — shown while a device waits for an admin
// to assign it to a store. The pairing code must be readable from across
// a counter - this is the whole point of the screen.
// See docs/terminal-provisioning-plan.md section 2.1.
// =============================================================

import React from "react";
import { View, Text, StyleSheet, StatusBar, ActivityIndicator } from "react-native";
import { useTerminal } from "../services/TerminalContext";

const COLORS = {
  bg: "#0A0A0F",
  surface: "#13131A",
  border: "#2A2A3D",
  accent: "#00E5A0",
  text: "#F0F0F8",
  textMuted: "#6B6B8A",
  error: "#FF5370",
};

export default function ProvisioningPendingScreen() {
  const { status, pairingCode, errorMessage, retry } = useTerminal();

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />

      {status === "error" && (
        <>
          <Text style={styles.title}>Connection error</Text>
          <Text style={styles.subtitle}>{errorMessage || "Could not reach the server"}</Text>
          <Text style={styles.retry} onPress={retry}>Tap to retry</Text>
        </>
      )}

      {status === "disabled" && (
        <>
          <Text style={styles.title}>Device disabled</Text>
          <Text style={styles.subtitle}>An admin has disabled this device. Contact your admin.</Text>
        </>
      )}

      {status === "checking" && <ActivityIndicator size="large" color={COLORS.accent} />}

      {status === "pending" && (
        <>
          <Text style={styles.subtitle}>Give this code to your admin{"\n"}to assign a store</Text>
          <View style={styles.codeBox}>
            <Text style={styles.code}>{pairingCode || "------"}</Text>
          </View>
          <Text style={styles.hint}>Waiting for assignment…</Text>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bg,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    gap: 20,
  },
  title: { fontSize: 22, fontWeight: "700", color: COLORS.text },
  subtitle: { fontSize: 15, color: COLORS.textMuted, textAlign: "center" },
  codeBox: {
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 20,
    paddingVertical: 28,
    paddingHorizontal: 40,
  },
  code: { fontSize: 48, fontWeight: "800", color: COLORS.accent, letterSpacing: 8 },
  hint: { fontSize: 13, color: COLORS.textMuted },
  retry: { fontSize: 15, color: COLORS.accent, fontWeight: "600", padding: 12 },
});
