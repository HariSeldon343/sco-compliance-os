// SCO Compliance OS — VaultPickerScreen: fase 4 onboarding cumulativa
// Tre modalità: (a) seleziona vault esistente, (b) carica vault Obsidian dal disco,
// (c) crea nuovo vault da template SCO.
// Conv. 47 + 48: lista vault dal backend (GET /api/vault/list), persistenza lato backend.

import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Database,
  FolderOpen,
  Plus,
  Check,
  AlertTriangle,
  Loader2,
} from "lucide-react";

import { useVaultStore, type VaultInspectResult } from "@/store/vault-store";
import { cn } from "@/lib/cn";

type Mode = "select" | "open-folder" | "create-new";

interface Template {
  id: string;
  label: string;
  description: string;
}

// Stub templates — backend POST /api/vault/add?scaffold=true&template=... NON ancora implementato.
// Per ora: la create-new modalità apre comunque il dialog folder picker e registra il vault scelto;
// lo scaffolding effettivo dei file template è carry-over backend Conv. 41.
const TEMPLATES: Template[] = [
  { id: "cyber", label: "Cybersecurity / NIS 2", description: "ISO 27001, NIS 2, Legge 90." },
  { id: "sanita", label: "Sanità / accreditamento", description: "DPR 14/1/1997, DM 70/2015, qualità sanitaria." },
  { id: "qualita", label: "Qualità ISO 9001", description: "SGQ, audit, procedure." },
  { id: "integrato", label: "Integrato cyber + qualità + sanità", description: "Multi-framework, audit congiunti." },
  { id: "vuoto", label: "Karpathy minimo vuoto", description: "Solo struttura cartelle base, nessun contenuto." },
];

export function VaultPickerScreen() {
  const vaults = useVaultStore((s) => s.vaults);
  const selectedVaultId = useVaultStore((s) => s.selectedVaultId);
  const loading = useVaultStore((s) => s.loading);
  const errorMessage = useVaultStore((s) => s.errorMessage);
  const initialFetchDone = useVaultStore((s) => s.initialFetchDone);

  const fetchVaults = useVaultStore((s) => s.fetchVaults);
  const addVault = useVaultStore((s) => s.addVault);
  const inspectVault = useVaultStore((s) => s.inspectVault);
  const selectVault = useVaultStore((s) => s.selectVault);

  const [mode, setMode] = useState<Mode>("select");
  const [pickedPath, setPickedPath] = useState<string>("");
  const [inspectResult, setInspectResult] = useState<VaultInspectResult | null>(null);
  const [inspecting, setInspecting] = useState(false);
  const [customName, setCustomName] = useState<string>("");
  const [selectedTemplate, setSelectedTemplate] = useState<string>("integrato");
  const [confirming, setConfirming] = useState(false);

  // Default mode: se non ci sono vault registrati, vai diretto a open-folder
  useEffect(() => {
    if (initialFetchDone && vaults.length === 0) {
      setMode("open-folder");
    }
  }, [initialFetchDone, vaults.length]);

  // Fetch iniziale vault
  useEffect(() => {
    if (!initialFetchDone) {
      fetchVaults();
    }
  }, [initialFetchDone, fetchVaults]);

  /**
   * Apre il file picker Tauri per scegliere una cartella vault.
   * In ambiente browser (Vite dev senza Tauri runtime) la chiamata fallisce graceful.
   */
  const handleOpenFolderPicker = async () => {
    try {
      // Lazy import per evitare errori SSR / browser pure
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        directory: true,
        multiple: false,
        title: "Scegli la cartella del vault Obsidian",
      });
      if (typeof selected !== "string") {
        return; // utente ha annullato
      }
      setPickedPath(selected);
      setInspecting(true);
      setInspectResult(null);

      const result = await inspectVault(selected);
      setInspecting(false);
      if (result) {
        setInspectResult(result);
        // Suggerisci nome dalla path
        const parts = selected.split(/[\\/]/);
        const suggested = parts[parts.length - 1] || "Vault";
        setCustomName(suggested);
      } else {
        toast.error("Impossibile ispezionare la cartella scelta.");
      }
    } catch (err) {
      setInspecting(false);
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`Errore apertura cartella: ${message}`);
    }
  };

  const handleConfirmAddVault = async () => {
    if (!pickedPath) {
      toast.error("Scegli prima una cartella.");
      return;
    }
    setConfirming(true);
    const entry = await addVault(pickedPath, customName || undefined);
    setConfirming(false);
    if (entry) {
      toast.success(`Vault "${entry.name}" registrato.`);
      // Il vault è ora selectedVaultId nel store; basta segnalare al gate che siamo OK
      // Il gate App.tsx si accorgerà al prossimo render perché vaults.length > 0 && selectedVaultId.
    } else {
      toast.error("Errore registrazione vault.");
    }
  };

  const handleConfirmExistingSelection = () => {
    if (!selectedVaultId) {
      toast.error("Seleziona un vault dalla lista.");
      return;
    }
    // selectedVaultId è già nello store — gate App.tsx procede.
    // Forza un piccolo refresh fetch per rinfrescare anche metadata cached.
    fetchVaults();
    toast.success("Vault attivo selezionato.");
  };

  const handleSelectMode = (next: Mode) => {
    setMode(next);
    setPickedPath("");
    setInspectResult(null);
    setCustomName("");
  };

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-gradient-to-br from-[#1a1837] via-[#302e5c] to-[#0074b4] p-8">
      <div className="flex w-full max-w-4xl flex-col rounded-2xl bg-white p-8 shadow-2xl dark:bg-slate-900">
        {/* Brand */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-[#0074b4]" />
            <h1 className="text-lg font-semibold text-[#302e5c] dark:text-white">
              SCO Compliance OS
            </h1>
          </div>
          <span className="rounded-full bg-[#ffa727]/15 px-3 py-1 text-xs font-medium text-[#ffa727]">
            Fase 4 di 5 — Vault
          </span>
        </div>

        <h2 className="mb-2 text-2xl font-bold text-slate-900 dark:text-white">
          Scegli il tuo vault
        </h2>
        <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
          Il vault è la cartella Obsidian dove vivono i tuoi file Markdown.
          L&apos;agente AI legge da qui per rispondere con il contesto del tuo lavoro.
        </p>

        {/* Mode selector — 3 tab */}
        <div className="mb-6 flex gap-2 border-b border-slate-200 dark:border-slate-700">
          {(
            [
              {
                id: "select" as Mode,
                label: "Vault già registrati",
                icon: <Database size={16} />,
                disabled: vaults.length === 0,
              },
              {
                id: "open-folder" as Mode,
                label: "Carica vault dal disco",
                icon: <FolderOpen size={16} />,
                disabled: false,
              },
              {
                id: "create-new" as Mode,
                label: "Crea nuovo da template",
                icon: <Plus size={16} />,
                disabled: false,
              },
            ]
          ).map((t) => (
            <button
              key={t.id}
              type="button"
              disabled={t.disabled}
              onClick={() => handleSelectMode(t.id)}
              className={cn(
                "flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors",
                mode === t.id
                  ? "border-[#0074b4] text-[#0074b4]"
                  : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200",
                t.disabled && "cursor-not-allowed opacity-40",
              )}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/* Errors */}
        {errorMessage && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* MODE: select existing */}
        {mode === "select" && (
          <div className="space-y-3">
            {vaults.length === 0 ? (
              <p className="text-sm italic text-slate-500">
                Nessun vault registrato. Usa una delle altre opzioni.
              </p>
            ) : (
              <>
                <div className="max-h-72 space-y-2 overflow-y-auto">
                  {vaults.map((v) => (
                    <button
                      key={v.id}
                      type="button"
                      onClick={() => selectVault(v.id)}
                      className={cn(
                        "flex w-full items-start gap-3 rounded-lg border p-4 text-left transition-colors",
                        selectedVaultId === v.id
                          ? "border-[#0074b4] bg-[#0074b4]/5"
                          : "border-slate-200 hover:border-[#0074b4] dark:border-slate-700",
                      )}
                    >
                      <Database size={20} className="mt-0.5 shrink-0 text-[#0074b4]" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-900 dark:text-white">
                            {v.name}
                          </span>
                          {v.isKarpathy && (
                            <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900 dark:text-green-300">
                              Karpathy
                            </span>
                          )}
                          {selectedVaultId === v.id && (
                            <Check size={14} className="text-[#0074b4]" />
                          )}
                        </div>
                        <div className="truncate text-xs text-slate-500 dark:text-slate-400">
                          {v.path}
                        </div>
                        <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {v.mdFilesCount.toLocaleString("it-IT")} file .md
                          {v.hasClaudeMd && " · CLAUDE.md"}
                          {v.hasWikiDir && " · wiki/"}
                          {v.hasRawDir && " · raw/"}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>

                <div className="flex justify-end pt-4">
                  <button
                    type="button"
                    onClick={handleConfirmExistingSelection}
                    disabled={!selectedVaultId || loading}
                    className="rounded-lg bg-[#0074b4] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#005a8f] disabled:opacity-50"
                  >
                    Continua con il vault selezionato
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {/* MODE: open existing folder */}
        {mode === "open-folder" && (
          <div className="space-y-4">
            <p className="text-sm text-slate-700 dark:text-slate-200">
              Apri una cartella che contiene già il tuo vault Obsidian.
              L&apos;app la registra e ne legge la struttura.
            </p>

            {!pickedPath && (
              <button
                type="button"
                onClick={handleOpenFolderPicker}
                disabled={loading || inspecting}
                className="flex items-center gap-2 rounded-lg bg-[#0074b4] px-6 py-3 text-sm font-semibold text-white hover:bg-[#005a8f] disabled:opacity-50"
              >
                <FolderOpen size={16} />
                {inspecting ? "Apertura..." : "Scegli cartella"}
              </button>
            )}

            {inspecting && (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Loader2 size={16} className="animate-spin" />
                Ispezione struttura vault in corso...
              </div>
            )}

            {pickedPath && inspectResult && (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
                <p className="mb-2 break-all text-xs text-slate-500 dark:text-slate-400">
                  {pickedPath}
                </p>

                <div className="mb-4 grid grid-cols-2 gap-2 text-sm">
                  <Info
                    label="Struttura Karpathy"
                    value={inspectResult.isKarpathy ? "OK completa" : "Parziale o assente"}
                    ok={inspectResult.isKarpathy}
                  />
                  <Info
                    label="File .md trovati"
                    value={inspectResult.mdFilesCount.toLocaleString("it-IT")}
                    ok={inspectResult.mdFilesCount > 0}
                  />
                  <Info
                    label="CLAUDE.md"
                    value={inspectResult.hasClaudeMd ? "Presente" : "Mancante"}
                    ok={inspectResult.hasClaudeMd}
                  />
                  <Info
                    label="Cartella wiki/"
                    value={inspectResult.hasWikiDir ? "Presente" : "Mancante"}
                    ok={inspectResult.hasWikiDir}
                  />
                  <Info
                    label="Cartella raw/"
                    value={inspectResult.hasRawDir ? "Presente" : "Mancante"}
                    ok={inspectResult.hasRawDir}
                  />
                  <Info
                    label="AGENTS.md"
                    value={inspectResult.hasAgentsMd ? "Presente" : "Mancante"}
                    ok={inspectResult.hasAgentsMd}
                  />
                </div>

                <label className="mb-3 block text-sm font-medium text-slate-700 dark:text-slate-200">
                  Nome leggibile per il vault
                  <input
                    type="text"
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    placeholder="es. Second Brain"
                    className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-[#0074b4] focus:outline-none focus:ring-2 focus:ring-[#0074b4]/30 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                  />
                </label>

                {!inspectResult.isKarpathy && (
                  <div className="mb-3 rounded-md bg-amber-50 p-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                    Attenzione: la cartella non ha la struttura Karpathy completa
                    (CLAUDE.md + wiki/ + raw/). L&apos;app funziona comunque, ma
                    l&apos;agente avrà meno contesto strutturato.
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleOpenFolderPicker}
                    disabled={confirming || loading}
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Cambia cartella
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmAddVault}
                    disabled={confirming || loading}
                    className="rounded-lg bg-[#0074b4] px-6 py-2 text-sm font-semibold text-white hover:bg-[#005a8f] disabled:opacity-50"
                  >
                    {confirming ? "Registrazione..." : "Registra e continua"}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* MODE: create new vault from template */}
        {mode === "create-new" && (
          <div className="space-y-4">
            <p className="text-sm text-slate-700 dark:text-slate-200">
              Crea una nuova cartella vault con la struttura base SCO. Scegli un
              template di partenza, poi scegli dove crearla.
            </p>

            <div className="rounded-md bg-amber-50 p-3 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              Lo scaffolding completo dei template è in arrivo. Per ora, dopo
              aver scelto la cartella, il vault viene registrato con la struttura
              base che già contiene (o senza struttura se vuota).
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Template
              </p>
              {TEMPLATES.map((t) => (
                <label
                  key={t.id}
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors",
                    selectedTemplate === t.id
                      ? "border-[#0074b4] bg-[#0074b4]/5"
                      : "border-slate-200 hover:border-[#0074b4] dark:border-slate-700",
                  )}
                >
                  <input
                    type="radio"
                    name="template"
                    value={t.id}
                    checked={selectedTemplate === t.id}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                    className="mt-1 h-4 w-4 text-[#0074b4]"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-slate-900 dark:text-white">
                      {t.label}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {t.description}
                    </div>
                  </div>
                </label>
              ))}
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={handleOpenFolderPicker}
                disabled={loading || inspecting}
                className="flex items-center gap-2 rounded-lg bg-[#0074b4] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#005a8f] disabled:opacity-50"
              >
                <FolderOpen size={16} />
                Scegli dove creare il vault
              </button>
            </div>

            {pickedPath && (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-700 dark:bg-slate-800">
                <p className="mb-2 break-all text-xs text-slate-500">
                  Cartella scelta: {pickedPath}
                </p>
                <p className="mb-3 text-xs text-slate-500">
                  Template selezionato: {TEMPLATES.find((t) => t.id === selectedTemplate)?.label}
                </p>
                <button
                  type="button"
                  onClick={handleConfirmAddVault}
                  disabled={confirming || loading}
                  className="rounded-lg bg-[#0074b4] px-4 py-2 text-sm font-semibold text-white hover:bg-[#005a8f] disabled:opacity-50"
                >
                  {confirming ? "Creazione..." : "Crea vault e continua"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Info({
  label,
  value,
  ok,
}: {
  label: string;
  value: string;
  ok: boolean;
}) {
  return (
    <div>
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
      <div
        className={cn(
          "text-sm font-medium",
          ok
            ? "text-green-700 dark:text-green-400"
            : "text-amber-700 dark:text-amber-400",
        )}
      >
        {value}
      </div>
    </div>
  );
}
