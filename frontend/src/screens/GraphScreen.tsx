// SCO Compliance OS — schermata Grafo: visualizzazione force-directed 2D del vault
// Pattern Conv. 47 + Conv. 48 enforcement: single source of truth backend, niente stub hardcoded.
// Pattern Karpathy: visualizza gap conoscitivo (orphan placeholder con status="missing").
//
// Linguaggio semplice (regola 14/05/2026 vault): comprensibile a bambino sveglio.
//
// Dipendenze: react-force-graph-2d (force-directed canvas 2D) + d3 (force engine).
//
// Layout: header con filtri + canvas full-page + side panel destra collapsible dettaglio nodo.
// Colori per entity_type (palette SCO):
//   atto-normativo   -> #0074b4 (blu SCO)
//   standard-tecnico -> #10b981 (verde)
//   linea-guida      -> #ffa727 (ambra SCO)
//   autorita         -> #ef4444 (rosso)
//   metodologia      -> #8b5cf6 (viola)
//   autore-prassi    -> #6b7280 (grigio)
//   soggetto-obbligato -> #14b8a6 (turchese)
//   scadenza         -> #1f2937 (nero)
//   cliente          -> #f59e0b (arancio)
//   placeholder/missing -> #d1d5db (grigio chiaro)

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import {
  Network,
  RefreshCw,
  Database,
  AlertCircle,
  X,
  Filter,
} from "lucide-react";

import { apiClient } from "@/api/client";
import { cn } from "@/lib/cn";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import type {
  WikiGraphNode,
  WikiGraphEdge,
  WikiGraphResponse,
} from "@/types/api";

// ----- Mappa colori per categoria + entity_type (palette SCO) -----

const COLOR_BY_ENTITY_TYPE: Record<string, string> = {
  "atto-normativo": "#0074b4", // blu SCO
  "standard-tecnico": "#10b981", // verde
  "linea-guida": "#ffa727", // ambra SCO
  autorita: "#ef4444", // rosso
  metodologia: "#8b5cf6", // viola
  "autore-prassi": "#6b7280", // grigio
  "soggetto-obbligato": "#14b8a6", // turchese
  scadenza: "#1f2937", // nero
};

const COLOR_CLIENTE = "#f59e0b"; // arancio
const COLOR_PLACEHOLDER = "#d1d5db"; // grigio chiaro per missing/orphan
const COLOR_DEFAULT = "#94a3b8"; // slate

function nodeColor(node: WikiGraphNode): string {
  if (node.status === "missing") return COLOR_PLACEHOLDER;
  if (node.category === "cliente") return COLOR_CLIENTE;
  if (node.category === "scadenza") return COLOR_BY_ENTITY_TYPE.scadenza;
  if (node.entity_type && COLOR_BY_ENTITY_TYPE[node.entity_type]) {
    return COLOR_BY_ENTITY_TYPE[node.entity_type];
  }
  return COLOR_DEFAULT;
}

// ----- Conversione shape backend -> shape react-force-graph -----

interface ForceGraphNode extends WikiGraphNode {
  // Force-graph aggiunge runtime x, y, vx, vy, fx, fy
  // Tipi opzionali per non rompere il backend shape.
  x?: number;
  y?: number;
}

interface ForceGraphLink extends WikiGraphEdge {
  // source/target sono accessor: ForceGraph2D li trasforma in NodeObject runtime.
}

function toForceGraphData(resp: WikiGraphResponse): {
  nodes: ForceGraphNode[];
  links: ForceGraphLink[];
} {
  return {
    nodes: resp.nodes.map((n) => ({ ...n })),
    links: resp.edges.map((e) => ({ ...e })),
  };
}

// ----- Catalogo filtri (vocabolari chiusi CLAUDE.md INGEST) -----

const ENTITY_TYPE_FILTERS = [
  { value: "", label: "Tutti i tipi" },
  { value: "atto-normativo", label: "Atto normativo" },
  { value: "standard-tecnico", label: "Standard tecnico" },
  { value: "linea-guida", label: "Linea guida" },
  { value: "autorita", label: "Autorità" },
  { value: "metodologia", label: "Metodologia" },
  { value: "autore-prassi", label: "Autore di prassi" },
  { value: "soggetto-obbligato", label: "Soggetto obbligato" },
  { value: "scadenza", label: "Scadenza" },
] as const;

const AMBITO_CANONICO_FILTERS = [
  { value: "", label: "Tutti gli ambiti" },
  { value: "cybersicurezza", label: "Cybersicurezza" },
  { value: "governance-ai", label: "Governance IA" },
  { value: "privacy-protezione-dati", label: "Privacy / protezione dati" },
  { value: "accreditamento-sanitario", label: "Accreditamento sanitario" },
  { value: "dispositivi-medici", label: "Dispositivi medici" },
  { value: "radioprotezione", label: "Radioprotezione" },
  { value: "sicurezza-lavoro", label: "Sicurezza lavoro" },
  { value: "farmacovigilanza", label: "Farmacovigilanza" },
  { value: "service-management-ict", label: "Service management ICT" },
  { value: "appalti-pubblici", label: "Appalti pubblici" },
  { value: "prevenzione-incendi", label: "Prevenzione incendi" },
  { value: "compliance-231", label: "Compliance 231" },
  { value: "qualita-sgq", label: "Qualità SGQ" },
  { value: "gestione-ambientale", label: "Gestione ambientale" },
  { value: "sicurezza-alimentare", label: "Sicurezza alimentare" },
  { value: "responsabilita-sociale", label: "Responsabilità sociale" },
  { value: "multi-dominio", label: "Multi-dominio" },
] as const;

// ----- Componente principale -----

type LoadState = "idle" | "loading" | "ok" | "error";

export function GraphScreen() {
  const [resp, setResp] = useState<WikiGraphResponse | null>(null);
  const [state, setState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<WikiGraphNode | null>(null);

  // Filtri
  const [entityType, setEntityType] = useState<string>("");
  const [ambito, setAmbito] = useState<string>("");
  const [includeClienti, setIncludeClienti] = useState(true);
  const [includeOrphans, setIncludeOrphans] = useState(true);

  // Container size (force-graph richiede width/height numerici espliciti).
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });

  const load = useCallback(async () => {
    setState("loading");
    setError(null);
    try {
      const data = await apiClient.getWikiGraph({
        entity_type: entityType || undefined,
        ambito_canonico: ambito || undefined,
        include_clienti: includeClienti,
        include_orphans: includeOrphans,
      });
      setResp(data);
      setState("ok");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Errore sconosciuto";
      setError(msg);
      setState("error");
    }
  }, [entityType, ambito, includeClienti, includeOrphans]);

  useEffect(() => {
    void load();
  }, [load]);

  // Auto-resize del canvas force-graph al ResizeObserver del container.
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setSize({
          width: Math.max(400, Math.floor(width)),
          height: Math.max(400, Math.floor(height)),
        });
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const graphData = useMemo(() => {
    if (!resp) return { nodes: [], links: [] };
    return toForceGraphData(resp);
  }, [resp]);

  const isEmpty = useMemo(
    () => state === "ok" && (!resp || resp.nodes.length === 0),
    [state, resp],
  );

  // Render badge stats sotto header.
  const renderStats = () => {
    if (!resp) return null;
    return (
      <div className="flex flex-wrap items-center gap-3 text-xs text-sco-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full bg-sco-blue" />
          {resp.stats.nodes_total} nodi
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full bg-sco-amber" />
          {resp.stats.edges_total} collegamenti
        </span>
        {resp.stats.by_entity_type &&
          Object.entries(resp.stats.by_entity_type).map(([k, v]) => (
            <span key={k} className="rounded-md bg-sco-muted px-2 py-0.5">
              {k}: {v}
            </span>
          ))}
      </div>
    );
  };

  return (
    <div className="flex h-full flex-col">
      {/* === Header con filtri === */}
      <header className="border-b border-sco-border bg-sco-surface px-6 py-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-sco-navy/10 text-sco-navy">
              <Network size={20} />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-sco-navy dark:text-sco-text-dark">
                Grafo del vault
              </h1>
              <p className="text-xs text-sco-muted-foreground">
                Visualizza norme, standard, autorità e clienti come una rete
                navigabile. Trascina i nodi, fai zoom, clicca per il dettaglio.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void load()}
            disabled={state === "loading"}
            className={cn(
              "flex items-center gap-2 rounded-md border border-sco-border bg-sco-bg px-3 py-1.5 text-sm transition-colors",
              state === "loading"
                ? "cursor-not-allowed opacity-60"
                : "hover:border-sco-blue/60 hover:text-sco-blue",
            )}
            title="Ricarica il grafo dal vault corrente"
          >
            <RefreshCw
              size={14}
              className={cn(state === "loading" && "animate-spin")}
            />
            <span>Aggiorna</span>
          </button>
        </div>

        {/* Filtri */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-sco-muted-foreground">
            <Filter size={12} />
            <span>Filtri:</span>
          </div>

          <select
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
            className="rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-sco-text dark:text-sco-text-dark"
            aria-label="Filtra per tipo di entità"
          >
            {ENTITY_TYPE_FILTERS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <select
            value={ambito}
            onChange={(e) => setAmbito(e.target.value)}
            className="rounded-md border border-sco-border bg-sco-bg px-2 py-1 text-sco-text dark:text-sco-text-dark"
            aria-label="Filtra per ambito"
          >
            {AMBITO_CANONICO_FILTERS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <label className="flex cursor-pointer items-center gap-1.5">
            <input
              type="checkbox"
              checked={includeClienti}
              onChange={(e) => setIncludeClienti(e.target.checked)}
              className="rounded border-sco-border"
            />
            <span>Mostra clienti</span>
          </label>

          <label className="flex cursor-pointer items-center gap-1.5">
            <input
              type="checkbox"
              checked={includeOrphans}
              onChange={(e) => setIncludeOrphans(e.target.checked)}
              className="rounded border-sco-border"
            />
            <span>Mostra collegamenti senza nodo (grigi)</span>
          </label>
        </div>

        {/* Stats badge row */}
        <div className="mt-2">{renderStats()}</div>
      </header>

      {/* === Body: canvas + side panel === */}
      <div className="flex flex-1 overflow-hidden">
        {/* Canvas area */}
        <div
          ref={containerRef}
          className="relative flex-1 overflow-hidden bg-sco-bg"
        >
          {state === "loading" && !resp && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-2 text-sco-muted-foreground">
                <RefreshCw size={32} className="animate-spin text-sco-blue" />
                <span className="text-sm">Carico il grafo del vault...</span>
              </div>
            </div>
          )}

          {state === "error" && (
            <div className="p-6">
              <ErrorState
                icon={AlertCircle}
                title="Non riesco a caricare il grafo"
                message={error || "Errore sconosciuto"}
                onRetry={() => void load()}
              />
            </div>
          )}

          {isEmpty && (
            <div className="p-6">
              <EmptyState
                icon={Database}
                title="Nessun nodo nel vault"
                description={
                  <>
                    Questo vault non ha entity wiki o clienti collegati a una
                    norma. Aggiungi entity in{" "}
                    <code className="rounded bg-sco-muted px-1 py-0.5 text-xs">
                      wiki/entities/
                    </code>{" "}
                    e il grafo si popolerà automaticamente.
                  </>
                }
                ctaLabel="Apri Wiki"
                ctaHref="/wiki"
                tone="info"
              />
            </div>
          )}

          {state === "ok" && resp && resp.nodes.length > 0 && (
            <ForceGraph2D
              graphData={graphData}
              width={size.width}
              height={size.height}
              backgroundColor="transparent"
              nodeId="id"
              nodeLabel={(n: any) =>
                `${n.label}${n.status === "missing" ? " (manca scheda)" : ""}`
              }
              nodeColor={(n: any) => nodeColor(n as WikiGraphNode)}
              nodeRelSize={6}
              nodeVal={(n: any) =>
                (n as WikiGraphNode).category === "cliente" ? 3 : 2
              }
              linkColor={() => "#94a3b8"}
              linkWidth={1}
              linkLabel={(l: any) =>
                `${l.type}${l.note ? ` — ${l.note.slice(0, 80)}` : ""}`
              }
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={0.95}
              linkDirectionalArrowColor={() => "#64748b"}
              onNodeClick={(n: any) => {
                setSelectedNode(n as WikiGraphNode);
              }}
              cooldownTicks={100}
              warmupTicks={50}
            />
          )}
        </div>

        {/* Side panel dettaglio nodo */}
        {selectedNode && (
          <aside className="w-[320px] shrink-0 overflow-y-auto border-l border-sco-border bg-sco-surface p-4">
            <div className="mb-3 flex items-start justify-between gap-2">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-sco-muted-foreground">
                  {selectedNode.category === "cliente"
                    ? "Cliente"
                    : selectedNode.category === "scadenza"
                      ? "Scadenza"
                      : "Entità wiki"}
                </div>
                <h2 className="mt-0.5 text-sm font-semibold leading-tight text-sco-text dark:text-sco-text-dark">
                  {selectedNode.label}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setSelectedNode(null)}
                className="rounded-md p-1 text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark"
                aria-label="Chiudi pannello"
              >
                <X size={14} />
              </button>
            </div>

            <dl className="space-y-2 text-xs">
              <div>
                <dt className="text-sco-muted-foreground">ID</dt>
                <dd className="font-mono text-[11px]">{selectedNode.id}</dd>
              </div>
              {selectedNode.status === "missing" ? (
                <div className="rounded-md bg-amber-50 p-2 text-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
                  Questo nodo è citato da altre pagine ma non ha una scheda
                  propria nel vault. Sarebbe utile crearla per riempire il
                  gap.
                </div>
              ) : (
                <>
                  {selectedNode.entity_type && (
                    <div>
                      <dt className="text-sco-muted-foreground">Tipo</dt>
                      <dd>{selectedNode.entity_type}</dd>
                    </div>
                  )}
                  {selectedNode.entity_subtype && (
                    <div>
                      <dt className="text-sco-muted-foreground">Sottotipo</dt>
                      <dd>{selectedNode.entity_subtype}</dd>
                    </div>
                  )}
                  {selectedNode.ambito_canonico && (
                    <div>
                      <dt className="text-sco-muted-foreground">Ambito</dt>
                      <dd>{selectedNode.ambito_canonico}</dd>
                    </div>
                  )}
                  <div>
                    <dt className="text-sco-muted-foreground">Stato</dt>
                    <dd>{selectedNode.status}</dd>
                  </div>
                  {selectedNode.path && (
                    <div>
                      <dt className="text-sco-muted-foreground">File</dt>
                      <dd className="font-mono text-[11px] break-all">
                        {selectedNode.path}
                      </dd>
                    </div>
                  )}
                </>
              )}
            </dl>
          </aside>
        )}
      </div>
    </div>
  );
}
