// =============================================================
// SmartCheckout — Cart Context
// Global cart state shared across all screens.
// =============================================================

import React, { createContext, useContext, useReducer, useCallback } from "react";

const CartContext = createContext(null);

const initialState = {
  items: [],         // [{ product, quantity }]
  customer: null,    // { name, phone }
  storeId: null,
};

function cartReducer(state, action) {
  switch (action.type) {

    case "SET_CUSTOMER":
      return { ...state, customer: action.payload };

    case "SET_STORE":
      return { ...state, storeId: action.payload };

    case "ADD_ITEM": {
      const { product } = action.payload;
      const existing = state.items.find((i) => i.product.product_id === product.product_id);
      if (existing) {
        // Increment quantity (cap at available stock)
        return {
          ...state,
          items: state.items.map((i) =>
            i.product.product_id === product.product_id
              ? { ...i, quantity: Math.min(i.quantity + 1, product.qty_available) }
              : i
          ),
        };
      }
      // New item
      return {
        ...state,
        items: [...state.items, { product, quantity: 1 }],
      };
    }

    case "UPDATE_QUANTITY": {
      const { productId, quantity } = action.payload;
      if (quantity <= 0) {
        return {
          ...state,
          items: state.items.filter((i) => i.product.product_id !== productId),
        };
      }
      return {
        ...state,
        items: state.items.map((i) =>
          i.product.product_id === productId
            ? { ...i, quantity: Math.min(quantity, i.product.qty_available) }
            : i
        ),
      };
    }

    case "REMOVE_ITEM":
      return {
        ...state,
        items: state.items.filter((i) => i.product.product_id !== action.payload),
      };

    case "CLEAR_CART":
      return { ...initialState };

    default:
      return state;
  }
}

export function CartProvider({ children }) {
  const [state, dispatch] = useReducer(cartReducer, initialState);

  const setCustomer  = useCallback((customer) => dispatch({ type: "SET_CUSTOMER", payload: customer }), []);
  const setStore     = useCallback((storeId)  => dispatch({ type: "SET_STORE",    payload: storeId }), []);
  const addItem      = useCallback((product)  => dispatch({ type: "ADD_ITEM",     payload: { product } }), []);
  const removeItem   = useCallback((productId) => dispatch({ type: "REMOVE_ITEM", payload: productId }), []);
  const clearCart    = useCallback(()          => dispatch({ type: "CLEAR_CART" }), []);

  const updateQuantity = useCallback((productId, quantity) =>
    dispatch({ type: "UPDATE_QUANTITY", payload: { productId, quantity } }), []);

  // Derived values
  const itemCount = state.items.reduce((s, i) => s + i.quantity, 0);

  const subtotal  = state.items.reduce((s, i) => s + i.product.selling_price * i.quantity, 0);

  const taxTotal  = state.items.reduce((s, i) => {
    const base   = i.product.selling_price * i.quantity;
    const cgst   = base * (i.product.cgst_rate / 100);
    const sgst   = base * (i.product.sgst_rate / 100);
    return s + cgst + sgst;
  }, 0);

  const grandTotal = subtotal + taxTotal;

  const orderPayload = state.customer && state.storeId
    ? {
        customer_name:  state.customer.name,
        customer_phone: state.customer.phone,
        store_id:       state.storeId,
        items: state.items.map((i) => ({
          product_id: i.product.product_id,
          quantity:   i.quantity,
        })),
        payment_method: "CASH",
      }
    : null;

  return (
    <CartContext.Provider value={{
      items:       state.items,
      customer:    state.customer,
      storeId:     state.storeId,
      itemCount,
      subtotal,
      taxTotal,
      grandTotal,
      orderPayload,
      setCustomer,
      setStore,
      addItem,
      removeItem,
      updateQuantity,
      clearCart,
    }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
