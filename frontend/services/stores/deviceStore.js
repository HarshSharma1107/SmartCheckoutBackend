import { create } from "zustand";

export const useDeviceStore = create((set) => ({
  device_id: null,
  terminal_id: null,
  store_id: null,
  brand_id: null,
  config: {
    heartbeat_interval_s: 30,
    offline_mode_allowed: true,
    max_offline_orders: 0,
  },

  setDeviceConfig: (config) => set({
    device_id: config.device_id ?? config.device_id,
    terminal_id: config.terminal_id,
    store_id: config.store_id,
    brand_id: config.brand_id,
    config,
  }),

  clearDeviceConfig: () => set({
    device_id: null,
    terminal_id: null,
    store_id: null,
    brand_id: null,
    config: { heartbeat_interval_s: 30, offline_mode_allowed: true, max_offline_orders: 0 },
  }),
}));

