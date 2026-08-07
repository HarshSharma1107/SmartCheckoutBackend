// =============================================================
// SmartCheckout — Card
// The surface + border + radius wrapper used identically across Checkout's
// sections and Cart's item cards. `style` can override padding/radius for
// the few call sites (HomeScreen's customer-details card) that
// intentionally use a larger radius/padding for emphasis - those are
// preserved via override, not normalized away.
// =============================================================

import React from "react";
import { View, StyleSheet } from "react-native";
import { COLORS, RADIUS } from "../theme";

export default function Card({ children, style }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    padding: 16,
    borderWidth: 0.5,
    borderColor: COLORS.border,
  },
});
