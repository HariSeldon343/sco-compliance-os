// SCO Compliance OS — indicatore "sto pensando" animato (3 dot pulsanti palette navy)
export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 rounded-2xl border border-sco-border bg-sco-surface-elevated px-4 py-3">
      <span
        className="h-2 w-2 animate-pulse-soft rounded-full bg-sco-navy"
        style={{ animationDelay: "0ms" }}
      />
      <span
        className="h-2 w-2 animate-pulse-soft rounded-full bg-sco-blue"
        style={{ animationDelay: "200ms" }}
      />
      <span
        className="h-2 w-2 animate-pulse-soft rounded-full bg-sco-amber"
        style={{ animationDelay: "400ms" }}
      />
      <span className="ml-2 text-xs italic text-sco-muted-foreground">
        Sto pensando...
      </span>
    </div>
  );
}
