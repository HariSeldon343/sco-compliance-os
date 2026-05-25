// SCO Compliance OS — widget cliccabile per AskUserQuestion inline.
//
// v0.11.0: 3 modalita supportate dal payload backend:
//
//   1. SINGLE  (default)  — radio-style: 1 click = invio immediato
//   2. MULTI   (multi_select: true) — checkbox: N selezioni + bottone Invia
//   3. FREE-TEXT (allow_free_text: true OR opzione "altro/free_text/other") —
//      al click sull'opzione "Altro" appare input text inline + bottone Invia
//
// Stati del widget:
//   - "pending" → bottoni attivi, nessuna risposta inviata
//   - "answered" → tutti i bottoni disabled + badge "Risposto" sulla selezione
//     finale + opzioni non scelte rese in muted
//
// Pattern Conv. 48: lo stato widget vive lato store (idealmente lato backend
// in DB). Il componente e' "presentational" — riceve state + answer_value
// + callback onAnswer come props.

import { useState } from "react";
import { Check, Send } from "lucide-react";

import { cn } from "@/lib/cn";
import type {
  InlineAskOption,
  InlineAskPayload,
} from "@/lib/parseInlineWidgets";

interface AskQuestionCardProps {
  /** Payload domanda + opzioni dal parser inline. */
  payload: InlineAskPayload;
  /** Callback invocato al click su una opzione (value della selezione). */
  onAnswer: (value: string) => void;
  /** Stato corrente del widget. */
  state: "pending" | "answered";
  /** Value dell'opzione selezionata (presente solo se state="answered"). */
  answer_value?: string;
  /** Flag di lock UI durante il POST verso il backend. */
  isSubmitting?: boolean;
}

const FREE_TEXT_VALUES = new Set(["altro", "free_text", "other"]);

function isFreeTextOption(opt: InlineAskOption): boolean {
  return FREE_TEXT_VALUES.has(opt.value.toLowerCase());
}

/**
 * Card domanda cliccabile in linguaggio semplice (regola 14/05 + Conv. 48).
 *
 * v0.11.0 — 3 modalita: single, multi-select, free-text.
 */
export function AskQuestionCard({
  payload,
  onAnswer,
  state,
  answer_value,
  isSubmitting = false,
}: AskQuestionCardProps) {
  const isAnswered = state === "answered";
  const isMulti = payload.multi_select === true;
  const allowFreeText = payload.allow_free_text === true;

  // Local state per multi-select selezioni accumulate prima di invio.
  const [multiSelected, setMultiSelected] = useState<string[]>([]);
  // Local state per free-text quando opzione "Altro" viene cliccata.
  const [freeTextValue, setFreeTextValue] = useState("");
  const [showFreeTextInput, setShowFreeTextInput] = useState(false);

  const handleSingleClick = (opt: InlineAskOption) => {
    if (isFreeTextOption(opt)) {
      // Mostra text input inline invece di inviare subito.
      setShowFreeTextInput(true);
      return;
    }
    onAnswer(opt.value);
  };

  const handleMultiToggle = (value: string) => {
    setMultiSelected((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value],
    );
  };

  const handleMultiSubmit = () => {
    if (multiSelected.length === 0 && !freeTextValue.trim()) return;
    // Concatena selezioni multi + eventuale free text con separatore virgola.
    // Pattern frontend → backend: il backend riceve come una user message
    // singola, riconosce le opzioni dalla virgola+spazio + dal contesto
    // (history + skill body os-setup definisce le opzioni valide).
    const parts: string[] = [];
    for (const val of multiSelected) {
      if (isFreeTextOption({ value: val, label: val })) continue;
      const opt = payload.options.find((o) => o.value === val);
      parts.push(opt?.label ?? val);
    }
    if (freeTextValue.trim()) parts.push(freeTextValue.trim());
    const combined = parts.join(", ");
    onAnswer(combined);
  };

  const handleFreeTextSubmit = () => {
    const text = freeTextValue.trim();
    if (!text) return;
    onAnswer(text);
  };

  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-sco-blue/30 bg-sco-blue/5 animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sco-blue/20 bg-sco-blue/10 px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-sco-blue">
          {isMulti ? "Domanda (selezione multipla)" : "Domanda"}
        </span>
        {isAnswered && (
          <span className="flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-green-700 dark:bg-green-900/30 dark:text-green-300">
            <Check size={10} />
            Risposto
          </span>
        )}
      </div>

      {/* Body */}
      <div className="p-3">
        <div className="mb-3 text-sm font-medium text-sco-text dark:text-sco-text-dark">
          {payload.question}
        </div>

        <div className="flex flex-col gap-1.5">
          {payload.options.map((opt) => {
            const isMultiChecked = multiSelected.includes(opt.value);
            const isSingleSelected = isAnswered && answer_value === opt.value;
            return (
              <OptionButton
                key={opt.value}
                option={opt}
                isMulti={isMulti}
                isMultiChecked={isMultiChecked}
                isAnswered={isAnswered}
                isSelected={isSingleSelected}
                isSubmitting={isSubmitting}
                onClick={() => {
                  if (isAnswered) return;
                  if (isMulti) {
                    handleMultiToggle(opt.value);
                  } else {
                    handleSingleClick(opt);
                  }
                }}
              />
            );
          })}
        </div>

        {/* Free-text input inline (single-select mode, opzione "Altro" cliccata) */}
        {!isMulti && !isAnswered && showFreeTextInput && (
          <div className="mt-3 flex flex-col gap-2 rounded-md border border-sco-blue/40 bg-sco-bg p-2.5">
            <label className="text-[11px] font-medium text-sco-muted-foreground">
              Scrivi la tua risposta:
            </label>
            <textarea
              value={freeTextValue}
              onChange={(e) => setFreeTextValue(e.target.value)}
              placeholder="Scrivi qui..."
              rows={2}
              autoFocus
              className="resize-none rounded border border-sco-border bg-sco-surface-elevated px-2 py-1.5 text-sm text-sco-text placeholder:text-sco-muted-foreground/70 focus:border-sco-blue focus:outline-none focus:ring-1 focus:ring-sco-blue/30 dark:text-sco-text-dark"
              disabled={isSubmitting}
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowFreeTextInput(false);
                  setFreeTextValue("");
                }}
                className="rounded px-2.5 py-1 text-xs text-sco-muted-foreground hover:bg-sco-muted"
                disabled={isSubmitting}
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={handleFreeTextSubmit}
                disabled={!freeTextValue.trim() || isSubmitting}
                className={cn(
                  "flex items-center gap-1.5 rounded px-3 py-1 text-xs font-semibold transition-colors",
                  freeTextValue.trim() && !isSubmitting
                    ? "bg-sco-blue text-white hover:bg-sco-navy"
                    : "cursor-not-allowed bg-sco-muted text-sco-muted-foreground",
                )}
              >
                <Send size={11} />
                Invia
              </button>
            </div>
          </div>
        )}

        {/* Multi-select: campo "Altro" facoltativo + bottone Invia */}
        {isMulti && !isAnswered && (
          <>
            {allowFreeText && (
              <div className="mt-3 flex flex-col gap-1.5">
                <label className="text-[11px] font-medium text-sco-muted-foreground">
                  Aggiungi un'altra opzione (facoltativo):
                </label>
                <input
                  type="text"
                  value={freeTextValue}
                  onChange={(e) => setFreeTextValue(e.target.value)}
                  placeholder='Es: "Pharmacovigilanza", "ISO 22301"...'
                  className="rounded border border-sco-border bg-sco-surface-elevated px-2 py-1.5 text-sm text-sco-text placeholder:text-sco-muted-foreground/70 focus:border-sco-blue focus:outline-none focus:ring-1 focus:ring-sco-blue/30 dark:text-sco-text-dark"
                  disabled={isSubmitting}
                />
              </div>
            )}
            <div className="mt-3 flex items-center justify-between">
              <span className="text-[11px] text-sco-muted-foreground">
                {multiSelected.length + (freeTextValue.trim() ? 1 : 0)} selezionate
              </span>
              <button
                type="button"
                onClick={handleMultiSubmit}
                disabled={
                  (multiSelected.length === 0 && !freeTextValue.trim()) ||
                  isSubmitting
                }
                className={cn(
                  "flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-semibold transition-colors",
                  (multiSelected.length > 0 || freeTextValue.trim()) &&
                    !isSubmitting
                    ? "bg-sco-blue text-white hover:bg-sco-navy"
                    : "cursor-not-allowed bg-sco-muted text-sco-muted-foreground",
                )}
              >
                <Send size={12} />
                Invia risposta
              </button>
            </div>
          </>
        )}

        {isAnswered && answer_value && (
          <div className="mt-2.5 border-t border-sco-blue/15 pt-2 text-xs text-sco-muted-foreground">
            Risposta inviata. L&apos;agente riprende.
          </div>
        )}
      </div>
    </div>
  );
}

interface OptionButtonProps {
  option: InlineAskOption;
  isMulti: boolean;
  isMultiChecked: boolean;
  isAnswered: boolean;
  isSelected: boolean;
  isSubmitting: boolean;
  onClick: () => void;
}

function OptionButton({
  option,
  isMulti,
  isMultiChecked,
  isAnswered,
  isSelected,
  isSubmitting,
  onClick,
}: OptionButtonProps) {
  const disabled = isAnswered || isSubmitting;
  const visualSelected = isMulti ? isMultiChecked : isSelected;

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "group flex w-full items-start gap-2 rounded-md border px-3 py-2 text-left text-sm transition-all duration-150",
        // Stato pending: cliccabile + hover
        !disabled &&
          !visualSelected &&
          "border-sco-border bg-sco-bg hover:border-sco-blue hover:bg-sco-blue/10 hover:shadow-sm",
        // Multi-select checked
        !disabled &&
          visualSelected &&
          isMulti &&
          "border-sco-blue bg-sco-blue/10 ring-1 ring-sco-blue/40 shadow-sm",
        // Stato disabled (answered NON selezionato): mute totale
        disabled &&
          !isSelected &&
          "cursor-not-allowed border-sco-border bg-sco-muted text-sco-muted-foreground opacity-60",
        // Stato disabled selezionato (single-select answered): highlight amber check
        disabled &&
          isSelected &&
          "cursor-default border-sco-amber bg-sco-amber/10 ring-1 ring-sco-amber/40",
      )}
    >
      {/* Checkbox visual marker per multi-select */}
      {isMulti && !disabled && (
        <span
          className={cn(
            "mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border-2 transition-colors",
            isMultiChecked
              ? "border-sco-blue bg-sco-blue"
              : "border-sco-border bg-sco-bg",
          )}
        >
          {isMultiChecked && <Check size={9} className="text-white" />}
        </span>
      )}
      {/* Selected marker per single-select answered */}
      {!isMulti && isSelected && (
        <span className="mt-0.5 shrink-0 text-sco-amber">
          <Check size={14} />
        </span>
      )}
      <span className="flex-1">
        <span className="font-medium text-sco-text dark:text-sco-text-dark">
          {option.label}
        </span>
        {option.description && (
          <span className="ml-1.5 text-xs text-sco-muted-foreground">
            — {option.description}
          </span>
        )}
      </span>
    </button>
  );
}
