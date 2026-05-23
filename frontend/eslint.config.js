// ESLint v9 flat config — sco-compliance-os frontend.
// Migrazione da legacy .eslintrc (carry-over W2-WIKI subagent) a flat config
// richiesta da eslint@^9.17.0.
//
// Pattern: minimo funzionante per typecheck-via-lint + react basics.
// Estensioni future (strict, hooks rules, jsx-a11y) on-demand quando l'utente
// richiede tightening del lint.

import js from "@eslint/js";
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";

export default [
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "src-tauri/target/**",
      "src-tauri/binaries/**",
      "*.config.js",
      "*.config.ts",
      "vite.config.ts",
      "tailwind.config.ts",
      "postcss.config.js",
    ],
  },
  js.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
      globals: {
        // Browser globals (Tauri WebView2 env)
        window: "readonly",
        document: "readonly",
        console: "readonly",
        fetch: "readonly",
        navigator: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        Promise: "readonly",
        AbortController: "readonly",
        AbortSignal: "readonly",
        crypto: "readonly",
        atob: "readonly",
        btoa: "readonly",
        TextEncoder: "readonly",
        TextDecoder: "readonly",
        Blob: "readonly",
        File: "readonly",
        FileReader: "readonly",
        FormData: "readonly",
        Headers: "readonly",
        Request: "readonly",
        Response: "readonly",
        EventSource: "readonly",
        WebSocket: "readonly",
        ReadableStream: "readonly",
        TransformStream: "readonly",
        // Node-flavored globals usati in alcuni script dev
        process: "readonly",
        __dirname: "readonly",
        __filename: "readonly",
        Buffer: "readonly",
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
      react: reactPlugin,
      "react-hooks": reactHooksPlugin,
    },
    settings: {
      react: { version: "detect" },
    },
    rules: {
      // Off the TypeScript-specific rules che richiederebbero typed linting
      // (project-aware), troppo costoso per CI base. Solo regole syntactic.
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": "off",
      "no-unused-vars": "off", // disabilitato in favore di @typescript-eslint variant
      "no-undef": "off", // delegato a TypeScript
      "react/react-in-jsx-scope": "off", // React 17+ JSX transform
      "react/prop-types": "off", // delegato a TypeScript
      "react/jsx-uses-react": "off",
      "react/jsx-uses-vars": "error",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
];
