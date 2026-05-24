// SCO Compliance OS — Zustand store per vault registrati + vault attivo selezionato
// Conv. 48 enforcement: lista vault dal backend (GET /api/vault/list), attivo persiste
// localmente come "selected" ma il backend rimane source of truth della struttura del vault.

import { create } from "zustand";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

export interface VaultEntry {
  id: string;
  name: string;
  path: string;
  isKarpathy: boolean;
  mdFilesCount: number;
  hasClaudeMd: boolean;
  hasAgentsMd: boolean;
  hasWikiDir: boolean;
  hasRawDir: boolean;
}

export interface VaultInspectResult {
  path: string;
  isKarpathy: boolean;
  mdFilesCount: number;
  hasClaudeMd: boolean;
  hasAgentsMd: boolean;
  hasWikiDir: boolean;
  hasRawDir: boolean;
}

export interface VaultState {
  vaults: VaultEntry[];
  selectedVaultId: string | null;
  loading: boolean;
  errorMessage: string;
  initialFetchDone: boolean;

  // Actions
  fetchVaults: () => Promise<void>;
  addVault: (path: string, name?: string) => Promise<VaultEntry | null>;
  inspectVault: (path: string) => Promise<VaultInspectResult | null>;
  removeVault: (id: string) => Promise<boolean>;
  selectVault: (id: string) => void;
}

interface BackendVaultEntry {
  id: string;
  name: string;
  path: string;
  is_karpathy: boolean;
  md_files_count: number;
  has_claude_md: boolean;
  has_agents_md: boolean;
  has_wiki_dir: boolean;
  has_raw_dir: boolean;
}

interface BackendVaultInspect {
  path: string;
  is_karpathy: boolean;
  md_files_count: number;
  has_claude_md: boolean;
  has_agents_md: boolean;
  has_wiki_dir: boolean;
  has_raw_dir: boolean;
}

function mapVaultEntry(data: BackendVaultEntry): VaultEntry {
  return {
    id: data.id,
    name: data.name,
    path: data.path,
    isKarpathy: Boolean(data.is_karpathy),
    mdFilesCount: data.md_files_count ?? 0,
    hasClaudeMd: Boolean(data.has_claude_md),
    hasAgentsMd: Boolean(data.has_agents_md),
    hasWikiDir: Boolean(data.has_wiki_dir),
    hasRawDir: Boolean(data.has_raw_dir),
  };
}

function mapInspect(data: BackendVaultInspect): VaultInspectResult {
  return {
    path: data.path,
    isKarpathy: Boolean(data.is_karpathy),
    mdFilesCount: data.md_files_count ?? 0,
    hasClaudeMd: Boolean(data.has_claude_md),
    hasAgentsMd: Boolean(data.has_agents_md),
    hasWikiDir: Boolean(data.has_wiki_dir),
    hasRawDir: Boolean(data.has_raw_dir),
  };
}

// LocalStorage key per selected vault id (non source of truth, solo UX persistence)
const SELECTED_VAULT_KEY = "sco.selectedVaultId";

function readSelectedFromStorage(): string | null {
  try {
    return localStorage.getItem(SELECTED_VAULT_KEY);
  } catch {
    return null;
  }
}

function writeSelectedToStorage(id: string | null): void {
  try {
    if (id) {
      localStorage.setItem(SELECTED_VAULT_KEY, id);
    } else {
      localStorage.removeItem(SELECTED_VAULT_KEY);
    }
  } catch {
    // ignore
  }
}

export const useVaultStore = create<VaultState>((set, get) => ({
  vaults: [],
  selectedVaultId: readSelectedFromStorage(),
  loading: false,
  errorMessage: "",
  initialFetchDone: false,

  fetchVaults: async () => {
    set({ loading: true, errorMessage: "" });
    try {
      const res = await fetch(`${BACKEND_URL}/api/vault/list`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: BackendVaultEntry[] = await res.json();
      const vaults = data.map(mapVaultEntry);

      // Se selectedVaultId punta a vault non più presente, ripulisci
      const currentSelected = get().selectedVaultId;
      const stillExists = currentSelected
        ? vaults.some((v) => v.id === currentSelected)
        : false;
      const newSelected = stillExists ? currentSelected : vaults[0]?.id ?? null;
      if (newSelected !== currentSelected) {
        writeSelectedToStorage(newSelected);
      }

      set({
        vaults,
        selectedVaultId: newSelected,
        loading: false,
        initialFetchDone: true,
      });
    } catch (err) {
      set({
        errorMessage: `Errore rete vault: ${
          err instanceof Error ? err.message : String(err)
        }`,
        loading: false,
        initialFetchDone: true,
      });
    }
  },

  addVault: async (path, name) => {
    set({ loading: true, errorMessage: "" });
    try {
      const res = await fetch(`${BACKEND_URL}/api/vault/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(name ? { path, name } : { path }),
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status} ${body}`);
      }
      const data: BackendVaultEntry = await res.json();
      const entry = mapVaultEntry(data);

      // Aggiorna lista: rimuovi duplicati per path, aggiungi nuovo
      const existing = get().vaults.filter((v) => v.path !== entry.path);
      const newVaults = [...existing, entry];
      writeSelectedToStorage(entry.id);

      set({
        vaults: newVaults,
        selectedVaultId: entry.id,
        loading: false,
      });
      return entry;
    } catch (err) {
      set({
        errorMessage: `Errore aggiungi vault: ${
          err instanceof Error ? err.message : String(err)
        }`,
        loading: false,
      });
      return null;
    }
  },

  inspectVault: async (path) => {
    set({ errorMessage: "" });
    try {
      const res = await fetch(`${BACKEND_URL}/api/vault/inspect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status} ${body}`);
      }
      const data: BackendVaultInspect = await res.json();
      return mapInspect(data);
    } catch (err) {
      set({
        errorMessage: `Errore ispezione vault: ${
          err instanceof Error ? err.message : String(err)
        }`,
      });
      return null;
    }
  },

  removeVault: async (id) => {
    set({ loading: true, errorMessage: "" });
    try {
      const res = await fetch(`${BACKEND_URL}/api/vault/${id}`, {
        method: "DELETE",
      });
      if (!res.ok && res.status !== 204) {
        throw new Error(`HTTP ${res.status}`);
      }
      const remaining = get().vaults.filter((v) => v.id !== id);
      const currentSelected = get().selectedVaultId;
      const newSelected =
        currentSelected === id ? remaining[0]?.id ?? null : currentSelected;
      writeSelectedToStorage(newSelected);

      set({
        vaults: remaining,
        selectedVaultId: newSelected,
        loading: false,
      });
      return true;
    } catch (err) {
      set({
        errorMessage: `Errore rimuovi vault: ${
          err instanceof Error ? err.message : String(err)
        }`,
        loading: false,
      });
      return false;
    }
  },

  selectVault: (id) => {
    const exists = get().vaults.some((v) => v.id === id);
    if (!exists) return;
    writeSelectedToStorage(id);
    set({ selectedVaultId: id });
  },
}));
