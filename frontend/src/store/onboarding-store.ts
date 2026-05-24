// SCO Compliance OS — Zustand store per stato onboarding (EULA + Privacy + Demo + Tutorial)
// Conv. 47 + 48 enforcement: il backend è single source of truth per le version correnti
// (current_eula_version, current_privacy_version, current_demo_version) e per i flag
// accepted/seen/done. Il frontend NON hardcoda mai le version. Refetch dopo ogni accept.

import { create } from "zustand";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

export interface OnboardingStatus {
  eulaAccepted: boolean;
  eulaAcceptedVersion: string | null;
  eulaAcceptedAt: string | null;

  privacyAccepted: boolean;
  privacyAcceptedVersion: string | null;
  privacyAcceptedAt: string | null;

  demoSeen: boolean;
  demoSeenVersion: string | null;
  demoSeenAt: string | null;

  tutorialDone: boolean;
  tutorialDoneAt: string | null;

  // Version correnti dal backend (Conv. 47)
  currentEulaVersion: string;
  currentPrivacyVersion: string;
  currentDemoVersion: string;
}

export interface OnboardingState extends OnboardingStatus {
  loading: boolean;
  errorMessage: string;
  initialFetchDone: boolean;

  // Actions
  fetchStatus: () => Promise<void>;
  acceptEula: () => Promise<boolean>;
  acceptPrivacy: () => Promise<boolean>;
  markDemoSeen: () => Promise<boolean>;
  markTutorialDone: () => Promise<boolean>;
  reset: () => void;
}

interface BackendOnboardingResponse {
  eula_accepted: boolean;
  eula_accepted_version: string | null;
  eula_accepted_at: string | null;
  privacy_accepted: boolean;
  privacy_accepted_version: string | null;
  privacy_accepted_at: string | null;
  demo_seen: boolean;
  demo_seen_version: string | null;
  demo_seen_at: string | null;
  tutorial_done: boolean;
  tutorial_done_at: string | null;
  current_eula_version: string;
  current_privacy_version: string;
  current_demo_version: string;
}

function mapResponse(data: BackendOnboardingResponse): OnboardingStatus {
  return {
    eulaAccepted: Boolean(data.eula_accepted),
    eulaAcceptedVersion: data.eula_accepted_version ?? null,
    eulaAcceptedAt: data.eula_accepted_at ?? null,

    privacyAccepted: Boolean(data.privacy_accepted),
    privacyAcceptedVersion: data.privacy_accepted_version ?? null,
    privacyAcceptedAt: data.privacy_accepted_at ?? null,

    demoSeen: Boolean(data.demo_seen),
    demoSeenVersion: data.demo_seen_version ?? null,
    demoSeenAt: data.demo_seen_at ?? null,

    tutorialDone: Boolean(data.tutorial_done),
    tutorialDoneAt: data.tutorial_done_at ?? null,

    currentEulaVersion: data.current_eula_version ?? "1.0",
    currentPrivacyVersion: data.current_privacy_version ?? "1.0",
    currentDemoVersion: data.current_demo_version ?? "1.0",
  };
}

const emptyStatus: OnboardingStatus = {
  eulaAccepted: false,
  eulaAcceptedVersion: null,
  eulaAcceptedAt: null,
  privacyAccepted: false,
  privacyAcceptedVersion: null,
  privacyAcceptedAt: null,
  demoSeen: false,
  demoSeenVersion: null,
  demoSeenAt: null,
  tutorialDone: false,
  tutorialDoneAt: null,
  currentEulaVersion: "1.0",
  currentPrivacyVersion: "1.0",
  currentDemoVersion: "1.0",
};

export const useOnboardingStore = create<OnboardingState>((set, get) => ({
  ...emptyStatus,
  loading: false,
  errorMessage: "",
  initialFetchDone: false,

  fetchStatus: async () => {
    set({ loading: true, errorMessage: "" });
    try {
      // v1.0.1 fix race condition: retry 5x backoff 500ms-8s assorbe startup sidecar.
      const { fetchWithRetry } = await import("@/api/retry");
      const res = await fetchWithRetry(`${BACKEND_URL}/api/onboarding/status`, {
        maxRetries: 5,
        baseMs: 500,
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: BackendOnboardingResponse = await res.json();
      set({
        ...mapResponse(data),
        loading: false,
        initialFetchDone: true,
      });
    } catch (err) {
      set({
        errorMessage: `Errore rete onboarding: ${
          err instanceof Error ? err.message : String(err)
        }`,
        loading: false,
        initialFetchDone: true,
      });
    }
  },

  acceptEula: async () => {
    const version = get().currentEulaVersion;
    set({ loading: true, errorMessage: "" });
    try {
      const res = await fetch(`${BACKEND_URL}/api/onboarding/eula/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: BackendOnboardingResponse = await res.json();
      // Refetch implicit: backend ritorna lo stato aggiornato (Conv. 48)
      set({ ...mapResponse(data), loading: false });
      return Boolean(data.eula_accepted);
    } catch (err) {
      set({
        errorMessage: `Errore accept EULA: ${
          err instanceof Error ? err.message : String(err)
        }`,
        loading: false,
      });
      return false;
    }
  },

  acceptPrivacy: async () => {
    const version = get().currentPrivacyVersion;
    set({ loading: true, errorMessage: "" });
    try {
      const res = await fetch(`${BACKEND_URL}/api/onboarding/privacy/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: BackendOnboardingResponse = await res.json();
      set({ ...mapResponse(data), loading: false });
      return Boolean(data.privacy_accepted);
    } catch (err) {
      set({
        errorMessage: `Errore accept Privacy: ${
          err instanceof Error ? err.message : String(err)
        }`,
        loading: false,
      });
      return false;
    }
  },

  markDemoSeen: async () => {
    const version = get().currentDemoVersion;
    set({ loading: true, errorMessage: "" });
    try {
      const res = await fetch(`${BACKEND_URL}/api/onboarding/demo/seen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: BackendOnboardingResponse = await res.json();
      set({ ...mapResponse(data), loading: false });
      return Boolean(data.demo_seen);
    } catch (err) {
      set({
        errorMessage: `Errore mark demo seen: ${
          err instanceof Error ? err.message : String(err)
        }`,
        loading: false,
      });
      return false;
    }
  },

  markTutorialDone: async () => {
    set({ loading: true, errorMessage: "" });
    try {
      const res = await fetch(`${BACKEND_URL}/api/onboarding/tutorial/done`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: BackendOnboardingResponse = await res.json();
      set({ ...mapResponse(data), loading: false });
      return Boolean(data.tutorial_done);
    } catch (err) {
      set({
        errorMessage: `Errore mark tutorial done: ${
          err instanceof Error ? err.message : String(err)
        }`,
        loading: false,
      });
      return false;
    }
  },

  reset: () => {
    set({
      ...emptyStatus,
      loading: false,
      errorMessage: "",
      initialFetchDone: false,
    });
  },
}));
