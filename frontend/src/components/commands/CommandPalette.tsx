// SCO Compliance OS — Command Palette (⌘K) Linear/Raycast-style
//
// Clean-room implementation:
// - Radix Dialog (MIT) per modal + backdrop blur + focus trap + accessibility
// - cmdk (MIT) per search/filter + keyboard navigation + grouping
// - Design tokens v0.5.0 (token CSS scoped --cmd-*) per coerenza con brand SCO
// - Hotkey Ctrl+K (Win/Linux) + Cmd+K (Mac) gestita da listener globale
//
// Pattern SCO single-source-of-truth: i comandi vivono in useCommandRegistry
// (Zustand store globale), questo componente li renderizza in tempo reale.
// Niente copy code OpenHuman GPL. Architettura derivata dalla doc cmdk + Radix.

import { useEffect, useState, useMemo } from "react";
import { Command } from "cmdk";
import * as Dialog from "@radix-ui/react-dialog";
import { Search, Hash } from "lucide-react";

import {
  useCommandRegistry,
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  type CommandCategory,
  type CommandDef,
} from "./CommandRegistry";
import { cn } from "@/lib/cn";

interface CommandPaletteProps {
  /** Forza apertura controllata (opzionale) */
  open?: boolean;
  /** Callback open change (per controllo esterno) */
  onOpenChange?: (open: boolean) => void;
}

export function CommandPalette({
  open: controlledOpen,
  onOpenChange,
}: CommandPaletteProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [search, setSearch] = useState("");

  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : internalOpen;
  const setOpen = (next: boolean) => {
    if (!isControlled) setInternalOpen(next);
    onOpenChange?.(next);
  };

  const commands = useCommandRegistry((s) => s.commands);

  // Hotkey listener: Ctrl+K (Win/Linux) + Cmd+K (Mac)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Toggle apertura con Cmd/Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!open);
      }
      // Chiudi con Escape (Radix Dialog lo gestisce, ma aggiunto qui come safety)
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Reset search quando si chiude
  useEffect(() => {
    if (!open) {
      setSearch("");
    }
  }, [open]);

  // Raggruppa comandi per categoria (in render time per reattività)
  const groupedCommands = useMemo<Record<CommandCategory, CommandDef[]>>(() => {
    const grouped: Record<CommandCategory, CommandDef[]> = {
      navigation: [],
      actions: [],
      search: [],
      vault: [],
      skills: [],
      settings: [],
    };
    for (const cmd of Object.values(commands)) {
      grouped[cmd.category].push(cmd);
    }
    return grouped;
  }, [commands]);

  const close = () => setOpen(false);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            "fixed inset-0 z-50",
            "bg-[color:var(--cmd-overlay-bg)]",
            "backdrop-blur-sm",
            "data-[state=open]:animate-fade-in data-[state=closed]:opacity-0",
          )}
          style={
            {
              "--cmd-overlay-bg": "rgba(10, 10, 20, 0.55)",
            } as React.CSSProperties
          }
        />
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-[20%] z-50 -translate-x-1/2",
            "w-[640px] max-w-[92vw]",
            "rounded-2xl border border-[color:var(--cmd-border)]",
            "bg-[color:var(--cmd-surface)] text-[color:var(--cmd-foreground)]",
            "shadow-cmd-palette",
            "outline-none",
            "data-[state=open]:animate-scale-in",
            "overflow-hidden",
          )}
          style={
            {
              "--cmd-surface": "var(--sco-color-surface-elevated)",
              "--cmd-foreground": "var(--sco-color-text-primary)",
              "--cmd-accent": "var(--sco-color-secondary)",
              "--cmd-border": "var(--sco-color-border)",
              "--cmd-muted": "var(--sco-color-text-tertiary)",
              "--cmd-hover": "var(--sco-color-surface)",
              "--cmd-selected": "var(--sco-color-secondary-500)",
            } as React.CSSProperties
          }
          aria-describedby={undefined}
        >
          <Dialog.Title className="sr-only">
            Command Palette
          </Dialog.Title>

          <Command
            shouldFilter={true}
            loop
            className="flex flex-col"
            label="Cerca comando"
          >
            {/* Search input row */}
            <div className="flex items-center gap-3 border-b border-[color:var(--cmd-border)] px-4 py-3">
              <Search
                size={16}
                className="shrink-0 text-[color:var(--cmd-muted)]"
                aria-hidden="true"
              />
              <Command.Input
                value={search}
                onValueChange={setSearch}
                placeholder="Cerca comando, conversazione, vault..."
                className={cn(
                  "flex-1 bg-transparent text-sm outline-none",
                  "text-[color:var(--cmd-foreground)] placeholder:text-[color:var(--cmd-muted)]",
                )}
              />
              <kbd
                className={cn(
                  "hidden md:inline-flex items-center justify-center",
                  "rounded-md border border-[color:var(--cmd-border)]",
                  "bg-[color:var(--cmd-hover)] px-2 py-0.5",
                  "text-[10px] font-mono text-[color:var(--cmd-muted)]",
                )}
                aria-hidden="true"
              >
                ESC
              </kbd>
            </div>

            {/* Command list */}
            <Command.List
              className={cn(
                "max-h-[420px] overflow-y-auto",
                "p-2",
              )}
            >
              <Command.Empty
                className={cn(
                  "py-10 text-center text-sm",
                  "text-[color:var(--cmd-muted)]",
                )}
              >
                Nessun comando trovato.
              </Command.Empty>

              {CATEGORY_ORDER.map((cat) => {
                const items = groupedCommands[cat];
                if (items.length === 0) return null;

                return (
                  <Command.Group
                    key={cat}
                    heading={CATEGORY_LABELS[cat]}
                    className={cn(
                      "[&_[cmdk-group-heading]]:px-2",
                      "[&_[cmdk-group-heading]]:py-1.5",
                      "[&_[cmdk-group-heading]]:text-[10px]",
                      "[&_[cmdk-group-heading]]:font-semibold",
                      "[&_[cmdk-group-heading]]:uppercase",
                      "[&_[cmdk-group-heading]]:tracking-wider",
                      "[&_[cmdk-group-heading]]:text-[color:var(--cmd-muted)]",
                      "mb-1",
                    )}
                  >
                    {items.map((cmd) => {
                      const Icon = cmd.icon ?? Hash;
                      return (
                        <Command.Item
                          key={cmd.id}
                          value={`${cmd.label} ${cmd.keywords?.join(" ") ?? ""}`}
                          onSelect={() => {
                            void cmd.action(close);
                          }}
                          className={cn(
                            "flex items-center gap-3 rounded-lg px-2.5 py-2",
                            "cursor-pointer select-none",
                            "transition-colors duration-100",
                            "text-sm",
                            // cmdk applica aria-selected="true" sull'item highlighted
                            "data-[selected=true]:bg-[color:var(--cmd-selected)]",
                            "data-[selected=true]:text-white",
                            "hover:bg-[color:var(--cmd-hover)]",
                          )}
                        >
                          <Icon
                            size={15}
                            className="shrink-0 opacity-80"
                            aria-hidden="true"
                          />
                          <span className="flex-1 truncate">{cmd.label}</span>
                          {cmd.hint && (
                            <span
                              className={cn(
                                "shrink-0 text-[11px]",
                                "text-[color:var(--cmd-muted)]",
                                "data-[selected=true]:text-white/80",
                              )}
                            >
                              {cmd.hint}
                            </span>
                          )}
                        </Command.Item>
                      );
                    })}
                  </Command.Group>
                );
              })}
            </Command.List>

            {/* Footer hint */}
            <div
              className={cn(
                "flex items-center justify-between gap-3 border-t border-[color:var(--cmd-border)]",
                "bg-[color:var(--cmd-hover)] px-4 py-2",
                "text-[11px] text-[color:var(--cmd-muted)]",
              )}
            >
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1.5">
                  <kbd className="inline-flex items-center rounded border border-[color:var(--cmd-border)] bg-[color:var(--cmd-surface)] px-1.5 py-0.5 font-mono text-[10px]">
                    ↑↓
                  </kbd>
                  Naviga
                </span>
                <span className="flex items-center gap-1.5">
                  <kbd className="inline-flex items-center rounded border border-[color:var(--cmd-border)] bg-[color:var(--cmd-surface)] px-1.5 py-0.5 font-mono text-[10px]">
                    ↵
                  </kbd>
                  Esegui
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <kbd className="inline-flex items-center rounded border border-[color:var(--cmd-border)] bg-[color:var(--cmd-surface)] px-1.5 py-0.5 font-mono text-[10px]">
                  ⌘K
                </kbd>
                <span>per aprire</span>
              </div>
            </div>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
