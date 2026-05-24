// SCO Compliance OS — componente EmptyState riusabile per stati vuoti legittimi.
// UX polish v1.0.0: copy chiaro italiano + icona Lucide grande + CTA visibile.
// Distinto dagli stati di errore (network/500): quelli usano toast separato.
//
// Linguaggio semplice (regola 14/05/2026 vault): comprensibile a bambino sveglio.

import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

import { cn } from "@/lib/cn";

export type EmptyStateTone = "info" | "neutral" | "warning";

export interface EmptyStateProps {
  /** Icona Lucide da mostrare nel cerchio decorativo */
  icon: LucideIcon;
  /** Titolo grande, 3-6 parole */
  title: string;
  /** Descrizione 1-2 frasi che spiega lo stato + cosa fare */
  description: React.ReactNode;
  /** Etichetta del CTA button (opzionale) */
  ctaLabel?: string;
  /** Destinazione react-router del CTA (mutualmente esclusivo con ctaAction) */
  ctaHref?: string;
  /** Azione del CTA (mutualmente esclusivo con ctaHref) */
  ctaAction?: () => void;
  /** CTA secondario opzionale (link più discreto sotto il primary) */
  secondaryCtaLabel?: string;
  secondaryCtaHref?: string;
  secondaryCtaAction?: () => void;
  /** Tono visivo. Default "info" (blu). */
  tone?: EmptyStateTone;
  /** Padding compatto per inserimenti in pannelli stretti */
  compact?: boolean;
  /** classNames extra per il wrapper esterno */
  className?: string;
}

const TONE_ICON_CLASSES: Record<EmptyStateTone, string> = {
  info: "bg-sco-blue/10 text-sco-blue",
  neutral: "bg-sco-navy/10 text-sco-navy dark:text-sco-text-dark",
  warning: "bg-sco-amber/10 text-sco-amber",
};

const TONE_CTA_CLASSES: Record<EmptyStateTone, string> = {
  info: "bg-sco-blue text-white hover:bg-sco-navy",
  neutral: "bg-sco-navy text-white hover:bg-sco-blue",
  warning: "bg-sco-amber text-white hover:bg-sco-amber/80",
};

/**
 * Stato vuoto legittimo: la categoria esiste ma non ha dati ancora.
 *
 * NON usare per errori di rete (network/500): per quelli c'è il toast separato
 * o un componente dedicato. Distinzione chiara empty vs error (Conv. 48).
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  ctaLabel,
  ctaHref,
  ctaAction,
  secondaryCtaLabel,
  secondaryCtaHref,
  secondaryCtaAction,
  tone = "info",
  compact = false,
  className,
}: EmptyStateProps) {
  const showCta = Boolean(ctaLabel && (ctaHref || ctaAction));
  const showSecondaryCta = Boolean(
    secondaryCtaLabel && (secondaryCtaHref || secondaryCtaAction),
  );

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed border-sco-border bg-sco-surface-elevated text-center",
        compact ? "p-6" : "p-12",
        className,
      )}
    >
      <div
        className={cn(
          "mb-4 flex items-center justify-center rounded-2xl",
          compact ? "h-12 w-12" : "h-16 w-16",
          TONE_ICON_CLASSES[tone],
        )}
      >
        <Icon size={compact ? 24 : 28} />
      </div>

      <h2
        className={cn(
          "font-semibold text-sco-text dark:text-sco-text-dark",
          compact ? "text-base" : "text-lg",
        )}
      >
        {title}
      </h2>

      <div
        className={cn(
          "mx-auto max-w-md text-sm leading-relaxed text-sco-muted-foreground",
          compact ? "mt-1.5" : "mt-2",
        )}
      >
        {description}
      </div>

      {(showCta || showSecondaryCta) && (
        <div className="mt-5 flex flex-col items-center gap-2 sm:flex-row sm:gap-3">
          {showCta &&
            (ctaHref ? (
              <Link
                to={ctaHref}
                className={cn(
                  "rounded-md px-4 py-2 text-sm font-medium shadow-sm transition-colors",
                  TONE_CTA_CLASSES[tone],
                )}
              >
                {ctaLabel}
              </Link>
            ) : (
              <button
                type="button"
                onClick={ctaAction}
                className={cn(
                  "rounded-md px-4 py-2 text-sm font-medium shadow-sm transition-colors",
                  TONE_CTA_CLASSES[tone],
                )}
              >
                {ctaLabel}
              </button>
            ))}

          {showSecondaryCta &&
            (secondaryCtaHref ? (
              <Link
                to={secondaryCtaHref}
                className="text-sm font-medium text-sco-muted-foreground transition-colors hover:text-sco-blue"
              >
                {secondaryCtaLabel}
              </Link>
            ) : (
              <button
                type="button"
                onClick={secondaryCtaAction}
                className="text-sm font-medium text-sco-muted-foreground transition-colors hover:text-sco-blue"
              >
                {secondaryCtaLabel}
              </button>
            ))}
        </div>
      )}
    </div>
  );
}

export interface ErrorStateProps {
  /** Icona Lucide. Default: AlertCircle */
  icon?: LucideIcon;
  /** Titolo errore */
  title?: string;
  /** Messaggio errore tecnico */
  message: string;
  /** Azione "Riprova" (opzionale) */
  onRetry?: () => void;
  /** Etichetta del retry button */
  retryLabel?: string;
  /** Padding compatto */
  compact?: boolean;
  className?: string;
}

/**
 * Stato di errore di rete / 500. Distinto dall'empty state.
 *
 * Usa palette rossa neutra (no toast: la stessa info è già nel toast,
 * questo è il fallback persistent quando l'utente entra in una vista
 * che non riesce a caricarsi affatto).
 */
export function ErrorState({
  icon: Icon,
  title = "Errore di rete",
  message,
  onRetry,
  retryLabel = "Riprova",
  compact = false,
  className,
}: ErrorStateProps) {
  const IconCmp = Icon;

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-red-200 bg-red-50 text-center dark:border-red-900/40 dark:bg-red-950/30",
        compact ? "p-6" : "p-10",
        className,
      )}
    >
      {IconCmp && (
        <div
          className={cn(
            "mb-4 flex items-center justify-center rounded-2xl bg-red-500/10 text-red-500",
            compact ? "h-12 w-12" : "h-14 w-14",
          )}
        >
          <IconCmp size={compact ? 22 : 26} />
        </div>
      )}

      <h2
        className={cn(
          "font-semibold text-red-800 dark:text-red-100",
          compact ? "text-base" : "text-lg",
        )}
      >
        {title}
      </h2>
      <p
        className={cn(
          "mx-auto max-w-md text-sm text-red-700 dark:text-red-300",
          compact ? "mt-1.5" : "mt-2",
        )}
      >
        {message}
      </p>

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-600"
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
}
