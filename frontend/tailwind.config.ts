// SCO Compliance OS — Tailwind 4 config con palette brand SCO (navy/blue/amber)
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Palette brand SCO mappata a CSS variables (vedi src/index.css)
        "sco-navy": "var(--sco-navy)",
        "sco-blue": "var(--sco-blue)",
        "sco-amber": "var(--sco-amber)",
        "sco-bg": "var(--sco-bg)",
        "sco-bg-dark": "var(--sco-bg-dark)",
        "sco-text": "var(--sco-text)",
        "sco-text-dark": "var(--sco-text-dark)",
        // Grigi semantici
        "sco-surface": "var(--sco-surface)",
        "sco-surface-elevated": "var(--sco-surface-elevated)",
        "sco-border": "var(--sco-border)",
        "sco-muted": "var(--sco-muted)",
        "sco-muted-foreground": "var(--sco-muted-foreground)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "Source Code Pro",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      // Pattern Claude.ai-like: container max-width contenuto chat
      maxWidth: {
        chat: "48rem",
      },
      // Animazioni stub per ThinkingIndicator
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "pulse-soft": "pulse-soft 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
