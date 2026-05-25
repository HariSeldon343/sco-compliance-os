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
      // v0.13.0 PSI: aggiunti shine + ripple + skeleton + sparkle + char-reveal
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
        // v0.13.0 PSI new keyframes
        "shine-sweep": {
          // Sweep gradient overlay sinistra→destra per hover effect su button/card
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        "ripple-tap": {
          // Ripple expansion + fade per tap/click microinteraction
          "0%": { transform: "scale(0)", opacity: "0.5" },
          "100%": { transform: "scale(2.5)", opacity: "0" },
        },
        "skeleton-pulse": {
          // Skeleton loader pulse (alternativa a shimmer per loading states)
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "0.7" },
        },
        sparkle: {
          // Sparkle rotation + scale + fade per success/celebration effects
          "0%, 100%": { opacity: "0", transform: "scale(0.3) rotate(0deg)" },
          "20%": { opacity: "0.9", transform: "scale(1.2) rotate(45deg)" },
          "60%": { opacity: "0.7", transform: "scale(1) rotate(180deg)" },
          "80%": { opacity: "0.4", transform: "scale(0.8) rotate(270deg)" },
        },
        "char-reveal": {
          // Char-by-char reveal letter del title hero (alternativa Framer Motion)
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-bounce": {
          // Scale bounce overshoot per success toast / celebrating microinteraction
          "0%": { transform: "scale(0.6)", opacity: "0" },
          "55%": { transform: "scale(1.08)", opacity: "1" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        "dot-wave": {
          // Wave per ThinkingIndicator dots (alternativa Framer Motion)
          "0%, 60%, 100%": { transform: "translateY(0)", opacity: "0.45" },
          "30%": { transform: "translateY(-4px)", opacity: "1" },
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
        // v0.13.0 PSI new animation utilities
        "shine-sweep": "shine-sweep 700ms cubic-bezier(0.16, 1, 0.3, 1)",
        "ripple-tap": "ripple-tap 600ms ease-out",
        "skeleton-pulse": "skeleton-pulse 1.6s ease-in-out infinite",
        sparkle: "sparkle 1.6s ease-in-out infinite",
        "char-reveal": "char-reveal 400ms cubic-bezier(0.16, 1, 0.3, 1) both",
        "scale-bounce":
          "scale-bounce 480ms cubic-bezier(0.34, 1.56, 0.64, 1) both",
        "dot-wave": "dot-wave 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
