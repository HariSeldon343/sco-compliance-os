// SCO Compliance OS — TutorialScreen: 5 slide guida operativa + mark done
// Conv. 48: backend persiste tutorial_done flag. Frontend refetch dopo accept.

import { useState } from "react";
import { toast } from "sonner";
import {
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  Upload,
  FileText,
  Sparkles,
  Settings,
} from "lucide-react";

import { useOnboardingStore } from "@/store/onboarding-store";

interface TutorialStep {
  icon: React.ReactNode;
  title: string;
  body: string;
  example: string;
}

const STEPS: TutorialStep[] = [
  {
    icon: <MessageSquare size={48} className="text-[#0074b4]" />,
    title: "1. Apri una chat con l'agente",
    body:
      "Clicca sul bottone Chat nella sidebar a sinistra. Scrivi la tua domanda in basso, premi invio. L'agente risponde nello spazio centrale.",
    example: "Prova: \"Riassumi gli obblighi NIS 2 per un IRCCS privato\"",
  },
  {
    icon: <Upload size={48} className="text-[#ffa727]" />,
    title: "2. Carica documenti nel vault",
    body:
      "Trascina i file PDF, DOCX, MD nella chat. L'app ti chiede se vuoi indicizzarli. Se accetti, finiscono in raw/ del vault e diventano contesto per l'agente.",
    example: "Esempio: trascina un PDF di normativa, poi chiedi \"Cosa dice il punto 3 di questo decreto?\"",
  },
  {
    icon: <FileText size={48} className="text-[#302e5c]" />,
    title: "3. Esplora il vault dalla sidebar",
    body:
      "Nella sidebar trovi la sezione Vault. Vedi le cartelle del tuo vault con il numero di file. Puoi aprire file, aggiungere nuovi vault, gestire la sincronizzazione.",
    example: "La struttura SCO ti aiuta a sapere dove va ogni nuovo file.",
  },
  {
    icon: <Sparkles size={48} className="text-[#0074b4]" />,
    title: "4. Usa le skill consulenziali",
    body:
      "L'agente sa attivare skill specializzate: redigere procedure, fare gap analysis, costruire perizie, applicare il tono Amodeo. Chiedi e ti dice cosa ha attivato.",
    example: "Esempio: \"Redigi una bozza di policy NIS 2 per soggetto essenziale\"",
  },
  {
    icon: <Settings size={48} className="text-[#ffa727]" />,
    title: "5. Personalizza dalle Impostazioni",
    body:
      "Nella sidebar trovi Impostazioni. Da qui scegli tema chiaro o scuro, gestisci le integrazioni (Gmail, Calendar, Drive), controlli lo stato della license, attivi i toggle delle feature.",
    example: "L'agente migliora ogni giorno con il tuo uso: più lavori con lui, più diventa preciso.",
  },
];

export function TutorialScreen() {
  const markTutorialDone = useOnboardingStore((s) => s.markTutorialDone);
  const loading = useOnboardingStore((s) => s.loading);

  const [index, setIndex] = useState(0);
  const isLast = index === STEPS.length - 1;
  const current = STEPS[index];

  const handleNext = async () => {
    if (isLast) {
      const ok = await markTutorialDone();
      if (ok) {
        toast.success("Pronto. Entriamo in chat.");
      } else {
        toast.error("Errore. Riprova fra qualche secondo.");
      }
      return;
    }
    setIndex((i) => Math.min(i + 1, STEPS.length - 1));
  };

  const handlePrev = () => {
    setIndex((i) => Math.max(0, i - 1));
  };

  const handleSkip = async () => {
    const ok = await markTutorialDone();
    if (ok) {
      toast.success("Tutorial saltato.");
    }
  };

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-gradient-to-br from-[#1a1837] via-[#302e5c] to-[#0074b4] p-8">
      <div className="flex w-full max-w-3xl flex-col rounded-2xl bg-white p-8 shadow-2xl dark:bg-slate-900">
        {/* Brand */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-[#0074b4]" />
            <h1 className="text-lg font-semibold text-[#302e5c] dark:text-white">
              SCO Compliance OS
            </h1>
          </div>
          <span className="rounded-full bg-[#ffa727]/15 px-3 py-1 text-xs font-medium text-[#ffa727]">
            Fase 5 di 5 — Tutorial
          </span>
        </div>

        {/* Step content */}
        <div className="flex min-h-[280px] flex-col items-center justify-center text-center">
          <div className="mb-4">{current.icon}</div>
          <h2 className="mb-3 text-2xl font-bold text-slate-900 dark:text-white">
            {current.title}
          </h2>
          <p className="mb-3 max-w-xl text-base leading-relaxed text-slate-700 dark:text-slate-200">
            {current.body}
          </p>
          <p className="max-w-xl text-sm italic text-slate-500 dark:text-slate-400">
            {current.example}
          </p>
        </div>

        {/* Indicatore step */}
        <div className="my-6 flex justify-center gap-2">
          {STEPS.map((_, i) => (
            <span
              key={i}
              className={`h-2 w-8 rounded-full transition-colors ${
                i === index ? "bg-[#0074b4]" : "bg-slate-300 dark:bg-slate-700"
              }`}
              aria-label={`Step ${i + 1} di ${STEPS.length}`}
            />
          ))}
        </div>

        {/* Navigazione */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={handlePrev}
            disabled={index === 0 || loading}
            className="flex items-center gap-1 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <ChevronLeft size={16} />
            Indietro
          </button>

          <button
            type="button"
            onClick={handleSkip}
            disabled={loading}
            className="text-sm text-slate-500 underline hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          >
            Salta tutorial
          </button>

          <button
            type="button"
            onClick={handleNext}
            disabled={loading}
            className="flex items-center gap-1 rounded-lg bg-[#0074b4] px-6 py-2 text-sm font-semibold text-white hover:bg-[#005a8f] disabled:opacity-50"
          >
            {loading ? "Attendi..." : isLast ? "Entra nell'app" : "Avanti"}
            {!isLast && <ChevronRight size={16} />}
          </button>
        </div>
      </div>
    </div>
  );
}
