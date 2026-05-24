// SCO Compliance OS — Zustand store per stato license cliente
// Conv. 48 enforcement: backend è single source of truth; frontend deduce status via fetch /api/license/status.

import { create } from "zustand";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

export type LicenseStatus =
  | "valid"
  | "invalid"
  | "revoked"
  | "expired"
  | "network_error"
  | "unknown";

export interface LicenseState {
  status: LicenseStatus;
  isValid: boolean;
  email: string;
  tenantId: string;
  expiresAt: string;
  plan: string;
  validatedAt: string;
  errorMessage: string;
  backendVersion: string;
  loading: boolean;
  // True dopo che il primo fetch è terminato (success o fail).
  // Necessario per distinguere "fetch in corso" da "no license attivata" —
  // entrambi danno status="unknown" + is_valid=false (backend ritorna "unknown" anche
  // dopo fetch quando non c'è license attivata).
  initialFetchDone: boolean;

  // Actions
  fetchStatus: () => Promise<void>;
  activate: (email: string, licenseKey: string) => Promise<boolean>;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

interface BackendStatusResponse {
  status: string;
  is_valid: boolean;
  email?: string;
  tenant_id?: string;
  expires_at?: string;
  plan?: string;
  validated_at?: string;
  error_message?: string;
  backend_version?: string;
}

function mapResponse(data: BackendStatusResponse): Omit<
  LicenseState,
  "loading" | "initialFetchDone" | "fetchStatus" | "activate" | "refresh" | "logout"
> {
  return {
    status: (data.status as LicenseStatus) ?? "unknown",
    isValid: Boolean(data.is_valid),
    email: data.email ?? "",
    tenantId: data.tenant_id ?? "",
    expiresAt: data.expires_at ?? "",
    plan: data.plan ?? "",
    validatedAt: data.validated_at ?? "",
    errorMessage: data.error_message ?? "",
    backendVersion: data.backend_version ?? "",
  };
}

export const useLicenseStore = create<LicenseState>((set) => ({
  status: "unknown",
  isValid: false,
  email: "",
  tenantId: "",
  expiresAt: "",
  plan: "",
  validatedAt: "",
  errorMessage: "",
  backendVersion: "",
  loading: false,
  initialFetchDone: false,

  fetchStatus: async () => {
    set({ loading: true });
    try {
      // v1.0.1 fix race condition: retry 5x backoff 500ms-8s = ~15s cumulative.
      // Copre worst-case startup sidecar PyInstaller v1.0.0 (61 MB, 5-10s bind porta).
      const { fetchWithRetry } = await import("@/api/retry");
      const res = await fetchWithRetry(`${BACKEND_URL}/api/license/status`, {
        maxRetries: 5,
        baseMs: 500,
      });
      const data: BackendStatusResponse = await res.json();
      set({ ...mapResponse(data), loading: false, initialFetchDone: true });
    } catch (err) {
      set({
        status: "network_error",
        isValid: false,
        errorMessage: `Errore rete: ${err instanceof Error ? err.message : String(err)}`,
        loading: false,
        initialFetchDone: true,
      });
    }
  },

  activate: async (email: string, licenseKey: string) => {
    set({ loading: true });
    try {
      const res = await fetch(`${BACKEND_URL}/api/license/activate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, license_key: licenseKey }),
      });
      const data: BackendStatusResponse = await res.json();
      set({ ...mapResponse(data), loading: false, initialFetchDone: true });
      return Boolean(data.is_valid);
    } catch (err) {
      set({
        status: "network_error",
        isValid: false,
        errorMessage: `Errore rete: ${err instanceof Error ? err.message : String(err)}`,
        loading: false,
        initialFetchDone: true,
      });
      return false;
    }
  },

  refresh: async () => {
    set({ loading: true });
    try {
      const res = await fetch(`${BACKEND_URL}/api/license/refresh`, {
        method: "POST",
      });
      const data: BackendStatusResponse = await res.json();
      set({ ...mapResponse(data), loading: false, initialFetchDone: true });
    } catch (err) {
      set({
        status: "network_error",
        isValid: false,
        errorMessage: `Errore rete: ${err instanceof Error ? err.message : String(err)}`,
        loading: false,
        initialFetchDone: true,
      });
    }
  },

  logout: async () => {
    set({ loading: true });
    try {
      await fetch(`${BACKEND_URL}/api/license/logout`, { method: "POST" });
      set({
        status: "unknown",
        isValid: false,
        email: "",
        tenantId: "",
        expiresAt: "",
        plan: "",
        validatedAt: "",
        errorMessage: "",
        loading: false,
      });
    } catch {
      set({ loading: false });
    }
  },
}));
