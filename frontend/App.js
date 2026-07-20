// =============================================================
// SmartCheckout — Root App
// Navigation + Context wiring
// =============================================================

import React, { useEffect } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { CartProvider, useCart } from "./services/CartContext";
import { TerminalProvider, useTerminal } from "./services/TerminalContext";

import HomeScreen                 from "./screens/HomeScreen";
import ScannerScreen              from "./screens/ScannerScreen";
import CartScreen                 from "./screens/CartScreen";
import CheckoutScreen             from "./screens/CheckoutScreen";
import ProvisioningPendingScreen  from "./screens/ProvisioningPendingScreen";

const Stack = createNativeStackNavigator();

// Once the device is assigned to a store, this is the only place storeId
// gets set - HomeScreen no longer asks the customer to pick one.
//
// Mounted for the app's whole lifetime (outside RootNavigator's
// status-gated render) rather than only while "assigned" - if it were
// nested inside that branch, the moment terminal resets to null, status
// flips away from "assigned" in the same batched update, RootNavigator
// swaps to ProvisioningPendingScreen, and this component would unmount
// before its effect ever saw terminal===null to clear the stale cart.
function TerminalStoreSync() {
  const { terminal } = useTerminal();
  const { setStore, clearCart, storeId } = useCart();

  useEffect(() => {
    if (terminal?.storeId) {
      // Reassigned to a different store than the cart currently holds -
      // drop stale items/customer before adopting the new store, so an
      // order can never be placed against the wrong store.
      if (storeId && storeId !== terminal.storeId) {
        clearCart();
      }
      setStore(terminal.storeId);
    } else if (storeId) {
      // Terminal was revoked/reset (admin reassigned this device, or a
      // heartbeat/refresh failure tore down terminal state) - the cart's
      // storeId/items are no longer valid for any store.
      clearCart();
    }
  }, [terminal, setStore, clearCart, storeId]);

  return null;
}

function RootNavigator() {
  const { status } = useTerminal();

  if (status !== "assigned") {
    return <ProvisioningPendingScreen />;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Home"
        screenOptions={{ headerShown: false, animation: "slide_from_right" }}
      >
        <Stack.Screen name="Home"     component={HomeScreen} />
        <Stack.Screen name="Scanner"  component={ScannerScreen} />
        <Stack.Screen name="Cart"     component={CartScreen} />
        <Stack.Screen name="Checkout" component={CheckoutScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <CartProvider>
        <TerminalProvider>
          <TerminalStoreSync />
          <RootNavigator />
        </TerminalProvider>
      </CartProvider>
    </SafeAreaProvider>
  );
}
