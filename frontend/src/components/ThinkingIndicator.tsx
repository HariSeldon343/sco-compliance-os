// SCO Compliance OS — ThinkingIndicator dots wave animato (v0.13.0 PSI upgrade)
//
// Premium upgrade rispetto a v0.12.x:
//   - 3 dot con wave animation (translateY -4px ciclica con stagger 160ms)
//   - Opacity stagger 0.3 → 1 → 0.3 ciclico per effetto "shimmer"
//   - Palette navy + blue + amber preservata (brand SCO core)
//   - Container con subtle backdrop blur per glass morphism
//   - Testo "Sto pensando..." con shimmer effect

import { motion } from "framer-motion";

export function ThinkingIndicator() {
  // Wave animation: ogni dot ha lo stesso pattern Y ma con delay diverso.
  // L'effetto cumulativo e' un'onda che scorre da sinistra a destra ciclica.
  const dotTransition = {
    duration: 1.4,
    repeat: Infinity,
    ease: "easeInOut" as const,
  };

  return (
    <div
      className="flex items-center gap-2 rounded-2xl border border-sco-border bg-sco-surface-elevated/85 px-4 py-3 shadow-soft backdrop-blur-sm"
      role="status"
      aria-live="polite"
      aria-label="L'agente sta elaborando la risposta"
    >
      {/* Dot navy — wave delay 0ms */}
      <motion.span
        animate={{ y: [0, -4, 0], opacity: [0.45, 1, 0.45] }}
        transition={{ ...dotTransition, delay: 0 }}
        className="h-2 w-2 rounded-full bg-sco-navy"
        aria-hidden="true"
      />
      {/* Dot blue — wave delay 160ms */}
      <motion.span
        animate={{ y: [0, -4, 0], opacity: [0.45, 1, 0.45] }}
        transition={{ ...dotTransition, delay: 0.16 }}
        className="h-2 w-2 rounded-full bg-sco-blue"
        aria-hidden="true"
      />
      {/* Dot amber — wave delay 320ms */}
      <motion.span
        animate={{ y: [0, -4, 0], opacity: [0.45, 1, 0.45] }}
        transition={{ ...dotTransition, delay: 0.32 }}
        className="h-2 w-2 rounded-full bg-sco-amber"
        aria-hidden="true"
      />
      {/* Label con shimmer gradient sottile (left→right cyclic) */}
      <span className="relative ml-2 overflow-hidden text-xs italic text-sco-muted-foreground">
        <span>Sto pensando...</span>
        <span
          aria-hidden="true"
          className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/40 to-transparent"
          style={{ backgroundSize: "200% 100%" }}
        />
      </span>
    </div>
  );
}
