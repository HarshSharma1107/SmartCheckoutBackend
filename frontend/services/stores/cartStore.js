import { create } from "zustand";

export const useCartStore = create((set, get) => ({
  order_id: null,
  items: [],
  totals: {
    subtotal: 0,
    cgst_total: 0,
    sgst_total: 0,
    grand_total: 0,
  },
  status: "IDLE",

  startOrder: (order) => set({ order_id: order.order_id, status: order.status || "ACTIVE" }),

  addOrUpdateItem: (item) => set((state) => {
    const existing = state.items.find((x) => x.item_id === item.item_id);
    const items = existing
      ? state.items.map((x) => (x.item_id === item.item_id ? item : x))
      : [...state.items, item];
    return { items };
  }),

  removeItem: (itemId) => set((state) => ({
    items: state.items.filter((item) => item.item_id !== itemId),
  })),

  setTotals: (totals) => set({ totals }),

  setStatus: (status) => set({ status }),

  resetCart: () => set({
    order_id: null,
    items: [],
    totals: { subtotal: 0, cgst_total: 0, sgst_total: 0, grand_total: 0 },
    status: "IDLE",
  }),

  itemCount: () => get().items.reduce((sum, item) => sum + item.quantity, 0),
}));

