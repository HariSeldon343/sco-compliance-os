// SCO Compliance OS — Microphone button con push-to-talk + hotkey globale
// Pipeline: MediaRecorder browser-native -> WebM Opus blob -> POST /api/voice/transcribe
// -> onTranscript(text) callback al genitore (ChatInput).
//
// Hotkey: Ctrl+Shift+Space toggle global per push-to-talk.
//
// Privacy: nessun upload cloud, tutto on-device via backend localhost.
import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { apiClient, ApiError } from "@/api/client";
import { useVoiceStore } from "@/store/voice-store";
import { cn } from "@/lib/cn";

interface MicButtonProps {
  /** Callback invocata con il testo trascritto. */
  onTranscript: (text: string) => void;
  /** Disabilita pulsante (es. mentre l'agente sta streamando). */
  disabled?: boolean;
  /** Override classe (sizing, padding). */
  className?: string;
}

type RecState = "idle" | "recording" | "transcribing";

/** Hotkey trigger Ctrl+Shift+Space (Cmd+Shift+Space su Mac via metaKey). */
function isHotkeyEvent(e: KeyboardEvent): boolean {
  const modOk = (e.ctrlKey || e.metaKey) && e.shiftKey;
  return modOk && e.code === "Space";
}

export function MicButton({
  onTranscript,
  disabled = false,
  className,
}: MicButtonProps) {
  const sttEnabled = useVoiceStore((s) => s.sttEnabled);
  const sttLanguage = useVoiceStore((s) => s.sttLanguage);
  const hotkeyEnabled = useVoiceStore((s) => s.hotkeyEnabled);

  const [state, setState] = useState<RecState>("idle");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  // Cleanup stream all'unmount
  useEffect(() => {
    return () => {
      stopStream();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stopStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // gia' fermato
      }
    }
    mediaRecorderRef.current = null;
  }, []);

  const startRecording = useCallback(async () => {
    if (state !== "idle" || disabled || !sttEnabled) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      audioChunksRef.current = [];

      // Preferisci WebM Opus (default Chrome/Edge/Firefox). Safari = audio/mp4.
      const preferredMime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : MediaRecorder.isTypeSupported("audio/mp4")
            ? "audio/mp4"
            : "";
      const recorder = new MediaRecorder(
        stream,
        preferredMime ? { mimeType: preferredMime } : undefined,
      );
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        audioChunksRef.current = [];
        stopStream();

        if (blob.size === 0) {
          setState("idle");
          toast.error("Registrazione vuota, nessun audio rilevato.");
          return;
        }

        setState("transcribing");
        try {
          const extension = mimeType.includes("mp4") ? "m4a" : "webm";
          const result = await apiClient.transcribeAudio({
            audio: blob,
            language: sttLanguage,
            filename: `recording.${extension}`,
          });
          if (result.text.trim()) {
            onTranscript(result.text.trim());
          } else {
            toast.info("Nessun parlato riconosciuto.");
          }
        } catch (err) {
          if (err instanceof ApiError && err.status === 503) {
            toast.error(
              "STT non disponibile. Installa ffmpeg + whisper-cli o attendi il download dei modelli.",
            );
          } else {
            toast.error(
              `Trascrizione fallita: ${err instanceof Error ? err.message : String(err)}`,
            );
          }
        } finally {
          setState("idle");
        }
      };

      recorder.start();
      setState("recording");
    } catch (err) {
      stopStream();
      setState("idle");
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("Permission") || msg.includes("NotAllowed")) {
        toast.error("Permesso microfono negato dal browser/sistema.");
      } else {
        toast.error(`Microfono non disponibile: ${msg}`);
      }
    }
  }, [disabled, onTranscript, sttEnabled, sttLanguage, state, stopStream]);

  const stopRecording = useCallback(() => {
    if (state !== "recording") return;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, [state]);

  const toggleRecording = useCallback(() => {
    if (state === "idle") void startRecording();
    else if (state === "recording") stopRecording();
    // "transcribing": ignore (in flight)
  }, [state, startRecording, stopRecording]);

  // Hotkey globale Ctrl+Shift+Space toggle
  useEffect(() => {
    if (!hotkeyEnabled || !sttEnabled) return;
    const handler = (e: KeyboardEvent) => {
      if (!isHotkeyEvent(e)) return;
      // Evita interferenze quando l'utente sta scrivendo nel textarea
      // (Ctrl+Shift+Space e' tipicamente libero pero' sicurezza extra)
      e.preventDefault();
      toggleRecording();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [hotkeyEnabled, sttEnabled, toggleRecording]);

  if (!sttEnabled) return null;

  const title =
    state === "recording"
      ? "Stop (Ctrl+Shift+Space)"
      : state === "transcribing"
        ? "Trascrizione in corso..."
        : "Registra (Ctrl+Shift+Space)";

  const Icon =
    state === "transcribing" ? Loader2 : state === "recording" ? MicOff : Mic;

  return (
    <button
      type="button"
      onClick={toggleRecording}
      disabled={disabled || state === "transcribing"}
      title={title}
      aria-label={title}
      aria-pressed={state === "recording"}
      className={cn(
        "relative flex h-8 w-8 items-center justify-center rounded-md transition-all duration-150",
        state === "recording"
          ? "bg-red-500/15 text-red-500 hover:bg-red-500/25"
          : state === "transcribing"
            ? "cursor-wait bg-sco-muted text-sco-muted-foreground"
            : "text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark",
        disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    >
      <Icon
        size={16}
        className={cn(state === "transcribing" && "animate-spin")}
      />
      {state === "recording" && (
        <span
          className="absolute -top-0.5 -right-0.5 h-2 w-2 animate-pulse rounded-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.7)]"
          aria-hidden="true"
        />
      )}
    </button>
  );
}
