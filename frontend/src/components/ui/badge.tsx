import { clsx } from "clsx";

const colorMap: Record<string, string> = {
  ok: "bg-emerald/15 text-emerald border-emerald/30",
  good: "bg-emerald/15 text-emerald border-emerald/30",
  online: "bg-emerald/15 text-emerald border-emerald/30",
  running: "bg-cyan/15 text-cyan border-cyan/30",
  active: "bg-cyan/15 text-cyan border-cyan/30",
  mock: "bg-cyan/15 text-cyan border-cyan/30",
  idle: "bg-muted/15 text-muted border-muted/30",
  monitoring: "bg-muted/15 text-muted border-muted/30",
  warning: "bg-amber/15 text-amber border-amber/30",
  attention: "bg-amber/15 text-amber border-amber/30",
  cycling: "bg-amber/15 text-amber border-amber/30",
  critical: "bg-critical/15 text-critical border-critical/30",
  fail: "bg-critical/15 text-critical border-critical/30",
};

export function Badge({ status, label }: { status: string; label?: string }) {
  const cls = colorMap[status.toLowerCase()] ?? "bg-muted/15 text-muted border-muted/30";
  return (
    <span className={clsx("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium", cls)}>
      {label ?? status}
    </span>
  );
}
