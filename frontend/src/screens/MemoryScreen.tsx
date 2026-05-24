// SCO Compliance OS — schermata Memoria: Memory Tree reale da backend /api/memory/tree
// Pattern Conv. 47 + Conv. 48 enforcement: single source of truth backend, niente stub hardcoded.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Brain, ChevronRight, ChevronDown, FileText, RefreshCw } from "lucide-react";

import { ApiError } from "@/api/client";
import { cn } from "@/lib/cn";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";

interface MemoryNodeRemote {
  id: string;
  title: string;
  path: string;
  kind: string;
  snippet: string | null;
  children: string[];
}

interface MemoryTreeResponse {
  root_ids: string[];
  nodes: Record<string, MemoryNodeRemote>;
  total_count: number;
}

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

async function fetchMemoryTree(): Promise<MemoryTreeResponse> {
  const res = await fetch(`${BACKEND_URL}/api/memory/tree`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, "memory_tree_error", `HTTP ${res.status} ${body}`);
  }
  return (await res.json()) as MemoryTreeResponse;
}

type LoadState = "idle" | "loading" | "ok" | "error";

export function MemoryScreen() {
  const [tree, setTree] = useState<MemoryTreeResponse | null>(null);
  const [state, setState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState("loading");
    setError(null);
    try {
      const data = await fetchMemoryTree();
      setTree(data);
      setState("ok");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Errore sconosciuto";
      setError(msg);
      setState("error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const isEmpty = useMemo(
    () => state === "ok" && (!tree || tree.total_count === 0),
    [state, tree],
  );

  return (
    <div className="h-full overflow-y-auto px-8 py-6">
      <div className="mx-auto max-w-4xl">
        <header className="mb-6 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-sco-navy/10 text-sco-navy">
              <Brain size={20} />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-sco-navy dark:text-sco-text-dark">
                Memoria
              </h1>
              <p className="mt-1 text-sm text-sco-muted-foreground">
                Cosa l'agente ricorda di te. Persistenza markdown, no vector DB.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void load()}
            disabled={state === "loading"}
            className={cn(
              "flex items-center gap-1.5 rounded-md border border-sco-border px-3 py-1.5 text-xs font-medium transition-colors",
              state === "loading"
                ? "cursor-not-allowed text-sco-muted-foreground"
                : "text-sco-text hover:border-sco-blue hover:bg-sco-muted dark:text-sco-text-dark",
            )}
            title="Ricarica dal backend"
          >
            <RefreshCw
              size={13}
              className={cn(state === "loading" && "animate-spin")}
            />
            Ricarica
          </button>
        </header>

        {state === "loading" && (
          <div className="flex items-center justify-center rounded-lg border border-sco-border bg-sco-surface-elevated p-12 text-sm text-sco-muted-foreground">
            <RefreshCw size={14} className="mr-2 animate-spin" />
            Caricamento Memory Tree...
          </div>
        )}

        {state === "error" && (
          <ErrorState
            icon={Brain}
            title="Non riesco a leggere il Memory Tree"
            message={`Il backend non risponde o ha restituito un errore. Dettaglio tecnico: ${error ?? "errore sconosciuto"}`}
            onRetry={() => void load()}
          />
        )}

        {isEmpty && (
          <EmptyState
            icon={Brain}
            tone="neutral"
            title="Memory Tree ancora vuoto"
            description="Qui vedrai i nodi gerarchici che l'agente costruisce mentre lavorate insieme. Avvia una chat dalla sidebar oppure collega un connettore per popolare la memoria."
            ctaLabel="Apri una nuova chat"
            ctaHref="/"
            secondaryCtaLabel="Vai a Connettori"
            secondaryCtaHref="/integrations"
          />
        )}

        {state === "ok" && tree && tree.total_count > 0 && (
          <div className="rounded-lg border border-sco-border bg-sco-surface-elevated p-4">
            {tree.root_ids.map((rootId) => {
              const node = tree.nodes[rootId];
              if (!node) return null;
              return (
                <TreeNode key={rootId} node={node} nodes={tree.nodes} level={0} />
              );
            })}
          </div>
        )}

        {state === "ok" && tree && tree.total_count > 0 && (
          <p className="mt-4 text-xs text-sco-muted-foreground">
            {tree.total_count} {tree.total_count === 1 ? "nodo" : "nodi"} in memoria.
            Persistenza filesystem markdown + indice JSON (no vector DB).
          </p>
        )}
      </div>
    </div>
  );
}

interface TreeNodeProps {
  node: MemoryNodeRemote;
  nodes: Record<string, MemoryNodeRemote>;
  level: number;
}

function TreeNode({ node, nodes, level }: TreeNodeProps) {
  const [open, setOpen] = useState(level < 2);
  const hasChildren = node.children.length > 0;

  return (
    <div style={{ paddingLeft: level === 0 ? 0 : 16 }}>
      <button
        type="button"
        onClick={() => hasChildren && setOpen(!open)}
        className={cn(
          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-sco-muted",
          !hasChildren && "cursor-default",
        )}
        title={node.path}
      >
        {hasChildren ? (
          open ? (
            <ChevronDown size={14} className="text-sco-muted-foreground" />
          ) : (
            <ChevronRight size={14} className="text-sco-muted-foreground" />
          )
        ) : (
          <FileText size={14} className="text-sco-blue" />
        )}
        <span className={cn(hasChildren && "font-medium")}>{node.title}</span>
        <span className="ml-auto text-[10px] uppercase tracking-wide text-sco-muted-foreground">
          {node.kind}
        </span>
      </button>
      {node.snippet && open && (
        <p className="ml-6 mt-0.5 text-xs text-sco-muted-foreground">
          {node.snippet}
        </p>
      )}
      {hasChildren && open && (
        <div className="mt-1">
          {node.children.map((childId) => {
            const child = nodes[childId];
            if (!child) return null;
            return (
              <TreeNode
                key={childId}
                node={child}
                nodes={nodes}
                level={level + 1}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
