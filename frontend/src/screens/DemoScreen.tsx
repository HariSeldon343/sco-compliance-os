// SCO Compliance OS — DemoScreen: 4 slide di presentazione + mark seen
// Conv. 47 + 48: backend è source of truth della version corrente.

import { useState } from "react";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, MessageSquare, Database, Shield, Wand2 } from "lucide-react";

import { useOnboardingStore } from "@/store/onboarding-store";

interface Slide {
  icon: React.ReactNode;
  title: string;
  body: string;
  hint: string;
}

const SLIDES: Slide[] = [
  {
    icon: <MessageSquare size={48} className="text-[#0074b4]" />,
    title: "Un agente AI specializzato in compliance italiana",
    body:
      "L'agente conosce le normative italiane: NIS 2, ISO 27001, GDPR, AI Act, accreditamento sanitario, sicurezza lavoro. Chiedi cose come faresti a un collega esperto.",
    hint: "Esempio: \"Riassumi gli obblighi NIS 2 per un IRCCS privato\"",
  },
  {
    icon: <Database size={48} className="text-[#ffa727]" />,
    title: "Il tuo vault Obsidian è la memoria dell'agente",
    body:
      "L'agente legge i tuoi file Markdown: indici cliente, procedure, audit, fonti normative. Più il vault è ricco, più le risposte sono precise per il tuo lavoro.",
    hint: "Strutture supportate: Karpathy three-layer (raw + wiki + CLAUDE.md)",
  },
  {
    icon: <Shield size={48} className="text-[#302e5c]" />,
    title: "Privato, tuo, italiano",
    body:
      "Tutto il lavoro sta sul tuo PC. Le chat, i documenti, le memorie. Solo le domande viaggiano verso il modello AI, e Anthropic non le usa per addestrarsi.",
    hint: "No cloud sync di documenti. No telemetria invasiva.",
  },
  {
    icon: <Wand2 size={48} className="text-[#0074b4]" />,
    title: "Quattro flussi pronti",
    body:
      "Apri una chat e parla. Carica documenti per indicizzarli. Genera procedure, perizie, gap analysis. Esegui audit con l'agente come secondo paio di occhi.",
    hint: "Inizia in 30 secondi dalla home.",
  },
];

export function DemoScreen() {
  const markDemoSeen = useOnboardingStore((s) => s.markDemoSeen);
  const loading = useOnboardingStore((s) => s.loading);
  const version = useOnboardingStore((s) => s.currentDemoVersion);

  const [index, setIndex] = useState(0);
  const isLast = index === SLIDES.length - 1;
  const current = SLIDES[index];

  const handleNext = async () => {
    if (isLast) {
      const ok = await markDemoSeen();
      if (ok) {
        toast.success("Demo completata. Proseguiamo.");
      } else {
        toast.error("Errore. Riprova fra qualche secondo.");
      }
      return;
    }
    setIndex((i) => Math.min(i + 1, SLIDES.length - 1));
  };

  const handlePrev = () => {
    setIndex((i) => Math.max(0, i - 1));
  };

  const handleSkip = async () => {
    const ok = await markDemoSeen();
    if (ok) {
      toast.success("Demo saltata.");
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
            Fase 3 di 5 — Demo
          </span>
        </div>

        {/* Slide content */}
        <div className="flex min-h-[280px] flex-col items-center justify-center text-center">
          <div className="mb-4">{current.icon}</div>
          <h2 className="mb-3 text-2xl font-bold text-slate-900 dark:text-white">
            {current.title}
          </h2>
          <p className="mb-3 max-w-xl text-base leading-relaxed text-slate-700 dark:text-slate-200">
            {current.body}
          </p>
          <p className="max-w-xl text-sm italic text-slate-500 dark:text-slate-400">
            {current.hint}
          </p>
        </div>

        {/* Indicatore slide */}
        <div className="my-6 flex justify-center gap-2">
          {SLIDES.map((_, i) => (
            <span
              key={i}
              className={`h-2 w-8 rounded-full transition-colors ${
                i === index ? "bg-[#0074b4]" : "bg-slate-300 dark:bg-slate-700"
              }`}
              aria-label={`Slide ${i + 1} di ${SLIDES.length}`}
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
            Salta demo
          </button>

          <button
            type="button"
            onClick={handleNext}
            disabled={loading}
            className="flex items-center gap-1 rounded-lg bg-[#0074b4] px-6 py-2 text-sm font-semibold text-white hover:bg-[#005a8f] disabled:opacity-50"
          >
            {loading ? "Attendi..." : isLast ? "Continua" : "Avanti"}
            {!isLast && <ChevronRight size={16} />}
          </button>
        </div>

        <p className="mt-4 text-center text-xs text-slate-400">
          Versione demo {version}
        </p>
      </div>
    </div>
  );
}
