// SCO Compliance OS — utility classnames merge (clsx + tailwind-merge)
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge classi Tailwind risolvendo conflitti (es. "p-2" + "p-4" → "p-4"). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
