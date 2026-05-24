// SCO Compliance OS — voice store Zustand: toggle STT/TTS + voci IT/EN
// Pattern Conv. 47: lo stato runtime tooling (binari/modelli installed) vive
// lato backend (/api/voice/status). Qui solo preferenze utente persistite.
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type SttLanguage = "it" | "en" | "auto";
export type PiperVoice = "it_IT-paola-medium" | "en_US-libritts-high";

interface VoiceState {
  /** STT (microfono): abilita pulsante mic in chat input + hotkey PTT */
  sttEnabled: boolean;
  /** TTS (lettura risposte): mostra play button su messaggi assistant */
  ttsEnabled: boolean;
  /** Lingua di trascrizione default (it/en/auto multilingue) */
  sttLanguage: SttLanguage;
  /** Voce sintesi italiana */
  ttsVoiceIt: PiperVoice;
  /** Voce sintesi inglese */
  ttsVoiceEn: PiperVoice;
  /** Hotkey push-to-talk globale abilitato */
  hotkeyEnabled: boolean;

  setSttEnabled: (v: boolean) => void;
  setTtsEnabled: (v: boolean) => void;
  setSttLanguage: (l: SttLanguage) => void;
  setTtsVoiceIt: (v: PiperVoice) => void;
  setTtsVoiceEn: (v: PiperVoice) => void;
  setHotkeyEnabled: (v: boolean) => void;
}

export const useVoiceStore = create<VoiceState>()(
  persist(
    (set) => ({
      // Default OFF v0.7.0: privacy + bandwidth (modelli ~75-140 MB lazy
      // download al primo use). L'utente deve opt-in via Settings.
      sttEnabled: false,
      ttsEnabled: false,
      sttLanguage: "it",
      ttsVoiceIt: "it_IT-paola-medium",
      ttsVoiceEn: "en_US-libritts-high",
      hotkeyEnabled: true,

      setSttEnabled: (v) => set({ sttEnabled: v }),
      setTtsEnabled: (v) => set({ ttsEnabled: v }),
      setSttLanguage: (l) => set({ sttLanguage: l }),
      setTtsVoiceIt: (v) => set({ ttsVoiceIt: v }),
      setTtsVoiceEn: (v) => set({ ttsVoiceEn: v }),
      setHotkeyEnabled: (v) => set({ hotkeyEnabled: v }),
    }),
    {
      name: "sco-voice-prefs",
      partialize: (s) => ({
        sttEnabled: s.sttEnabled,
        ttsEnabled: s.ttsEnabled,
        sttLanguage: s.sttLanguage,
        ttsVoiceIt: s.ttsVoiceIt,
        ttsVoiceEn: s.ttsVoiceEn,
        hotkeyEnabled: s.hotkeyEnabled,
      }),
    },
  ),
);
