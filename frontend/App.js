// =============================================================
// SmartCheckout — Root App
// Navigation + Context wiring
// =============================================================

import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { CartProvider } from "./services/CartContext";

import HomeScreen     from "./screens/HomeScreen";
import ScannerScreen  from "./screens/ScannerScreen";
import CartScreen     from "./screens/CartScreen";
import CheckoutScreen from "./screens/CheckoutScreen";

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <CartProvider>
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
    </CartProvider>
  );
}
