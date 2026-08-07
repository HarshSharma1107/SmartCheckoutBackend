// =============================================================
// CartScreen — Full cart view with quantity controls
// =============================================================

import React, { useCallback } from "react";
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  Platform, StatusBar, Alert,
} from "react-native";
import { useCart } from "../services/CartContext";
import { COLORS, RADIUS } from "../theme";
import PrimaryButton from "../components/PrimaryButton";
import Card from "../components/Card";
import IconState from "../components/IconState";

function CartItem({ item, onIncrease, onDecrease, onRemove }) {
  const { product, quantity } = item;
  const lineBase   = product.selling_price * quantity;
  const tax        = lineBase * (product.tax_rate / 100);
  const lineTotal  = lineBase + tax;

  return (
    <Card>
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
    </Card>
  );
}

function EmptyCart({ onScan }) {
  return (
    <IconState
      icon="🛒"
      title="Cart is empty"
      description="Scan products to add them here"
      actionLabel="Scan a Product"
      onAction={onScan}
    />
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

            <PrimaryButton
              label="Proceed to Checkout"
              icon="→"
              onPress={() => navigation.navigate("Checkout")}
            />
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
});
