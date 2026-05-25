// SCO Compliance OS — Walkthrough first-launch (react-joyride 3.x) v0.13.2 PSI-2
//
// 10 step contestualizzati al workflow SCO consulenza compliance italiana.
// Pattern openhuman-inspired clean-room (NO copia codice GPL-3.0 da
// openhuman-main, solo idea di pattern "guided tour").
//
// API: react-joyride 3.1.0 (named export `Joyride`, onEvent + Controls,
// `EventData` + `STATUS`). API differs significantly from joyride 2.x.
//
// Trigger:
//   - first-launch: localStorage flag `sco:walkthrough_completed` assente
//   - on-demand: bottone "Mostra tour guidato" in AdvancedTab Settings
//
// Targets (data-tour selectors stabili):
//   1. [data-tour="sidebar-chat"] - Chat (intro app)
//   2. [data-tour="sidebar-wiki"] - Wiki (knowledge base)
//   3. [data-tour="sidebar-grafo"] - Grafo (visualizza vault)
//   4. [data-tour="sidebar-skills"] - Skills (catalog competenze)
//   5. [data-tour="sidebar-vault"] - Vault (gestione)
//   6. [data-tour="sidebar-memory"] - Memoria (subconscious)
//   7. [data-tour="sidebar-settings"] - Impostazioni
//   8. [data-tour="header-end-session"] - Header Fine sessione
//   9. [data-tour="chat-input-textarea"] - Chat input
//  10. [data-tour="chat-send-button"] - Send button
//
// Persistenza: localStorage flag `sco:walkthrough_completed` settato a "1"
// alla chiusura (joyride event STATUS.FINISHED o STATUS.SKIPPED).

import { useEffect, useState } from "react";
import {
  Joyride,
  STATUS,
  type EventData,
  type Step,
} from "react-joyride";

const WALKTHROUGH_FLAG_KEY = "sco:walkthrough_completed";

const TOUR_STEPS: Step[] = [
  {
    target: '[data-tour="sidebar-chat"]',
    title: "Benvenuto in SCO Compliance OS",
    content:
      "Il tuo AI consulente compliance italiana. Tutto in locale: nessun dato esce dalla tua macchina. Da questa voce torni sempre alla chat.",
    placement: "right",
    skipBeacon: true,
  },
  {
    target: '[data-tour="sidebar-wiki"]',
    title: "Wiki",
    content:
      "La tua base di conoscenza memoria-gerarchica L0/L1/L2. Qui vivono le fonti normative ingerite (NIS 2, ISO 27001, AI Act, GDPR), gli articoli citati e le sintesi cross-framework.",
    placement: "right",
  },
  {
    target: '[data-tour="sidebar-grafo"]',
    title: "Grafo",
    content:
      "Visualizza il tuo vault come rete force-directed 2D. Nodi cliente, entity normative, edge fra clienti e standard certificandi. Utile per trovare correlazioni che la lista appiattisce.",
    placement: "right",
  },
  {
    target: '[data-tour="sidebar-skills"]',
    title: "Skills",
    content:
      "Il catalogo delle competenze dell'agente: NIS 2, ISO 27001, audit sanitario, RSPP, antincendio, GDPR. Puoi attivarle al volo per task specifici o creare skill custom via wizard.",
    placement: "right",
  },
  {
    target: '[data-tour="sidebar-vault"]',
    title: "Vault",
    content:
      "Gestisci i tuoi vault Obsidian-style: cartelle Contesto, Business clienti, Giornaliero, Skill, Libreria. Tutto markdown plain-text, niente DB proprietari.",
    placement: "right",
  },
  {
    target: '[data-tour="sidebar-memory"]',
    title: "Memoria",
    content:
      "Cosa l'agente ricorda di te: profilo, preferenze, fatti stabili. Persistenza markdown + JSON index, NO vector DB. Single source of truth lato backend (Conv. 47).",
    placement: "right",
  },
  {
    target: '[data-tour="sidebar-settings"]',
    title: "Impostazioni",
    content:
      "Profilo, vault, voice, skill, team, connettori. Da qui puoi rivedere questo tour in qualsiasi momento (Avanzate -> Mostra tour guidato).",
    placement: "right",
  },
  {
    target: '[data-tour="header-end-session"]',
    title: "Fine sessione",
    content:
      "Chiusura ordinata: dump del log giornaliero, aggiornamento attivi.md, propagazione fatti stabili nel Contesto. Pattern session-lifecycle Karpathy.",
    placement: "bottom",
  },
  {
    target: '[data-tour="chat-input-textarea"]',
    title: "Scrivi qui",
    content:
      "Scrivi la tua domanda o trascina file (PDF normative, DOCX audit, immagini evidenze). Slash command e modalita agente sono nella toolbar sotto.",
    placement: "top",
  },
  {
    target: '[data-tour="chat-send-button"]',
    title: "Invia",
    content:
      "Click o Invio per inviare. L'agente risponde in streaming token-per-token. Buona consulenza!",
    placement: "top",
  },
];

export interface WalkthroughTourProps {
  /** Se true, forza il run del tour anche se gia` completato (per "rilancia tour" da Settings). */
  forceRun?: boolean;
  /** Callback chiusura tour (qualunque esito) per reset di stato genitore. */
  onFinish?: () => void;
}

/**
 * Wrapper React per react-joyride 3.x. Si auto-attiva al first-launch (flag
 * localStorage assente) e puo` essere ri-lanciato on-demand via forceRun.
 *
 * Joyride 3.x usa pattern controlled tramite stepIndex + onEvent invece di
 * callback. STATUS.FINISHED / STATUS.SKIPPED rimangono come marker di
 * chiusura tour (controllati via EventData.status).
 */
export function WalkthroughTour({ forceRun, onFinish }: WalkthroughTourProps) {
  const [run, setRun] = useState(false);

  // Auto-trigger first-launch
  useEffect(() => {
    if (forceRun) {
      setRun(true);
      return;
    }
    try {
      const completed = window.localStorage.getItem(WALKTHROUGH_FLAG_KEY);
      if (completed !== "1") {
        // Delay leggero per assicurare che AuthGate sia past + sidebar montata
        const timer = window.setTimeout(() => setRun(true), 800);
        return () => window.clearTimeout(timer);
      }
    } catch {
      // localStorage non disponibile (private browsing?): skip auto-launch
    }
  }, [forceRun]);

  const handleEvent = (data: EventData) => {
    const { status } = data;
    // Tour finished o skipped (utente ha completato o cliccato salta)
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      try {
        window.localStorage.setItem(WALKTHROUGH_FLAG_KEY, "1");
      } catch {
        // ignore
      }
      setRun(false);
      onFinish?.();
    }
  };

  return (
    <Joyride
      steps={TOUR_STEPS}
      run={run}
      continuous
      onEvent={handleEvent}
      locale={{
        back: "Indietro",
        close: "Chiudi",
        last: "Finito",
        next: "Avanti",
        open: "Apri tour",
        skip: "Salta",
      }}
      options={{
        // Brand SCO colors via design tokens (no CSS override)
        primaryColor: "#0074b4", // sco-blue
        textColor: "#1a1a2e",
        backgroundColor: "#ffffff",
        arrowColor: "#ffffff",
        overlayColor: "rgba(15, 17, 36, 0.55)",
        zIndex: 10000,
        width: 360,
        showProgress: true,
        // Mantieni 'skip' nel set buttons cosi l'utente puo` chiudere il tour
        buttons: ["back", "skip", "primary"],
        // Disabilita chiusura overlay click per evitare dismiss accidentale
        overlayClickAction: false,
        // ESC chiude la step corrente (default)
        dismissKeyAction: "close",
      }}
      styles={{
        tooltipTitle: {
          fontSize: 15,
          fontWeight: 600,
          color: "#302e5c", // sco-navy
        },
        tooltipContent: {
          fontSize: 13,
          lineHeight: 1.55,
          padding: "10px 0",
        },
      }}
    />
  );
}

/**
 * Helper per leggere/scrivere il flag dalla UI senza accedere direttamente a localStorage.
 * Usato dal bottone "Mostra tour guidato" in AdvancedTab Settings.
 */
export function resetWalkthroughFlag(): void {
  try {
    window.localStorage.removeItem(WALKTHROUGH_FLAG_KEY);
  } catch {
    // ignore
  }
}

export function isWalkthroughCompleted(): boolean {
  try {
    return window.localStorage.getItem(WALKTHROUGH_FLAG_KEY) === "1";
  } catch {
    return false;
  }
}
