// SCO Compliance OS — Tailwind 4 config (companion JS-side al @theme inline in index.css)
//
// In Tailwind 4 il source-of-truth dei design tokens vive nelle CSS variables
// registrate da @theme inline in src/index.css + src/styles/design-tokens.css.
// Questo file resta come "compat layer" per:
//   - content scan path (Tailwind 4 in dev mode legge ancora questa lista)
//   - darkMode strategy (class-based su <html>)
//   - keyframes/animation NON gestite via @theme (fallback)
//   - alias semantici extra ai brand SCO che usano var() risolto a runtime
//
// I nuovi token (palette neutral/slate/sage/coral, font display/mono/serif,
// radius xs→5xl, shadow glow/cmd-palette, animation fade-up/scale-in/shimmer,
// ecc.) sono dichiarati in @theme inline di index.css e vengono esposti come
// utility class Tailwind senza ridondanza qui.
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Brand SCO — alias semantici (back-compat con componenti pre-esistenti).
        // Risolto a runtime via CSS var --sco-* (vedi @theme inline in index.css).
        "sco-navy": "var(--color-primary-500)",
        "sco-blue": "var(--color-secondary-500)",
        "sco-amber": "var(--color-amber-500)",
        "sco-bg": "var(--color-background)",
        "sco-bg-dark": "var(--color-background)",
        "sco-text": "var(--color-text-primary)",
        "sco-text-dark": "var(--color-text-primary)",
        "sco-surface": "var(--color-surface)",
        "sco-surface-elevated": "var(--color-surface-elevated)",
        "sco-border": "var(--color-border)",
        "sco-muted": "var(--color-surface)",
        "sco-muted-foreground": "var(--color-text-tertiary)",
      },
      maxWidth: {
        chat: "48rem",
        prose: "65ch",
        "prose-wide": "75ch",
      },
      // Keyframes fallback (sono già in @theme inline; qui per compat IDE/JIT)
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in": {
          from: { opacity: "0", transform: "translateX(-16px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        "slide-right": {
          from: { opacity: "0", transform: "translateX(16px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 20px -5px rgba(0, 116, 180, 0.25)" },
          "50%": { boxShadow: "0 0 40px -5px rgba(0, 116, 180, 0.55)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        ticker: {
          from: { transform: "translateX(0)" },
          to: { transform: "translateX(-50%)" },
        },
      },
      animation: {
        "pulse-soft": "pulse-soft 1.4s ease-in-out infinite",
        "fade-in": "fade-in 320ms cubic-bezier(0.4, 0, 0.2, 1) both",
        "fade-up": "fade-up 420ms cubic-bezier(0.16, 1, 0.3, 1) both",
        "slide-in": "slide-in 360ms cubic-bezier(0.25, 1, 0.5, 1) both",
        "slide-right": "slide-right 360ms cubic-bezier(0.25, 1, 0.5, 1) both",
        "scale-in": "scale-in 240ms cubic-bezier(0.16, 1, 0.3, 1) both",
        shimmer: "shimmer 2.4s linear infinite",
        "glow-pulse": "glow-pulse 2.8s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        float: "float 4.2s ease-in-out infinite",
        ticker: "ticker 24s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
