// =============================================================
// ScannerScreen — Camera + Real-time Barcode Detection
// THE core screen of SmartCheckout.
//
// Flow: Camera opens → barcode detected → API call → product card
//       → user taps "Add to Cart" → scan next item
//
// Libraries: expo-camera (CameraView + useCameraPermissions)
// Barcode types: EAN-13, EAN-8, UPC-A, Code128, QR
// =============================================================

import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  View, Text, StyleSheet, TouchableOpacity, Animated,
  ActivityIndicator, Platform, StatusBar, Dimensions,
  Alert,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { useCart } from "../services/CartContext";
import { scanBarcode } from "../services/api";

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get("window");
const SCAN_AREA_SIZE = SCREEN_W * 0.7;
const DEBOUNCE_MS = 1500; // prevent re-scanning same barcode too fast

const COLORS = {
  bg:       "#0A0A0F",
  surface:  "#13131A",
  border:   "#2A2A3D",
  accent:   "#00E5A0",
  error:    "#FF5370",
  text:     "#F0F0F8",
  textMuted:"#6B6B8A",
  overlay:  "rgba(0,0,0,0.65)",
};

// =============================================================
// PERMISSION GATE SCREEN
// =============================================================
function PermissionScreen({ onRequest }) {
  return (
    <View style={styles.permContainer}>
      <Text style={styles.permIcon}>📷</Text>
      <Text style={styles.permTitle}>Camera Access Needed</Text>
      <Text style={styles.permDesc}>
        SmartCheckout needs camera access to scan product barcodes.
      </Text>
      <TouchableOpacity style={styles.permBtn} onPress={onRequest} activeOpacity={0.85}>
        <Text style={styles.permBtnText}>Grant Camera Access</Text>
      </TouchableOpacity>
    </View>
  );
}

// =============================================================
// PRODUCT RESULT CARD (shown after successful scan)
// =============================================================
function ProductCard({ product, onAdd, onDismiss, slideAnim }) {
  if (!product) return null;

  const taxAmt = product.selling_price * (product.tax_rate / 100);
  const priceInclTax = (product.selling_price + taxAmt).toFixed(2);

  return (
    <Animated.View style={[styles.productCard, { transform: [{ translateY: slideAnim }] }]}>
      <View style={styles.productCardHeader}>
        <View style={styles.productBadge}>
          <Text style={styles.productBadgeText}>SCANNED</Text>
        </View>
        <TouchableOpacity onPress={onDismiss} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
          <Text style={styles.dismissText}>✕</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.productName} numberOfLines={2}>{product.name}</Text>
      {product.brand && <Text style={styles.productBrand}>{product.brand}</Text>}

      <View style={styles.productMeta}>
        <View style={styles.priceBlock}>
          <Text style={styles.priceLabel}>MRP</Text>
          <Text style={styles.price}>₹{product.selling_price.toFixed(2)}</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.priceBlock}>
          <Text style={styles.priceLabel}>Incl. Tax ({product.tax_rate}%)</Text>
          <Text style={styles.priceSub}>₹{priceInclTax}</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.priceBlock}>
          <Text style={styles.priceLabel}>Stock</Text>
          <Text style={[styles.priceSub, { color: product.in_stock ? COLORS.accent : COLORS.error }]}>
            {product.qty_available} units
          </Text>
        </View>
      </View>

      {product.in_stock ? (
        <TouchableOpacity style={styles.addBtn} onPress={onAdd} activeOpacity={0.85}>
          <Text style={styles.addBtnText}>Add to Cart  +</Text>
        </TouchableOpacity>
      ) : (
        <View style={styles.outOfStockBanner}>
          <Text style={styles.outOfStockText}>Out of Stock</Text>
        </View>
      )}
    </Animated.View>
  );
}

// =============================================================
// SCANNER ERROR CARD
// =============================================================
function ErrorCard({ message, onDismiss }) {
  return (
    <View style={styles.errorCard}>
      <Text style={styles.errorIcon}>⚠</Text>
      <Text style={styles.errorTitle}>Not Found</Text>
      <Text style={styles.errorMessage}>{message}</Text>
      <TouchableOpacity style={styles.errorBtn} onPress={onDismiss} activeOpacity={0.85}>
        <Text style={styles.errorBtnText}>Scan Another</Text>
      </TouchableOpacity>
    </View>
  );
}

// =============================================================
// VIEWFINDER OVERLAY
// =============================================================
function Viewfinder({ isScanning }) {
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.4, duration: 800, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1,   duration: 800, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, []);

  return (
    <View style={styles.viewfinder} pointerEvents="none">
      {/* Scanning laser line */}
      {isScanning && (
        <Animated.View style={[styles.laserLine, { opacity: pulseAnim }]} />
      )}
      {/* Corner brackets */}
      <View style={[styles.corner, styles.cornerTL]} />
      <View style={[styles.corner, styles.cornerTR]} />
      <View style={[styles.corner, styles.cornerBL]} />
      <View style={[styles.corner, styles.cornerBR]} />
    </View>
  );
}

// =============================================================
// MAIN SCANNER SCREEN
// =============================================================
export default function ScannerScreen({ navigation }) {
  const { addItem, itemCount, storeId } = useCart();

  const [permission, requestPermission] = useCameraPermissions();
  const [facing,     setFacing]    = useState("back");
  const [torch,      setTorch]     = useState(false);
  const [state,      setState]     = useState("idle"); // idle | scanning | loading | result | error
  const [product,    setProduct]   = useState(null);
  const [errorMsg,   setErrorMsg]  = useState("");
  const [lastBarcode, setLastBarcode] = useState(null);

  const lastScanTime = useRef(0);
  const slideAnim    = useRef(new Animated.Value(300)).current;

  // Slide product card up
  function showCard() {
    Animated.spring(slideAnim, {
      toValue: 0,
      tension: 65,
      friction: 11,
      useNativeDriver: true,
    }).start();
  }

  // Slide card back down then reset
  function dismissCard() {
    Animated.timing(slideAnim, { toValue: 300, duration: 250, useNativeDriver: true }).start(() => {
      setProduct(null);
      setErrorMsg("");
      setLastBarcode(null);
      setState("idle");
    });
  }

  // ============================================================
  // CORE BARCODE HANDLER — called by expo-camera on every frame
  // that contains a barcode
  // ============================================================
  const onBarcodeScanned = useCallback(async ({ data: barcode, type }) => {
    const now = Date.now();

    // 1. Debounce: ignore if same barcode scanned within DEBOUNCE_MS
    if (barcode === lastBarcode && now - lastScanTime.current < DEBOUNCE_MS) return;

    // 2. Ignore if already processing
    if (state === "loading" || state === "result" || state === "error") return;

    lastScanTime.current = now;
    setLastBarcode(barcode);
    setState("loading");

    try {
      // 3. Call backend
      const response = await scanBarcode(barcode, storeId);

      if (response.found && response.product) {
        setProduct(response.product);
        setState("result");
        showCard();
      } else {
        setErrorMsg(response.error || "Barcode not found in catalogue");
        setState("error");
        showCard();
      }
    } catch (err) {
      setErrorMsg(err.message || "Network error. Try again.");
      setState("error");
      showCard();
    }
  }, [state, lastBarcode, storeId]);

  function handleAddToCart() {
    if (!product) return;
    addItem(product);
    dismissCard();
  }

  // ============================================================
  // PERMISSION HANDLING
  // ============================================================
  if (!permission) {
    return (
      <View style={styles.container}>
        <ActivityIndicator color={COLORS.accent} />
      </View>
    );
  }

  if (!permission.granted) {
    return <PermissionScreen onRequest={requestPermission} />;
  }

  // ============================================================
  // RENDER
  // ============================================================
  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />

      {/* CAMERA */}
      <CameraView
        style={StyleSheet.absoluteFill}
        facing={facing}
        enableTorch={torch}
        onBarcodeScanned={state === "idle" || state === "scanning" ? onBarcodeScanned : undefined}
        barcodeScannerSettings={{
          barcodeTypes: ["ean13", "ean8", "upc_a", "upc_e", "code128", "qr", "code39"],
        }}
      />

      {/* DARK OVERLAY — cutout for scan area */}
      <View style={styles.overlayTop}    pointerEvents="none" />
      <View style={styles.overlayMiddle} pointerEvents="none">
        <View style={styles.overlaySide} />
        <View style={styles.scanArea}>
          <Viewfinder isScanning={state === "idle"} />
        </View>
        <View style={styles.overlaySide} />
      </View>
      <View style={styles.overlayBottom} pointerEvents="none" />

      {/* TOP BAR */}
      <View style={styles.topBar}>
        <TouchableOpacity style={styles.topBtn} onPress={() => navigation.goBack()} activeOpacity={0.7}>
          <Text style={styles.topBtnText}>←</Text>
        </TouchableOpacity>

        <Text style={styles.topTitle}>Scan Product</Text>

        <TouchableOpacity style={styles.topBtn} onPress={() => setTorch((t) => !t)} activeOpacity={0.7}>
          <Text style={styles.topBtnText}>{torch ? "🔦" : "💡"}</Text>
        </TouchableOpacity>
      </View>

      {/* HINT TEXT */}
      <View style={styles.hintContainer} pointerEvents="none">
        <Text style={styles.hintText}>
          {state === "loading" ? "Looking up product…" : "Align barcode within the frame"}
        </Text>
      </View>

      {/* LOADING SPINNER (shown while API call is in flight) */}
      {state === "loading" && (
        <View style={styles.loadingOverlay} pointerEvents="none">
          <ActivityIndicator size="large" color={COLORS.accent} />
          <Text style={styles.loadingText}>Fetching product…</Text>
        </View>
      )}

      {/* PRODUCT RESULT CARD */}
      {state === "result" && product && (
        <ProductCard
          product={product}
          onAdd={handleAddToCart}
          onDismiss={dismissCard}
          slideAnim={slideAnim}
        />
      )}

      {/* ERROR CARD */}
      {state === "error" && (
        <Animated.View style={{ transform: [{ translateY: slideAnim }] }}>
          <ErrorCard message={errorMsg} onDismiss={dismissCard} />
        </Animated.View>
      )}

      {/* CART FAB */}
      {itemCount > 0 && (
        <TouchableOpacity
          style={styles.cartFab}
          onPress={() => navigation.navigate("Cart")}
          activeOpacity={0.85}
        >
          <Text style={styles.cartFabText}>🛒  {itemCount} item{itemCount !== 1 ? "s" : ""}</Text>
          <Text style={styles.cartFabArrow}>→</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

// =============================================================
// STYLES
// =============================================================
const CORNER_SIZE = 22;
const CORNER_WIDTH = 3;

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: "#000" },

  // --- Overlays that create the scan-area cutout ---
  overlayTop: {
    position: "absolute", top: 0, left: 0, right: 0,
    height: (SCREEN_H - SCAN_AREA_SIZE) / 2,
    backgroundColor: COLORS.overlay,
  },
  overlayMiddle: {
    position: "absolute",
    top: (SCREEN_H - SCAN_AREA_SIZE) / 2,
    left: 0, right: 0,
    height: SCAN_AREA_SIZE,
    flexDirection: "row",
  },
  overlaySide:  { flex: 1, backgroundColor: COLORS.overlay },
  scanArea:     { width: SCAN_AREA_SIZE, height: SCAN_AREA_SIZE },
  overlayBottom: {
    position: "absolute",
    top: (SCREEN_H - SCAN_AREA_SIZE) / 2 + SCAN_AREA_SIZE,
    left: 0, right: 0, bottom: 0,
    backgroundColor: COLORS.overlay,
  },

  // --- Viewfinder & corner brackets ---
  viewfinder: {
    flex: 1,
    position: "relative",
  },
  laserLine: {
    position: "absolute",
    top: "50%",
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: COLORS.accent,
    shadowColor: COLORS.accent,
    shadowRadius: 6,
    shadowOpacity: 0.8,
  },
  corner: {
    position: "absolute",
    width: CORNER_SIZE,
    height: CORNER_SIZE,
    borderColor: COLORS.accent,
  },
  cornerTL: { top: 0, left: 0, borderTopWidth: CORNER_WIDTH, borderLeftWidth: CORNER_WIDTH },
  cornerTR: { top: 0, right: 0, borderTopWidth: CORNER_WIDTH, borderRightWidth: CORNER_WIDTH },
  cornerBL: { bottom: 0, left: 0, borderBottomWidth: CORNER_WIDTH, borderLeftWidth: CORNER_WIDTH },
  cornerBR: { bottom: 0, right: 0, borderBottomWidth: CORNER_WIDTH, borderRightWidth: CORNER_WIDTH },

  // --- Top bar ---
  topBar: {
    position: "absolute",
    top: Platform.OS === "ios" ? 54 : 36,
    left: 0, right: 0,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
  },
  topBtn:     { width: 40, height: 40, borderRadius: 12, backgroundColor: "rgba(0,0,0,0.5)", alignItems: "center", justifyContent: "center" },
  topBtnText: { fontSize: 18, color: COLORS.text },
  topTitle:   { fontSize: 16, fontWeight: "700", color: COLORS.text },

  // --- Hint ---
  hintContainer: {
    position: "absolute",
    bottom: SCREEN_H - (SCREEN_H - SCAN_AREA_SIZE) / 2 + 16,
    left: 0, right: 0,
    alignItems: "center",
  },
  hintText: {
    fontSize: 13,
    color: "rgba(255,255,255,0.7)",
    backgroundColor: "rgba(0,0,0,0.4)",
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
  },

  // --- Loading overlay ---
  loadingOverlay: {
    position: "absolute",
    inset: 0,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
  },
  loadingText: { color: COLORS.accent, fontSize: 13 },

  // --- Product card ---
  productCard: {
    position: "absolute",
    bottom: 0, left: 0, right: 0,
    backgroundColor: COLORS.surface,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
    paddingBottom: Platform.OS === "ios" ? 40 : 28,
    borderTopWidth: 0.5,
    borderColor: COLORS.border,
    shadowColor: "#000",
    shadowRadius: 30,
    shadowOpacity: 0.6,
    shadowOffset: { width: 0, height: -8 },
    elevation: 20,
  },
  productCardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  productBadge:      { backgroundColor: COLORS.accent + "20", borderRadius: 6, paddingHorizontal: 10, paddingVertical: 4 },
  productBadgeText:  { fontSize: 10, fontWeight: "700", color: COLORS.accent, letterSpacing: 1.5 },
  dismissText:       { fontSize: 18, color: COLORS.textMuted },
  productName:       { fontSize: 20, fontWeight: "700", color: COLORS.text, lineHeight: 26, marginBottom: 4 },
  productBrand:      { fontSize: 13, color: COLORS.textMuted, marginBottom: 18 },

  productMeta:  { flexDirection: "row", alignItems: "center", marginBottom: 20, gap: 12 },
  priceBlock:   { flex: 1, alignItems: "center" },
  priceLabel:   { fontSize: 10, color: COLORS.textMuted, fontWeight: "600", letterSpacing: 0.5, marginBottom: 4, textAlign: "center" },
  price:        { fontSize: 22, fontWeight: "800", color: COLORS.accent },
  priceSub:     { fontSize: 16, fontWeight: "700", color: COLORS.text },
  divider:      { width: 1, height: 36, backgroundColor: COLORS.border },

  addBtn: {
    backgroundColor: COLORS.accent,
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: "center",
  },
  addBtnText:         { fontSize: 17, fontWeight: "700", color: COLORS.bg, letterSpacing: -0.3 },
  outOfStockBanner:   { backgroundColor: COLORS.error + "20", borderRadius: 12, paddingVertical: 14, alignItems: "center" },
  outOfStockText:     { fontSize: 15, fontWeight: "700", color: COLORS.error },

  // --- Error card ---
  errorCard: {
    position: "absolute",
    bottom: 0, left: 0, right: 0,
    backgroundColor: COLORS.surface,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 28,
    paddingBottom: Platform.OS === "ios" ? 44 : 32,
    alignItems: "center",
  },
  errorIcon:    { fontSize: 36, marginBottom: 8 },
  errorTitle:   { fontSize: 20, fontWeight: "700", color: COLORS.text, marginBottom: 8 },
  errorMessage: { fontSize: 14, color: COLORS.textMuted, textAlign: "center", lineHeight: 20, marginBottom: 20 },
  errorBtn: {
    backgroundColor: COLORS.surfaceHigh ?? "#1C1C27",
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  errorBtnText: { fontSize: 15, fontWeight: "600", color: COLORS.text },

  // --- Cart FAB ---
  cartFab: {
    position: "absolute",
    bottom: Platform.OS === "ios" ? 44 : 28,
    left: 20, right: 20,
    backgroundColor: COLORS.bg,
    borderRadius: 18,
    paddingVertical: 16,
    paddingHorizontal: 24,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
    borderColor: COLORS.accent,
    shadowColor: COLORS.accent,
    shadowRadius: 16,
    shadowOpacity: 0.3,
    shadowOffset: { width: 0, height: 4 },
    elevation: 10,
  },
  cartFabText:  { fontSize: 15, fontWeight: "600", color: COLORS.accent },
  cartFabArrow: { fontSize: 18, fontWeight: "700", color: COLORS.accent },

  // --- Permission ---
  permContainer: { flex: 1, backgroundColor: COLORS.bg, alignItems: "center", justifyContent: "center", paddingHorizontal: 40 },
  permIcon:      { fontSize: 56, marginBottom: 20 },
  permTitle:     { fontSize: 22, fontWeight: "700", color: COLORS.text, marginBottom: 12, textAlign: "center" },
  permDesc:      { fontSize: 14, color: COLORS.textMuted, textAlign: "center", lineHeight: 22, marginBottom: 32 },
  permBtn:       { backgroundColor: COLORS.accent, borderRadius: 16, paddingVertical: 16, paddingHorizontal: 32 },
  permBtnText:   { fontSize: 16, fontWeight: "700", color: COLORS.bg },
});
