import { create } from "zustand";

export const useCustomerStore = create((set) => ({
  customer_id: null,
  name: null,
  phone: null,
  loyalty_points: 0,
  logged_in: false,
  whatsapp_opt_in: false,

  setCustomer: (customer) => set({
    customer_id: customer.customer_id,
    name: customer.name,
    phone: customer.phone,
    loyalty_points: customer.loyalty_points ?? 0,
    logged_in: Boolean(customer.customer_id),
    whatsapp_opt_in: Boolean(customer.whatsapp_opt_in),
  }),

  clearCustomer: () => set({
    customer_id: null,
    name: null,
    phone: null,
    loyalty_points: 0,
    logged_in: false,
    whatsapp_opt_in: false,
  }),
}));

