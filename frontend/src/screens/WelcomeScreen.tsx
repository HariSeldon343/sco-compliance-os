// SCO Compliance OS — WelcomeScreen hero animato (v0.13.0 PSI clean-room + v0.13.2 PSI-2)
//
// Componente standalone usato come "empty state" della ChatArea quando
// non c'è ancora una conversation attiva o messaggi presenti. Premium
// upgrade rispetto alla hero inline che viveva dentro ChatArea fino a v0.12.x.
//
// Animation stack (Framer Motion 12 + Tailwind 4 keyframes):
//   1. Logo SCO con glow pulse + scale-in (entrance)
//   2. v0.13.2 Typing welcome carousel — 3 varianti italiane in rotazione
//      (typing 55ms, deleting 36ms, pause 1400ms, gap 250ms). Usa profilo nome
//      se presente (fallback "consulente"). Pattern openhuman-inspired clean-room
//      (NO copia codice GPL-3.0 da openhuman-main).
//   3. Sottotitolo fade-up con delay
//   4. 4 suggestion card stagger entrance + hover shine effect
//   5. Tagline "Privato. Tuo. Italiano." con stagger ciascuna parola
//
// Clean-room legal: tutte le animation timing + sequencing sono originali.
// NON e' una copia di openhuman-main hero (codebase GPL-3.0 non aperto).
// Pattern di stagger reveal + typing carousel e' tecnica standard di motion design.
//
// Performance:
//   - LazyMotion non usato qui (welcome screen e' frequente come empty state,
//     non vale caching/lazyload). Bundle increase ~50KB gzip framer-motion.
//   - Typing carousel via setTimeout state machine. Cleanup su unmount.
//
// Accessibility:
//   - prefers-reduced-motion → static fallback Framer Motion + skip typing
//     animation (mostra solo 1° variante senza loop).
//   - Tutti gli href button ancora cliccabili durante animation (no
//     pointer-events disabled)
//   - aria-label preserved sui button suggestion
//   - aria-live="polite" su typing carousel per screen reader announcement

import { useEffect, useMemo, useRef, useState } from "react";
import { motion, type Variants } from "framer-motion";
import {
  ShieldCheck,
  ScanSearch,
  HeartPulse,
  AlertTriangle,
  ArrowUpRight,
} from "lucide-react";

import { useChatStore } from "@/store/chat-store";
import { useProfileStore } from "@/store/profile-store";
import { cn } from "@/lib/cn";

// ===== Typing carousel state machine (v0.13.2 PSI-2 P0 feature) =====
// Pattern: array di welcome variants -> typing letter-by-letter -> pause ->
// deleting letter-by-letter -> gap -> next variant.
// Timing originali (clean-room): 55ms typing, 36ms deleting, 1400ms pause,
// 250ms gap. Non sono i timing originali di openhuman-main (mai aperto per
// boundary GPL-3.0), sono calibrati ad hoc per registro italiano + UX SCO.
const TYPING_DELAY = 55;
const DELETING_DELAY = 36;
const PAUSE_AFTER_FULL = 1400;
const GAP_BETWEEN_VARIANTS = 250;

// 4 suggestion card branded compliance — 2x2 grid stile OpenHuman-inspired clean-room
// Identico contenuto del vecchio inline hero in ChatArea (back-compat invariato).
const SUGGESTIONS = [
  {
    icon: ShieldCheck,
    title: "Audit ISO 27001",
    description: "Checklist Annex A per cliente sanitario",
    prompt:
      "Prepara una checklist audit ISO 27001:2022 Annex A per cliente sanitario, includendo i controlli A.5–A.18.",
    accent: "text-sco-blue",
    iconBg: "bg-sco-blue/10",
  },
  {
    icon: ScanSearch,
    title: "Gap analysis NIS 2",
    description: "D.Lgs. 138/2024 art. per art. per fornitore PA",
    prompt:
      "Esegui una gap analysis del D.Lgs. 138/2024 per un fornitore ICT verso PA, articolo per articolo.",
    accent: "text-sco-navy dark:text-sco-text-dark",
    iconBg: "bg-sco-navy/10 dark:bg-sco-text-dark/10",
  },
  {
    icon: HeartPulse,
    title: "Procedura sanitaria",
    description: "ISO 9001:2015 cartelle cliniche IRCCS",
    prompt:
      "Redigi una procedura SGQ ISO 9001:2015 per gestione cartelle cliniche in IRCCS, sezione 7 e 8.",
    accent: "text-sco-amber",
    iconBg: "bg-sco-amber/10",
  },
  {
    icon: AlertTriangle,
    title: "Risk assessment cloud",
    description: "ISO 27005:2022 matrice probabilità × impatto",
    prompt:
      "Conduci un risk assessment ISO 27005:2022 su infrastruttura cloud Azure, con matrice probabilità × impatto.",
    accent: "text-red-500",
    iconBg: "bg-red-500/10",
  },
];

// Variants stagger per griglia 4 card
const gridVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      delayChildren: 0.65,
      staggerChildren: 0.08,
    },
  },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.16, 1, 0.3, 1],
    },
  },
};

// Variants stagger tagline (3 parole "Privato. Tuo. Italiano.")
const taglineContainerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      delayChildren: 1.1,
      staggerChildren: 0.15,
    },
  },
};

const taglineWordVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] },
  },
};

const TAGLINE_WORDS = ["Privato.", "Tuo.", "Italiano."];

// Reduced-motion detector hook — cooperare con prefers-reduced-motion
function usePrefersReducedMotion(): boolean {
  const [prefersReduced, setPrefersReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReduced(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return prefersReduced;
}

export function WelcomeScreen() {
  const sendMessage = useChatStore((s) => s.sendMessage);
  const profileNome = useProfileStore((s) => s.nome);
  const prefersReducedMotion = usePrefersReducedMotion();

  // Nome utente o fallback. Capitalize primo carattere se profile.nome ha contenuto.
  const displayName = useMemo(() => {
    const trimmed = (profileNome ?? "").trim();
    if (!trimmed) return "consulente";
    // Solo prima parola (es. "Antonio Silvestro" -> "Antonio")
    return trimmed.split(/\s+/)[0];
  }, [profileNome]);

  // Welcome variants — array di stringhe italiane parametrizzate sul nome.
  // useMemo cosi cambia solo quando displayName cambia.
  const welcomeVariants = useMemo<string[]>(
    () => [
      `Bentornato, ${displayName}`,
      `Vediamo le compliance, ${displayName}`,
      "Tempo di focus",
    ],
    [displayName],
  );

  // ===== Typing carousel state machine =====
  // currentVariantIdx: indice array welcomeVariants attualmente in scena.
  // displayText: testo visibile (sub-string del variant corrente).
  // phase: 'typing' | 'pausing' | 'deleting' | 'gap'.
  const [currentVariantIdx, setCurrentVariantIdx] = useState(0);
  const [displayText, setDisplayText] = useState("");
  const [phase, setPhase] = useState<"typing" | "pausing" | "deleting" | "gap">(
    "typing",
  );
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    // Reduced-motion fallback: mostra solo la 1° variante full, niente carousel.
    if (prefersReducedMotion) {
      setDisplayText(welcomeVariants[0]);
      setPhase("pausing");
      return;
    }

    const currentVariant = welcomeVariants[currentVariantIdx];
    let delay = TYPING_DELAY;

    if (phase === "typing") {
      if (displayText.length < currentVariant.length) {
        delay = TYPING_DELAY;
        timeoutRef.current = window.setTimeout(() => {
          setDisplayText(currentVariant.slice(0, displayText.length + 1));
        }, delay);
      } else {
        // Raggiunto full text -> pausa
        setPhase("pausing");
      }
    } else if (phase === "pausing") {
      delay = PAUSE_AFTER_FULL;
      timeoutRef.current = window.setTimeout(() => {
        setPhase("deleting");
      }, delay);
    } else if (phase === "deleting") {
      if (displayText.length > 0) {
        delay = DELETING_DELAY;
        timeoutRef.current = window.setTimeout(() => {
          setDisplayText(displayText.slice(0, -1));
        }, delay);
      } else {
        // Variant svuotato -> gap -> prossima variante
        setPhase("gap");
      }
    } else if (phase === "gap") {
      delay = GAP_BETWEEN_VARIANTS;
      timeoutRef.current = window.setTimeout(() => {
        setCurrentVariantIdx((idx) => (idx + 1) % welcomeVariants.length);
        setPhase("typing");
      }, delay);
    }

    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, [
    displayText,
    phase,
    currentVariantIdx,
    welcomeVariants,
    prefersReducedMotion,
  ]);

  return (
    <div className="flex h-full flex-col items-center justify-center overflow-y-auto px-6 py-12">
      <div className="flex w-full max-w-3xl flex-col items-center text-center">
        {/* Logo SCO con entrance scale-in + glow pulse continuo */}
        <motion.div
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{
            duration: 0.7,
            ease: [0.16, 1, 0.3, 1],
            delay: 0.05,
          }}
          className="mb-6"
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-sco-navy via-sco-blue to-sco-amber shadow-glow-lg animate-glow-pulse">
            <span className="text-2xl font-bold text-white">S</span>
          </div>
        </motion.div>

        {/* v0.13.2 PSI-2: Typing welcome carousel */}
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          aria-live="polite"
          aria-label={welcomeVariants[currentVariantIdx]}
          className="font-display text-3xl font-semibold tracking-tight text-sco-text dark:text-sco-text-dark md:text-4xl min-h-[2.5rem] md:min-h-[3rem]"
        >
          <span>{displayText}</span>
          {!prefersReducedMotion && (
            <motion.span
              aria-hidden="true"
              animate={{ opacity: [1, 1, 0, 0] }}
              transition={{ duration: 1.0, repeat: Infinity, ease: "linear" }}
              className="ml-0.5 inline-block text-sco-blue"
            >
              |
            </motion.span>
          )}
        </motion.h1>

        {/* Sottotitolo fade-up con delay (visible dopo il titolo) */}
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.5,
            ease: [0.16, 1, 0.3, 1],
            delay: 0.55,
          }}
          className="mt-3 max-w-xl text-sm leading-relaxed text-sco-muted-foreground md:text-base"
        >
          Scrivi una domanda nel campo qui sotto, oppure scegli un punto di
          partenza dalle quattro card. Posso aiutarti con audit, procedure,
          gap analysis e risk assessment.
        </motion.p>

        {/* 4 card quick action — 2x2 grid stagger entrance + hover shine */}
        <motion.div
          variants={gridVariants}
          initial="hidden"
          animate="visible"
          className="mt-10 grid w-full grid-cols-1 gap-3 md:grid-cols-2"
        >
          {SUGGESTIONS.map((s) => {
            const Icon = s.icon;
            return (
              <motion.button
                key={s.title}
                variants={cardVariants}
                type="button"
                onClick={() => sendMessage(s.prompt)}
                whileHover={{
                  y: -3,
                  transition: { duration: 0.2, ease: "easeOut" },
                }}
                whileTap={{ scale: 0.97, transition: { duration: 0.1 } }}
                className="group relative flex items-start gap-3 overflow-hidden rounded-xl border border-sco-border bg-sco-surface-elevated p-4 text-left shadow-subtle transition-shadow duration-200 hover:border-sco-blue/60 hover:shadow-float"
              >
                {/* Shine effect overlay sweeping left→right on hover */}
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/12 to-transparent transition-transform duration-700 ease-out group-hover:translate-x-full"
                />

                <div
                  className={cn(
                    "relative flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-transform duration-200 group-hover:scale-105",
                    s.iconBg,
                  )}
                >
                  <Icon size={20} className={s.accent} />
                </div>
                <div className="relative flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-sco-text dark:text-sco-text-dark">
                      {s.title}
                    </span>
                    <ArrowUpRight
                      size={14}
                      className="shrink-0 text-sco-muted-foreground/0 transition-all duration-200 group-hover:text-sco-blue group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                    />
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-sco-muted-foreground">
                    {s.description}
                  </p>
                </div>
              </motion.button>
            );
          })}
        </motion.div>

        {/* Tagline footer "Privato. Tuo. Italiano." con stagger per parola */}
        <motion.div
          variants={taglineContainerVariants}
          initial="hidden"
          animate="visible"
          className="mt-12 flex items-center gap-2 text-xs italic text-sco-muted-foreground/70"
          aria-label="Privato. Tuo. Italiano."
        >
          {TAGLINE_WORDS.map((word) => (
            <motion.span
              key={word}
              variants={taglineWordVariants}
              aria-hidden="true"
            >
              {word}
            </motion.span>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
