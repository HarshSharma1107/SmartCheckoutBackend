// =============================================================
// ProvisioningPendingScreen — shown while a device waits for an admin
// to assign it to a store. The pairing code must be readable from across
// a counter - this is the whole point of the "pending" state.
// See docs/terminal-provisioning-plan.md section 2.1.
//
// This is the first screen a freshly set-up device shows, so it carries
// the same branding/animation treatment as HomeScreen rather than reading
// as a bare diagnostic screen.
// =============================================================

import React, { useEffect, useRef } from "react";
import { View, Text, StyleSheet, StatusBar, ActivityIndicator, Animated } from "react-native";
import { useTerminal } from "../services/TerminalContext";
import { COLORS, RADIUS } from "../theme";
import IconState from "../components/IconState";

export default function ProvisioningPendingScreen() {
  const { status, pairingCode, errorMessage, retry } = useTerminal();

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim,  { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 500, useNativeDriver: true }),
    ]).start();
  }, []);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />

      <Animated.View style={[styles.header, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
        <View style={styles.logoMark}>
          <View style={styles.logoInner} />
        </View>
        <Text style={styles.appName}>SmartCheckout</Text>
      </Animated.View>

      <Animated.View style={[styles.body, { opacity: fadeAnim }]}>
        {status === "error" && (
          <IconState
            icon="⚠️"
            title="Connection Error"
            description={errorMessage || "Could not reach the server"}
            actionLabel="Retry"
            onAction={retry}
          />
        )}

        {status === "disabled" && (
          <IconState
            icon="🚫"
            title="Device Disabled"
            description="An admin has disabled this device. Contact your admin."
          />
        )}

        {status === "checking" && (
          <View style={styles.checkingContainer}>
            <ActivityIndicator size="large" color={COLORS.accent} />
            <Text style={styles.checkingLabel}>Checking device status…</Text>
          </View>
        )}

        {status === "pending" && (
          <View style={styles.pendingContainer}>
            <Text style={styles.subtitle}>Give this code to your admin{"\n"}to assign a store</Text>
            <View style={styles.codeBox}>
              <Text style={styles.code}>{pairingCode || "------"}</Text>
            </View>
            <Text style={styles.hint}>Waiting for assignment…</Text>
          </View>
        )}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg, paddingHorizontal: 24 },

  header:    { alignItems: "center", marginTop: 64, marginBottom: 12 },
  logoMark:  { width: 56, height: 56, borderRadius: RADIUS.lg, backgroundColor: COLORS.accent, alignItems: "center", justifyContent: "center", marginBottom: 16 },
  logoInner: { width: 24, height: 24, borderRadius: 6, backgroundColor: COLORS.bg },
  appName:   { fontSize: 24, fontWeight: "700", color: COLORS.text, letterSpacing: -0.5 },

  body: { flex: 1, width: "100%", alignItems: "center", justifyContent: "center" },

  checkingContainer: { alignItems: "center", gap: 16 },
  checkingLabel:      { fontSize: 14, color: COLORS.textMuted },

  pendingContainer: { alignItems: "center", gap: 20 },
  subtitle: { fontSize: 15, color: COLORS.textMuted, textAlign: "center" },
  codeBox: {
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: RADIUS.xl,
    paddingVertical: 28,
    paddingHorizontal: 40,
  },
  code: { fontSize: 48, fontWeight: "800", color: COLORS.accent, letterSpacing: 8 },
  hint: { fontSize: 13, color: COLORS.textMuted },
});
