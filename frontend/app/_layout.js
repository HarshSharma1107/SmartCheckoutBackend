import { Stack } from "expo-router";
import { CartProvider } from "../services/CartContext";

export default function Layout() {
  return (
    <CartProvider>
      <Stack />
    </CartProvider>
  );
}