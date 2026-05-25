// SCO Compliance OS — Mascot 2D SVG procedurale clean-room.
//
// Volto round minimalista coerente con brand SCO (navy + blue + amber). Composizione:
//   - Body round (cerchio 200x200 viewBox, fill navy SCO #302e5c)
//   - 2 occhi tondi bianchi con pupilla scura, posizionati sopra l'asse
//   - Bocca animata (5 visemes per lipsync TTS futuro: chiusa, aperta piccola,
//     aperta grande, sorriso, sorpresa)
//   - 1 antenna SCO blu/amber con sfera apicale (rotate slow su 'thinking',
//     pulse dot rosso al posto della sfera apicale su 'listening')
//
// 5 stati visuali:
//   - idle        → float subtle ±5px su asse Y + blink occhi ogni ~4s
//   - listening   → antenna con dot rosso pulsante + occhi più aperti
//   - thinking    → antenna in rotazione lenta 360° + bocca closed line
//   - speaking    → viseme cycle 5 shapes ogni 200ms (libero, lipsync TTS futuro)
//   - celebrating → jump up + sparkles attorno al body + bocca smile (v0.13.0 PSI)
//
// Animation CSS-only via Tailwind keyframes già esistenti (animate-float,
// animate-pulse-soft, animate-glow-pulse) + 4 keyframes locali inline (style jsx-like)
// per blink occhi, rotate antenna, viseme cycle, listening pulse.
//
// Clean-room legal: tutti i path SVG sono scritti ex-novo. NON è una copia di
// OpenHuman YellowMascot, BondAI mascot, o altri asset terzi. Composizione
// algoritmica con coordinate calcolate manualmente per geometria minimalista.
//
// Pattern Conv. 48 single source of truth backend: lo stato del widget mascot
// vive in mascot-store Zustand (NON in optimistic UI). MascotCharacter è puro
// rendering: legge prop `state` + `variant` e disegna. Niente side effect.

import { type FC } from "react";

import type { MascotState, MascotVariant } from "@/store/mascot-store";
import { cn } from "@/lib/cn";

interface MascotCharacterProps {
  /** Stato visuale corrente. */
  state: MascotState;
  /** Variante palette. */
  variant?: MascotVariant;
  /** Override dimensione (default 200x200). */
  size?: number;
  /** ClassName aggiuntivo. */
  className?: string;
}

// Palette per variante. Brand SCO preserved (navy + blue + amber + bianco).
// minimal = navy + bianco senza accent caldo, per setup molto sobrio.
const VARIANT_PALETTE: Record<
  MascotVariant,
  { body: string; antennaStem: string; antennaBall: string; accent: string }
> = {
  blue: {
    body: "#302e5c",
    antennaStem: "#0074b4",
    antennaBall: "#0074b4",
    accent: "#0074b4",
  },
  amber: {
    body: "#302e5c",
    antennaStem: "#ffa727",
    antennaBall: "#ffa727",
    accent: "#ffa727",
  },
  minimal: {
    body: "#302e5c",
    antennaStem: "#ffffff",
    antennaBall: "#ffffff",
    accent: "#ffffff",
  },
};

// Viseme paths: 5 forme bocca calcolate sul viewBox 200x200 centrato in (100, 130).
// closed       = linea orizzontale lieve curva (chiusa)
// open-small   = ellisse piccola verticale (vocale /e/, /i/)
// open-large   = ellisse grande verticale (vocale /a/, /o/)
// smile        = arco aperto verso l'alto (felicità)
// surprise     = cerchio piccolo (vocale /u/ stretta o reazione)
type Viseme = "closed" | "open-small" | "open-large" | "smile" | "surprise";

function visemePath(v: Viseme): string {
  switch (v) {
    case "closed":
      // Linea curva sottile, leggermente sorridente di default
      return "M 80 130 Q 100 134 120 130";
    case "open-small":
      // Ellisse piccola 16x10
      return "M 92 130 Q 100 124 108 130 Q 100 138 92 130 Z";
    case "open-large":
      // Ellisse grande 26x18
      return "M 87 130 Q 100 118 113 130 Q 100 144 87 130 Z";
    case "smile":
      // Arco aperto verso l'alto, ampio
      return "M 78 128 Q 100 142 122 128";
    case "surprise":
      // Cerchio piccolo (r=7) centrato in (100, 132)
      return "M 100 125 A 7 7 0 1 0 100 139 A 7 7 0 1 0 100 125 Z";
  }
}

// Stylesheet locale con keyframes mascot-specifici. Inline come <style> nel
// rendering del componente per garantire portabilità senza dipendere da
// modifiche al tailwind.config.ts (le keyframes mascot-* sono fuori scope
// design-tokens premium).
const mascotStyles = `
  /* Blink eyes: chiude ogni ~4s con compressione verticale rapida */
  @keyframes mascot-blink {
    0%, 92%, 100% { transform: scaleY(1); }
    94%, 98% { transform: scaleY(0.1); }
  }
  /* Rotate antenna 360° lento (thinking) */
  @keyframes mascot-antenna-rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  /* Pulse listening dot: dimensione + opacità */
  @keyframes mascot-listening-pulse {
    0%, 100% { transform: scale(1); opacity: 0.7; }
    50% { transform: scale(1.5); opacity: 1; }
  }
  /* Viseme cycle: scala il gruppo bocca per dare "stacchi" tra le forme */
  @keyframes mascot-viseme-tick {
    0%, 100% { transform: scaleY(1); }
    50% { transform: scaleY(1.05); }
  }
  /* Idle float subtle ±5px (override animate-float di Tailwind che è ±6px) */
  @keyframes mascot-idle-float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-5px); }
  }
  /* Celebrating jump: salto -30px + atterraggio (anticipo + overshoot) v0.13.0 PSI */
  @keyframes mascot-celebrate-jump {
    0% { transform: translateY(0) scaleY(1); }
    15% { transform: translateY(4px) scaleY(0.92); }
    40% { transform: translateY(-30px) scaleY(1.06); }
    65% { transform: translateY(-10px) scaleY(0.98); }
    85% { transform: translateY(2px) scaleY(0.96); }
    100% { transform: translateY(0) scaleY(1); }
  }
  /* Celebrating sparkle: scintille pulsanti attorno al body */
  @keyframes mascot-sparkle {
    0%, 100% { opacity: 0; transform: scale(0.3) rotate(0deg); }
    20% { opacity: 0.9; transform: scale(1.2) rotate(45deg); }
    60% { opacity: 0.7; transform: scale(1) rotate(180deg); }
    80% { opacity: 0.4; transform: scale(0.8) rotate(270deg); }
  }

  .mascot-svg { transform-origin: center; transform-box: fill-box; }
  .mascot-svg.mascot-idle { animation: mascot-idle-float 3.6s ease-in-out infinite; }
  .mascot-svg.mascot-celebrate { animation: mascot-celebrate-jump 1.4s cubic-bezier(0.22, 1, 0.36, 1) infinite; }
  .mascot-eye-group { transform-origin: center; transform-box: fill-box; }
  .mascot-eye-group.mascot-blink { animation: mascot-blink 4s ease-in-out infinite; }
  .mascot-antenna-stem-group { transform-origin: 100px 65px; }
  .mascot-antenna-stem-group.mascot-spin { animation: mascot-antenna-rotate 4s linear infinite; }
  .mascot-listening-dot { transform-origin: center; transform-box: fill-box; animation: mascot-listening-pulse 1.2s ease-in-out infinite; }
  .mascot-mouth-group { transform-origin: center; transform-box: fill-box; animation: mascot-viseme-tick 0.2s ease-in-out infinite; }
  .mascot-sparkle-particle { transform-origin: center; transform-box: fill-box; animation: mascot-sparkle 1.6s ease-in-out infinite; }
`;

export const MascotCharacter: FC<MascotCharacterProps> = ({
  state,
  variant = "blue",
  size = 200,
  className,
}) => {
  const palette = VARIANT_PALETTE[variant];

  // Viseme selezionato per stato statico (non in speaking).
  // closed       = default per idle/thinking
  // smile        = listening (più aperto, occhi più aperti, viseme cordiale)
  // smile        = celebrating (espressione felice durante salto) v0.13.0 PSI
  // surprise / cycle vivono in speaking via keyframe steps (vedi sotto)
  const staticViseme: Viseme =
    state === "listening" || state === "celebrating"
      ? "smile"
      : state === "thinking"
        ? "closed"
        : "closed";

  // Occhi: dimensione baseline 8 (raggio bianco). Listening + celebrating allargano a 9.5.
  const eyeRadius = state === "listening" || state === "celebrating" ? 9.5 : 8;
  const pupilRadius =
    state === "listening" || state === "celebrating" ? 4.5 : 3.5;

  // Speaking → viseme cycle via animation-name dinamica (5 step ~200ms ciascuno).
  // Implementato come keyframes generate-on-the-fly nello <style> embedded.
  const speakingKeyframes =
    state === "speaking"
      ? `
        @keyframes mascot-speaking-cycle {
          0%   { d: path("${visemePath("closed")}"); }
          20%  { d: path("${visemePath("open-small")}"); }
          40%  { d: path("${visemePath("open-large")}"); }
          60%  { d: path("${visemePath("smile")}"); }
          80%  { d: path("${visemePath("surprise")}"); }
          100% { d: path("${visemePath("closed")}"); }
        }
        .mascot-mouth-speaking {
          animation: mascot-speaking-cycle 1s steps(5, end) infinite;
        }
      `
      : "";

  return (
    <div
      className={cn("inline-block select-none", className)}
      aria-hidden="true"
      role="presentation"
      data-mascot-state={state}
      data-mascot-variant={variant}
    >
      <style>{mascotStyles + speakingKeyframes}</style>

      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 200 200"
        width={size}
        height={size}
        className={cn(
          "mascot-svg",
          state === "idle" && "mascot-idle",
          state === "celebrating" && "mascot-celebrate",
        )}
      >
        {/* Subtle drop shadow filter (no library) */}
        <defs>
          <filter id="mascot-soft-shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="3" />
            <feOffset dx="0" dy="2" result="offsetblur" />
            <feComponentTransfer>
              <feFuncA type="linear" slope="0.35" />
            </feComponentTransfer>
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Gradient sottile per dare profondità al body navy */}
          <radialGradient id="mascot-body-grad" cx="0.5" cy="0.4" r="0.65">
            <stop offset="0%" stopColor={palette.body} stopOpacity="1" />
            <stop offset="100%" stopColor="#1a1832" stopOpacity="1" />
          </radialGradient>
        </defs>

        {/* Antenna (stem + ball/dot). Origin rotation in (100, 65) = base antenna sul body */}
        <g
          className={cn(
            "mascot-antenna-stem-group",
            state === "thinking" && "mascot-spin",
          )}
        >
          {/* Stem antenna: linea curva dal top body verso alto */}
          <path
            d="M 100 75 Q 100 55 100 38"
            stroke={palette.antennaStem}
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
          />
          {/* Ball apicale: cerchio sfera apicale (idle/thinking/speaking/celebrating) */}
          {state !== "listening" && (
            <circle
              cx="100"
              cy="34"
              r="6"
              fill={palette.antennaBall}
              className={
                state === "idle" || state === "celebrating"
                  ? "animate-pulse-soft"
                  : ""
              }
            />
          )}
          {/* Listening: dot rosso pulsante al posto della sfera */}
          {state === "listening" && (
            <circle
              cx="100"
              cy="34"
              r="7"
              fill="#ef4444"
              className="mascot-listening-dot"
            />
          )}
        </g>

        {/* Body (cerchio principale 200x200 viewBox, r=68 centrato in 100,110) */}
        <circle
          cx="100"
          cy="110"
          r="68"
          fill="url(#mascot-body-grad)"
          stroke={palette.body}
          strokeWidth="1.5"
          filter="url(#mascot-soft-shadow)"
        />

        {/* Subtle highlight curvo top-left (depth) */}
        <ellipse
          cx="78"
          cy="78"
          rx="16"
          ry="8"
          fill="#ffffff"
          opacity="0.08"
          transform="rotate(-25 78 78)"
        />

        {/* Celebrating sparkles: 4 stelline 4-point ai vertici NE/NW/SE/SW del body,
            ciascuna con delay diverso per dare effetto pop scattering. v0.13.0 PSI */}
        {state === "celebrating" && (
          <g aria-hidden="true">
            {/* Stella NE (alto-destra) */}
            <path
              d="M 162 56 L 165 64 L 173 67 L 165 70 L 162 78 L 159 70 L 151 67 L 159 64 Z"
              fill={palette.accent}
              className="mascot-sparkle-particle"
              style={{ animationDelay: "0ms", transformOrigin: "162px 67px" }}
            />
            {/* Stella NW (alto-sinistra) */}
            <path
              d="M 38 64 L 41 71 L 48 74 L 41 77 L 38 84 L 35 77 L 28 74 L 35 71 Z"
              fill="#ffffff"
              className="mascot-sparkle-particle"
              style={{ animationDelay: "200ms", transformOrigin: "38px 74px" }}
            />
            {/* Stella SE (basso-destra) */}
            <path
              d="M 170 142 L 173 149 L 180 152 L 173 155 L 170 162 L 167 155 L 160 152 L 167 149 Z"
              fill={palette.accent}
              className="mascot-sparkle-particle"
              style={{ animationDelay: "400ms", transformOrigin: "170px 152px" }}
            />
            {/* Stella SW (basso-sinistra) */}
            <path
              d="M 30 150 L 33 157 L 40 160 L 33 163 L 30 170 L 27 163 L 20 160 L 27 157 Z"
              fill="#ffffff"
              className="mascot-sparkle-particle"
              style={{ animationDelay: "600ms", transformOrigin: "30px 160px" }}
            />
          </g>
        )}

        {/* Eye sx (gruppo) */}
        <g
          className={cn(
            "mascot-eye-group",
            state !== "listening" &&
              state !== "celebrating" &&
              "mascot-blink",
          )}
        >
          <circle cx="78" cy="100" r={eyeRadius} fill="#ffffff" />
          <circle cx="78" cy="100" r={pupilRadius} fill="#0a0916" />
          {/* Riflesso bianco sottile */}
          <circle cx="80" cy="98" r="1.2" fill="#ffffff" />
        </g>

        {/* Eye dx (gruppo) */}
        <g
          className={cn(
            "mascot-eye-group",
            state !== "listening" &&
              state !== "celebrating" &&
              "mascot-blink",
          )}
        >
          <circle cx="122" cy="100" r={eyeRadius} fill="#ffffff" />
          <circle cx="122" cy="100" r={pupilRadius} fill="#0a0916" />
          {/* Riflesso bianco sottile */}
          <circle cx="124" cy="98" r="1.2" fill="#ffffff" />
        </g>

        {/* Mouth — statico (idle/listening/thinking) oppure animato (speaking) */}
        {state === "speaking" ? (
          <g className="mascot-mouth-group">
            <path
              d={visemePath("closed")}
              stroke={palette.accent}
              strokeWidth="2.5"
              strokeLinecap="round"
              fill={palette.accent}
              fillOpacity="0.85"
              className="mascot-mouth-speaking"
            />
          </g>
        ) : (
          // I visemi statici correnti (closed / smile) sono solo stroke senza fill.
          // Quando lo set statico verrà esteso a forme "aperte", reintrodurre il
          // pattern fill condizionale qui.
          <path
            d={visemePath(staticViseme)}
            stroke={palette.accent}
            strokeWidth="2.5"
            strokeLinecap="round"
            fill="none"
          />
        )}

        {/* Cheeks subtle (solo amber + idle) per dare un tocco caldo */}
        {state === "idle" && variant === "amber" && (
          <>
            <ellipse cx="72" cy="120" rx="6" ry="3" fill="#ffa727" opacity="0.35" />
            <ellipse cx="128" cy="120" rx="6" ry="3" fill="#ffa727" opacity="0.35" />
          </>
        )}
      </svg>
    </div>
  );
};

MascotCharacter.displayName = "MascotCharacter";
