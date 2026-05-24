// SCO Compliance OS — Zustand store per stato connettori OAuth
// Conv. 48 enforcement: backend è single source of truth; frontend deduce status via fetch /api/integrations/available.
// Pattern parallelo a license-store.ts: stesso shape (loading + initialFetchDone + errorMessage + actions).

import { create } from "zustand";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

export type IntegrationStatus =
  | "pending"
  | "connected"
  | "error"
  | "disconnected";

// Shape allineata al Pydantic IntegrationInfo del backend (integrations_routes.py).
export interface IntegrationItem {
  slug: string;
  name: string;
  description: string;
  status: IntegrationStatus;
  iconSlug: string | null;
  lastSyncAt: string | null;
  account: string | null;
}

interface BackendIntegrationInfo {
  slug: string;
  name: string;
  description: string;
  status: string;
  icon_slug?: string | null;
  last_sync_at?: string | null;
  account?: string | null;
}

interface BackendConnectResponse {
  slug: string;
  oauth_url: string;
  state_token: string;
  message: string;
}

export interface IntegrationsState {
  integrations: IntegrationItem[];
  loading: boolean;
  errorMessage: string;
  // True dopo che il primo fetch è terminato (success o fail).
  // Necessario per distinguere "fetch in corso" da "lista vuota / nessun connettore registrato".
  initialFetchDone: boolean;

  // Actions
  fetchIntegrations: () => Promise<void>;
  connectIntegration: (slug: string) => Promise<BackendConnectResponse | null>;
  disconnectIntegration: (slug: string) => Promise<boolean>;
}

function mapItem(data: BackendIntegrationInfo): IntegrationItem {
  return {
    slug: data.slug,
    name: data.name,
    description: data.description,
    status: (data.status as IntegrationStatus) ?? "disconnected",
    iconSlug: data.icon_slug ?? null,
    lastSyncAt: data.last_sync_at ?? null,
    account: data.account ?? null,
  };
}

export const useIntegrationsStore = create<IntegrationsState>((set, get) => ({
  integrations: [],
  loading: false,
  errorMessage: "",
  initialFetchDone: false,

  fetchIntegrations: async () => {
    set({ loading: true, errorMessage: "" });
    try {
      const res = await fetch(`${BACKEND_URL}/api/integrations/available`);
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        set({
          loading: false,
          initialFetchDone: true,
          errorMessage: `Backend ha risposto ${res.status}: ${txt || res.statusText}`,
        });
        return;
      }
      const data: BackendIntegrationInfo[] = await res.json();
      set({
        integrations: data.map(mapItem),
        loading: false,
        initialFetchDone: true,
        errorMessage: "",
      });
    } catch (err) {
      set({
        loading: false,
        initialFetchDone: true,
        errorMessage: `Errore rete: ${err instanceof Error ? err.message : String(err)}`,
      });
    }
  },

  connectIntegration: async (slug: string) => {
    set({ loading: true, errorMessage: "" });
    try {
      const res = await fetch(
        `${BACKEND_URL}/api/integrations/${encodeURIComponent(slug)}/connect`,
        { method: "POST" },
      );
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        set({
          loading: false,
          errorMessage: `Connect ${slug} fallito (${res.status}): ${txt || res.statusText}`,
        });
        return null;
      }
      const data: BackendConnectResponse = await res.json();
      set({ loading: false });
      return data;
    } catch (err) {
      set({
        loading: false,
        errorMessage: `Errore rete: ${err instanceof Error ? err.message : String(err)}`,
      });
      return null;
    }
  },

  disconnectIntegration: async (slug: string) => {
    set({ loading: true, errorMessage: "" });
    try {
      const res = await fetch(
        `${BACKEND_URL}/api/integrations/${encodeURIComponent(slug)}`,
        { method: "DELETE" },
      );
      if (res.status !== 204 && !res.ok) {
        const txt = await res.text().catch(() => "");
        set({
          loading: false,
          errorMessage: `Disconnect ${slug} fallito (${res.status}): ${txt || res.statusText}`,
        });
        return false;
      }
      // Re-fetch lista per riallineare status dal backend (single source of truth Conv. 48).
      await get().fetchIntegrations();
      return true;
    } catch (err) {
      set({
        loading: false,
        errorMessage: `Errore rete: ${err instanceof Error ? err.message : String(err)}`,
      });
      return false;
    }
  },
}));
