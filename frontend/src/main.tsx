// SCO Compliance OS — entry point React 19 con StrictMode + Router + Toaster globale
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";

import App from "./App";
import { ChatLayout } from "./screens/ChatLayout";
import { SettingsScreen } from "./screens/SettingsScreen";
import { IntegrationsScreen } from "./screens/IntegrationsScreen";
import { VaultScreen } from "./screens/VaultScreen";
import { MemoryScreen } from "./screens/MemoryScreen";
import { WikiView } from "./components/WikiView";

import "./index.css";
import "highlight.js/styles/github-dark.css";

// Router: tutte le route vivono sotto <App /> che fornisce sidebar + header + outlet
const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <ChatLayout /> },
      { path: "settings", element: <SettingsScreen /> },
      { path: "integrations", element: <IntegrationsScreen /> },
      { path: "vault", element: <VaultScreen /> },
      { path: "memory", element: <MemoryScreen /> },
      // Wave 2 OpenHuman replica — Memory Tree gerarchico L0/L1/L2 navigabile
      { path: "wiki", element: <WikiView /> },
    ],
  },
]);

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Elemento root non trovato in index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <RouterProvider router={router} />
    <Toaster
      position="top-right"
      richColors
      closeButton
      toastOptions={{
        style: {
          fontFamily: "Inter, system-ui, sans-serif",
        },
      }}
    />
  </StrictMode>,
);
