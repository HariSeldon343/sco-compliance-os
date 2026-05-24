// SCO Compliance OS — Audio player per leggere risposte agente via TTS
// Pattern: Play -> POST /api/voice/synthesize -> audio/wav blob -> HTML5 Audio play.
//
// Privacy: nessun testo lascia il dispositivo, sintesi locale via piper.
import { useEffect, useRef, useState } from "react";
import { Volume2, Loader2, Square } from "lucide-react";
import { toast } from "sonner";

import { apiClient, ApiError } from "@/api/client";
import { useVoiceStore, type PiperVoice } from "@/store/voice-store";
import { cn } from "@/lib/cn";

interface AudioPlayerProps {
  /** Testo da sintetizzare (tipicamente message.content dell'agente). */
  text: string;
  /** Override voce (default: prefs utente in base alla lingua testo). */
  voice?: PiperVoice;
  /** Class override. */
  className?: string;
}

type PlayState = "idle" | "loading" | "playing";

/** Heuristic semplice per decidere voce IT vs EN dal testo (basata su sample). */
function detectLanguageHeuristic(text: string): "it" | "en" {
  // Sample primi 200 char, conta parole funzionali italiane vs inglesi
  const sample = text.slice(0, 200).toLowerCase();
  const itMarkers = [" il ", " la ", " di ", " che ", " un ", " per ", " con ", " del ", " sono "];
  const enMarkers = [" the ", " and ", " of ", " to ", " is ", " for ", " with ", " in ", " that "];
  const itCount = itMarkers.reduce((c, m) => c + (sample.includes(m) ? 1 : 0), 0);
  const enCount = enMarkers.reduce((c, m) => c + (sample.includes(m) ? 1 : 0), 0);
  return enCount > itCount ? "en" : "it";
}

export function AudioPlayer({ text, voice, className }: AudioPlayerProps) {
  const ttsEnabled = useVoiceStore((s) => s.ttsEnabled);
  const ttsVoiceIt = useVoiceStore((s) => s.ttsVoiceIt);
  const ttsVoiceEn = useVoiceStore((s) => s.ttsVoiceEn);

  const [state, setState] = useState<PlayState>("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  // Cleanup objectURL all'unmount
  useEffect(() => {
    return () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const stop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
    setState("idle");
  };

  const play = async () => {
    if (state !== "idle" || !text.trim()) return;
    setState("loading");

    // Scegli voce in base a override > heuristic
    const chosenVoice: PiperVoice =
      voice ?? (detectLanguageHeuristic(text) === "en" ? ttsVoiceEn : ttsVoiceIt);

    try {
      const blob = await apiClient.synthesizeText({
        text: text.slice(0, 2000), // hard cap allineato a backend
        voice: chosenVoice,
      });
      const url = URL.createObjectURL(blob);
      objectUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        stop();
      };
      audio.onerror = () => {
        toast.error("Riproduzione audio fallita.");
        stop();
      };
      setState("playing");
      await audio.play();
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        toast.error(
          "TTS non disponibile. Installa piper o attendi il download della voce.",
        );
      } else {
        toast.error(
          `Sintesi fallita: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
      stop();
    }
  };

  const handleClick = () => {
    if (state === "playing") stop();
    else if (state === "idle") void play();
  };

  if (!ttsEnabled) return null;

  const title =
    state === "loading"
      ? "Sintesi in corso..."
      : state === "playing"
        ? "Stop"
        : "Leggi ad alta voce";
  const Icon = state === "loading" ? Loader2 : state === "playing" ? Square : Volume2;

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={state === "loading"}
      title={title}
      aria-label={title}
      aria-pressed={state === "playing"}
      className={cn(
        "inline-flex h-6 w-6 items-center justify-center rounded-md transition-colors duration-150",
        state === "playing"
          ? "bg-sco-blue/15 text-sco-blue hover:bg-sco-blue/25"
          : state === "loading"
            ? "cursor-wait text-sco-muted-foreground"
            : "text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark",
        className,
      )}
    >
      <Icon
        size={12}
        className={cn(state === "loading" && "animate-spin")}
      />
    </button>
  );
}
