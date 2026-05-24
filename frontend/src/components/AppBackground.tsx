// SCO Compliance OS — AppBackground wrapper canvas WebGL MeshGradient
//
// Componente "drop-in" per il root layout di App.tsx.
// Posizionato fixed inset-0 z-0 opacity-10 pointer-events-none — non disturba
// leggibilità ma aggiunge depth visivo premium stile Stripe.com.
//
// Fallback strategy:
// 1. Try WebGL2 via initMeshGradient() — se PASS, RAF loop attivo
// 2. Se WebGL2 fail (WebView2 vecchie, GPU acceleration disabled),
//    initMeshGradient ritorna null e si mostra un fallback CSS
//    radial-gradient statico con stessi colori
//
// L'overhead runtime è minimo: shader fragment 4 blob + clear, ~0.3-0.5ms
// per frame su iGPU integrata, quindi sicuro anche su hardware modesto.

import { useEffect, useRef, useState } from "react";

import {
  initMeshGradient,
  SCO_DEFAULT_COLORS,
  SCO_DARK_COLORS,
  type MeshGradientHandle,
} from "@/lib/meshGradient";
import { useThemeStore } from "@/store/theme-store";

interface AppBackgroundProps {
  /** Opacity finale del canvas (default 0.10 — non disturba leggibilità) */
  opacity?: number;
  /** Disabilita completamente (es. per debug perf o utente che preferisce no-anim) */
  disabled?: boolean;
}

export function AppBackground({
  opacity = 0.1,
  disabled = false,
}: AppBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const handleRef = useRef<MeshGradientHandle | null>(null);
  const [webglFailed, setWebglFailed] = useState(false);

  const theme = useThemeStore((s) => s.theme);

  // Reactive resolution dell'effettiva preferenza tema (light/dark/system)
  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  useEffect(() => {
    if (disabled) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const colors = isDark ? SCO_DARK_COLORS : SCO_DEFAULT_COLORS;

    const handle = initMeshGradient(canvas, {
      colors,
      speed: 0.0005,
      intensity: 0.9,
    });

    if (handle) {
      handleRef.current = handle;
    } else {
      setWebglFailed(true);
    }

    return () => {
      handleRef.current?.destroy();
      handleRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disabled]);

  // Update colors on theme change (senza re-init contesto)
  useEffect(() => {
    if (!handleRef.current) return;
    const colors = isDark ? SCO_DARK_COLORS : SCO_DEFAULT_COLORS;
    handleRef.current.updateColors(colors);
  }, [isDark]);

  if (disabled) return null;

  // Fallback CSS radial-gradient se WebGL2 fail
  if (webglFailed) {
    return (
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          opacity,
          background: isDark
            ? `radial-gradient(at 20% 30%, rgba(48, 46, 92, 1) 0%, transparent 50%),
               radial-gradient(at 80% 20%, rgba(0, 80, 124, 1) 0%, transparent 55%),
               radial-gradient(at 30% 80%, rgba(184, 111, 16, 1) 0%, transparent 60%),
               radial-gradient(at 80% 80%, rgba(85, 80, 153, 1) 0%, transparent 50%),
               #0a0a14`
            : `radial-gradient(at 20% 30%, rgba(48, 46, 92, 1) 0%, transparent 50%),
               radial-gradient(at 80% 20%, rgba(0, 116, 180, 1) 0%, transparent 55%),
               radial-gradient(at 30% 80%, rgba(255, 167, 39, 1) 0%, transparent 60%),
               radial-gradient(at 80% 80%, rgba(155, 138, 251, 1) 0%, transparent 50%),
               #ffffff`,
        }}
      />
    );
  }

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0 h-full w-full"
      style={{ opacity }}
    />
  );
}
