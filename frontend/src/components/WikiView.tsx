// SCO Compliance OS — Wiki view: Memory Tree gerarchico L0/L1/L2 navigabile
// Wave 2 v0.3.0 OpenHuman replica — consuma /api/memory/tree-summaries + /api/memory/hotness/top
// Conv. 48 enforcement: il backend è single source of truth. Niente ottimizzazioni "preserva-prev".
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Filter,
  FolderTree,
  Hash,
  Loader2,
  RefreshCw,
  TrendingUp,
} from "lucide-react";

import { apiClient, ApiError } from "@/api/client";
import { cn } from "@/lib/cn";
import type { HotnessItem, TreeLevel, TreeSummaryItem } from "@/types/api";

// Polling interval in ms. 30s come da brief.
const POLL_INTERVAL_MS = 30_000;
// Retry exponential backoff: 3 tentativi, base 500ms.
const MAX_RETRIES = 3;
const RETRY_BASE_MS = 500;

/** Wrapper retry exponential backoff per chiamate API resilient.
 *  Solleva l'ultimo errore se tutti i tentativi falliscono. */
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
  // tutti i retry falliti → log + rilancia
  // eslint-disable-next-line no-console
  console.warn(`[WikiView] ${label} fallito dopo ${MAX_RETRIES} tentativi`, lastErr);
  throw lastErr;
}

interface Filters {
  source: string; // "" = nessun filtro
  level: TreeLevel | "all";
  topic: string;
  day: string; // ISO YYYY-MM-DD oppure ""
}

const DEFAULT_FILTERS: Filters = {
  source: "",
  level: "all",
  topic: "",
  day: "",
};

/** Pagina full-screen Wiki Memory Tree.
 *  Layout: header filtri + 2-pane (tree left 40% / detail right 60%) + footer stats. */
export function WikiView() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [summaries, setSummaries] = useState<TreeSummaryItem[]>([]);
  const [hotness, setHotness] = useState<HotnessItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  // mobile detail toggle: su < md la detail view si apre solo dopo click su un nodo
  const [mobileDetailOpen, setMobileDetailOpen] = useState<boolean>(false);

  // Ref per evitare race condition fra polling e refresh manuale
  const inFlightRef = useRef<boolean>(false);

  /** Carica tree summaries + hotness in parallelo. Resilient con retry. */
  const refresh = useCallback(async (showToast = false) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    try {
      setError(null);
      const summariesParams: {
        source?: string;
        level?: TreeLevel;
        topic?: string;
        day?: string;
        limit?: number;
      } = { limit: 500 };
      if (filters.source) summariesParams.source = filters.source;
      if (filters.level !== "all") summariesParams.level = filters.level;
      if (filters.topic) summariesParams.topic = filters.topic;
      if (filters.day) summariesParams.day = filters.day;

      const [summariesRes, hotnessRes] = await Promise.all([
        withRetry(
          () => apiClient.listTreeSummaries(summariesParams),
          "listTreeSummaries",
        ),
        withRetry(() => apiClient.getTopHotness({ n: 20 }), "getTopHotness"),
      ]);
      setSummaries(summariesRes);
      setHotness(hotnessRes);
      if (showToast) toast.success("Memory Tree aggiornato");
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `${err.code}: ${err.message}`
          : err instanceof Error
            ? err.message
            : "Errore sconosciuto";
      setError(msg);
      if (showToast) toast.error(`Refresh fallito: ${msg}`);
    } finally {
      setLoading(false);
      inFlightRef.current = false;
    }
  }, [filters]);

  // Fetch iniziale + ri-fetch su cambio filtri
  useEffect(() => {
    setLoading(true);
    void refresh();
  }, [refresh]);

  // Polling periodico ogni 30s (solo se non in errore — evita storm di retry)
  useEffect(() => {
    if (error) return;
    const id = setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh, error]);

  // Costruisci indice per lookup rapido + albero gerarchico
  const summariesById = useMemo(() => {
    const map = new Map<string, TreeSummaryItem>();
    for (const s of summaries) map.set(s.id, s);
    return map;
  }, [summaries]);

  // Raggruppa per source → root nodes
  const tree = useMemo(() => {
    type SourceGroup = { source: string; topNodes: TreeSummaryItem[] };
    const bySource = new Map<string, TreeSummaryItem[]>();
    for (const s of summaries) {
      // top node = nodo senza parent OR il cui parent non è nel set filtrato
      const isTop =
        s.parent_id === null || !summariesById.has(s.parent_id ?? "");
      if (!isTop) continue;
      const arr = bySource.get(s.source) ?? [];
      arr.push(s);
      bySource.set(s.source, arr);
    }
    const groups: SourceGroup[] = [];
    for (const [source, topNodes] of bySource) {
      // Sort interno: level DESC (L2 prima), poi created_at DESC
      topNodes.sort((a, b) => {
        if (b.level !== a.level) return b.level - a.level;
        return b.created_at.localeCompare(a.created_at);
      });
      groups.push({ source, topNodes });
    }
    // Sort source alfabetico
    groups.sort((a, b) => a.source.localeCompare(b.source));
    return groups;
  }, [summaries, summariesById]);

  const selected = selectedId ? (summariesById.get(selectedId) ?? null) : null;

  // Stats globali compression ratio
  const stats = useMemo(() => {
    const l0 = summaries.filter((s) => s.level === 0).length;
    const l1 = summaries.filter((s) => s.level === 1).length;
    const l2 = summaries.filter((s) => s.level === 2).length;
    const ratio = l1 > 0 ? Math.round(l0 / l1) : 0;
    return { l0, l1, l2, ratio, total: summaries.length };
  }, [summaries]);

  // Source choices dropdown
  const sourceChoices = useMemo(() => {
    const set = new Set<string>();
    for (const s of summaries) set.add(s.source);
    return Array.from(set).sort();
  }, [summaries]);

  const toggleExpanded = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const onSelectNode = useCallback((id: string) => {
    setSelectedId(id);
    setMobileDetailOpen(true);
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  const hasActiveFilters =
    filters.source !== "" ||
    filters.level !== "all" ||
    filters.topic !== "" ||
    filters.day !== "";

  return (
    <div className="flex h-full flex-col bg-sco-bg">
      {/* === Header filtri === */}
      <div className="shrink-0 border-b border-sco-border bg-sco-surface px-6 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 pr-2">
            <FolderTree size={18} className="text-sco-blue" />
            <h2 className="text-sm font-semibold text-sco-text dark:text-sco-text-dark">
              Wiki — Memory Tree
            </h2>
          </div>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            {/* Source dropdown */}
            <div className="flex items-center gap-1.5">
              <Filter size={12} className="text-sco-muted-foreground" />
              <select
                value={filters.source}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, source: e.target.value }))
                }
                className="rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-xs text-sco-text outline-none transition-colors hover:border-sco-blue focus:border-sco-blue dark:text-sco-text-dark"
                aria-label="Filtra per source"
              >
                <option value="">Tutte le source</option>
                {sourceChoices.map((src) => (
                  <option key={src} value={src}>
                    {src}
                  </option>
                ))}
              </select>
            </div>

            {/* Level toggle */}
            <div className="flex items-center gap-0.5 rounded-md border border-sco-border bg-sco-bg p-0.5">
              {(["all", 0, 1, 2] as const).map((lv) => {
                const label = lv === "all" ? "Tutti" : `L${lv}`;
                const isActive = filters.level === lv;
                return (
                  <button
                    key={String(lv)}
                    type="button"
                    onClick={() => setFilters((f) => ({ ...f, level: lv }))}
                    className={cn(
                      "rounded px-2 py-0.5 text-xs font-medium transition-colors",
                      isActive
                        ? "bg-sco-blue text-white"
                        : "text-sco-muted-foreground hover:bg-sco-muted",
                    )}
                    aria-label={`Filtra per level ${label}`}
                    aria-pressed={isActive}
                  >
                    {label}
                  </button>
                );
              })}
            </div>

            {/* Topic input */}
            <input
              type="text"
              value={filters.topic}
              onChange={(e) =>
                setFilters((f) => ({ ...f, topic: e.target.value }))
              }
              placeholder="Topic..."
              className="w-32 rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-xs text-sco-text outline-none transition-colors hover:border-sco-blue focus:border-sco-blue dark:text-sco-text-dark"
              aria-label="Filtra per topic"
            />

            {/* Day picker */}
            <input
              type="date"
              value={filters.day}
              onChange={(e) =>
                setFilters((f) => ({ ...f, day: e.target.value }))
              }
              className="rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-xs text-sco-text outline-none transition-colors hover:border-sco-blue focus:border-sco-blue dark:text-sco-text-dark"
              aria-label="Filtra per giorno"
            />

            {/* Reset filtri */}
            {hasActiveFilters && (
              <button
                type="button"
                onClick={resetFilters}
                className="rounded-md px-2 py-1 text-xs text-sco-muted-foreground transition-colors hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
                aria-label="Resetta filtri"
              >
                Reset
              </button>
            )}

            {/* Refresh manuale */}
            <button
              type="button"
              onClick={() => void refresh(true)}
              disabled={loading}
              className="flex items-center gap-1 rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-xs text-sco-text transition-colors hover:border-sco-blue hover:bg-sco-muted disabled:cursor-not-allowed disabled:opacity-50 dark:text-sco-text-dark"
              aria-label="Aggiorna Memory Tree"
              title="Aggiorna"
            >
              <RefreshCw
                size={12}
                className={cn(loading && "animate-spin")}
              />
              <span className="hidden sm:inline">Aggiorna</span>
            </button>
          </div>
        </div>
      </div>

      {/* === Body === */}
      <div className="flex flex-1 flex-col overflow-hidden md:flex-row">
        {/* Stato loading iniziale */}
        {loading && summaries.length === 0 && !error && (
          <div className="flex flex-1 items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-sco-muted-foreground">
              <Loader2 size={16} className="animate-spin text-sco-blue" />
              <span>Caricamento Memory Tree...</span>
            </div>
          </div>
        )}

        {/* Stato errore (con summaries vuote) */}
        {error && summaries.length === 0 && !loading && (
          <div className="flex flex-1 items-center justify-center p-6">
            <div className="flex max-w-md flex-col items-center gap-3 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 text-red-500">
                <FolderTree size={24} />
              </div>
              <h3 className="text-base font-semibold text-sco-text dark:text-sco-text-dark">
                Backend non raggiungibile
              </h3>
              <p className="text-sm text-sco-muted-foreground">{error}</p>
              <button
                type="button"
                onClick={() => void refresh(true)}
                className="rounded-md bg-sco-blue px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-sco-navy"
              >
                Riprova
              </button>
            </div>
          </div>
        )}

        {/* Stato vuoto */}
        {!loading && !error && summaries.length === 0 && (
          <div className="flex flex-1 items-center justify-center p-6">
            <div className="flex max-w-md flex-col items-center gap-3 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-sco-blue/10 text-sco-blue">
                <FolderTree size={28} />
              </div>
              <h3 className="text-base font-semibold text-sco-text dark:text-sco-text-dark">
                Memory Tree vuoto
              </h3>
              <p className="text-sm text-sco-muted-foreground">
                Nessuna summary ancora indicizzata. Avvia un Subconscious tick
                oppure ingerisci documenti via{" "}
                <code className="rounded bg-sco-muted px-1 py-0.5 text-xs">
                  /api/memory/ingest
                </code>
                .
              </p>
              <Link
                to="/integrations"
                className="mt-2 rounded-md bg-sco-blue px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-sco-navy"
              >
                Vai a Connettori
              </Link>
            </div>
          </div>
        )}

        {/* Layout 2-pane attivo (summaries presenti) */}
        {summaries.length > 0 && (
          <>
            {/* === Left pane: tree (40%) === */}
            <aside
              className={cn(
                "flex w-full flex-col overflow-y-auto border-sco-border bg-sco-surface md:w-2/5 md:border-r",
                mobileDetailOpen && "hidden md:flex",
              )}
              role="tree"
              aria-label="Memory Tree gerarchico"
            >
              <div className="px-4 py-3">
                {tree.length === 0 ? (
                  <p className="text-xs italic text-sco-muted-foreground">
                    Nessun nodo dopo il filtro applicato.
                  </p>
                ) : (
                  tree.map((group) => (
                    <div key={group.source} className="mb-3">
                      <div className="mb-1 flex items-center gap-1.5 px-1 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
                        <Hash size={10} />
                        <span className="truncate">{group.source}</span>
                        <span className="ml-auto rounded bg-sco-muted px-1.5 py-0.5 text-[10px] font-normal text-sco-muted-foreground">
                          {group.topNodes.length}
                        </span>
                      </div>
                      <ul className="space-y-0.5">
                        {group.topNodes.map((node) => (
                          <TreeNodeRow
                            key={node.id}
                            node={node}
                            depth={0}
                            expandedIds={expandedIds}
                            selectedId={selectedId}
                            summariesById={summariesById}
                            onToggle={toggleExpanded}
                            onSelect={onSelectNode}
                          />
                        ))}
                      </ul>
                    </div>
                  ))
                )}
              </div>
            </aside>

            {/* === Right pane: detail (60%) === */}
            <section
              className={cn(
                "flex w-full flex-col overflow-y-auto bg-sco-bg md:w-3/5",
                !mobileDetailOpen && "hidden md:flex",
              )}
              aria-label="Dettaglio nodo selezionato"
            >
              {/* Back button mobile */}
              {mobileDetailOpen && (
                <button
                  type="button"
                  onClick={() => setMobileDetailOpen(false)}
                  className="m-3 self-start rounded-md border border-sco-border bg-sco-surface px-2 py-1 text-xs text-sco-muted-foreground hover:bg-sco-muted md:hidden"
                  aria-label="Torna al tree"
                >
                  &larr; Tree
                </button>
              )}

              {selected ? (
                <DetailPane
                  node={selected}
                  childrenNodes={selected.children_ids
                    .map((id) => summariesById.get(id))
                    .filter((x): x is TreeSummaryItem => x !== undefined)}
                  parentNode={
                    selected.parent_id
                      ? (summariesById.get(selected.parent_id) ?? null)
                      : null
                  }
                  onSelectId={onSelectNode}
                />
              ) : (
                <div className="flex flex-1 items-center justify-center p-6">
                  <p className="text-sm italic text-sco-muted-foreground">
                    Seleziona un nodo dal tree per vederne il dettaglio.
                  </p>
                </div>
              )}
            </section>
          </>
        )}
      </div>

      {/* === Footer stats === */}
      {summaries.length > 0 && (
        <div className="shrink-0 border-t border-sco-border bg-sco-surface px-6 py-2">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-sco-muted-foreground">
            <span className="flex items-center gap-1">
              <FolderTree size={11} className="text-sco-blue" />
              <strong className="font-medium text-sco-text dark:text-sco-text-dark">
                {stats.total}
              </strong>{" "}
              nodi
            </span>
            <span className="opacity-50">·</span>
            <span>
              L0:{" "}
              <strong className="font-medium text-sco-text dark:text-sco-text-dark">
                {stats.l0}
              </strong>
            </span>
            <span>
              L1:{" "}
              <strong className="font-medium text-sco-text dark:text-sco-text-dark">
                {stats.l1}
              </strong>
            </span>
            <span>
              L2:{" "}
              <strong className="font-medium text-sco-text dark:text-sco-text-dark">
                {stats.l2}
              </strong>
            </span>
            {stats.ratio > 0 && (
              <>
                <span className="opacity-50">·</span>
                <span className="text-sco-amber">
                  Compression{" "}
                  <strong className="font-medium">{stats.ratio}x</strong> (L0 →
                  L1)
                </span>
              </>
            )}

            {hotness.length > 0 && (
              <>
                <span className="opacity-50">·</span>
                <span className="flex items-center gap-1.5">
                  <TrendingUp size={11} className="text-sco-amber" />
                  Top hotness:
                </span>
                <div className="flex flex-wrap items-center gap-1">
                  {hotness.slice(0, 5).map((h) => (
                    <span
                      key={h.chunk_id}
                      className="rounded bg-sco-amber/10 px-1.5 py-0.5 font-mono text-[10px] text-sco-amber"
                      title={`Hotness ${h.hotness.toFixed(2)} · ${h.access_count} accessi`}
                    >
                      {h.chunk_id.slice(0, 8)} {h.hotness.toFixed(2)}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ===== Tree node row (recursive) =====

interface TreeNodeRowProps {
  node: TreeSummaryItem;
  depth: number;
  expandedIds: Set<string>;
  selectedId: string | null;
  summariesById: Map<string, TreeSummaryItem>;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
}

function TreeNodeRow({
  node,
  depth,
  expandedIds,
  selectedId,
  summariesById,
  onToggle,
  onSelect,
}: TreeNodeRowProps) {
  // children resolved dalla mappa (alcuni potrebbero essere stati esclusi dal filtro)
  const resolvedChildren = useMemo(
    () =>
      node.children_ids
        .map((id) => summariesById.get(id))
        .filter((x): x is TreeSummaryItem => x !== undefined),
    [node.children_ids, summariesById],
  );

  const hasChildren = resolvedChildren.length > 0;
  const isExpanded = expandedIds.has(node.id);
  const isSelected = selectedId === node.id;

  // Icona per livello: L0 = doc, L1/L2 = folder
  const Icon = node.level === 0 ? FileText : FolderTree;

  // Preview shortcut
  const preview = node.content_preview.trim().slice(0, 80);

  return (
    <li>
      <div
        role="treeitem"
        aria-expanded={hasChildren ? isExpanded : undefined}
        aria-selected={isSelected}
        className={cn(
          "group flex items-start gap-1 rounded-md py-1 pr-2 transition-colors",
          isSelected ? "bg-sco-blue/15" : "hover:bg-sco-muted",
        )}
        style={{ paddingLeft: 8 + depth * 14 }}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={() => onToggle(node.id)}
            className="mt-0.5 shrink-0 rounded p-0.5 text-sco-muted-foreground transition-colors hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
            aria-label={isExpanded ? "Comprimi" : "Espandi"}
          >
            {isExpanded ? (
              <ChevronDown size={12} />
            ) : (
              <ChevronRight size={12} />
            )}
          </button>
        ) : (
          <span className="mt-0.5 w-[18px] shrink-0" aria-hidden="true" />
        )}

        <button
          type="button"
          onClick={() => onSelect(node.id)}
          className="flex flex-1 min-w-0 items-start gap-1.5 text-left"
        >
          <Icon
            size={12}
            className={cn(
              "mt-0.5 shrink-0",
              node.level === 0
                ? "text-sco-blue"
                : node.level === 1
                  ? "text-sco-amber"
                  : "text-sco-navy dark:text-sco-text-dark",
            )}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "truncate text-xs",
                  isSelected
                    ? "font-medium text-sco-blue dark:text-sco-text-dark"
                    : "text-sco-text dark:text-sco-text-dark",
                )}
              >
                {node.topic ?? preview ?? `Nodo ${node.id.slice(0, 8)}`}
              </span>
              <span className="shrink-0 rounded bg-sco-muted px-1 py-0 font-mono text-[9px] text-sco-muted-foreground">
                L{node.level}
              </span>
            </div>
            {!node.topic && preview && (
              <p className="mt-0.5 truncate text-[10px] text-sco-muted-foreground">
                {preview}
              </p>
            )}
          </div>
        </button>
      </div>

      {hasChildren && isExpanded && (
        <ul className="mt-0.5 space-y-0.5">
          {resolvedChildren.map((child) => (
            <TreeNodeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              expandedIds={expandedIds}
              selectedId={selectedId}
              summariesById={summariesById}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

// ===== Detail pane =====

interface DetailPaneProps {
  node: TreeSummaryItem;
  childrenNodes: TreeSummaryItem[];
  parentNode: TreeSummaryItem | null;
  onSelectId: (id: string) => void;
}

function DetailPane({
  node,
  childrenNodes,
  parentNode,
  onSelectId,
}: DetailPaneProps) {
  const createdAtPretty = useMemo(() => {
    try {
      const d = new Date(node.created_at);
      if (Number.isNaN(d.getTime())) return node.created_at;
      return d.toLocaleString("it-IT", {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return node.created_at;
    }
  }, [node.created_at]);

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-5">
      {/* Header */}
      <div className="mb-4 flex items-start gap-3">
        <div
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            node.level === 0
              ? "bg-sco-blue/10 text-sco-blue"
              : node.level === 1
                ? "bg-sco-amber/10 text-sco-amber"
                : "bg-sco-navy/10 text-sco-navy dark:text-sco-text-dark",
          )}
        >
          {node.level === 0 ? <FileText size={18} /> : <FolderTree size={18} />}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-lg font-semibold text-sco-text dark:text-sco-text-dark">
            {node.topic ?? `Nodo ${node.id.slice(0, 8)}`}
          </h3>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-sco-muted-foreground">
            <span className="rounded bg-sco-muted px-1.5 py-0.5 font-mono">
              L{node.level}
            </span>
            <span>
              source:{" "}
              <strong className="font-medium text-sco-text dark:text-sco-text-dark">
                {node.source}
              </strong>
            </span>
            {node.day && (
              <span>
                day:{" "}
                <strong className="font-medium text-sco-text dark:text-sco-text-dark">
                  {node.day}
                </strong>
              </span>
            )}
            <span>
              {node.token_count.toLocaleString("it-IT")} token
            </span>
            <span>{createdAtPretty}</span>
          </div>
        </div>
      </div>

      {/* Markdown content */}
      <div className="prose prose-sm max-w-none rounded-lg border border-sco-border bg-sco-surface-elevated p-4 leading-relaxed dark:prose-invert prose-p:my-2 prose-headings:mt-3 prose-headings:mb-2 prose-pre:my-2 prose-pre:bg-sco-bg prose-pre:border prose-pre:border-sco-border prose-code:text-sco-blue dark:prose-code:text-sco-amber">
        {node.content_preview ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {node.content_preview}
          </ReactMarkdown>
        ) : (
          <p className="italic text-sco-muted-foreground">
            Nessun preview disponibile.
          </p>
        )}
      </div>

      {/* Children */}
      {childrenNodes.length > 0 && (
        <div className="mt-5">
          <h4 className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
            <FolderTree size={11} />
            Figli ({childrenNodes.length})
          </h4>
          <ul className="space-y-1">
            {childrenNodes.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => onSelectId(c.id)}
                  className="flex w-full items-start gap-2 rounded-md border border-sco-border bg-sco-surface-elevated px-3 py-2 text-left transition-colors hover:border-sco-blue hover:bg-sco-muted"
                >
                  {c.level === 0 ? (
                    <FileText
                      size={12}
                      className="mt-0.5 shrink-0 text-sco-blue"
                    />
                  ) : (
                    <FolderTree
                      size={12}
                      className="mt-0.5 shrink-0 text-sco-amber"
                    />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate text-xs font-medium text-sco-text dark:text-sco-text-dark">
                        {c.topic ?? `Nodo ${c.id.slice(0, 8)}`}
                      </span>
                      <span className="shrink-0 rounded bg-sco-muted px-1 py-0 font-mono text-[9px] text-sco-muted-foreground">
                        L{c.level}
                      </span>
                    </div>
                    {c.content_preview && (
                      <p className="mt-0.5 truncate text-[10px] text-sco-muted-foreground">
                        {c.content_preview.trim().slice(0, 100)}
                      </p>
                    )}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Chunk ids (per L1/L2: chunks aggregati) */}
      {node.level > 0 && node.children_ids.length > 0 && (
        <div className="mt-4 rounded-md border border-sco-border bg-sco-surface p-3">
          <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-sco-muted-foreground">
            <Hash size={10} />
            Chunk IDs aggregati
          </div>
          <p className="mt-1 text-xs text-sco-muted-foreground">
            Questo nodo aggrega{" "}
            <strong className="font-medium text-sco-text dark:text-sco-text-dark">
              {node.children_ids.length}
            </strong>{" "}
            chunk del livello inferiore.
          </p>
        </div>
      )}

      {/* Parent breadcrumb */}
      {parentNode && (
        <div className="mt-4">
          <button
            type="button"
            onClick={() => onSelectId(parentNode.id)}
            className="flex items-center gap-1.5 text-xs text-sco-muted-foreground hover:text-sco-blue"
          >
            <ChevronRight
              size={11}
              className="rotate-180"
              aria-hidden="true"
            />
            <span>
              Parent: {parentNode.topic ?? `Nodo ${parentNode.id.slice(0, 8)}`}
              <span className="ml-1 opacity-60">(L{parentNode.level})</span>
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
