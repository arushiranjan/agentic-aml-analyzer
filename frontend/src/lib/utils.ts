import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merges Tailwind classes, resolving conflicts (last one wins) — the standard shadcn/ui helper. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Formats a number as a compact currency string, e.g. 1234567 -> "$1.23M". */
export function formatCurrency(value: number, currency = "$"): string {
  if (Math.abs(value) >= 1_000_000) return `${currency}${(value / 1_000_000).toFixed(2)}M`;
  if (Math.abs(value) >= 1_000) return `${currency}${(value / 1_000).toFixed(1)}K`;
  return `${currency}${value.toFixed(2)}`;
}

/** Formats a 0-1 or 0-100 score as a percentage string. */
export function formatPercent(value: number, alreadyPercent = false): string {
  const pct = alreadyPercent ? value : value * 100;
  return `${pct.toFixed(1)}%`;
}

/** Formats an ISO timestamp into a short, readable local string. */
export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

/** Title-cases a snake_case rule name for display, e.g. "high_velocity" -> "High Velocity". */
export function titleCase(value: string): string {
  return value
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
