// SCO Compliance OS — Vite 6 configuration con Tauri 2 dev server + Tailwind 4 plugin
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

// Porta default Tauri (https://v2.tauri.app/start/frontend/vite/)
const DEV_PORT = 1420;

// https://vitejs.dev/config/
export default defineConfig(async () => ({
  plugins: [react(), tailwindcss()],

  // Prevent vite from obscuring rust errors quando lanciato via `tauri dev`
  clearScreen: false,

  // Tauri requisiti: server fisso su porta nota
  server: {
    port: DEV_PORT,
    strictPort: true,
    host: "127.0.0.1",
    watch: {
      // Evita di sorvegliare il target Rust
      ignored: ["**/src-tauri/**"],
    },
  },

  // Tauri legge solo variabili con prefisso VITE_
  envPrefix: ["VITE_", "TAURI_ENV_"],

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },

  build: {
    // Tauri usa Chromium 100+ su Win, Safari 14+ su Mac
    target:
      process.env.TAURI_ENV_PLATFORM === "windows" ? "chrome105" : "safari14",
    // Genera sourcemap solo in debug
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
    minify: !process.env.TAURI_ENV_DEBUG ? "esbuild" : false,
    outDir: "dist",
    emptyOutDir: true,
  },
}));
