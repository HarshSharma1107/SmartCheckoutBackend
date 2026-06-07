// =============================================================
// CartScreen — Full cart view with quantity controls
// =============================================================

import React, { useCallback } from "react";
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  Platform, StatusBar, Alert,
} from "react-native";
import { useCart } from "../services/CartContext";

const COLORS = {
  bg:       "#0A0A0F",
  surface:  "#13131A",
  surfaceHigh: "#1C1C27",
  border:   "#2A2A3D",
  accent:   "#00E5A0",
  error:    "#FF5370",
  text:     "#F0F0F8",
  textMuted:"#6B6B8A",
};

function CartItem({ item, onIncrease, onDecrease, onRemove }) {
  const { product, quantity } = item;
  const lineBase   = product.selling_price * quantity;
  const tax        = lineBase * (product.tax_rate / 100);
  const lineTotal  = lineBase + tax;

  return (
    <View style={styles.itemCard}>
      <View style={styles.itemTop}>
        <View style={styles.itemInfo}>
          <Text style={styles.itemName} numberOfLines={2}>{product.name}</Text>
          {product.brand && <Text style={styles.itemBrand}>{product.brand}</Text>}
          <Text style={styles.itemSku}>{product.sku}</Text>
        </View>
        <TouchableOpacity onPress={() => onRemove(product.product_id)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <Text style={styles.removeBtn}>✕</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.itemBottom}>
        {/* Quantity stepper */}
        <View style={styles.stepper}>
          <TouchableOpacity
            style={[styles.stepBtn, quantity <= 1 && styles.stepBtnDanger]}
            onPress={() => onDecrease(product.product_id, quantity - 1)}
          >
            <Text style={[styles.stepBtnText, quantity <= 1 && styles.stepBtnTextDanger]}>
              {quantity <= 1 ? "🗑" : "−"}
            </Text>
          </TouchableOpacity>

          <Text style={styles.qtyText}>{quantity}</Text>

          <TouchableOpacity
            style={[styles.stepBtn, quantity >= product.qty_available && styles.stepBtnDisabled]}
            onPress={() => quantity < product.qty_available && onIncrease(product.product_id, quantity + 1)}
            disabled={quantity >= product.qty_available}
          >
            <Text style={styles.stepBtnText}>+</Text>
          </TouchableOpacity>
        </View>

        {/* Price */}
        <View style={styles.priceCol}>
          <Text style={styles.unitPrice}>₹{product.selling_price.toFixed(2)} × {quantity}</Text>
          <Text style={styles.lineTotal}>₹{lineTotal.toFixed(2)}</Text>
          <Text style={styles.taxNote}>incl. {product.tax_rate}% GST</Text>
        </View>
      </View>
    </View>
  );
}

function EmptyCart({ onScan }) {
  return (
    <View style={styles.emptyContainer}>
      <Text style={styles.emptyIcon}>🛒</Text>
      <Text style={styles.emptyTitle}>Cart is empty</Text>
      <Text style={styles.emptyDesc}>Scan products to add them here</Text>
      <TouchableOpacity style={styles.scanNowBtn} onPress={onScan} activeOpacity={0.85}>
        <Text style={styles.scanNowBtnText}>Scan a Product</Text>
      </TouchableOpacity>
    </View>
  );
}

export default function CartScreen({ navigation }) {
  const { items, customer, subtotal, taxTotal, grandTotal, updateQuantity, removeItem } = useCart();

  const handleIncrease = useCallback((productId, qty) => updateQuantity(productId, qty), []);
  const handleDecrease = useCallback((productId, qty) => {
    if (qty <= 0) {
      Alert.alert(
        "Remove Item",
        "Remove this item from cart?",
        [
          { text: "Cancel", style: "cancel" },
          { text: "Remove", style: "destructive", onPress: () => removeItem(productId) },
        ]
      );
    } else {
      updateQuantity(productId, qty);
    }
  }, []);

  const handleRemove = useCallback((productId) => {
    Alert.alert(
      "Remove Item",
      "Remove this item from your cart?",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Remove", style: "destructive", onPress: () => removeItem(productId) },
      ]
    );
  }, []);

  const renderItem = ({ item }) => (
    <CartItem
      item={item}
      onIncrease={handleIncrease}
      onDecrease={handleDecrease}
      onRemove={handleRemove}
    />
  );

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backBtnText}>←</Text>
        </TouchableOpacity>
        <View>
          <Text style={styles.headerTitle}>Your Cart</Text>
          {customer && (
            <Text style={styles.headerSub}>{customer.name} · {customer.phone}</Text>
          )}
        </View>
        <TouchableOpacity
          style={styles.scanMoreBtn}
          onPress={() => navigation.navigate("Scanner")}
        >
          <Text style={styles.scanMoreText}>Scan +</Text>
        </TouchableOpacity>
      </View>

      {items.length === 0 ? (
        <EmptyCart onScan={() => navigation.navigate("Scanner")} />
      ) : (
        <>
          <FlatList
            data={items}
            keyExtractor={(i) => i.product.product_id}
            renderItem={renderItem}
            contentContainerStyle={styles.list}
            showsVerticalScrollIndicator={false}
            ItemSeparatorComponent={() => <View style={styles.separator} />}
          />

          {/* Summary panel */}
          <View style={styles.summaryPanel}>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Subtotal</Text>
              <Text style={styles.summaryValue}>₹{subtotal.toFixed(2)}</Text>
            </View>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>GST</Text>
              <Text style={styles.summaryValue}>₹{taxTotal.toFixed(2)}</Text>
            </View>
            <View style={[styles.summaryRow, styles.summaryTotal]}>
              <Text style={styles.totalLabel}>Total Payable</Text>
              <Text style={styles.totalValue}>₹{grandTotal.toFixed(2)}</Text>
            </View>

            <TouchableOpacity
              style={styles.checkoutBtn}
              onPress={() => navigation.navigate("Checkout")}
              activeOpacity={0.85}
            >
              <Text style={styles.checkoutBtnText}>Proceed to Checkout</Text>
              <Text style={styles.checkoutArrow}>→</Text>
            </TouchableOpacity>
          </View>
        </>
      )}
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
  headerSub:   { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },
  scanMoreBtn: { backgroundColor: COLORS.accent + "20", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 8, borderWidth: 1, borderColor: COLORS.accent },
  scanMoreText: { fontSize: 13, fontWeight: "600", color: COLORS.accent },

  list:        { padding: 16, paddingBottom: 8 },
  separator:   { height: 10 },

  itemCard: {
    backgroundColor: COLORS.surface,
    borderRadius: 16,
    padding: 16,
    borderWidth: 0.5,
    borderColor: COLORS.border,
  },
  itemTop:     { flexDirection: "row", marginBottom: 14 },
  itemInfo:    { flex: 1, marginRight: 12 },
  itemName:    { fontSize: 15, fontWeight: "600", color: COLORS.text, lineHeight: 20 },
  itemBrand:   { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },
  itemSku:     { fontSize: 11, color: COLORS.border, marginTop: 2, fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace" },
  removeBtn:   { fontSize: 16, color: COLORS.textMuted },

  itemBottom:  { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },

  stepper:     { flexDirection: "row", alignItems: "center", gap: 0, backgroundColor: COLORS.surfaceHigh, borderRadius: 12, overflow: "hidden", borderWidth: 1, borderColor: COLORS.border },
  stepBtn:     { width: 40, height: 40, alignItems: "center", justifyContent: "center" },
  stepBtnDanger:     { backgroundColor: COLORS.error + "20" },
  stepBtnDisabled:   { opacity: 0.4 },
  stepBtnText:       { fontSize: 18, fontWeight: "600", color: COLORS.text },
  stepBtnTextDanger: { color: COLORS.error },
  qtyText:     { fontSize: 16, fontWeight: "700", color: COLORS.text, minWidth: 32, textAlign: "center" },

  priceCol:    { alignItems: "flex-end" },
  unitPrice:   { fontSize: 12, color: COLORS.textMuted },
  lineTotal:   { fontSize: 18, fontWeight: "700", color: COLORS.accent, marginTop: 2 },
  taxNote:     { fontSize: 10, color: COLORS.textMuted, marginTop: 1 },

  emptyContainer: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 40 },
  emptyIcon:      { fontSize: 64, marginBottom: 20 },
  emptyTitle:     { fontSize: 22, fontWeight: "700", color: COLORS.text, marginBottom: 8 },
  emptyDesc:      { fontSize: 14, color: COLORS.textMuted, textAlign: "center", marginBottom: 28 },
  scanNowBtn:     { backgroundColor: COLORS.accent, borderRadius: 14, paddingVertical: 14, paddingHorizontal: 32 },
  scanNowBtnText: { fontSize: 16, fontWeight: "700", color: COLORS.bg },

  summaryPanel: {
    backgroundColor: COLORS.surface,
    borderTopWidth: 0.5,
    borderColor: COLORS.border,
    padding: 20,
    paddingBottom: Platform.OS === "ios" ? 36 : 20,
  },
  summaryRow:   { flexDirection: "row", justifyContent: "space-between", marginBottom: 8 },
  summaryLabel: { fontSize: 14, color: COLORS.textMuted },
  summaryValue: { fontSize: 14, color: COLORS.text },
  summaryTotal: { paddingTop: 12, borderTopWidth: 0.5, borderColor: COLORS.border, marginTop: 4, marginBottom: 16 },
  totalLabel:   { fontSize: 16, fontWeight: "700", color: COLORS.text },
  totalValue:   { fontSize: 20, fontWeight: "800", color: COLORS.accent },
  checkoutBtn: {
    backgroundColor: COLORS.accent,
    borderRadius: 16,
    paddingVertical: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  checkoutBtnText: { fontSize: 17, fontWeight: "700", color: COLORS.bg },
  checkoutArrow:   { fontSize: 20, fontWeight: "700", color: COLORS.bg },
});
