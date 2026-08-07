// =============================================================
// HomeScreen — Customer Info Entry
// Dark industrial theme. Clean, purposeful retail UX.
// =============================================================

import React, { useState, useRef, useEffect } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  StatusBar, KeyboardAvoidingView, Platform, ScrollView,
  Animated,
} from "react-native";
import { useCart } from "../services/CartContext";
import { COLORS, RADIUS } from "../theme";
import PrimaryButton from "../components/PrimaryButton";
import Card from "../components/Card";

export default function HomeScreen({ navigation }) {
  // storeId is set by TerminalStoreSync (App.js) once the device's
  // provisioning assignment resolves - customers never pick a store here.
  const { setCustomer, customer, items } = useCart();

  const [name,    setName]    = useState(customer?.name  || "");
  const [phone,   setPhone]   = useState(customer?.phone || "");
  const [email,   setEmail]   = useState(customer?.email || "");
  const [errors,  setErrors]  = useState({});

  const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

  // Mirrors backend.schemas.OrderCreateRequest.phone_must_be_valid exactly -
  // a number this screen accepts must never be rejected later at checkout.
  function normalizeIndianPhone(raw) {
    let digits = raw.replace(/\D/g, "");
    if (digits.length === 12 && digits.startsWith("91")) digits = digits.slice(2);
    else if (digits.length === 11 && digits.startsWith("0")) digits = digits.slice(1);
    return digits;
  }

  function isValidIndianPhone(raw) {
    const digits = normalizeIndianPhone(raw);
    return digits.length === 10 && /^[6-9]/.test(digits);
  }

  const formIsValid = name.trim().length > 0 && isValidIndianPhone(phone) && EMAIL_RE.test(email.trim());

  const fadeAnim  = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim,  { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 500, useNativeDriver: true }),
    ]).start();
  }, []);

  function validate() {
    const errs = {};
    if (!name.trim())                        errs.name  = "Name is required";
    if (!phone.trim())                       errs.phone = "Phone is required";
    else if (!isValidIndianPhone(phone))     errs.phone = "Enter a valid 10-digit mobile number.";
    if (!email.trim())                       errs.email = "Email is required";
    else if (!EMAIL_RE.test(email.trim()))   errs.email = "Enter a valid email address";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleStart() {
    if (!validate()) return;
    setCustomer({ name: name.trim(), phone: normalizeIndianPhone(phone), email: email.trim() });
    navigation.navigate("Scanner");
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

          <Animated.View style={{ opacity: fadeAnim }}>
          <Card style={styles.card}>
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

            {/* Email */}
            <View style={styles.fieldGroup}>
              <Text style={styles.label}>Email</Text>
              <TextInput
                style={[styles.input, errors.email && styles.inputError]}
                placeholder="e.g. rahul@example.com"
                placeholderTextColor={COLORS.textMuted}
                value={email}
                onChangeText={(v) => { setEmail(v); setErrors((e) => ({ ...e, email: null })); }}
                autoCapitalize="none"
                keyboardType="email-address"
                returnKeyType="done"
              />
              {errors.email && <Text style={styles.errorText}>{errors.email}</Text>}
            </View>
          </Card>
          </Animated.View>

          {/* Cart summary (if returning) */}
          {items.length > 0 && (
            <TouchableOpacity style={styles.cartResume} onPress={() => navigation.navigate("Cart")} activeOpacity={0.8}>
              <Text style={styles.cartResumeText}>📦  {items.length} item{items.length !== 1 ? "s" : ""} in cart</Text>
              <Text style={styles.cartResumeAction}>View →</Text>
            </TouchableOpacity>
          )}

          <PrimaryButton
            label="Start Shopping"
            icon="→"
            onPress={handleStart}
            disabled={!formIsValid}
            style={styles.startBtn}
          />
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
  logoMark:         { width: 56, height: 56, borderRadius: RADIUS.lg, backgroundColor: COLORS.accent, alignItems: "center", justifyContent: "center", marginBottom: 16 },
  logoInner:        { width: 24, height: 24, borderRadius: 6, backgroundColor: COLORS.bg },
  appName:          { fontSize: 28, fontWeight: "700", color: COLORS.text, letterSpacing: -0.5 },
  tagline:          { fontSize: 14, color: COLORS.textMuted, marginTop: 4, letterSpacing: 0.3 },

  // Home's customer-details card intentionally uses a larger radius/padding
  // than the standard Card default (16/16) for emphasis - preserved via
  // override rather than normalized away.
  card:             { borderRadius: RADIUS.xl, padding: 20, marginBottom: 16 },
  sectionLabel:     { fontSize: 10, fontWeight: "700", color: COLORS.textMuted, letterSpacing: 2, marginBottom: 16 },

  fieldGroup:       { marginBottom: 18 },
  label:            { fontSize: 12, fontWeight: "600", color: COLORS.textMuted, marginBottom: 8, letterSpacing: 0.5 },
  input: {
    backgroundColor: COLORS.surfaceHigh,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: RADIUS.sm,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: COLORS.text,
  },
  inputError:       { borderColor: COLORS.error, backgroundColor: COLORS.errorDim },
  errorText:        { fontSize: 12, color: COLORS.error, marginTop: 6 },

  cartResume: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: COLORS.surfaceHigh,
    borderRadius: RADIUS.sm,
    padding: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cartResumeText:   { fontSize: 14, color: COLORS.text },
  cartResumeAction: { fontSize: 14, color: COLORS.accent, fontWeight: "600" },

  startBtn: { paddingVertical: 18 },
});
