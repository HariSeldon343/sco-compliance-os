// SCO Compliance OS — Settings Tab "Aspetto"
// v0.8.1: card Tema (Chiaro/Scuro/Sistema preview live) + card Layout (Sidebar/
// Bottom tab) + card Mascot (toggle + 3 variant preview) + card Font size.

import { Palette, LayoutPanelLeft, Navigation, Smile, Type } from "lucide-react";

import { useThemeStore, type Theme } from "@/store/theme-store";
import { useLayoutStore, type LayoutMode } from "@/store/layout-store";
import { useMascotStore, type MascotVariant } from "@/store/mascot-store";
import {
  useVaultSettingsStore,
  type FontSize,
} from "@/store/vault-settings-store";
import { MascotCharacter } from "@/components/mascot/MascotCharacter";
import { cn } from "@/lib/cn";

export function AppearanceTab() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const layoutMode = useLayoutStore((s) => s.mode);
  const setLayoutMode = useLayoutStore((s) => s.setMode);
  const mascotEnabled = useMascotStore((s) => s.enabled);
  const mascotVariant = useMascotStore((s) => s.variant);
  const setMascotEnabled = useMascotStore((s) => s.setEnabled);
  const setMascotVariant = useMascotStore((s) => s.setVariant);
  const fontSize = useVaultSettingsStore((s) => s.fontSize);
  const setFontSize = useVaultSettingsStore((s) => s.setFontSize);

  return (
    <div className="space-y-6">
      {/* Tema */}
      <Card icon={Palette} title="Tema">
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Scegli l'aspetto chiaro, scuro o lascia che segua le preferenze del
          sistema operativo. Il cambio e` immediato.
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {(["light", "dark", "system"] as Theme[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTheme(t)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border p-4 transition-all",
                theme === t
                  ? "border-sco-blue bg-sco-blue/10 ring-1 ring-sco-blue"
                  : "border-sco-border hover:border-sco-blue/60",
              )}
            >
              {/* Preview live: mini bg + 2 bubble */}
              <div
                className={cn(
                  "h-16 w-full rounded-md border",
                  t === "light"
                    ? "border-gray-300 bg-white"
                    : t === "dark"
                      ? "border-gray-700 bg-[#0f0f1e]"
                      : "border-sco-border bg-gradient-to-r from-white to-[#0f0f1e]",
                )}
              >
                <div className="flex h-full flex-col justify-center gap-1 px-2">
                  <div
                    className={cn(
                      "h-2 w-3/4 rounded",
                      t === "light" ? "bg-sco-blue/40" : "bg-sco-blue/80",
                    )}
                  />
                  <div
                    className={cn(
                      "h-2 w-1/2 rounded",
                      t === "light" ? "bg-gray-300" : "bg-gray-500",
                    )}
                  />
                </div>
              </div>
              <span className="text-sm font-medium capitalize">
                {t === "light"
                  ? "Chiaro"
                  : t === "dark"
                    ? "Scuro"
                    : "Sistema"}
              </span>
            </button>
          ))}
        </div>
      </Card>

      {/* Layout */}
      <Card icon={Navigation} title="Layout di navigazione">
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Sidebar laterale piu` ricca con lista conversazioni, oppure barra
          inferiore pill che lascia piu` spazio alla chat.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          {(
            [
              {
                value: "sidebar",
                label: "Sidebar laterale",
                desc: "Pannello sinistro 280px con conversazioni e navigazione.",
                icon: LayoutPanelLeft,
              },
              {
                value: "bottom-tab",
                label: "Barra inferiore",
                desc: "Pill flottante in basso, piu` spazio per la chat.",
                icon: Navigation,
              },
            ] as Array<{
              value: LayoutMode;
              label: string;
              desc: string;
              icon: typeof LayoutPanelLeft;
            }>
          ).map((opt) => {
            const Icon = opt.icon;
            const active = layoutMode === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setLayoutMode(opt.value)}
                className={cn(
                  "flex flex-col gap-2 rounded-lg border p-4 text-left transition-all",
                  active
                    ? "border-sco-blue bg-sco-blue/10 ring-1 ring-sco-blue"
                    : "border-sco-border hover:border-sco-blue/60",
                )}
              >
                <div className="flex items-center gap-2">
                  <Icon
                    size={16}
                    className={cn(
                      active ? "text-sco-blue" : "text-sco-muted-foreground",
                    )}
                  />
                  <span className="text-sm font-medium">{opt.label}</span>
                </div>
                <p className="text-xs text-sco-muted-foreground">{opt.desc}</p>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Mascot */}
      <Card icon={Smile} title="Mascot">
        <label className="mb-3 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={mascotEnabled}
            onChange={(e) => setMascotEnabled(e.target.checked)}
            className="h-4 w-4 accent-sco-blue"
          />
          Abilita mascot animato (opt-in, default disattivato)
        </label>
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Il mascot e` una piccola illustrazione in alto a destra che reagisce
          a quello che fa l'agente: si muove durante il pensiero, sorride in
          ascolto, "parla" quando legge la risposta. Decorativo. Puoi spegnerlo
          quando vuoi.
        </p>
        {mascotEnabled && (
          <div>
            <p className="mb-2 text-xs font-medium text-sco-muted-foreground">
              Variante palette
            </p>
            <div className="grid gap-3 sm:grid-cols-3">
              {(
                [
                  {
                    value: "blue",
                    label: "SCO blu",
                    desc: "Antenna blu, palette brand core.",
                  },
                  {
                    value: "amber",
                    label: "SCO ambra",
                    desc: "Antenna ambra, accent caldo.",
                  },
                  {
                    value: "minimal",
                    label: "Minimal",
                    desc: "Antenna bianca, look sobrio.",
                  },
                ] as Array<{
                  value: MascotVariant;
                  label: string;
                  desc: string;
                }>
              ).map((opt) => {
                const active = mascotVariant === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setMascotVariant(opt.value)}
                    className={cn(
                      "flex flex-col items-center gap-2 rounded-lg border p-3 text-center transition-all",
                      active
                        ? "border-sco-blue bg-sco-blue/10 ring-1 ring-sco-blue"
                        : "border-sco-border hover:border-sco-blue/60",
                    )}
                  >
                    <MascotCharacter
                      state="idle"
                      variant={opt.value}
                      size={64}
                    />
                    <span className="text-xs font-medium">{opt.label}</span>
                    <span className="text-[11px] text-sco-muted-foreground">
                      {opt.desc}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </Card>

      {/* Font size */}
      <Card icon={Type} title="Dimensione testo">
        <p className="mb-3 text-xs text-sco-muted-foreground">
          Scala globale del testo nell'interfaccia. Utile per migliorare la
          leggibilita`.
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {(
            [
              { value: "small", label: "Piccolo", sample: "Aa" },
              { value: "medium", label: "Medio", sample: "Aa" },
              { value: "large", label: "Grande", sample: "Aa" },
            ] as Array<{ value: FontSize; label: string; sample: string }>
          ).map((opt) => {
            const active = fontSize === opt.value;
            const sizeClass =
              opt.value === "small"
                ? "text-sm"
                : opt.value === "medium"
                  ? "text-base"
                  : "text-lg";
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setFontSize(opt.value)}
                className={cn(
                  "flex flex-col items-center gap-2 rounded-lg border p-3 transition-all",
                  active
                    ? "border-sco-blue bg-sco-blue/10 ring-1 ring-sco-blue"
                    : "border-sco-border hover:border-sco-blue/60",
                )}
              >
                <span className={cn("font-semibold", sizeClass)}>
                  {opt.sample}
                </span>
                <span className="text-xs font-medium">{opt.label}</span>
              </button>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

interface CardProps {
  icon: typeof Palette;
  title: string;
  children: React.ReactNode;
}

function Card({ icon: Icon, title, children }: CardProps) {
  return (
    <section className="rounded-xl border border-sco-border bg-sco-surface-elevated p-6">
      <div className="mb-4 flex items-center gap-2">
        <Icon size={18} className="text-sco-blue" />
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      {children}
    </section>
  );
}
