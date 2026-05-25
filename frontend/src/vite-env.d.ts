// SCO Compliance OS — type declarations Vite env
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// v0.10.0: __APP_VERSION__ globale iniettato da vite.config.ts define{}
// dalla version di package.json. Conv. 47 single source of truth version.
declare const __APP_VERSION__: string;
