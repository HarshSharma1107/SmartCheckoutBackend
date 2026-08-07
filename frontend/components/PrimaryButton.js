// =============================================================
// SmartCheckout — PrimaryButton
// The accent-filled, rounded action button, previously hand-duplicated
// (with 14-18px of drifting vertical padding) across every screen's Start/
// Checkout/Pay/Done/Grant-Access buttons. Vertical padding is normalized
// to 16px here as a small, deliberate consistency fix, not a redesign.
// =============================================================

import React from "react";
import { TouchableOpacity, Text, ActivityIndicator, StyleSheet } from "react-native";
import { COLORS, RADIUS } from "../theme";

export default function PrimaryButton({ label, icon, onPress, loading = false, disabled = false, style, textStyle }) {
  const isDisabled = disabled || loading;
  return (
    <TouchableOpacity
      style={[styles.btn, isDisabled && styles.btnDisabled, style]}
      onPress={onPress}
      activeOpacity={0.85}
      disabled={isDisabled}
    >
      {loading ? (
        <ActivityIndicator color={COLORS.bg} />
      ) : (
        <>
          <Text style={[styles.text, textStyle]}>{label}</Text>
          {icon ? <Text style={[styles.text, textStyle]}>{icon}</Text> : null}
        </>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  btn: {
    backgroundColor: COLORS.accent,
    borderRadius: RADIUS.lg,
    paddingVertical: 16,
    paddingHorizontal: 24,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  btnDisabled: { backgroundColor: COLORS.textMuted, opacity: 0.4 },
  text: { fontSize: 17, fontWeight: "700", color: COLORS.bg, letterSpacing: -0.3 },
});
