// SCO Compliance OS — BottomTabBar pill floating (alternative layout)
//
// Clean-room implementation:
// - Floating bottom-center fixed con glass morphism background
// - 6 tab: Chat / Wiki / Vault / Memoria / Integrazioni / Impostazioni
// - SVG icon inline (no react-icons, mantieni bundle minimal)
// - Label hidden by default, expand on hover/active con animation
//   cubic-bezier(0.22, 1, 0.36, 1) 500ms (ease-bottom-tab token)
// - Active state con bg-primary + text-primary-fg
// - aria-label per accessibility + keyboard nav (tab + enter)
//
// Nessuna copy code OpenHuman. Pattern Spotify mini player + Linear toolbar.

import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { cn } from "@/lib/cn";

interface TabDef {
  to: string;
  label: string;
  /** SVG path body (24x24 viewbox) — Heroicons / Lucide-style stroke 1.5 */
  iconPath: React.ReactNode;
  /** Match esatto su pathname (utile per "/" che altrimenti matcherebbe tutto) */
  exact?: boolean;
}

// Icon paths inline (NO react-icons import per bundle minimal)
const TABS: TabDef[] = [
  {
    to: "/",
    label: "Chat",
    exact: true,
    iconPath: (
      <>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"
        />
      </>
    ),
  },
  {
    to: "/wiki",
    label: "Wiki",
    iconPath: (
      <>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 0 1-2.25 2.25M16.5 7.5V18a2.25 2.25 0 0 0 2.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875V18a2.25 2.25 0 0 0 2.25 2.25h13.5M6 7.5h3v3H6v-3Z"
        />
      </>
    ),
  },
  {
    to: "/vault",
    label: "Vault",
    iconPath: (
      <>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
        />
      </>
    ),
  },
  {
    to: "/memory",
    label: "Memoria",
    iconPath: (
      <>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
        />
      </>
    ),
  },
  {
    to: "/integrations",
    label: "Integrazioni",
    iconPath: (
      <>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"
        />
      </>
    ),
  },
  {
    to: "/settings",
    label: "Impostazioni",
    iconPath: (
      <>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
        />
      </>
    ),
  },
];

function isTabActive(currentPath: string, tab: TabDef): boolean {
  if (tab.exact) return currentPath === tab.to;
  return currentPath === tab.to || currentPath.startsWith(`${tab.to}/`);
}

export function BottomTabBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  return (
    <nav
      className={cn(
        "fixed bottom-4 left-1/2 z-40 -translate-x-1/2",
        "flex items-center gap-1",
        "rounded-full",
        "glass-strong",
        "px-2 py-1.5",
        "shadow-float",
      )}
      aria-label="Barra di navigazione principale"
    >
      {TABS.map((tab, idx) => {
        const isActive = isTabActive(location.pathname, tab);
        const isExpanded = isActive || hoveredIdx === idx;

        return (
          <button
            key={tab.to}
            type="button"
            onClick={() => navigate(tab.to)}
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
            onFocus={() => setHoveredIdx(idx)}
            onBlur={() => setHoveredIdx(null)}
            aria-label={tab.label}
            aria-current={isActive ? "page" : undefined}
            title={tab.label}
            className={cn(
              "group relative flex items-center",
              "rounded-full",
              "transition-[background-color,color,padding,width] duration-500",
              "ease-bottom-tab",
              "outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
              "focus-visible:ring-secondary-500 focus-visible:ring-offset-transparent",
              isActive
                ? "bg-secondary-500 text-white shadow-glow"
                : "text-text-tertiary hover:bg-surface hover:text-text-primary",
              isExpanded ? "px-3.5 py-2 gap-2" : "px-2.5 py-2 gap-0",
            )}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.6}
              stroke="currentColor"
              className="h-[18px] w-[18px] shrink-0"
              aria-hidden="true"
            >
              {tab.iconPath}
            </svg>
            <span
              className={cn(
                "overflow-hidden whitespace-nowrap text-[13px] font-medium",
                "transition-[max-width,opacity] duration-500 ease-bottom-tab",
                isExpanded ? "max-w-[120px] opacity-100" : "max-w-0 opacity-0",
              )}
            >
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
