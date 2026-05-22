// =============================================================
// HomeScreen — Customer Info Entry
// Dark industrial theme. Clean, purposeful retail UX.
// =============================================================

import React, { useState, useEffect, useRef } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  StatusBar, KeyboardAvoidingView, Platform, ScrollView,
  Animated, ActivityIndicator, Alert,
} from "react-native";
import { useCart } from "../services/CartContext";
import { listStores, healthCheck } from "../services/api";

const COLORS = {
  bg:          "#0A0A0F",
  surface:     "#13131A",
  surfaceHigh: "#1C1C27",
  border:      "#2A2A3D",
  accent:      "#00E5A0",
  accentDim:   "#00E5A020",
  text:        "#F0F0F8",
  textMuted:   "#6B6B8A",
  error:       "#FF5370",
  errorDim:    "#FF537015",
  white:       "#FFFFFF",
};

export default function HomeScreen({ navigation }) {
  const { setCustomer, setStore, customer, items } = useCart();

  const [name,    setName]    = useState(customer?.name  || "");
  const [phone,   setPhone]   = useState(customer?.phone || "");
  const [stores,  setStores]  = useState([]);
  const [storeId, setStoreId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errors,  setErrors]  = useState({});

  const fadeAnim  = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim,  { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 500, useNativeDriver: true }),
    ]).start();

    loadStores();
  }, []);

  async function loadStores() {
    try {
      await healthCheck();
      const data = await listStores();
      setStores(data);
      if (data.length > 0) setStoreId(data[0].store_id);
    } catch {
      Alert.alert("Connection Error", "Cannot reach the server. Check your API_URL in api.js.");
    } finally {
      setLoading(false);
    }
  }

  function validate() {
    const errs = {};
    if (!name.trim())                              errs.name  = "Name is required";
    if (!phone.trim())                             errs.phone = "Phone is required";
    else if (phone.replace(/\D/g, "").length < 10) errs.phone = "Enter a valid 10-digit number";
    if (!storeId)                                  errs.store = "Select a store to continue";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleStart() {
    if (!validate()) return;
    setCustomer({ name: name.trim(), phone: phone.trim() });
    setStore(storeId);
    navigation.navigate("Scanner");
  }

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.accent} />
        <Text style={styles.loadingText}>Connecting to store…</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={{ flex: 1 }}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <Animated.View style={[styles.header, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
            {/* Logo mark */}
            <View style={styles.logoMark}>
              <View style={styles.logoInner} />
            </View>
            <Text style={styles.appName}>SmartCheckout</Text>
            <Text style={styles.tagline}>Scan. Add. Pay. Done.</Text>
          </Animated.View>

          <Animated.View style={[styles.card, { opacity: fadeAnim }]}>
            <Text style={styles.sectionLabel}>CUSTOMER DETAILS</Text>

            {/* Name */}
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>Full Name</Text>
              <TextInput
                style={[styles.input, errors.name && styles.inputError]}
                placeholder="e.g. Rahul Sharma"
                placeholderTextColor={COLORS.textMuted}
                value={name}
                onChangeText={(v) => { setName(v); setErrors((e) => ({ ...e, name: null })); }}
                autoCapitalize="words"
                returnKeyType="next"
              />
              {errors.name && <Text style={styles.errorText}>{errors.name}</Text>}
            </View>

            {/* Phone */}
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>Phone Number</Text>
              <TextInput
                style={[styles.input, errors.phone && styles.inputError]}
                placeholder="e.g. 9876543210"
                placeholderTextColor={COLORS.textMuted}
                value={phone}
                onChangeText={(v) => { setPhone(v.replace(/\D/g, "")); setErrors((e) => ({ ...e, phone: null })); }}
                keyboardType="phone-pad"
                maxLength={13}
                returnKeyType="done"
              />
              {errors.phone && <Text style={styles.errorText}>{errors.phone}</Text>}
            </View>

            {/* Store selection */}
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>Store</Text>
              <View style={styles.storeGrid}>
                {stores.map((s) => (
                  <TouchableOpacity
                    key={s.store_id}
                    style={[styles.storeChip, storeId === s.store_id && styles.storeChipActive]}
                    onPress={() => { setStoreId(s.store_id); setErrors((e) => ({ ...e, store: null })); }}
                    activeOpacity={0.7}
                  >
                    <Text style={[styles.storeChipText, storeId === s.store_id && styles.storeChipTextActive]}>
                      {s.name}
                    </Text>
                    {s.city && (
                      <Text style={[styles.storeChipCity, storeId === s.store_id && styles.storeChipTextActive]}>
                        {s.city}
                      </Text>
                    )}
                  </TouchableOpacity>
                ))}
              </View>
              {errors.store && <Text style={styles.errorText}>{errors.store}</Text>}
            </View>
          </Animated.View>

          {/* Cart summary (if returning) */}
          {items.length > 0 && (
            <TouchableOpacity style={styles.cartResume} onPress={() => navigation.navigate("Cart")} activeOpacity={0.8}>
              <Text style={styles.cartResumeText}>📦  {items.length} item{items.length !== 1 ? "s" : ""} in cart</Text>
              <Text style={styles.cartResumeAction}>View →</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity style={styles.startBtn} onPress={handleStart} activeOpacity={0.85}>
            <Text style={styles.startBtnText}>Start Shopping</Text>
            <Text style={styles.startBtnIcon}>→</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container:        { flex: 1, backgroundColor: COLORS.bg },
  loadingContainer: { flex: 1, backgroundColor: COLORS.bg, alignItems: "center", justifyContent: "center", gap: 16 },
  loadingText:      { color: COLORS.textMuted, fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace", fontSize: 13 },
  scroll:           { flexGrow: 1, paddingHorizontal: 20, paddingTop: 60, paddingBottom: 40 },

  header:           { alignItems: "center", marginBottom: 36 },
  logoMark:         { width: 56, height: 56, borderRadius: 16, backgroundColor: COLORS.accent, alignItems: "center", justifyContent: "center", marginBottom: 16 },
  logoInner:        { width: 24, height: 24, borderRadius: 6, backgroundColor: COLORS.bg },
  appName:          { fontSize: 28, fontWeight: "700", color: COLORS.text, letterSpacing: -0.5 },
  tagline:          { fontSize: 14, color: COLORS.textMuted, marginTop: 4, letterSpacing: 0.3 },

  card:             { backgroundColor: COLORS.surface, borderRadius: 20, padding: 20, borderWidth: 0.5, borderColor: COLORS.border, marginBottom: 16 },
  sectionLabel:     { fontSize: 10, fontWeight: "700", color: COLORS.textMuted, letterSpacing: 2, marginBottom: 16 },

  fieldGroup:       { marginBottom: 18 },
  label:            { fontSize: 12, fontWeight: "600", color: COLORS.textMuted, marginBottom: 8, letterSpacing: 0.5 },
  input: {
    backgroundColor: COLORS.surfaceHigh,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: COLORS.text,
  },
  inputError:       { borderColor: COLORS.error, backgroundColor: COLORS.errorDim },
  errorText:        { fontSize: 12, color: COLORS.error, marginTop: 6 },

  storeGrid:        { gap: 8 },
  storeChip: {
    backgroundColor: COLORS.surfaceHigh,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 12,
    padding: 14,
  },
  storeChipActive:      { backgroundColor: COLORS.accentDim, borderColor: COLORS.accent },
  storeChipText:        { fontSize: 14, fontWeight: "600", color: COLORS.textMuted },
  storeChipTextActive:  { color: COLORS.accent },
  storeChipCity:        { fontSize: 12, color: COLORS.textMuted, marginTop: 2 },

  cartResume: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: COLORS.surfaceHigh,
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cartResumeText:   { fontSize: 14, color: COLORS.text },
  cartResumeAction: { fontSize: 14, color: COLORS.accent, fontWeight: "600" },

  startBtn: {
    backgroundColor: COLORS.accent,
    borderRadius: 16,
    paddingVertical: 18,
    paddingHorizontal: 24,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  startBtnText:     { fontSize: 17, fontWeight: "700", color: COLORS.bg, letterSpacing: -0.3 },
  startBtnIcon:     { fontSize: 20, fontWeight: "700", color: COLORS.bg },
});
