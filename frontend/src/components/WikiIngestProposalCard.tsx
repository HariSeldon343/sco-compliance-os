// SCO Compliance OS — widget "Vuoi salvare questo documento nel wiki?"
//
// Si rendererizza sotto la bubble assistant quando il backend emette via SSE
// l'evento `wiki_ingest_proposal` (vedi backend/sco_compliance_os/services/chat/
// wiki_proposal.py). Il widget aiuta l'utente a confermare l'ingest nella
// destinazione corretta (sources / entities / concepts / synthesis / glossari /
// memory_tree) editando slug, frontmatter e body prima del salvataggio.
//
// Pattern Conv. 47 single source of truth: il dato finale che viene salvato e'
// quello che l'utente conferma, non la suggested_destination/slug iniziale.
// L'utente puo' modificare TUTTO. Il backend accetta i valori finali via
// POST /api/wiki/ingest/confirm.
//
// Pattern Conv. 48 stato widget persistito: la proposta arriva dal backend con
// proposal_id deterministico (sha256 di conversation_id + message_id), cosi
// idempotente a refresh. L'utente dismiss locale (per session) vive nello
// store come wikiIngestDismissed[message_id].

import { useMemo, useState } from "react";
import {
  BookOpen,
  Boxes,
  Lightbulb,
  Network,
  BookA,
  TreePine,
  X,
  Save,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

import { cn } from "@/lib/cn";
import { apiClient } from "@/api/client";
import { useChatStore } from "@/store/chat-store";
import type {
  WikiIngestDestination,
  WikiIngestProposal,
  WikiIngestSlot,
} from "@/types/api";

// Mapping destinazione -> icon + label leggibile + colore accent.
// Allineato al vocabolario chiuso del backend (WIKI_CATEGORIES + memory_tree).
const DESTINATION_META: Record<
  WikiIngestDestination,
  { icon: typeof BookOpen; label: string; description: string; accent: string }
> = {
  sources: {
    icon: BookOpen,
    label: "Sources",
    description: "Schede di sintesi per fonti raw (PDF normative, audit, web-clip)",
    accent: "text-sco-blue",
  },
  entities: {
    icon: Boxes,
    label: "Entities",
    description: "Atti normativi, standard tecnici, autorità, linee guida",
    accent: "text-sco-amber",
  },
  concepts: {
    icon: Lightbulb,
    label: "Concepts",
    description: "Concetti trasversali cross-cliente e cross-standard",
    accent: "text-yellow-500",
  },
  synthesis: {
    icon: Network,
    label: "Synthesis",
    description: "Mapping cross-framework e confronti normativi",
    accent: "text-purple-500",
  },
  glossari: {
    icon: BookA,
    label: "Glossari",
    description: "Sigle aziendali e di settore con espansione canonica",
    accent: "text-pink-500",
  },
  memory_tree: {
    icon: TreePine,
    label: "Memory Tree",
    description: "Chunk generico nell'inbox (fallback)",
    accent: "text-green-600",
  },
};

const DESTINATION_OPTIONS: WikiIngestDestination[] = [
  "sources",
  "entities",
  "concepts",
  "synthesis",
  "glossari",
  "memory_tree",
];

interface WikiIngestProposalCardProps {
  proposal: WikiIngestProposal;
  messageId: string;
}

export function WikiIngestProposalCard({
  proposal,
  messageId,
}: WikiIngestProposalCardProps) {
  const dismissProposal = useChatStore((s) => s.dismissWikiIngestProposal);
  const removeProposal = useChatStore((s) => s.removeWikiIngestProposal);

  // Indice slot attivo (default: il primo con confidence piu' alta).
  const initialIndex = useMemo(() => {
    if (proposal.slots.length === 0) return 0;
    let best = 0;
    let bestConf = proposal.slots[0]?.confidence ?? 0;
    proposal.slots.forEach((s, i) => {
      if (s.confidence > bestConf) {
        bestConf = s.confidence;
        best = i;
      }
    });
    return best;
  }, [proposal.slots]);

  const [activeSlotIdx, setActiveSlotIdx] = useState(initialIndex);
  const slot: WikiIngestSlot | undefined = proposal.slots[activeSlotIdx];

  // Editor state (campi modificabili dall'utente).
  const [destination, setDestination] = useState<WikiIngestDestination>(
    (slot?.suggested_destination as WikiIngestDestination) ?? "sources",
  );
  const [slug, setSlug] = useState(slot?.suggested_slug ?? "");
  const [frontmatterText, setFrontmatterText] = useState(
    JSON.stringify(slot?.suggested_frontmatter ?? {}, null, 2),
  );
  const [bodyMd, setBodyMd] = useState(slot?.summary ?? "");
  const [isExpanded, setIsExpanded] = useState(false);

  // Submit state.
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<
    | { kind: "ok"; filePath: string; overwrite: boolean }
    | { kind: "error"; message: string }
    | null
  >(null);

  // Sincronizza editor state quando l'utente cambia slot attivo.
  const handleSlotChange = (idx: number) => {
    const next = proposal.slots[idx];
    if (!next) return;
    setActiveSlotIdx(idx);
    setDestination(next.suggested_destination as WikiIngestDestination);
    setSlug(next.suggested_slug);
    setFrontmatterText(JSON.stringify(next.suggested_frontmatter, null, 2));
    setBodyMd(next.summary);
    setSubmitResult(null);
  };

  const handleConfirm = async () => {
    if (!slot) return;
    setIsSubmitting(true);
    setSubmitResult(null);
    try {
      let parsedFm: Record<string, unknown>;
      try {
        parsedFm = JSON.parse(frontmatterText);
      } catch (jsonErr) {
        throw new Error(
          `Frontmatter JSON non valido: ${jsonErr instanceof Error ? jsonErr.message : String(jsonErr)}`,
        );
      }
      const response = await apiClient.confirmWikiIngest({
        proposal_id: proposal.proposal_id,
        slot_index: activeSlotIdx,
        destination,
        slug,
        frontmatter: parsedFm,
        body_md: bodyMd,
        source_identifier: slot.identifier,
        source_type: slot.source_type,
      });
      setSubmitResult({
        kind: "ok",
        filePath: response.file_path,
        overwrite: response.overwrite,
      });
      // Dopo 1.5s rimuovi la card per non ingombrare la conversation.
      setTimeout(() => {
        removeProposal(messageId);
      }, 1500);
    } catch (err) {
      setSubmitResult({
        kind: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!slot) {
    return null;
  }

  const destMeta = DESTINATION_META[destination];
  const DestIcon = destMeta.icon;

  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-sco-amber/30 bg-sco-amber/5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sco-amber/20 bg-sco-amber/10 px-3 py-2">
        <div className="flex items-center gap-2">
          <Save size={14} className="text-sco-amber" />
          <span className="text-xs font-semibold uppercase tracking-wider text-sco-amber">
            Vuoi salvare nel wiki?
          </span>
        </div>
        <button
          type="button"
          onClick={() => dismissProposal(messageId)}
          className="rounded p-0.5 text-sco-muted-foreground transition-colors hover:bg-sco-amber/10 hover:text-sco-text dark:hover:text-sco-text-dark"
          title="Scarta proposta"
          aria-label="Scarta proposta"
        >
          <X size={14} />
        </button>
      </div>

      {/* Tab strip dei candidati (slot) se piu' di uno */}
      {proposal.slots.length > 1 && (
        <div className="flex gap-1 overflow-x-auto border-b border-sco-amber/20 bg-sco-amber/5 px-2 py-1.5">
          {proposal.slots.map((s, idx) => (
            <button
              key={`${s.identifier}-${idx}`}
              type="button"
              onClick={() => handleSlotChange(idx)}
              className={cn(
                "shrink-0 rounded-md px-2 py-1 text-[11px] font-medium transition-colors",
                idx === activeSlotIdx
                  ? "bg-sco-amber text-white"
                  : "bg-sco-bg text-sco-muted-foreground hover:bg-sco-amber/20",
              )}
              title={`${s.source_type} — confidence ${(s.confidence * 100).toFixed(0)}%`}
            >
              {s.title.length > 28
                ? `${s.title.slice(0, 26)}...`
                : s.title || s.identifier}
            </button>
          ))}
        </div>
      )}

      {/* Body */}
      <div className="space-y-3 p-3">
        {/* Riga summary + confidence */}
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <div className="text-sm font-medium text-sco-text dark:text-sco-text-dark">
              {slot.title}
            </div>
            <div className="mt-0.5 text-[11px] text-sco-muted-foreground">
              {slot.rationale}
            </div>
            {slot.summary && (
              <div className="mt-1 text-xs leading-relaxed text-sco-muted-foreground">
                {slot.summary}
              </div>
            )}
          </div>
          <span
            className={cn(
              "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
              slot.confidence >= 0.7
                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                : slot.confidence >= 0.5
                  ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
            )}
            title="Confidence del classificatore"
          >
            {(slot.confidence * 100).toFixed(0)}%
          </span>
        </div>

        {/* Dropdown destinazione */}
        <div>
          <label
            htmlFor={`dest-${messageId}`}
            className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-sco-muted-foreground"
          >
            Destinazione nel wiki
          </label>
          <div className="relative">
            <select
              id={`dest-${messageId}`}
              value={destination}
              onChange={(e) =>
                setDestination(e.target.value as WikiIngestDestination)
              }
              disabled={isSubmitting || submitResult?.kind === "ok"}
              className="w-full appearance-none rounded-md border border-sco-border bg-sco-bg px-3 py-2 pr-8 text-sm text-sco-text outline-none focus:border-sco-amber focus:ring-1 focus:ring-sco-amber dark:text-sco-text-dark"
            >
              {DESTINATION_OPTIONS.map((dst) => (
                <option key={dst} value={dst}>
                  {DESTINATION_META[dst].label} — {DESTINATION_META[dst].description}
                </option>
              ))}
            </select>
            <DestIcon
              size={14}
              className={cn(
                "pointer-events-none absolute right-2 top-1/2 -translate-y-1/2",
                destMeta.accent,
              )}
            />
          </div>
        </div>

        {/* Slug input */}
        <div>
          <label
            htmlFor={`slug-${messageId}`}
            className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-sco-muted-foreground"
          >
            Slug file (nome senza estensione)
          </label>
          <input
            id={`slug-${messageId}`}
            type="text"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            disabled={isSubmitting || submitResult?.kind === "ok"}
            className="w-full rounded-md border border-sco-border bg-sco-bg px-3 py-2 font-mono text-sm text-sco-text outline-none focus:border-sco-amber focus:ring-1 focus:ring-sco-amber dark:text-sco-text-dark"
            placeholder="es-d-lgs-138-2024"
            maxLength={120}
          />
          <div className="mt-0.5 text-[10px] text-sco-muted-foreground">
            Solo lettere, numeri, trattini e underscore. Verra' creato il file{" "}
            <code>
              {destination === "memory_tree"
                ? `raw/inbox/${slug || "<slug>"}.md`
                : `wiki/${destination}/${slug || "<slug>"}.md`}
            </code>
          </div>
        </div>

        {/* Expand/collapse advanced editor (frontmatter + body) */}
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-[11px] font-medium text-sco-blue underline-offset-2 hover:underline"
        >
          {isExpanded ? "Nascondi" : "Mostra"} editor avanzato (frontmatter + body)
        </button>

        {isExpanded && (
          <div className="space-y-2 rounded-md border border-sco-border bg-sco-bg/30 p-2">
            <div>
              <label
                htmlFor={`fm-${messageId}`}
                className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-sco-muted-foreground"
              >
                Frontmatter (JSON)
              </label>
              <textarea
                id={`fm-${messageId}`}
                value={frontmatterText}
                onChange={(e) => setFrontmatterText(e.target.value)}
                disabled={isSubmitting || submitResult?.kind === "ok"}
                rows={6}
                className="w-full resize-y rounded-md border border-sco-border bg-sco-bg px-2 py-1.5 font-mono text-[11px] text-sco-text outline-none focus:border-sco-amber focus:ring-1 focus:ring-sco-amber dark:text-sco-text-dark"
                spellCheck={false}
              />
            </div>
            <div>
              <label
                htmlFor={`body-${messageId}`}
                className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-sco-muted-foreground"
              >
                Body markdown
              </label>
              <textarea
                id={`body-${messageId}`}
                value={bodyMd}
                onChange={(e) => setBodyMd(e.target.value)}
                disabled={isSubmitting || submitResult?.kind === "ok"}
                rows={4}
                className="w-full resize-y rounded-md border border-sco-border bg-sco-bg px-2 py-1.5 text-xs text-sco-text outline-none focus:border-sco-amber focus:ring-1 focus:ring-sco-amber dark:text-sco-text-dark"
                placeholder="Scrivi qui il contenuto del file markdown..."
              />
            </div>
          </div>
        )}

        {/* Risultato salvataggio */}
        {submitResult?.kind === "ok" && (
          <div className="flex items-start gap-2 rounded-md border border-green-200 bg-green-50 p-2 text-xs text-green-800 dark:border-green-800 dark:bg-green-900/20 dark:text-green-200">
            <CheckCircle2 size={14} className="mt-0.5 shrink-0" />
            <div>
              {submitResult.overwrite ? "File sovrascritto" : "File creato"}:{" "}
              <code className="break-all font-mono text-[11px]">
                {submitResult.filePath}
              </code>
            </div>
          </div>
        )}
        {submitResult?.kind === "error" && (
          <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            <div className="break-words">{submitResult.message}</div>
          </div>
        )}

        {/* Bottoni azione */}
        <div className="flex items-center justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={() => dismissProposal(messageId)}
            disabled={isSubmitting}
            className="rounded-md border border-sco-border bg-sco-bg px-3 py-1.5 text-xs font-medium text-sco-muted-foreground transition-colors hover:bg-sco-amber/5 disabled:opacity-50"
          >
            Scarta
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={
              isSubmitting ||
              submitResult?.kind === "ok" ||
              slug.trim().length === 0
            }
            className="flex items-center gap-1.5 rounded-md bg-sco-amber px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-sco-amber/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={12} className="animate-spin" /> Salvataggio...
              </>
            ) : (
              <>
                <Save size={12} /> Salva nel wiki
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
