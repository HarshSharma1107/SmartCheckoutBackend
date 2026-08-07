// =============================================================
// SmartCheckout — IconState
// Icon + title + description(+ optional action button), the shape shared
// by Cart's empty-cart state, Scanner's camera-permission states, and
// ProvisioningPendingScreen's error/disabled states. Previously three
// near-identical hand-copies with small unintentional drift (e.g. a 64px
// vs 56px icon, 28px vs 32px bottom margin) - unified here.
// =============================================================

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { COLORS } from "../theme";
import PrimaryButton from "./PrimaryButton";

export default function IconState({ icon, title, description, actionLabel, onAction, style }) {
  return (
    <View style={[styles.container, style]}>
      <Text style={styles.icon}>{icon}</Text>
      <Text style={styles.title}>{title}</Text>
      {description ? <Text style={styles.description}>{description}</Text> : null}
      {actionLabel && onAction ? (
        <PrimaryButton label={actionLabel} onPress={onAction} style={styles.actionBtn} />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 40 },
  icon:        { fontSize: 60, marginBottom: 20 },
  title:       { fontSize: 22, fontWeight: "700", color: COLORS.text, marginBottom: 12, textAlign: "center" },
  description: { fontSize: 14, color: COLORS.textMuted, textAlign: "center", lineHeight: 22, marginBottom: 28 },
  actionBtn:   { paddingHorizontal: 32 },
});
