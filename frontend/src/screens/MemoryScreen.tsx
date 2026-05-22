// SCO Compliance OS — schermata Memoria: tree visualizer Memory Tree (placeholder visivo)
import { useState } from "react";
import { Brain, ChevronRight, ChevronDown, FileText } from "lucide-react";

import { cn } from "@/lib/cn";

interface MemoryNode {
  id: string;
  label: string;
  children?: MemoryNode[];
  // Foglia: leaf con contenuto
  excerpt?: string;
}

// Stub tree — verrà popolato da backend (memory_tree service)
const STUB_TREE: MemoryNode = {
  id: "root",
  label: "Memory Tree",
  children: [
    {
      id: "regole",
      label: "Regole permanenti",
      children: [
        {
          id: "r1",
          label: "Tipografia 03/05/2026",
          excerpt:
            "Virgolette dritte, al punto, font uniforme, humanizer attivo.",
        },
        {
          id: "r2",
          label: "Placeholder italiano 14/05/2026",
          excerpt: "Mai <<TESTO>>, usare ____________________ + (indicare ...).",
        },
        {
          id: "r3",
          label: "Goal persistence 20/05/2026",
          excerpt: "Keep working until the condition is met. Cross-machine.",
        },
      ],
    },
    {
      id: "operatori",
      label: "Operatori",
      children: [
        {
          id: "op1",
          label: "Antonio (titolare)",
          excerpt: "Profilo pieno, decisioni definitive.",
        },
        {
          id: "op2",
          label: "Pietro (collaboratore)",
          excerpt: "Perimetro ristretto, modalità tutor obbligatoria.",
        },
      ],
    },
    {
      id: "convenzioni",
      label: "Convenzioni cristallizzate",
      children: [
        {
          id: "c40",
          label: "Conv. 40 — 5 closing question delegate",
        },
        {
          id: "c46",
          label: "Conv. 46 — Smoke test E2E prima del tag",
        },
        {
          id: "c48",
          label: "Conv. 48 — Single source of truth backend per widget",
        },
      ],
    },
  ],
};

export function MemoryScreen() {
  return (
    <div className="h-full overflow-y-auto px-8 py-6">
      <div className="mx-auto max-w-4xl">
        <header className="mb-6 flex items-center gap-3">
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
        </header>

        <div className="rounded-lg border border-sco-border bg-sco-surface-elevated p-4">
          <TreeNode node={STUB_TREE} level={0} />
        </div>

        <p className="mt-4 text-xs text-sco-muted-foreground">
          Stub visualizer. Il Memory Tree reale arriverà dal backend
          /api/memory/tree.
        </p>
      </div>
    </div>
  );
}

interface TreeNodeProps {
  node: MemoryNode;
  level: number;
}
function TreeNode({ node, level }: TreeNodeProps) {
  const [open, setOpen] = useState(level < 2);
  const hasChildren = !!node.children && node.children.length > 0;

  return (
    <div style={{ paddingLeft: level === 0 ? 0 : 16 }}>
      <button
        type="button"
        onClick={() => hasChildren && setOpen(!open)}
        className={cn(
          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-sco-muted",
          !hasChildren && "cursor-default",
        )}
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
        <span className={cn(hasChildren && "font-medium")}>{node.label}</span>
      </button>
      {node.excerpt && open && (
        <p className="ml-6 mt-0.5 text-xs text-sco-muted-foreground">
          {node.excerpt}
        </p>
      )}
      {hasChildren && open && (
        <div className="mt-1">
          {node.children!.map((child) => (
            <TreeNode key={child.id} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
