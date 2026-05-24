// SCO Compliance OS — Zustand store per impostazioni operative vault
// (auto-sync polling interval, auto-ingest trigger, font size UI).
// v0.8.1: stub locale; backend non cabla ancora questi parametri (sono settings
// di UX runtime, vivono interamente lato client e si applicano via hook).

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AutoSyncInterval = "off" | "5s" | "15s" | "30s" | "60s" | "5m";
export type FontSize = "small" | "medium" | "large";

export interface VaultSettingsState {
  // Polling interval per fetchConversations (oggi 5s hardcoded in Sidebar).
  // "off" disabilita il polling (richiesta manuale via pull-to-refresh).
  autoSyncInterval: AutoSyncInterval;
  // Auto-sync su file system change (richiede backend fs watcher, oggi N/A).
  autoSyncOnModify: boolean;
  // Auto-ingest dei file droppati nella chat (Conv. 43 Smart File Injection).
  // True = popup auto-trigger; False = nessun popup, solo contesto chat.
  autoIngestChatAttachments: boolean;
  // Auto-ingest dei risultati web search (skill autoresearch).
  autoIngestWebSearch: boolean;
  // UI font size scaler per accessibility.
  fontSize: FontSize;

  // Actions
  setAutoSyncInterval: (v: AutoSyncInterval) => void;
  setAutoSyncOnModify: (v: boolean) => void;
  setAutoIngestChatAttachments: (v: boolean) => void;
  setAutoIngestWebSearch: (v: boolean) => void;
  setFontSize: (v: FontSize) => void;
  reset: () => void;
}

export const useVaultSettingsStore = create<VaultSettingsState>()(
  persist(
    (set) => ({
      autoSyncInterval: "5s",
      autoSyncOnModify: false,
      autoIngestChatAttachments: true,
      autoIngestWebSearch: false,
      fontSize: "medium",

      setAutoSyncInterval: (v) => set({ autoSyncInterval: v }),
      setAutoSyncOnModify: (v) => set({ autoSyncOnModify: v }),
      setAutoIngestChatAttachments: (v) =>
        set({ autoIngestChatAttachments: v }),
      setAutoIngestWebSearch: (v) => set({ autoIngestWebSearch: v }),
      setFontSize: (v) => set({ fontSize: v }),

      reset: () =>
        set({
          autoSyncInterval: "5s",
          autoSyncOnModify: false,
          autoIngestChatAttachments: true,
          autoIngestWebSearch: false,
          fontSize: "medium",
        }),
    }),
    {
      name: "sco-vault-settings",
      version: 1,
    },
  ),
);
