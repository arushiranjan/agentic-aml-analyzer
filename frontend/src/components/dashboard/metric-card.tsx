"use client";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";

interface MetricCardProps {
  label: string;
  value: string;
  unit?: string;
  icon: LucideIcon;
  accent?: "emerald" | "amber" | "cyan" | "critical";
  sublabel?: string;
}

const accentText: Record<string, string> = {
  emerald: "text-emerald",
  amber: "text-amber",
  cyan: "text-cyan",
  critical: "text-critical",
};

export function MetricCard({ label, value, unit, icon: Icon, accent = "cyan", sublabel }: MetricCardProps) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <Card className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-wide text-muted">{label}</span>
          <Icon className={`h-4 w-4 ${accentText[accent]}`} />
        </div>
        <div className="mono text-2xl font-semibold text-white">
          {value}
          {unit && <span className="ml-1 text-sm text-muted">{unit}</span>}
        </div>
        {sublabel && <span className="text-xs text-muted">{sublabel}</span>}
      </Card>
    </motion.div>
  );
}
