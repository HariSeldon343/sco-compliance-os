// SCO Compliance OS — Tabs component minimale stile shadcn/ui (no @radix-ui dep)
// Pattern: Context-based state, accessible (aria-selected/aria-controls), keyboard nav.
// Usato in SettingsScreen v2 (refactor v0.8.1) come tabbar orizzontale top.

import { createContext, useContext, useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

interface TabsContextValue {
  value: string;
  setValue: (v: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext(): TabsContextValue {
  const ctx = useContext(TabsContext);
  if (!ctx) {
    throw new Error(
      "Tabs.Trigger/Content devono essere usati dentro <Tabs>",
    );
  }
  return ctx;
}

interface TabsProps {
  defaultValue: string;
  value?: string;
  onValueChange?: (v: string) => void;
  className?: string;
  children: ReactNode;
}

export function Tabs({
  defaultValue,
  value: controlledValue,
  onValueChange,
  className,
  children,
}: TabsProps) {
  const [internalValue, setInternalValue] = useState(defaultValue);
  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : internalValue;

  const setValue = (v: string) => {
    if (!isControlled) setInternalValue(v);
    onValueChange?.(v);
  };

  return (
    <TabsContext.Provider value={{ value, setValue }}>
      <div className={cn("flex flex-col gap-4", className)}>{children}</div>
    </TabsContext.Provider>
  );
}

interface TabsListProps {
  className?: string;
  children: ReactNode;
}

export function TabsList({ className, children }: TabsListProps) {
  return (
    <div
      role="tablist"
      className={cn(
        "inline-flex h-auto flex-wrap items-center justify-start gap-1 rounded-lg border border-sco-border bg-sco-surface-elevated p-1",
        className,
      )}
    >
      {children}
    </div>
  );
}

interface TabsTriggerProps {
  value: string;
  className?: string;
  children: ReactNode;
  disabled?: boolean;
}

export function TabsTrigger({
  value,
  className,
  children,
  disabled,
}: TabsTriggerProps) {
  const { value: activeValue, setValue } = useTabsContext();
  const isActive = activeValue === value;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      aria-controls={`tab-content-${value}`}
      id={`tab-trigger-${value}`}
      data-state={isActive ? "active" : "inactive"}
      disabled={disabled}
      onClick={() => setValue(value)}
      className={cn(
        "inline-flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sco-blue/50",
        "disabled:pointer-events-none disabled:opacity-50",
        isActive
          ? "bg-sco-blue text-white shadow-sm"
          : "text-sco-muted-foreground hover:bg-sco-muted hover:text-sco-text dark:hover:text-sco-text-dark",
        className,
      )}
    >
      {children}
    </button>
  );
}

interface TabsContentProps {
  value: string;
  className?: string;
  children: ReactNode;
}

export function TabsContent({
  value,
  className,
  children,
}: TabsContentProps) {
  const { value: activeValue } = useTabsContext();
  if (activeValue !== value) return null;

  return (
    <div
      role="tabpanel"
      id={`tab-content-${value}`}
      aria-labelledby={`tab-trigger-${value}`}
      className={cn("focus-visible:outline-none", className)}
      tabIndex={0}
    >
      {children}
    </div>
  );
}
