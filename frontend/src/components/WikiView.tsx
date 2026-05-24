// SCO Compliance OS — Wiki view: 5 categorie SCO + Memory Tree Fase 4
// Refactor v0.7.4: usa endpoint /api/wiki/* (ALPHA v0.4.0) + /api/memory/tree/*
// (DEV-MEMORY-TREE v0.6.0) invece di endpoint Wave 1 legacy che davano HTTP 500
// "no such table". Conv. 47 enforcement: single source of truth lato backend.
// Conv. 48 enforcement: nessun workaround "preserva-prev" state, refetch al cambio tab.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertCircle,
  Book,
  BookOpen,
  Clock,
  FileText,
  Filter,
  FolderTree,
  GitBranch,
  Layers,
  Library,
  Loader2,
  Network,
  RefreshCw,
  Tags,
  Type,
} from "lucide-react";

import { apiClient, ApiError } from "@/api/client";
import { cn } from "@/lib/cn";
import type {
  TreeChunkItem,
  TreeSummaryItemV2,
  WikiCategory,
  WikiFileDetail,
  WikiListResponse,
  WikiStatsResponse,
  WikiSummaryItem,
} from "@/types/api";

// Polling automatico 30s come da brief
const POLL_INTERVAL_MS = 30_000;
// Retry exponential backoff
const MAX_RETRIES = 3;
const RETRY_BASE_MS = 500;

/** Wrapper retry exponential backoff per chiamate API resilient. */
async function withRetry<T>(fn: () => Promise<T>, label: string): Promise<T> {
  let lastErr: unknown = null;
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (attempt < MAX_RETRIES - 1) {
        const delay = RETRY_BASE_MS * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }
  console.warn(`[WikiView] ${label} fallito dopo ${MAX_RETRIES} tentativi`, lastErr);
  throw lastErr;
}

// ===== Tab definition: 5 categorie Wiki SCO + Memory Tree =====

type TabId = WikiCategory | "memory-tree";

interface TabDef {
  id: TabId;
  label: string;
  icon: typeof FileText;
  description: string;
}

const TABS: TabDef[] = [
  {
    id: "sources",
    label: "Sources",
    icon: BookOpen,
    description: "Schede di sintesi delle fonti raw ingestite",
  },
  {
    id: "entities",
    label: "Entities",
    icon: Library,
    description: "Atti normativi, standard, autorita, linee guida",
  },
  {
    id: "concepts",
    label: "Concepts",
    icon: Book,
    description: "Concetti normativi e tecnici trasversali",
  },
  {
    id: "synthesis",
    label: "Synthesis",
    icon: Network,
    description: "Confronti, gap analysis, mapping cross-standard",
  },
  {
    id: "glossari",
    label: "Glossari",
    icon: Tags,
    description: "Glossari aziendali per dominio (sigle canoniche)",
  },
  {
    id: "memory-tree",
    label: "Memory Tree",
    icon: GitBranch,
    description: "Chunks + summaries L1/L2/L3 bucket-seal (Fase 4)",
  },
];

// ===== Vocabolari chiusi filtri Entities tab (Ondate 2-3 CLAUDE.md INGEST) =====

const ENTITY_TYPES = [
  { value: "", label: "Tutti i tipi" },
  { value: "atto-normativo", label: "Atto normativo" },
  { value: "standard-tecnico", label: "Standard tecnico" },
  { value: "linea-guida", label: "Linea guida" },
  { value: "autorita", label: "Autorita" },
  { value: "metodologia", label: "Metodologia" },
  { value: "autore-prassi", label: "Autore prassi" },
  { value: "soggetto-obbligato", label: "Soggetto obbligato" },
  { value: "scadenza", label: "Scadenza" },
];

const AMBITI_CANONICI = [
  { value: "", label: "Tutti gli ambiti" },
  { value: "cybersicurezza", label: "Cybersicurezza" },
  { value: "governance-ai", label: "Governance AI" },
  { value: "privacy-protezione-dati", label: "Privacy / Protezione dati" },
  { value: "accreditamento-sanitario", label: "Accreditamento sanitario" },
  { value: "dispositivi-medici", label: "Dispositivi medici" },
  { value: "radioprotezione", label: "Radioprotezione" },
  { value: "sicurezza-lavoro", label: "Sicurezza lavoro" },
  { value: "farmacovigilanza", label: "Farmacovigilanza" },
  { value: "service-management-ict", label: "Service management ICT" },
  { value: "appalti-pubblici", label: "Appalti pubblici" },
  { value: "prevenzione-incendi", label: "Prevenzione incendi" },
  { value: "compliance-231", label: "Compliance 231" },
  { value: "qualita-sgq", label: "Qualita SGQ" },
  { value: "gestione-ambientale", label: "Gestione ambientale" },
  { value: "sicurezza-alimentare", label: "Sicurezza alimentare" },
  { value: "responsabilita-sociale", label: "Responsabilita sociale" },
  { value: "multi-dominio", label: "Multi-dominio" },
];

const STATUSES = [
  { value: "", label: "Tutti gli stati" },
  { value: "active", label: "Active" },
  { value: "draft", label: "Draft" },
  { value: "stub", label: "Stub" },
  { value: "deprecated", label: "Deprecated" },
  { value: "archived", label: "Archived" },
];

// ===== Memory Tree filtri =====

const TREE_KINDS = [
  { value: "", label: "Tutti i tree kind" },
  { value: "source", label: "Source" },
  { value: "topic", label: "Topic" },
  { value: "global", label: "Global" },
];

const SUMMARY_LEVELS = [
  { value: "all" as const, label: "Tutti" },
  { value: 1 as const, label: "L1" },
  { value: 2 as const, label: "L2" },
  { value: 3 as const, label: "L3" },
];

// ===== Filtri per Entities tab =====

interface EntityFilters {
  entity_type: string;
  ambito_canonico: string;
  status: string;
}

const DEFAULT_ENTITY_FILTERS: EntityFilters = {
  entity_type: "",
  ambito_canonico: "",
  status: "",
};

// ===== Filtri per altre wiki tabs (sources/concepts/synthesis) =====

interface WikiFilters {
  ambito_canonico: string;
  status: string;
}

const DEFAULT_WIKI_FILTERS: WikiFilters = {
  ambito_canonico: "",
  status: "",
};

// ===== Filtri per Memory Tree tab =====

interface MemoryFilters {
  tree_kind: string;
  level: "all" | 1 | 2 | 3;
}

const DEFAULT_MEMORY_FILTERS: MemoryFilters = {
  tree_kind: "",
  level: "all",
};

/** Pagina full-screen Wiki: tabs orizzontali per 5 categorie SCO + Memory Tree. */
export function WikiView() {
  const [activeTab, setActiveTab] = useState<TabId>("entities");
  const [stats, setStats] = useState<WikiStatsResponse | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);

  // ===== Wiki state per categoria (sources/entities/concepts/synthesis/glossari) =====
  const [wikiData, setWikiData] = useState<WikiListResponse | null>(null);
  const [wikiLoading, setWikiLoading] = useState<boolean>(false);
  const [wikiError, setWikiError] = useState<string | null>(null);
  const [entityFilters, setEntityFilters] = useState<EntityFilters>(DEFAULT_ENTITY_FILTERS);
  const [wikiFilters, setWikiFilters] = useState<WikiFilters>(DEFAULT_WIKI_FILTERS);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [detail, setDetail] = useState<WikiFileDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // ===== Memory Tree state =====
  const [chunks, setChunks] = useState<TreeChunkItem[]>([]);
  const [summaries, setSummaries] = useState<TreeSummaryItemV2[]>([]);
  const [memoryLoading, setMemoryLoading] = useState<boolean>(false);
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [memoryFilters, setMemoryFilters] = useState<MemoryFilters>(DEFAULT_MEMORY_FILTERS);
  const [selectedTreeId, setSelectedTreeId] = useState<string | null>(null);

  // Ref per evitare race fra polling e refresh manuale
  const inFlightRef = useRef<boolean>(false);

  /** Carica counts categorie wiki nel vault attivo. Resilient se vault non risolto. */
  const refreshStats = useCallback(async () => {
    try {
      setStatsError(null);
      const res = await withRetry(() => apiClient.getWikiStats(), "getWikiStats");
      setStats(res);
    } catch (err) {
      const msg = formatError(err);
      setStatsError(msg);
      // Non mostriamo toast: stats footer e' decorativo, non bloccante.
    }
  }, []);

  /** Carica lista wiki per categoria attiva. Tab dipendente: filtri diversi per Entities. */
  const refreshWiki = useCallback(
    async (category: WikiCategory) => {
      if (inFlightRef.current) return;
      inFlightRef.current = true;
      setWikiLoading(true);
      try {
        setWikiError(null);
        let res: WikiListResponse;
        if (category === "sources") {
          res = await withRetry(
            () =>
              apiClient.listWikiSources({
                ambito_canonico: wikiFilters.ambito_canonico || undefined,
                status: wikiFilters.status || undefined,
                limit: 200,
              }),
            "listWikiSources",
          );
        } else if (category === "entities") {
          res = await withRetry(
            () =>
              apiClient.listWikiEntities({
                entity_type: entityFilters.entity_type || undefined,
                ambito_canonico: entityFilters.ambito_canonico || undefined,
                status: entityFilters.status || undefined,
                limit: 200,
              }),
            "listWikiEntities",
          );
        } else if (category === "concepts") {
          res = await withRetry(
            () =>
              apiClient.listWikiConcepts({
                ambito_canonico: wikiFilters.ambito_canonico || undefined,
                status: wikiFilters.status || undefined,
                limit: 200,
              }),
            "listWikiConcepts",
          );
        } else if (category === "synthesis") {
          res = await withRetry(
            () =>
              apiClient.listWikiSynthesis({
                ambito_canonico: wikiFilters.ambito_canonico || undefined,
                status: wikiFilters.status || undefined,
                limit: 200,
              }),
            "listWikiSynthesis",
          );
        } else {
          // glossari — nessun filtro
          res = await withRetry(
            () => apiClient.listWikiGlossari({ limit: 200 }),
            "listWikiGlossari",
          );
        }
        setWikiData(res);
      } catch (err) {
        const msg = formatError(err);
        setWikiError(msg);
        setWikiData(null);
      } finally {
        setWikiLoading(false);
        inFlightRef.current = false;
      }
    },
    [entityFilters, wikiFilters],
  );

  /** Carica chunks + summaries Memory Tree. Filtri tree_kind + level. */
  const refreshMemory = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    setMemoryLoading(true);
    try {
      setMemoryError(null);
      const [chunksRes, summariesRes] = await Promise.all([
        withRetry(
          () => apiClient.getMemoryTreeChunks({ limit: 50 }),
          "getMemoryTreeChunks",
        ),
        withRetry(
          () =>
            apiClient.getMemoryTreeSummariesNew({
              tree_kind: memoryFilters.tree_kind || undefined,
              level: memoryFilters.level === "all" ? undefined : memoryFilters.level,
              limit: 50,
            }),
          "getMemoryTreeSummariesNew",
        ),
      ]);
      setChunks(chunksRes);
      setSummaries(summariesRes);
    } catch (err) {
      const msg = formatError(err);
      setMemoryError(msg);
    } finally {
      setMemoryLoading(false);
      inFlightRef.current = false;
    }
  }, [memoryFilters]);

  /** Refresh combinato (stats + tab attiva). */
  const refresh = useCallback(
    async (showToast = false) => {
      await refreshStats();
      if (activeTab === "memory-tree") {
        await refreshMemory();
      } else {
        await refreshWiki(activeTab);
      }
      if (showToast) toast.success("Wiki aggiornato");
    },
    [activeTab, refreshMemory, refreshStats, refreshWiki],
  );

  /** Fetch dettaglio singolo file wiki al click su item. */
  const fetchDetail = useCallback(
    async (category: WikiCategory, slug: string) => {
      setDetailLoading(true);
      setDetailError(null);
      setDetail(null);
      try {
        const res = await withRetry(
          () => apiClient.getWikiFile(category, slug),
          `getWikiFile(${category}/${slug})`,
        );
        setDetail(res);
      } catch (err) {
        setDetailError(formatError(err));
      } finally {
        setDetailLoading(false);
      }
    },
    [],
  );

  // === Effetti: cambio tab triggera refresh categoria + reset selezione ===
  useEffect(() => {
    setSelectedSlug(null);
    setDetail(null);
    setDetailError(null);
    setSelectedTreeId(null);
    if (activeTab === "memory-tree") {
      void refreshMemory();
    } else {
      void refreshWiki(activeTab);
    }
  }, [activeTab, refreshMemory, refreshWiki]);

  // === Effetto stats: una volta al mount ===
  useEffect(() => {
    void refreshStats();
  }, [refreshStats]);

  // === Polling automatico 30s ===
  useEffect(() => {
    const id = setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  // === Effetto detail fetch al click ===
  useEffect(() => {
    if (selectedSlug && activeTab !== "memory-tree") {
      void fetchDetail(activeTab, selectedSlug);
    }
  }, [selectedSlug, activeTab, fetchDetail]);

  const selectedChunk = useMemo(
    () => chunks.find((c) => c.id === selectedTreeId) ?? null,
    [chunks, selectedTreeId],
  );
  const selectedSummary = useMemo(
    () => summaries.find((s) => s.id === selectedTreeId) ?? null,
    [summaries, selectedTreeId],
  );

  return (
    <div className="flex h-full flex-col bg-sco-bg">
      {/* === Header tabs orizzontali === */}
      <div className="shrink-0 border-b border-sco-border bg-sco-surface">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2">
            <Library size={18} className="text-sco-blue" />
            <h2 className="text-sm font-semibold text-sco-text dark:text-sco-text-dark">
              Wiki SCO
            </h2>
            {stats && (
              <span className="ml-1 rounded bg-sco-muted px-1.5 py-0.5 text-[10px] text-sco-muted-foreground">
                {stats.total} file totali
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={() => void refresh(true)}
            disabled={wikiLoading || memoryLoading}
            className="flex items-center gap-1 rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-xs text-sco-text transition-colors hover:border-sco-blue hover:bg-sco-muted disabled:cursor-not-allowed disabled:opacity-50 dark:text-sco-text-dark"
            aria-label="Aggiorna Wiki"
            title="Aggiorna"
          >
            <RefreshCw
              size={12}
              className={cn((wikiLoading || memoryLoading) && "animate-spin")}
            />
            <span className="hidden sm:inline">Aggiorna</span>
          </button>
        </div>

        {/* Tabs scrollabili orizzontalmente su mobile */}
        <div className="flex items-center gap-1 overflow-x-auto px-4 pb-2" role="tablist">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const count =
              tab.id === "memory-tree"
                ? chunks.length + summaries.length
                : (stats?.counts[tab.id] ?? null);
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex shrink-0 items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors",
                  isActive
                    ? "border-sco-blue bg-sco-blue/10 text-sco-blue"
                    : "border-transparent text-sco-muted-foreground hover:border-sco-border hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark",
                )}
                title={tab.description}
              >
                <Icon size={13} />
                <span>{tab.label}</span>
                {count !== null && count > 0 && (
                  <span
                    className={cn(
                      "ml-1 rounded px-1.5 py-0 text-[10px] font-normal",
                      isActive
                        ? "bg-sco-blue/20 text-sco-blue"
                        : "bg-sco-muted text-sco-muted-foreground",
                    )}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* === Body === */}
      <div className="flex flex-1 flex-col overflow-hidden md:flex-row">
        {activeTab === "memory-tree" ? (
          <MemoryTreePane
            chunks={chunks}
            summaries={summaries}
            loading={memoryLoading}
            error={memoryError}
            filters={memoryFilters}
            onFiltersChange={setMemoryFilters}
            onRetry={() => void refreshMemory()}
            selectedTreeId={selectedTreeId}
            onSelectId={setSelectedTreeId}
            selectedChunk={selectedChunk}
            selectedSummary={selectedSummary}
          />
        ) : (
          <WikiCategoryPane
            category={activeTab}
            data={wikiData}
            loading={wikiLoading}
            error={wikiError}
            entityFilters={entityFilters}
            onEntityFiltersChange={setEntityFilters}
            wikiFilters={wikiFilters}
            onWikiFiltersChange={setWikiFilters}
            selectedSlug={selectedSlug}
            onSelectSlug={setSelectedSlug}
            detail={detail}
            detailLoading={detailLoading}
            detailError={detailError}
            onRetry={() => void refreshWiki(activeTab)}
          />
        )}
      </div>

      {/* === Footer stats === */}
      <div className="shrink-0 border-t border-sco-border bg-sco-surface px-6 py-2">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-sco-muted-foreground">
          {stats && !statsError ? (
            <>
              <span className="flex items-center gap-1">
                <Library size={11} className="text-sco-blue" />
                <strong className="font-medium text-sco-text dark:text-sco-text-dark">
                  {stats.total}
                </strong>{" "}
                file wiki
              </span>
              <span className="opacity-50">·</span>
              {TABS.filter((t) => t.id !== "memory-tree").map((tab) => {
                const count = stats.counts[tab.id as WikiCategory] ?? 0;
                return (
                  <span key={tab.id}>
                    {tab.label}:{" "}
                    <strong className="font-medium text-sco-text dark:text-sco-text-dark">
                      {count}
                    </strong>
                  </span>
                );
              })}
              {(chunks.length > 0 || summaries.length > 0) && (
                <>
                  <span className="opacity-50">·</span>
                  <span className="flex items-center gap-1">
                    <GitBranch size={11} className="text-sco-amber" />
                    Memory:{" "}
                    <strong className="font-medium text-sco-text dark:text-sco-text-dark">
                      {chunks.length}
                    </strong>{" "}
                    chunks /{" "}
                    <strong className="font-medium text-sco-text dark:text-sco-text-dark">
                      {summaries.length}
                    </strong>{" "}
                    summaries
                  </span>
                </>
              )}
              <span className="ml-auto truncate text-[10px] opacity-60" title={stats.vault_path}>
                Vault: {abbreviatePath(stats.vault_path)}
              </span>
            </>
          ) : statsError ? (
            <span className="flex items-center gap-1 text-sco-amber">
              <AlertCircle size={11} />
              Vault non risolto. Registra un vault dalla schermata Vault.
            </span>
          ) : (
            <span className="italic">Caricamento statistiche...</span>
          )}
        </div>
      </div>
    </div>
  );
}

// =====================================================================
// === Pane per categoria wiki (sources / entities / concepts / etc.) ===
// =====================================================================

interface WikiCategoryPaneProps {
  category: WikiCategory;
  data: WikiListResponse | null;
  loading: boolean;
  error: string | null;
  entityFilters: EntityFilters;
  onEntityFiltersChange: (f: EntityFilters) => void;
  wikiFilters: WikiFilters;
  onWikiFiltersChange: (f: WikiFilters) => void;
  selectedSlug: string | null;
  onSelectSlug: (slug: string | null) => void;
  detail: WikiFileDetail | null;
  detailLoading: boolean;
  detailError: string | null;
  onRetry: () => void;
}

function WikiCategoryPane({
  category,
  data,
  loading,
  error,
  entityFilters,
  onEntityFiltersChange,
  wikiFilters,
  onWikiFiltersChange,
  selectedSlug,
  onSelectSlug,
  detail,
  detailLoading,
  detailError,
  onRetry,
}: WikiCategoryPaneProps) {
  const tabMeta = TABS.find((t) => t.id === category);
  const isEntities = category === "entities";
  const showAmbitoStatusFilters =
    category === "sources" ||
    category === "concepts" ||
    category === "synthesis";

  return (
    <>
      {/* === Left pane: filtri + lista (40%) === */}
      <aside
        className={cn(
          "flex w-full flex-col overflow-hidden border-sco-border bg-sco-surface md:w-2/5 md:border-r",
          selectedSlug && "hidden md:flex",
        )}
        role="region"
        aria-label={`Lista ${tabMeta?.label ?? category}`}
      >
        {/* Filtri tipizzati */}
        {(isEntities || showAmbitoStatusFilters) && (
          <div className="shrink-0 border-b border-sco-border bg-sco-surface px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <Filter size={11} className="text-sco-muted-foreground" />
              {isEntities && (
                <select
                  value={entityFilters.entity_type}
                  onChange={(e) =>
                    onEntityFiltersChange({
                      ...entityFilters,
                      entity_type: e.target.value,
                    })
                  }
                  className="rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-xs text-sco-text outline-none transition-colors hover:border-sco-blue focus:border-sco-blue dark:text-sco-text-dark"
                  aria-label="Filtra per entity_type"
                >
                  {ENTITY_TYPES.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}
              {(isEntities || showAmbitoStatusFilters) && (
                <select
                  value={
                    isEntities
                      ? entityFilters.ambito_canonico
                      : wikiFilters.ambito_canonico
                  }
                  onChange={(e) => {
                    if (isEntities) {
                      onEntityFiltersChange({
                        ...entityFilters,
                        ambito_canonico: e.target.value,
                      });
                    } else {
                      onWikiFiltersChange({
                        ...wikiFilters,
                        ambito_canonico: e.target.value,
                      });
                    }
                  }}
                  className="rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-xs text-sco-text outline-none transition-colors hover:border-sco-blue focus:border-sco-blue dark:text-sco-text-dark"
                  aria-label="Filtra per ambito_canonico"
                >
                  {AMBITI_CANONICI.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}
              {(isEntities || showAmbitoStatusFilters) && (
                <select
                  value={
                    isEntities ? entityFilters.status : wikiFilters.status
                  }
                  onChange={(e) => {
                    if (isEntities) {
                      onEntityFiltersChange({
                        ...entityFilters,
                        status: e.target.value,
                      });
                    } else {
                      onWikiFiltersChange({
                        ...wikiFilters,
                        status: e.target.value,
                      });
                    }
                  }}
                  className="rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-xs text-sco-text outline-none transition-colors hover:border-sco-blue focus:border-sco-blue dark:text-sco-text-dark"
                  aria-label="Filtra per status"
                >
                  {STATUSES.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}
              {((isEntities &&
                (entityFilters.entity_type ||
                  entityFilters.ambito_canonico ||
                  entityFilters.status)) ||
                (showAmbitoStatusFilters &&
                  (wikiFilters.ambito_canonico || wikiFilters.status))) && (
                <button
                  type="button"
                  onClick={() => {
                    if (isEntities) onEntityFiltersChange(DEFAULT_ENTITY_FILTERS);
                    else onWikiFiltersChange(DEFAULT_WIKI_FILTERS);
                  }}
                  className="rounded-md px-2 py-1 text-xs text-sco-muted-foreground transition-colors hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
                  aria-label="Resetta filtri"
                >
                  Reset
                </button>
              )}
            </div>
          </div>
        )}

        {/* Lista items */}
        <div className="flex-1 overflow-y-auto px-2 py-2">
          {loading && !data && (
            <div className="flex h-full items-center justify-center">
              <div className="flex items-center gap-2 text-sm text-sco-muted-foreground">
                <Loader2 size={16} className="animate-spin text-sco-blue" />
                <span>Caricamento {tabMeta?.label}...</span>
              </div>
            </div>
          )}

          {error && !data && (
            <div className="flex h-full items-center justify-center p-4">
              <div className="flex max-w-sm flex-col items-center gap-3 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/10 text-red-500">
                  <AlertCircle size={20} />
                </div>
                <h3 className="text-sm font-semibold text-sco-text dark:text-sco-text-dark">
                  Errore caricamento
                </h3>
                <p className="text-xs text-sco-muted-foreground">{error}</p>
                <button
                  type="button"
                  onClick={onRetry}
                  className="rounded-md bg-sco-blue px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-sco-navy"
                >
                  Riprova
                </button>
              </div>
            </div>
          )}

          {data && data.items.length === 0 && !loading && (
            <EmptyState category={category} label={tabMeta?.label ?? category} />
          )}

          {data && data.items.length > 0 && (
            <ul className="space-y-1">
              {data.items.map((item) => (
                <WikiItemCard
                  key={item.slug}
                  item={item}
                  isSelected={selectedSlug === item.slug}
                  onClick={() => onSelectSlug(item.slug)}
                />
              ))}
            </ul>
          )}
        </div>
      </aside>

      {/* === Right pane: detail (60%) === */}
      <section
        className={cn(
          "flex w-full flex-col overflow-y-auto bg-sco-bg md:w-3/5",
          !selectedSlug && "hidden md:flex",
        )}
        aria-label="Dettaglio file wiki selezionato"
      >
        {selectedSlug && (
          <button
            type="button"
            onClick={() => onSelectSlug(null)}
            className="m-3 self-start rounded-md border border-sco-border bg-sco-surface px-2 py-1 text-xs text-sco-muted-foreground hover:bg-sco-muted md:hidden"
            aria-label="Torna alla lista"
          >
            &larr; Lista
          </button>
        )}

        {!selectedSlug && (
          <div className="flex flex-1 items-center justify-center p-6">
            <p className="text-sm italic text-sco-muted-foreground">
              Seleziona un file dalla lista per vederne il dettaglio.
            </p>
          </div>
        )}

        {selectedSlug && detailLoading && (
          <div className="flex flex-1 items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-sco-muted-foreground">
              <Loader2 size={16} className="animate-spin text-sco-blue" />
              <span>Caricamento dettaglio...</span>
            </div>
          </div>
        )}

        {selectedSlug && detailError && !detail && (
          <div className="flex flex-1 items-center justify-center p-4">
            <div className="flex max-w-sm flex-col items-center gap-3 text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/10 text-red-500">
                <AlertCircle size={20} />
              </div>
              <p className="text-sm font-medium text-sco-text dark:text-sco-text-dark">
                Errore caricamento dettaglio
              </p>
              <p className="text-xs text-sco-muted-foreground">{detailError}</p>
            </div>
          </div>
        )}

        {selectedSlug && detail && <WikiDetailPane detail={detail} />}
      </section>
    </>
  );
}

// =====================================================================
// === Item card per lista wiki ===
// =====================================================================

interface WikiItemCardProps {
  item: WikiSummaryItem;
  isSelected: boolean;
  onClick: () => void;
}

function WikiItemCard({ item, isSelected, onClick }: WikiItemCardProps) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        aria-pressed={isSelected}
        className={cn(
          "w-full rounded-md border px-3 py-2 text-left transition-colors",
          isSelected
            ? "border-sco-blue bg-sco-blue/10"
            : "border-transparent hover:border-sco-border hover:bg-sco-muted",
        )}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <FileText
                size={11}
                className={cn(
                  "shrink-0",
                  isSelected ? "text-sco-blue" : "text-sco-muted-foreground",
                )}
              />
              <h4
                className={cn(
                  "truncate text-xs font-medium",
                  isSelected
                    ? "text-sco-blue dark:text-sco-text-dark"
                    : "text-sco-text dark:text-sco-text-dark",
                )}
              >
                {item.title}
              </h4>
            </div>
            {item.body_excerpt && (
              <p className="mt-1 line-clamp-2 text-[10px] text-sco-muted-foreground">
                {item.body_excerpt}
              </p>
            )}
            <div className="mt-1 flex flex-wrap items-center gap-1">
              {item.entity_type && (
                <span className="rounded bg-sco-muted px-1.5 py-0 text-[9px] font-mono text-sco-muted-foreground">
                  {item.entity_type}
                </span>
              )}
              {item.ambito_canonico && (
                <span className="rounded bg-sco-blue/10 px-1.5 py-0 text-[9px] text-sco-blue">
                  {item.ambito_canonico}
                </span>
              )}
              {item.status && (
                <span
                  className={cn(
                    "rounded px-1.5 py-0 text-[9px] font-mono",
                    statusColorClass(item.status),
                  )}
                >
                  {item.status}
                </span>
              )}
              {item.applica_entity_count > 0 && (
                <span className="rounded bg-sco-amber/10 px-1.5 py-0 text-[9px] text-sco-amber">
                  {item.applica_entity_count} clienti
                </span>
              )}
              {item.relationships_count > 0 && (
                <span className="rounded bg-sco-navy/10 px-1.5 py-0 text-[9px] text-sco-navy dark:text-sco-text-dark">
                  {item.relationships_count} rel
                </span>
              )}
            </div>
          </div>
        </div>
      </button>
    </li>
  );
}

// =====================================================================
// === Detail pane per singolo file wiki ===
// =====================================================================

function WikiDetailPane({ detail }: { detail: WikiFileDetail }) {
  const lastModifiedPretty = useMemo(
    () => formatIsoDate(detail.last_modified),
    [detail.last_modified],
  );

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-5">
      {/* Header */}
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-sco-blue/10 text-sco-blue">
          <FileText size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-lg font-semibold text-sco-text dark:text-sco-text-dark">
            {detail.title}
          </h3>
          <p className="mt-0.5 truncate text-[11px] text-sco-muted-foreground">
            {detail.slug}.md
          </p>
        </div>
      </div>

      {/* Metadata frontmatter */}
      <div className="mb-4 grid grid-cols-1 gap-2 rounded-lg border border-sco-border bg-sco-surface p-3 sm:grid-cols-2">
        {detail.entity_type && (
          <MetaRow label="Entity type" value={detail.entity_type} icon={Type} />
        )}
        {detail.entity_subtype && (
          <MetaRow
            label="Entity subtype"
            value={detail.entity_subtype}
            icon={Layers}
          />
        )}
        {detail.ambito_canonico && (
          <MetaRow
            label="Ambito"
            value={detail.ambito_canonico}
            icon={Tags}
          />
        )}
        {detail.status && (
          <MetaRow label="Status" value={detail.status} icon={Clock} />
        )}
        {detail.last_reviewed && (
          <MetaRow
            label="Last reviewed"
            value={detail.last_reviewed}
            icon={Clock}
          />
        )}
        {lastModifiedPretty && (
          <MetaRow
            label="Modificato"
            value={lastModifiedPretty}
            icon={Clock}
          />
        )}
        {detail.domini_applicabili.length > 0 && (
          <div className="col-span-full">
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
              Domini applicabili
            </div>
            <div className="flex flex-wrap gap-1">
              {detail.domini_applicabili.map((d) => (
                <span
                  key={d}
                  className="rounded bg-sco-blue/10 px-2 py-0.5 text-[10px] text-sco-blue"
                >
                  {d}
                </span>
              ))}
            </div>
          </div>
        )}
        {detail.tags.length > 0 && (
          <div className="col-span-full">
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
              Tags
            </div>
            <div className="flex flex-wrap gap-1">
              {detail.tags.map((t) => (
                <span
                  key={t}
                  className="rounded bg-sco-muted px-2 py-0.5 text-[10px] font-mono text-sco-muted-foreground"
                >
                  #{t}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Relationships count summary */}
      {(detail.relationships.length > 0 ||
        detail.applica_entity.length > 0 ||
        detail.pertinenza_in_verifica.length > 0 ||
        detail.fornitore_di.length > 0) && (
        <div className="mb-4 flex flex-wrap gap-2 text-[11px]">
          {detail.relationships.length > 0 && (
            <span className="rounded-md bg-sco-navy/10 px-2 py-1 text-sco-navy dark:text-sco-text-dark">
              <strong>{detail.relationships.length}</strong> relationships
            </span>
          )}
          {detail.applica_entity.length > 0 && (
            <span className="rounded-md bg-sco-amber/10 px-2 py-1 text-sco-amber">
              <strong>{detail.applica_entity.length}</strong> clienti applicano
            </span>
          )}
          {detail.pertinenza_in_verifica.length > 0 && (
            <span className="rounded-md bg-orange-500/10 px-2 py-1 text-orange-600 dark:text-orange-400">
              <strong>{detail.pertinenza_in_verifica.length}</strong> in
              verifica
            </span>
          )}
          {detail.fornitore_di.length > 0 && (
            <span className="rounded-md bg-sco-blue/10 px-2 py-1 text-sco-blue">
              <strong>{detail.fornitore_di.length}</strong> servizi forniti
            </span>
          )}
        </div>
      )}

      {/* Markdown body */}
      <div className="prose prose-sm max-w-none rounded-lg border border-sco-border bg-sco-surface-elevated p-4 leading-relaxed dark:prose-invert prose-p:my-2 prose-headings:mt-3 prose-headings:mb-2 prose-pre:my-2 prose-pre:bg-sco-bg prose-pre:border prose-pre:border-sco-border prose-code:text-sco-blue dark:prose-code:text-sco-amber">
        {detail.body_md ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {detail.body_md}
          </ReactMarkdown>
        ) : (
          <p className="italic text-sco-muted-foreground">
            Body vuoto (solo frontmatter).
          </p>
        )}
      </div>
    </div>
  );
}

// =====================================================================
// === Memory Tree pane (chunks + summaries Fase 4) ===
// =====================================================================

interface MemoryTreePaneProps {
  chunks: TreeChunkItem[];
  summaries: TreeSummaryItemV2[];
  loading: boolean;
  error: string | null;
  filters: MemoryFilters;
  onFiltersChange: (f: MemoryFilters) => void;
  onRetry: () => void;
  selectedTreeId: string | null;
  onSelectId: (id: string | null) => void;
  selectedChunk: TreeChunkItem | null;
  selectedSummary: TreeSummaryItemV2 | null;
}

function MemoryTreePane({
  chunks,
  summaries,
  loading,
  error,
  filters,
  onFiltersChange,
  onRetry,
  selectedTreeId,
  onSelectId,
  selectedChunk,
  selectedSummary,
}: MemoryTreePaneProps) {
  const isEmpty = !loading && !error && chunks.length === 0 && summaries.length === 0;

  return (
    <>
      {/* === Left pane: filtri + lista (40%) === */}
      <aside
        className={cn(
          "flex w-full flex-col overflow-hidden border-sco-border bg-sco-surface md:w-2/5 md:border-r",
          selectedTreeId && "hidden md:flex",
        )}
        role="region"
        aria-label="Lista Memory Tree"
      >
        {/* Filtri */}
        <div className="shrink-0 border-b border-sco-border bg-sco-surface px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <Filter size={11} className="text-sco-muted-foreground" />
            <select
              value={filters.tree_kind}
              onChange={(e) =>
                onFiltersChange({ ...filters, tree_kind: e.target.value })
              }
              className="rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-xs text-sco-text outline-none transition-colors hover:border-sco-blue focus:border-sco-blue dark:text-sco-text-dark"
              aria-label="Filtra per tree_kind"
            >
              {TREE_KINDS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <div className="flex items-center gap-0.5 rounded-md border border-sco-border bg-sco-bg p-0.5">
              {SUMMARY_LEVELS.map((lv) => {
                const isActive = filters.level === lv.value;
                return (
                  <button
                    key={String(lv.value)}
                    type="button"
                    onClick={() =>
                      onFiltersChange({ ...filters, level: lv.value })
                    }
                    className={cn(
                      "rounded px-2 py-0.5 text-xs font-medium transition-colors",
                      isActive
                        ? "bg-sco-blue text-white"
                        : "text-sco-muted-foreground hover:bg-sco-muted",
                    )}
                    aria-label={`Filtra per level ${lv.label}`}
                    aria-pressed={isActive}
                  >
                    {lv.label}
                  </button>
                );
              })}
            </div>
            {(filters.tree_kind || filters.level !== "all") && (
              <button
                type="button"
                onClick={() => onFiltersChange(DEFAULT_MEMORY_FILTERS)}
                className="rounded-md px-2 py-1 text-xs text-sco-muted-foreground transition-colors hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
                aria-label="Resetta filtri Memory Tree"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Lista */}
        <div className="flex-1 overflow-y-auto px-2 py-2">
          {loading && chunks.length === 0 && summaries.length === 0 && (
            <div className="flex h-full items-center justify-center">
              <div className="flex items-center gap-2 text-sm text-sco-muted-foreground">
                <Loader2 size={16} className="animate-spin text-sco-blue" />
                <span>Caricamento Memory Tree...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="flex h-full items-center justify-center p-4">
              <div className="flex max-w-sm flex-col items-center gap-3 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/10 text-red-500">
                  <AlertCircle size={20} />
                </div>
                <h3 className="text-sm font-semibold text-sco-text dark:text-sco-text-dark">
                  Errore caricamento Memory Tree
                </h3>
                <p className="text-xs text-sco-muted-foreground">{error}</p>
                <button
                  type="button"
                  onClick={onRetry}
                  className="rounded-md bg-sco-blue px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-sco-navy"
                >
                  Riprova
                </button>
              </div>
            </div>
          )}

          {isEmpty && <EmptyState category="memory-tree" label="Memory Tree" />}

          {/* Summaries L1/L2/L3 prima (più alto valore semantico) */}
          {summaries.length > 0 && (
            <>
              <div className="mb-1 mt-2 flex items-center gap-1 px-2 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
                <Layers size={10} />
                Summaries ({summaries.length})
              </div>
              <ul className="mb-3 space-y-1">
                {summaries.map((s) => (
                  <MemorySummaryCard
                    key={s.id}
                    summary={s}
                    isSelected={selectedTreeId === s.id}
                    onClick={() => onSelectId(s.id)}
                  />
                ))}
              </ul>
            </>
          )}

          {/* Chunks L0 dopo */}
          {chunks.length > 0 && (
            <>
              <div className="mb-1 mt-2 flex items-center gap-1 px-2 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
                <FileText size={10} />
                Chunks ({chunks.length})
              </div>
              <ul className="space-y-1">
                {chunks.map((c) => (
                  <MemoryChunkCard
                    key={c.id}
                    chunk={c}
                    isSelected={selectedTreeId === c.id}
                    onClick={() => onSelectId(c.id)}
                  />
                ))}
              </ul>
            </>
          )}
        </div>
      </aside>

      {/* === Right pane: detail (60%) === */}
      <section
        className={cn(
          "flex w-full flex-col overflow-y-auto bg-sco-bg md:w-3/5",
          !selectedTreeId && "hidden md:flex",
        )}
        aria-label="Dettaglio Memory Tree selezionato"
      >
        {selectedTreeId && (
          <button
            type="button"
            onClick={() => onSelectId(null)}
            className="m-3 self-start rounded-md border border-sco-border bg-sco-surface px-2 py-1 text-xs text-sco-muted-foreground hover:bg-sco-muted md:hidden"
            aria-label="Torna alla lista"
          >
            &larr; Lista
          </button>
        )}

        {!selectedTreeId && (
          <div className="flex flex-1 items-center justify-center p-6">
            <p className="text-sm italic text-sco-muted-foreground">
              Seleziona un summary o un chunk per vederne il dettaglio.
            </p>
          </div>
        )}

        {selectedSummary && <MemorySummaryDetail summary={selectedSummary} />}
        {selectedChunk && !selectedSummary && (
          <MemoryChunkDetail chunk={selectedChunk} />
        )}
      </section>
    </>
  );
}

// =====================================================================
// === Card per summary L1/L2/L3 ===
// =====================================================================

interface MemorySummaryCardProps {
  summary: TreeSummaryItemV2;
  isSelected: boolean;
  onClick: () => void;
}

function MemorySummaryCard({
  summary,
  isSelected,
  onClick,
}: MemorySummaryCardProps) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        aria-pressed={isSelected}
        className={cn(
          "w-full rounded-md border px-3 py-2 text-left transition-colors",
          isSelected
            ? "border-sco-blue bg-sco-blue/10"
            : "border-transparent hover:border-sco-border hover:bg-sco-muted",
        )}
      >
        <div className="flex items-start gap-2">
          <Layers
            size={11}
            className={cn(
              "mt-0.5 shrink-0",
              isSelected ? "text-sco-blue" : "text-sco-amber",
            )}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "truncate text-xs font-medium",
                  isSelected
                    ? "text-sco-blue dark:text-sco-text-dark"
                    : "text-sco-text dark:text-sco-text-dark",
                )}
              >
                {summary.tree_kind}/{summary.tree_id}
              </span>
              <span className="shrink-0 rounded bg-sco-muted px-1 py-0 font-mono text-[9px] text-sco-muted-foreground">
                L{summary.level}
              </span>
            </div>
            {summary.content_preview && (
              <p className="mt-0.5 line-clamp-2 text-[10px] text-sco-muted-foreground">
                {summary.content_preview}
              </p>
            )}
            <div className="mt-1 flex flex-wrap items-center gap-1 text-[9px] text-sco-muted-foreground">
              <span>{summary.token_count.toLocaleString("it-IT")} token</span>
              {summary.source_kind_hint && (
                <>
                  <span>·</span>
                  <span>{summary.source_kind_hint}</span>
                </>
              )}
              <span>·</span>
              <span>{summary.status}</span>
            </div>
          </div>
        </div>
      </button>
    </li>
  );
}

// =====================================================================
// === Card per chunk L0 ===
// =====================================================================

interface MemoryChunkCardProps {
  chunk: TreeChunkItem;
  isSelected: boolean;
  onClick: () => void;
}

function MemoryChunkCard({ chunk, isSelected, onClick }: MemoryChunkCardProps) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        aria-pressed={isSelected}
        className={cn(
          "w-full rounded-md border px-3 py-2 text-left transition-colors",
          isSelected
            ? "border-sco-blue bg-sco-blue/10"
            : "border-transparent hover:border-sco-border hover:bg-sco-muted",
        )}
      >
        <div className="flex items-start gap-2">
          <FileText
            size={11}
            className={cn(
              "mt-0.5 shrink-0",
              isSelected ? "text-sco-blue" : "text-sco-muted-foreground",
            )}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "truncate text-xs font-medium",
                  isSelected
                    ? "text-sco-blue dark:text-sco-text-dark"
                    : "text-sco-text dark:text-sco-text-dark",
                )}
              >
                [{chunk.source_kind}] {chunk.source_id}
              </span>
              <span
                className={cn(
                  "shrink-0 rounded px-1 py-0 text-[9px] font-mono",
                  statusColorClass(chunk.status),
                )}
              >
                {chunk.status}
              </span>
            </div>
            {chunk.content_preview && (
              <p className="mt-0.5 line-clamp-2 text-[10px] text-sco-muted-foreground">
                {chunk.content_preview}
              </p>
            )}
            <div className="mt-1 flex flex-wrap items-center gap-1 text-[9px] text-sco-muted-foreground">
              <span>{chunk.token_count.toLocaleString("it-IT")} token</span>
              <span>·</span>
              <span>seq {chunk.seq_in_source}</span>
              {chunk.tags.length > 0 && (
                <>
                  <span>·</span>
                  <span>tags: {chunk.tags.slice(0, 2).join(", ")}</span>
                </>
              )}
            </div>
          </div>
        </div>
      </button>
    </li>
  );
}

// =====================================================================
// === Detail summary ===
// =====================================================================

function MemorySummaryDetail({ summary }: { summary: TreeSummaryItemV2 }) {
  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-5">
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-sco-amber/10 text-sco-amber">
          <Layers size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-lg font-semibold text-sco-text dark:text-sco-text-dark">
            Summary L{summary.level}
          </h3>
          <p className="mt-0.5 text-[11px] text-sco-muted-foreground">
            {summary.tree_kind} · {summary.tree_id} · {summary.status}
          </p>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-2 rounded-lg border border-sco-border bg-sco-surface p-3 sm:grid-cols-2">
        <MetaRow
          label="Token count"
          value={summary.token_count.toLocaleString("it-IT")}
          icon={Type}
        />
        {summary.source_kind_hint && (
          <MetaRow
            label="Source kind"
            value={summary.source_kind_hint}
            icon={Tags}
          />
        )}
        <MetaRow label="Owner" value={summary.owner} icon={Tags} />
        <MetaRow
          label="Created"
          value={formatMsTimestamp(summary.created_at_ms)}
          icon={Clock}
        />
        {summary.sealed_at_ms && (
          <MetaRow
            label="Sealed"
            value={formatMsTimestamp(summary.sealed_at_ms)}
            icon={Clock}
          />
        )}
        {summary.children_chunk_ids.length > 0 && (
          <MetaRow
            label="Children chunks"
            value={String(summary.children_chunk_ids.length)}
            icon={FileText}
          />
        )}
        {summary.children_summary_ids.length > 0 && (
          <MetaRow
            label="Children summaries"
            value={String(summary.children_summary_ids.length)}
            icon={Layers}
          />
        )}
      </div>

      <div className="prose prose-sm max-w-none rounded-lg border border-sco-border bg-sco-surface-elevated p-4 leading-relaxed dark:prose-invert prose-p:my-2 prose-headings:mt-3 prose-headings:mb-2">
        {summary.content_summary ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {summary.content_summary}
          </ReactMarkdown>
        ) : (
          <p className="italic text-sco-muted-foreground">
            Summary vuoto.
          </p>
        )}
      </div>
    </div>
  );
}

// =====================================================================
// === Detail chunk ===
// =====================================================================

function MemoryChunkDetail({ chunk }: { chunk: TreeChunkItem }) {
  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-5">
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-sco-blue/10 text-sco-blue">
          <FileText size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-lg font-semibold text-sco-text dark:text-sco-text-dark">
            Chunk {chunk.id.slice(0, 8)}
          </h3>
          <p className="mt-0.5 text-[11px] text-sco-muted-foreground">
            {chunk.source_kind} · {chunk.source_id}
          </p>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-2 rounded-lg border border-sco-border bg-sco-surface p-3 sm:grid-cols-2">
        <MetaRow label="Status" value={chunk.status} icon={Clock} />
        <MetaRow
          label="Token count"
          value={chunk.token_count.toLocaleString("it-IT")}
          icon={Type}
        />
        <MetaRow
          label="Seq in source"
          value={String(chunk.seq_in_source)}
          icon={Layers}
        />
        <MetaRow label="Owner" value={chunk.owner} icon={Tags} />
        <MetaRow
          label="Created"
          value={formatMsTimestamp(chunk.created_at_ms)}
          icon={Clock}
        />
        <MetaRow
          label="Timestamp"
          value={formatMsTimestamp(chunk.timestamp_ms)}
          icon={Clock}
        />
        {chunk.tags.length > 0 && (
          <div className="col-span-full">
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
              Tags
            </div>
            <div className="flex flex-wrap gap-1">
              {chunk.tags.map((t) => (
                <span
                  key={t}
                  className="rounded bg-sco-muted px-2 py-0.5 text-[10px] font-mono text-sco-muted-foreground"
                >
                  #{t}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="prose prose-sm max-w-none rounded-lg border border-sco-border bg-sco-surface-elevated p-4 leading-relaxed dark:prose-invert prose-p:my-2 prose-headings:mt-3 prose-headings:mb-2">
        {chunk.content_preview ? (
          <p>{chunk.content_preview}</p>
        ) : (
          <p className="italic text-sco-muted-foreground">
            Preview vuoto.
          </p>
        )}
      </div>
    </div>
  );
}

// =====================================================================
// === Empty state condiviso ===
// =====================================================================

interface EmptyStateProps {
  category: TabId;
  label: string;
}

function EmptyState({ category, label }: EmptyStateProps) {
  const isMemory = category === "memory-tree";
  return (
    <div className="flex h-full items-center justify-center p-4">
      <div className="flex max-w-sm flex-col items-center gap-3 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-sco-blue/10 text-sco-blue">
          <FolderTree size={24} />
        </div>
        <h3 className="text-sm font-semibold text-sco-text dark:text-sco-text-dark">
          Categoria {label} vuota
        </h3>
        <p className="text-xs text-sco-muted-foreground">
          {isMemory ? (
            <>
              Nessun chunk o summary nel Memory Tree. Avvia un'ingestione tramite
              <code className="mx-1 rounded bg-sco-muted px-1 py-0.5 text-[10px]">
                POST /api/memory/tree/ingest
              </code>
              oppure usa la chat per generare contenuto.
            </>
          ) : (
            <>
              Aggiungi documenti al vault per popolare la categoria{" "}
              <strong>{label}</strong> via auto-ingest (Conv. 43 smart file
              injection).
            </>
          )}
        </p>
        <Link
          to="/vault"
          className="mt-1 rounded-md bg-sco-blue px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-sco-navy"
        >
          Vai a Vault
        </Link>
      </div>
    </div>
  );
}

// =====================================================================
// === Componenti atomici condivisi ===
// =====================================================================

function MetaRow({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: typeof FileText;
}) {
  return (
    <div className="flex items-start gap-1.5 text-[11px]">
      <Icon size={11} className="mt-0.5 shrink-0 text-sco-muted-foreground" />
      <div className="min-w-0 flex-1">
        <div className="text-[9px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
          {label}
        </div>
        <div className="truncate text-sco-text dark:text-sco-text-dark">
          {value}
        </div>
      </div>
    </div>
  );
}

// =====================================================================
// === Helper functions ===
// =====================================================================

function formatError(err: unknown): string {
  if (err instanceof ApiError) return `${err.code}: ${err.message}`;
  if (err instanceof Error) return err.message;
  return "Errore sconosciuto";
}

function formatIsoDate(iso: string): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("it-IT", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatMsTimestamp(ms: number): string {
  if (!ms) return "";
  try {
    const d = new Date(ms);
    if (Number.isNaN(d.getTime())) return String(ms);
    return d.toLocaleString("it-IT", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(ms);
  }
}

function abbreviatePath(path: string): string {
  if (!path) return "";
  const parts = path.split(/[\\/]/);
  if (parts.length <= 3) return path;
  return `.../${parts.slice(-2).join("/")}`;
}

function statusColorClass(status: string): string {
  const s = status.toLowerCase();
  if (s === "active" || s === "admitted" || s === "sealed") {
    return "bg-green-500/10 text-green-600 dark:text-green-400";
  }
  if (s === "draft" || s === "pending_extraction" || s === "buffered") {
    return "bg-sco-amber/10 text-sco-amber";
  }
  if (s === "stub") {
    return "bg-sco-blue/10 text-sco-blue";
  }
  if (s === "deprecated" || s === "archived" || s === "dropped") {
    return "bg-red-500/10 text-red-600 dark:text-red-400";
  }
  return "bg-sco-muted text-sco-muted-foreground";
}
