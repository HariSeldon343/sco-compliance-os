// SCO Compliance OS — widget cliccabile per AskUserQuestion inline.
//
// Bug v1.0.2: il backend emette nei content dei messaggi assistant un tag
// testuale `<ASK_USER_QUESTION>{json}</ASK_USER_QUESTION>` che il frontend
// non sapeva renderizzare come bottoni. Questo componente, in coppia con
// `lib/parseInlineWidgets.ts`, chiude il bug producendo l'interazione
// cliccabile attesa dall'utente.
//
// Stato del widget:
// - "pending" → bottoni attivi, nessuna selezione
// - "answered" → tutti i bottoni disabled + badge "Risposto" sulla
//   selezione + opzioni non scelte rese in muted
//
// Pattern Conv. 48: la state del widget vive lato store (e dovrebbe vivere
// lato backend in DB). Il componente e' "presentational" — riceve `state` +
// `answer_value` + callback `onAnswer` come props.

import { Check } from "lucide-react";

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

/**
 * Card domanda cliccabile in linguaggio semplice (regola 14/05 + Conv. 48).
 *
 * Layout:
 * - Header in alto a sinistra: badge "Domanda" + titolo della question
 * - Body: lista verticale di bottoni opzione cliccabili
 * - In stato "answered": opzione selezionata evidenziata con check verde +
 *   badge "Risposto", altre opzioni mute/disabled
 */
export function AskQuestionCard({
  payload,
  onAnswer,
  state,
  answer_value,
  isSubmitting = false,
}: AskQuestionCardProps) {
  const isAnswered = state === "answered";

  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-sco-blue/30 bg-sco-blue/5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sco-blue/20 bg-sco-blue/10 px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-sco-blue">
          Domanda
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
          {payload.options.map((opt) => (
            <OptionButton
              key={opt.value}
              option={opt}
              isAnswered={isAnswered}
              isSelected={isAnswered && answer_value === opt.value}
              isSubmitting={isSubmitting}
              onClick={() => onAnswer(opt.value)}
            />
          ))}
        </div>
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
  isAnswered: boolean;
  isSelected: boolean;
  isSubmitting: boolean;
  onClick: () => void;
}

function OptionButton({
  option,
  isAnswered,
  isSelected,
  isSubmitting,
  onClick,
}: OptionButtonProps) {
  const disabled = isAnswered || isSubmitting;

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "group flex w-full items-start gap-2 rounded-md border px-3 py-2 text-left text-sm transition-all duration-150",
        // Stato pending: cliccabile + hover
        !disabled &&
          "border-sco-border bg-sco-bg hover:border-sco-blue hover:bg-sco-blue/10 hover:shadow-sm",
        // Stato disabled (answered NON selezionato): mute totale
        disabled &&
          !isSelected &&
          "cursor-not-allowed border-sco-border bg-sco-muted text-sco-muted-foreground opacity-60",
        // Stato disabled selezionato: highlight amber con check
        disabled &&
          isSelected &&
          "cursor-default border-sco-amber bg-sco-amber/10 ring-1 ring-sco-amber/40",
      )}
    >
      {isSelected && (
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
