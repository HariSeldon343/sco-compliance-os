// SCO Compliance OS — Mascot floating overlay.
//
// Renderizza MascotCharacter come overlay floating top-right corner 200x200,
// ma solo se useMascotStore.enabled === true (opt-in dell'utente da Settings).
//
// Auto-update dello stato dal chat-store (Conv. 48 single source of truth):
//   - isStreaming === true  → mascot.state = "thinking"
//   - isStreaming === false → mascot.state = "idle" (se non già listening/speaking)
//
// Listening e speaking sono placeholder: oggi non c'è cablaggio mic / TTS, ma
// l'overlay è già pronto a riceverli appena disponibili (carry-over Sessione 8+).
// Il pubblicatore (componente che attiva mic o TTS) farà semplicemente:
//   useMascotStore.getState().setState("listening" | "speaking" | "idle")
//
// Posizionamento: fixed top-4 right-4 z-50 — overlay z-index 50 coerente con
// Header / Sidebar (z-10), CommandPalette (z-50), Toaster (z-100).
// Niente pointer-events: il mascot è decorativo, non intercetta click.
//
// Performance: il componente non re-render se enabled = false (early return
// prima del rendering SVG). Animazioni CSS-only, no JS animation loop.

import { useEffect } from "react";

import { MascotCharacter } from "./MascotCharacter";
import { useMascotStore } from "@/store/mascot-store";
import { useChatStore } from "@/store/chat-store";

interface MascotOverlayProps {
  /** Override dimensione (default 160px per overlay floating più discreto). */
  size?: number;
}

export function MascotOverlay({ size = 160 }: MascotOverlayProps) {
  const enabled = useMascotStore((s) => s.enabled);
  const state = useMascotStore((s) => s.state);
  const variant = useMascotStore((s) => s.variant);
  const setState = useMascotStore((s) => s.setState);

  const isStreaming = useChatStore((s) => s.isStreaming);

  // Auto-update mascot state da chat events.
  // Regola di transizione:
  //   - isStreaming true  → thinking (override solo se non listening/speaking/celebrating)
  //   - isStreaming false → idle (override solo se attualmente thinking)
  // Listening, speaking, celebrating restano "sticky" e devono essere reset
  // esplicitamente dal loro publisher (mic stop, TTS playback end, celebrate
  // timeout auto-reset via store.celebrate(durationMs)).
  useEffect(() => {
    if (!enabled) return;
    if (isStreaming) {
      // Non sovrascrivere listening (l'utente sta parlando al mic), speaking
      // (TTS playback in corso) o celebrating (success event in corso).
      // In pratica solo idle → thinking.
      if (state === "idle") {
        setState("thinking");
      }
    } else {
      // Quando lo streaming finisce, torna idle se eri in thinking.
      // Non toccare listening/speaking/celebrating (sticky, reset esplicito).
      if (state === "thinking") {
        setState("idle");
      }
    }
    // Dipendenze: isStreaming + enabled. `state` e `setState` letti via store
    // ma esclusi dalla dependency list per evitare loop di re-render
    // (transizioni di stato innescate da setState non devono ri-eseguire l'hook).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isStreaming, enabled]);

  if (!enabled) return null;

  return (
    <div
      className="pointer-events-none fixed right-4 top-4 z-50 animate-fade-in"
      aria-hidden="true"
    >
      <div className="relative">
        {/* Glow ring sottile dietro al mascot, varianza per stato */}
        <div
          className={
            state === "listening"
              ? "absolute inset-0 -z-10 rounded-full bg-red-500/20 blur-2xl animate-pulse-soft"
              : state === "speaking"
                ? "absolute inset-0 -z-10 rounded-full bg-sco-amber/20 blur-2xl animate-pulse-soft"
                : state === "celebrating"
                  ? "absolute inset-0 -z-10 rounded-full bg-sco-amber/30 blur-3xl animate-pulse-soft"
                  : state === "thinking"
                    ? "absolute inset-0 -z-10 rounded-full bg-sco-blue/15 blur-2xl"
                    : "absolute inset-0 -z-10 rounded-full bg-sco-blue/10 blur-2xl"
          }
        />
        <MascotCharacter state={state} variant={variant} size={size} />

        {/* Sottotitolo accessibile (visivamente nascosto, esposto a screen reader) */}
        <span className="sr-only">
          Mascot SCO Compliance OS — stato {state}, variante {variant}
        </span>
      </div>
    </div>
  );
}
