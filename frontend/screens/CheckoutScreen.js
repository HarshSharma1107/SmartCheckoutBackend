// =============================================================
// CheckoutScreen — Payment + Receipt / Pay Slip Generation
// =============================================================

import React, { useState, useRef } from "react";
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  Platform, StatusBar, Alert, Animated,
} from "react-native";
import { useCart } from "../services/CartContext";
import { createOrder } from "../services/api";
import { generateUuidV4 } from "../services/deviceIdentity";
import { getDisplayMessage } from "../services/errorMessages";
import { COLORS, RADIUS } from "../theme";
import PrimaryButton from "../components/PrimaryButton";
import Card from "../components/Card";

const PAYMENT_METHODS = [
  { id: "CASH",   label: "Cash",   icon: "💵" },
  { id: "UPI",    label: "UPI",    icon: "📱" },
  { id: "CARD",   label: "Card",   icon: "💳" },
  { id: "WALLET", label: "Wallet", icon: "👛" },
];

// =============================================================
// RECEIPT COMPONENT
// =============================================================
function Receipt({ order, onDone }) {
  const fadeAnim = useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
  }, []);

  const date = new Date(order.ordered_at);
  const dateStr = date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  const timeStr = date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

  return (
    <Animated.View style={[styles.receiptContainer, { opacity: fadeAnim }]}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.receiptScroll}>
        {/* Success badge */}
        <View style={styles.successBadge}>
          <Text style={styles.successIcon}>✓</Text>
        </View>
        <Text style={styles.successTitle}>Payment Successful!</Text>
        <Text style={styles.successSub}>Order #{order.order_number}</Text>

        {/* Receipt card */}
        <View style={styles.receiptCard}>
          {/* Header */}
          <View style={styles.receiptHeader}>
            <View style={styles.receiptLogoMark} />
            <Text style={styles.receiptStoreName}>SmartCheckout</Text>
            <Text style={styles.receiptMeta}>{dateStr}  {timeStr}</Text>
            <Text style={styles.receiptMeta}>Order: {order.order_number}</Text>
          </View>

          <View style={styles.receiptDivider} />

          {/* Customer */}
          <View style={styles.receiptSection}>
            <Text style={styles.receiptSectionLabel}>CUSTOMER</Text>
            <Text style={styles.receiptCustomer}>{order.customer_name}</Text>
            <Text style={styles.receiptCustomerPhone}>{order.customer_phone}</Text>
            {order.customer_email ? (
              <Text style={styles.receiptCustomerPhone}>{order.customer_email}</Text>
            ) : null}
          </View>

          <View style={styles.receiptDivider} />

          {/* Items */}
          <View style={styles.receiptSection}>
            <Text style={styles.receiptSectionLabel}>ITEMS</Text>
            {order.items.map((item) => (
              <View key={item.item_id} style={styles.receiptItemRow}>
                <View style={styles.receiptItemLeft}>
                  <Text style={styles.receiptItemName} numberOfLines={1}>{item.product_name}</Text>
                  <Text style={styles.receiptItemDetail}>
                    ₹{item.unit_price.toFixed(2)} × {item.quantity}
                  </Text>
                </View>
                <Text style={styles.receiptItemTotal}>₹{item.line_total.toFixed(2)}</Text>
              </View>
            ))}
          </View>

          <View style={styles.receiptDivider} />

          {/* Totals */}
          <View style={styles.receiptSection}>
            <View style={styles.receiptTotalRow}>
              <Text style={styles.receiptTotalLabel}>Subtotal</Text>
              <Text style={styles.receiptTotalValue}>₹{order.subtotal.toFixed(2)}</Text>
            </View>
            <View style={styles.receiptTotalRow}>
              <Text style={styles.receiptTotalLabel}>CGST</Text>
              <Text style={styles.receiptTotalValue}>₹{order.cgst_total.toFixed(2)}</Text>
            </View>
            <View style={styles.receiptTotalRow}>
              <Text style={styles.receiptTotalLabel}>SGST</Text>
              <Text style={styles.receiptTotalValue}>₹{order.sgst_total.toFixed(2)}</Text>
            </View>
            <View style={[styles.receiptTotalRow, styles.receiptGrandRow]}>
              <Text style={styles.receiptGrandLabel}>TOTAL PAID</Text>
              <Text style={styles.receiptGrandValue}>₹{order.grand_total.toFixed(2)}</Text>
            </View>
            <View style={styles.receiptTotalRow}>
              <Text style={styles.receiptTotalLabel}>Payment Method</Text>
              <Text style={styles.receiptTotalValue}>{order.payment_method}</Text>
            </View>
          </View>

          <View style={styles.receiptDivider} />

          {/* Footer */}
          <Text style={styles.receiptFooter}>Thank you for shopping with us!</Text>
          <Text style={styles.receiptFooterSub}>
            {order.customer_email
              ? `A copy of this receipt has been emailed to ${order.customer_email}.`
              : "This is your digital receipt."}
          </Text>
        </View>

        <PrimaryButton label="Start New Shopping Session" onPress={onDone} />
      </ScrollView>
    </Animated.View>
  );
}

// =============================================================
// MAIN CHECKOUT SCREEN
// =============================================================
export default function CheckoutScreen({ navigation }) {
  const { items, customer, subtotal, taxTotal, grandTotal, orderPayload, clearCart, storeId } = useCart();

  const [payMethod,  setPayMethod]  = useState("UPI");
  const [loading,    setLoading]    = useState(false);
  const [order,      setOrder]      = useState(null);
  const [errorMsg,   setErrorMsg]   = useState("");

  // One key per checkout-screen mount, reused across retries of the same
  // attempt so a double-tapped or network-retried Pay never creates a
  // second order - the backend dedupes on (device, idempotency_key).
  const idempotencyKeyRef = useRef(generateUuidV4());

  async function handleCheckout() {
    if (loading) return;
    if (!customer) {
      Alert.alert("Missing Info", "Customer information is required.");
      return;
    }
    if (items.length === 0) {
      Alert.alert("Empty Cart", "Add items before checking out.");
      return;
    }

    setLoading(true);
    setErrorMsg("");

    try {
      const payload = {
        customer_name:    customer.name,
        customer_phone:   customer.phone,
        customer_email:   customer.email,
        store_id:         storeId,
        payment_method:   payMethod,
        idempotency_key:  idempotencyKeyRef.current,
        items: items.map((i) => ({
          product_id: i.product.product_id,
          quantity:   i.quantity,
        })),
      };

      const result = await createOrder(payload);
      setOrder(result);
      clearCart();
    } catch (err) {
      setErrorMsg(getDisplayMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function handleDone() {
    navigation.reset({ index: 0, routes: [{ name: "Home" }] });
  }

  // Show receipt after successful payment
  if (order) {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />
        <Receipt order={order} onDone={handleDone} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.backBtnText}>←</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Checkout</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>

        {/* Customer info */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>CUSTOMER</Text>
          <Card>
            <Text style={styles.customerName}>{customer?.name}</Text>
            <Text style={styles.customerPhone}>{customer?.phone}</Text>
            <Text style={styles.customerPhone}>{customer?.email}</Text>
          </Card>
        </View>

        {/* Order summary */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>ORDER SUMMARY</Text>
          <Card>
            {items.map((item) => {
              const lineBase  = item.product.selling_price * item.quantity;
              const tax       = lineBase * (item.product.tax_rate / 100);
              const lineTotal = lineBase + tax;
              return (
                <View key={item.product.product_id} style={styles.orderRow}>
                  <View style={styles.orderItemLeft}>
                    <Text style={styles.orderItemName} numberOfLines={1}>{item.product.name}</Text>
                    <Text style={styles.orderItemMeta}>₹{item.product.selling_price.toFixed(2)} × {item.quantity}</Text>
                  </View>
                  <Text style={styles.orderItemTotal}>₹{lineTotal.toFixed(2)}</Text>
                </View>
              );
            })}
          </Card>
        </View>

        {/* Payment method */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>PAYMENT METHOD</Text>
          <View style={styles.paymentGrid}>
            {PAYMENT_METHODS.map((m) => (
              <TouchableOpacity
                key={m.id}
                style={[styles.paymentOption, payMethod === m.id && styles.paymentOptionActive]}
                onPress={() => setPayMethod(m.id)}
                activeOpacity={0.75}
              >
                <Text style={styles.paymentIcon}>{m.icon}</Text>
                <Text style={[styles.paymentLabel, payMethod === m.id && styles.paymentLabelActive]}>
                  {m.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Bill breakdown */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>BILL BREAKDOWN</Text>
          <Card>
            <View style={styles.billRow}>
              <Text style={styles.billLabel}>Items ({items.reduce((s, i) => s + i.quantity, 0)})</Text>
              <Text style={styles.billValue}>₹{subtotal.toFixed(2)}</Text>
            </View>
            <View style={styles.billRow}>
              <Text style={styles.billLabel}>GST</Text>
              <Text style={styles.billValue}>₹{taxTotal.toFixed(2)}</Text>
            </View>
            <View style={[styles.billRow, styles.billTotalRow]}>
              <Text style={styles.billTotalLabel}>Total Payable</Text>
              <Text style={styles.billTotalValue}>₹{grandTotal.toFixed(2)}</Text>
            </View>
          </Card>
        </View>

        {errorMsg ? (
          <View style={styles.errorBanner}>
            <Text style={styles.errorBannerText}>⚠ {errorMsg}</Text>
          </View>
        ) : null}
      </ScrollView>

      {/* Pay button */}
      <View style={styles.payPanel}>
        <View style={styles.payAmountRow}>
          <Text style={styles.payAmountLabel}>Pay Now</Text>
          <Text style={styles.payAmountValue}>₹{grandTotal.toFixed(2)}</Text>
        </View>
        <PrimaryButton
          label={`Pay via ${payMethod}  ✓`}
          onPress={handleCheckout}
          loading={loading}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: COLORS.bg },

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingTop: Platform.OS === "ios" ? 58 : 36,
    paddingBottom: 16,
    paddingHorizontal: 20,
    borderBottomWidth: 0.5,
    borderColor: COLORS.border,
  },
  backBtn:     { width: 40, height: 40, borderRadius: 12, backgroundColor: COLORS.surfaceHigh, alignItems: "center", justifyContent: "center" },
  backBtnText: { fontSize: 20, color: COLORS.text },
  headerTitle: { fontSize: 20, fontWeight: "700", color: COLORS.text },

  scroll:      { padding: 20, paddingBottom: 10 },
  section:     { marginBottom: 20 },
  sectionLabel:{ fontSize: 10, fontWeight: "700", color: COLORS.textMuted, letterSpacing: 2, marginBottom: 10 },

  customerName:  { fontSize: 17, fontWeight: "700", color: COLORS.text },
  customerPhone: { fontSize: 14, color: COLORS.textMuted, marginTop: 4 },

  orderRow:      { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", paddingVertical: 8, borderBottomWidth: 0.5, borderColor: COLORS.border },
  orderItemLeft: { flex: 1, marginRight: 12 },
  orderItemName: { fontSize: 14, fontWeight: "600", color: COLORS.text },
  orderItemMeta: { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },
  orderItemTotal:{ fontSize: 14, fontWeight: "700", color: COLORS.text },

  paymentGrid: { flexDirection: "row", gap: 8 },
  paymentOption: {
    flex: 1,
    backgroundColor: COLORS.surface,
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: "center",
    borderWidth: 0.5,
    borderColor: COLORS.border,
    gap: 4,
  },
  paymentOptionActive: { backgroundColor: COLORS.accentDim, borderColor: COLORS.accent },
  paymentIcon:         { fontSize: 22 },
  paymentLabel:        { fontSize: 12, fontWeight: "600", color: COLORS.textMuted },
  paymentLabelActive:  { color: COLORS.accent },

  billRow:       { flexDirection: "row", justifyContent: "space-between", paddingVertical: 6 },
  billLabel:     { fontSize: 14, color: COLORS.textMuted },
  billValue:     { fontSize: 14, color: COLORS.text },
  billTotalRow:  { paddingTop: 12, borderTopWidth: 0.5, borderColor: COLORS.border, marginTop: 4 },
  billTotalLabel:{ fontSize: 16, fontWeight: "700", color: COLORS.text },
  billTotalValue:{ fontSize: 18, fontWeight: "800", color: COLORS.accent },

  errorBanner:     { backgroundColor: COLORS.error + "18", borderRadius: 12, padding: 14, marginBottom: 8, borderWidth: 1, borderColor: COLORS.error + "40" },
  errorBannerText: { fontSize: 13, color: COLORS.error, lineHeight: 18 },

  payPanel: {
    backgroundColor: COLORS.surface,
    borderTopWidth: 0.5,
    borderColor: COLORS.border,
    padding: 20,
    paddingBottom: Platform.OS === "ios" ? 40 : 20,
    gap: 14,
  },
  payAmountRow:  { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  payAmountLabel:{ fontSize: 14, color: COLORS.textMuted },
  payAmountValue:{ fontSize: 22, fontWeight: "800", color: COLORS.accent },

  // Receipt styles
  receiptContainer:  { flex: 1 },
  receiptScroll:     { padding: 20, paddingBottom: 40 },
  successBadge:      { width: 72, height: 72, borderRadius: 36, backgroundColor: COLORS.accent, alignItems: "center", justifyContent: "center", alignSelf: "center", marginTop: 20, marginBottom: 12 },
  successIcon:       { fontSize: 32, color: COLORS.bg, fontWeight: "700" },
  successTitle:      { fontSize: 24, fontWeight: "800", color: COLORS.text, textAlign: "center" },
  successSub:        { fontSize: 13, color: COLORS.textMuted, textAlign: "center", marginTop: 4, marginBottom: 24, fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace" },

  receiptCard: {
    backgroundColor: COLORS.surface,
    borderRadius: 20,
    overflow: "hidden",
    borderWidth: 0.5,
    borderColor: COLORS.border,
    marginBottom: 20,
  },
  receiptHeader:    { alignItems: "center", padding: 20, backgroundColor: COLORS.surfaceHigh },
  receiptLogoMark:  { width: 28, height: 28, borderRadius: 8, backgroundColor: COLORS.accent, marginBottom: 8 },
  receiptStoreName: { fontSize: 18, fontWeight: "700", color: COLORS.text },
  receiptMeta:      { fontSize: 12, color: COLORS.textMuted, marginTop: 3 },
  receiptDivider:   { height: 0.5, backgroundColor: COLORS.border, marginHorizontal: 0 },
  receiptSection:   { padding: 16 },
  receiptSectionLabel: { fontSize: 9, fontWeight: "700", color: COLORS.textMuted, letterSpacing: 2, marginBottom: 10 },
  receiptCustomer:  { fontSize: 15, fontWeight: "600", color: COLORS.text },
  receiptCustomerPhone: { fontSize: 13, color: COLORS.textMuted, marginTop: 2 },
  receiptItemRow:   { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", paddingVertical: 6 },
  receiptItemLeft:  { flex: 1, marginRight: 12 },
  receiptItemName:  { fontSize: 13, fontWeight: "500", color: COLORS.text },
  receiptItemDetail:{ fontSize: 11, color: COLORS.textMuted, marginTop: 1 },
  receiptItemTotal: { fontSize: 13, fontWeight: "700", color: COLORS.text },
  receiptTotalRow:  { flexDirection: "row", justifyContent: "space-between", paddingVertical: 5 },
  receiptTotalLabel:{ fontSize: 13, color: COLORS.textMuted },
  receiptTotalValue:{ fontSize: 13, color: COLORS.text },
  receiptGrandRow:  { paddingTop: 10, borderTopWidth: 0.5, borderColor: COLORS.border, marginTop: 6 },
  receiptGrandLabel:{ fontSize: 15, fontWeight: "700", color: COLORS.text },
  receiptGrandValue:{ fontSize: 18, fontWeight: "800", color: COLORS.accent },
  receiptFooter:    { textAlign: "center", fontSize: 13, fontWeight: "600", color: COLORS.text, padding: 16, paddingBottom: 4 },
  receiptFooterSub: { textAlign: "center", fontSize: 11, color: COLORS.textMuted, paddingBottom: 16 },
});
