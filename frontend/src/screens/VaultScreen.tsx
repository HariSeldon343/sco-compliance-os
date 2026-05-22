// SCO Compliance OS — schermata Vault: lista vault registrati + aggiungi via dialog Tauri
import { useState } from "react";
import { Database, FolderPlus, Check, AlertCircle } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/cn";

interface VaultEntry {
  id: string;
  name: string;
  path: string;
  isActive: boolean;
  fileCount: number;
  lastSync: string;
}

// Stub vault — verranno sostituiti da fetch /api/vaults
const INITIAL_VAULTS: VaultEntry[] = [
  {
    id: "v1",
    name: "Second Brain",
    path: "C:\\Users\\aoedo\\Desktop\\Second Brain",
    isActive: true,
    fileCount: 1247,
    lastSync: "2026-05-21 14:30",
  },
];

export function VaultScreen() {
  const [vaults, setVaults] = useState<VaultEntry[]>(INITIAL_VAULTS);
  const [selected, setSelected] = useState<string>(INITIAL_VAULTS[0]?.id ?? "");

  const activeVault = vaults.find((v) => v.id === selected) ?? null;

  const handleAddVault = async () => {
    // TODO: integrare @tauri-apps/plugin-dialog `open({ directory: true })`
    // try { const path = await open({ directory: true }); ... } catch ...
    toast.info("Aggiungi vault: dialog Tauri in arrivo (stub).");
  };

  const handleSetActive = (id: string) => {
    setVaults((prev) =>
      prev.map((v) => ({ ...v, isActive: v.id === id })),
    );
    toast.success("Vault attivo aggiornato.");
  };

  return (
    <div className="h-full overflow-y-auto px-8 py-6">
      <div className="mx-auto max-w-5xl">
        <header className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-sco-navy dark:text-sco-text-dark">
              Vault
            </h1>
            <p className="mt-1 text-sm text-sco-muted-foreground">
              Le tue cartelle Obsidian collegate. Filing rule Karpathy
              applicata.
            </p>
          </div>
          <button
            type="button"
            onClick={handleAddVault}
            className="flex items-center gap-2 rounded-md bg-sco-navy px-3 py-2 text-sm font-medium text-white hover:bg-sco-blue"
          >
            <FolderPlus size={16} />
            Aggiungi vault
          </button>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_2fr]">
          {/* Lista vault */}
          <div className="space-y-2">
            {vaults.map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => setSelected(v.id)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-md border p-3 text-left transition-colors",
                  selected === v.id
                    ? "border-sco-blue bg-sco-blue/5"
                    : "border-sco-border hover:border-sco-blue",
                )}
              >
                <Database size={18} className="text-sco-blue" />
                <div className="flex-1 truncate">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{v.name}</span>
                    {v.isActive && (
                      <span className="rounded-full bg-sco-amber/20 px-2 py-0.5 text-xs font-medium text-sco-amber">
                        Attivo
                      </span>
                    )}
                  </div>
                  <div className="truncate text-xs text-sco-muted-foreground">
                    {v.path}
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Dettaglio vault */}
          {activeVault && (
            <div className="rounded-lg border border-sco-border bg-sco-surface-elevated p-6">
              <h2 className="text-lg font-semibold">{activeVault.name}</h2>
              <p className="mt-1 break-all text-xs text-sco-muted-foreground">
                {activeVault.path}
              </p>

              <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
                <Detail
                  label="File indicizzati"
                  value={activeVault.fileCount.toLocaleString("it-IT")}
                />
                <Detail label="Ultimo sync" value={activeVault.lastSync} />
                <Detail
                  label="Stato"
                  value={
                    <span className="flex items-center gap-1">
                      <Check size={14} className="text-green-600" />
                      Healthy
                    </span>
                  }
                />
                <Detail label="Filing rule" value="Karpathy 10 step" />
              </dl>

              <div className="mt-6 flex gap-2">
                {!activeVault.isActive && (
                  <button
                    type="button"
                    onClick={() => handleSetActive(activeVault.id)}
                    className="rounded-md bg-sco-navy px-3 py-2 text-sm font-medium text-white hover:bg-sco-blue"
                  >
                    Imposta come attivo
                  </button>
                )}
                <button
                  type="button"
                  className="rounded-md border border-sco-border px-3 py-2 text-sm hover:bg-sco-muted"
                >
                  Re-indicizza
                </button>
                <button
                  type="button"
                  className="ml-auto flex items-center gap-1 rounded-md border border-red-300 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <AlertCircle size={14} />
                  Scollega
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Detail({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs text-sco-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-medium">{value}</dd>
    </div>
  );
}
