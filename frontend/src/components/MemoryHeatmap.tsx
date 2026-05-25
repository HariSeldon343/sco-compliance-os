// SCO Compliance OS — Memory Heatmap GitHub-style (SVG pure, no lib) v0.13.2 PSI-2
//
// Visualizza l'attivita` di ingestione memory tree negli ultimi N giorni
// (default 240, ovvero 8 mesi × 30 giorni). Griglia week-column con
// domenica come prima riga (col[0] = Sunday).
//
// 5 intensity level (palette SCO blue):
//   - Level 0: rgba(255,255,255,0.04) (no activity)
//   - Level 1: rgba(0,116,180,0.20) (low)
//   - Level 2: rgba(0,116,180,0.40) (medium-low)
//   - Level 3: rgba(0,116,180,0.60) (medium-high)
//   - Level 4: rgba(0,116,180,0.85) (high)
//
// Pattern openhuman-inspired clean-room (NO copia codice GPL-3.0 da
// openhuman-main). L'idea della heatmap GitHub-style e` ben nota dal 2013
// (GitHub contribution graph), implementazione originale a partire da dati
// raw del backend SCO.
//
// Accessibility:
//   - role="img" + aria-label sintetico
//   - <title> SVG per tooltip nativo screen reader
//   - tooltip hover popover via <foreignObject> + setState (no lib)

import { useCallback, useMemo, useState } from "react";

import { ApiError } from "@/api/client";
import { cn } from "@/lib/cn";

export interface ActivityPoint {
  date: string; // ISO YYYY-MM-DD
  count: number;
}

export interface ActivityResponse {
  days: number;
  total: number;
  points: ActivityPoint[];
}

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:7800";

export async function fetchMemoryActivity(
  days: number = 240,
): Promise<ActivityResponse> {
  const res = await fetch(`${BACKEND_URL}/api/memory/activity?days=${days}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(
      res.status,
      "memory_activity_error",
      `HTTP ${res.status} ${body}`,
    );
  }
  return (await res.json()) as ActivityResponse;
}

// ----- Date utility (pure, no dep) -----

/** Format date as YYYY-MM-DD (local timezone). */
function isoDay(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Italian short month name (gen, feb, mar, ...). */
const MONTH_LABELS_IT = [
  "gen",
  "feb",
  "mar",
  "apr",
  "mag",
  "giu",
  "lug",
  "ago",
  "set",
  "ott",
  "nov",
  "dic",
];

const DAY_LABELS_IT_SHORT = ["dom", "lun", "mar", "mer", "gio", "ven", "sab"];

// ----- Component -----

interface MemoryHeatmapProps {
  data: ActivityPoint[];
  days?: number; // window length in days (default 240)
  className?: string;
}

interface Cell {
  date: string;
  count: number;
  level: 0 | 1 | 2 | 3 | 4;
  weekIdx: number; // column 0..N
  dayIdx: number; // row 0..6 (0 = Sunday)
  monthIdx: number; // mese del giorno (0..11)
}

/**
 * GitHub-style contribution heatmap renderizzata in SVG puro.
 *
 * Dati input: array di punti (date, count) dal backend
 * /api/memory/activity?days=N. I giorni mancanti vengono interpolati come
 * count=0 (level 0). La griglia parte dalla domenica della settimana che
 * contiene oggi-(N-1) e termina con oggi.
 */
export function MemoryHeatmap({
  data,
  days = 240,
  className,
}: MemoryHeatmapProps) {
  const [hoverCell, setHoverCell] = useState<Cell | null>(null);

  // Indicizza dati input per lookup O(1)
  const dataMap = useMemo(() => {
    const m = new Map<string, number>();
    for (const p of data) m.set(p.date, p.count);
    return m;
  }, [data]);

  // Calcola min/max per mapping intensity → level
  const maxCount = useMemo(() => {
    let max = 0;
    for (const p of data) if (p.count > max) max = p.count;
    return max;
  }, [data]);

  /** Map count -> level 0..4 (quartile-like) */
  const levelOf = useCallback(
    (count: number): 0 | 1 | 2 | 3 | 4 => {
      if (count === 0) return 0;
      if (maxCount === 0) return 0;
      const ratio = count / maxCount;
      if (ratio <= 0.25) return 1;
      if (ratio <= 0.5) return 2;
      if (ratio <= 0.75) return 3;
      return 4;
    },
    [maxCount],
  );

  // Costruisci griglia cells
  const { cells, weeks, monthMarkers } = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const start = new Date(today);
    start.setDate(start.getDate() - (days - 1));

    // Allinea inizio a domenica (col 0 = Sunday). Se start cade su altro giorno,
    // rewind alla domenica precedente cosi la griglia inizia sempre da una colonna piena.
    const startDow = start.getDay(); // 0=Sunday..6=Saturday
    const gridStart = new Date(start);
    gridStart.setDate(gridStart.getDate() - startDow);

    const cellsOut: Cell[] = [];
    const markers: { weekIdx: number; label: string }[] = [];
    let lastMonth = -1;
    let weekIdx = 0;
    const cursor = new Date(gridStart);

    while (cursor <= today) {
      const dow = cursor.getDay(); // 0..6
      if (dow === 0 && cursor.getMonth() !== lastMonth) {
        // Nuovo mese inizia su questa colonna -> aggiungi marker
        markers.push({
          weekIdx,
          label: MONTH_LABELS_IT[cursor.getMonth()],
        });
        lastMonth = cursor.getMonth();
      }
      const iso = isoDay(cursor);
      const count = dataMap.get(iso) ?? 0;
      cellsOut.push({
        date: iso,
        count,
        level: levelOf(count),
        weekIdx,
        dayIdx: dow,
        monthIdx: cursor.getMonth(),
      });
      cursor.setDate(cursor.getDate() + 1);
      if (dow === 6) weekIdx++;
    }

    const totalWeeks = weekIdx + (cellsOut.length > 0 ? 1 : 0);
    return { cells: cellsOut, weeks: totalWeeks, monthMarkers: markers };
  }, [days, dataMap, levelOf]);

  // SVG geometry
  const CELL = 11;
  const GAP = 3;
  const STRIDE = CELL + GAP;
  const LEFT_LABELS_W = 22;
  const TOP_LABELS_H = 16;
  const svgWidth = LEFT_LABELS_W + weeks * STRIDE;
  const svgHeight = TOP_LABELS_H + 7 * STRIDE;

  const formatDateIt = (iso: string): string => {
    const [y, m, d] = iso.split("-").map(Number);
    const date = new Date(y, m - 1, d);
    return `${d} ${MONTH_LABELS_IT[date.getMonth()]} ${y}`;
  };

  return (
    <div className={cn("relative", className)}>
      <svg
        role="img"
        aria-label={`Memory Heatmap: ${data.length} giorni con attivita negli ultimi ${days} giorni`}
        width={svgWidth}
        height={svgHeight}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="block"
      >
        {/* Month labels (top row) */}
        {monthMarkers.map((m) => (
          <text
            key={`${m.weekIdx}-${m.label}`}
            x={LEFT_LABELS_W + m.weekIdx * STRIDE}
            y={11}
            fontSize={9}
            fill="currentColor"
            opacity={0.6}
            className="select-none"
          >
            {m.label}
          </text>
        ))}

        {/* Day-of-week labels (left col): lun, mer, ven only (compact) */}
        {[1, 3, 5].map((dayIdx) => (
          <text
            key={`dow-${dayIdx}`}
            x={0}
            y={TOP_LABELS_H + dayIdx * STRIDE + CELL - 2}
            fontSize={9}
            fill="currentColor"
            opacity={0.6}
            className="select-none"
          >
            {DAY_LABELS_IT_SHORT[dayIdx]}
          </text>
        ))}

        {/* Cells */}
        {cells.map((c) => {
          const x = LEFT_LABELS_W + c.weekIdx * STRIDE;
          const y = TOP_LABELS_H + c.dayIdx * STRIDE;
          const fill = LEVEL_COLORS[c.level];
          return (
            <rect
              key={c.date}
              x={x}
              y={y}
              width={CELL}
              height={CELL}
              rx={2.5}
              fill={fill}
              stroke="rgba(255,255,255,0.04)"
              strokeWidth={0.5}
              onMouseEnter={() => setHoverCell(c)}
              onMouseLeave={() => setHoverCell(null)}
              className="cursor-default transition-opacity duration-100 hover:opacity-80"
            >
              <title>
                {`${formatDateIt(c.date)} — ${c.count} ${c.count === 1 ? "chunk" : "chunks"}`}
              </title>
            </rect>
          );
        })}
      </svg>

      {/* Hover popover (state-driven, no portal) */}
      {hoverCell && (
        <div
          className="pointer-events-none absolute z-10 rounded-md border border-sco-border bg-sco-surface-elevated px-2.5 py-1.5 text-xs shadow-md"
          style={{
            left: LEFT_LABELS_W + hoverCell.weekIdx * STRIDE + CELL / 2,
            top: TOP_LABELS_H + hoverCell.dayIdx * STRIDE - 36,
            transform: "translateX(-50%)",
          }}
        >
          <div className="font-medium text-sco-text dark:text-sco-text-dark">
            {formatDateIt(hoverCell.date)}
          </div>
          <div className="text-sco-muted-foreground">
            {hoverCell.count === 0
              ? "Nessuna attivita`"
              : `${hoverCell.count} ${hoverCell.count === 1 ? "chunk" : "chunks"} ingeriti`}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="mt-2 flex items-center justify-end gap-2 text-[10px] text-sco-muted-foreground">
        <span>Meno</span>
        {([0, 1, 2, 3, 4] as const).map((lvl) => (
          <span
            key={lvl}
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ background: LEVEL_COLORS[lvl] }}
            aria-hidden="true"
          />
        ))}
        <span>Piu`</span>
      </div>
    </div>
  );
}

// Palette SCO blue intensity levels (clean-room originali, NO copia openhuman)
const LEVEL_COLORS: Record<0 | 1 | 2 | 3 | 4, string> = {
  0: "rgba(255, 255, 255, 0.04)",
  1: "rgba(0, 116, 180, 0.20)",
  2: "rgba(0, 116, 180, 0.40)",
  3: "rgba(0, 116, 180, 0.60)",
  4: "rgba(0, 116, 180, 0.85)",
};
