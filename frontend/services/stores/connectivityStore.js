import { create } from "zustand";

export const useConnectivityStore = create((set) => ({
  online: true,
  mqtt_connected: false,
  last_heartbeat_at: null,
  offline_queue_depth: 0,

  setOnline: (online) => set({ online }),
  setMqttConnected: (mqtt_connected) => set({ mqtt_connected }),
  markHeartbeat: () => set({ last_heartbeat_at: new Date().toISOString() }),
  setOfflineQueueDepth: (offline_queue_depth) => set({ offline_queue_depth }),
}));

