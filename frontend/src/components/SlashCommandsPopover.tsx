import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";

import { cn } from "@/lib/cn";
import type { SkillSummary } from "@/types/api";

type ScopeBadge = "user" | "project" | "legacy";

const SCOPE_BADGE_STYLE: Record<ScopeBadge, string> = {
  user: "bg-sco-blue/10 text-sco-blue",
  project: "bg-purple-500/10 text-purple-600 dark:text-purple-300",
  legacy: "bg-gray-500/10 text-gray-600 dark:text-gray-300",
};

export interface SlashCommandsPopoverHandle {
  highlightNext(): void;
  highlightPrevious(): void;
  selectCurrent(): SkillSummary | null;
  resetSelection(): void;
}

export interface SlashCommandsPopoverProps {
  open: boolean;
  query: string;
  skills: SkillSummary[];
  onSelect: (skill: SkillSummary) => void;
  onClose: () => void;
  anchorRef: RefObject<HTMLTextAreaElement | null>;
}

export const SlashCommandsPopover = forwardRef<
  SlashCommandsPopoverHandle,
  SlashCommandsPopoverProps
>(function SlashCommandsPopover(
  { open, query, skills, onSelect, onClose, anchorRef },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [popoverWidth, setPopoverWidth] = useState<number>();

  const filteredSkills = useMemo(() => {
    if (!skills.length) return [];
    const trimmed = query.trim().toLowerCase();
    const candidates = trimmed
      ? skills.filter((skill) => {
          const name = skill.name.toLowerCase();
          const description = skill.description.toLowerCase();
          return name.includes(trimmed) || description.includes(trimmed);
        })
      : skills;
    return candidates.slice(0, 8);
  }, [query, skills]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query, filteredSkills.length]);

  useEffect(() => {
    if (!open) return;

    const anchor = anchorRef.current;
    if (!anchor) return;

    const updateWidth = () => {
      const rect = anchor.getBoundingClientRect();
      setPopoverWidth(rect.width);
    };

    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => {
      window.removeEventListener("resize", updateWidth);
    };
  }, [open, anchorRef]);

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: Event) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (containerRef.current?.contains(target)) return;
      if (anchorRef.current?.contains(target)) return;
      onClose();
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    window.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
      window.removeEventListener("keydown", handleEscape);
    };
  }, [open, onClose, anchorRef]);

  useImperativeHandle(
    ref,
    () => ({
      highlightNext() {
        if (!filteredSkills.length) return;
        setSelectedIndex((prev) => (prev + 1) % filteredSkills.length);
      },
      highlightPrevious() {
        if (!filteredSkills.length) return;
        setSelectedIndex((prev) =>
          (prev - 1 + filteredSkills.length) % filteredSkills.length,
        );
      },
      selectCurrent() {
        const current = filteredSkills[selectedIndex] ?? null;
        if (current) {
          onSelect(current);
        }
        return current ?? null;
      },
      resetSelection() {
        setSelectedIndex(0);
      },
    }),
    [filteredSkills, onSelect, selectedIndex],
  );

  if (!open || !anchorRef.current) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      className="absolute bottom-full left-0 z-50 mb-2 w-full rounded-lg border border-sco-border bg-sco-surface-elevated shadow-lg"
      style={{ width: popoverWidth ? `${popoverWidth}px` : undefined }}
      role="listbox"
      aria-label="Slash commands"
    >
      {filteredSkills.length === 0 ? (
        <div className="px-3 py-2 text-xs text-sco-muted-foreground">
          Nessuna skill trovata.
        </div>
      ) : (
        <div className="max-h-72 overflow-y-auto py-1">
          {filteredSkills.map((skill, index) => {
            const isActive = index === selectedIndex;
            return (
              <button
                key={skill.name}
                type="button"
                className={cn(
                  "w-full px-3 py-2 text-left text-sm transition-colors",
                  isActive
                    ? "bg-sco-blue/10 text-sco-text"
                    : "hover:bg-sco-muted",
                )}
                onMouseEnter={() => setSelectedIndex(index)}
                onMouseDown={(event) => {
                  event.preventDefault();
                  onSelect(skill);
                }}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono text-xs font-semibold">
                    /{skill.name}
                  </span>
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                      SCOPE_BADGE_STYLE[skill.scope],
                    )}
                  >
                    {skill.scope}
                  </span>
                </div>
                <p className="mt-1 text-[11px] leading-snug text-sco-muted-foreground line-clamp-2">
                  {skill.description}
                </p>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
});
