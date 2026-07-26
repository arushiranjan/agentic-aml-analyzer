"use client";
import { useEffect, useState, type ElementType } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download, Leaf, Thermometer, Zap } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { getComparisonExportUrl, getLatestComparison } from "@/lib/api";
import type { OptimizationComparison } from "@/types";

function pct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value > 0 ? "-" : "+"}${Math.abs(value).toFixed(1)}%`;
}

function SavingsCard({
  label,
  value,
  good,
  icon: Icon,
}: {
  label: string;
  value: string;
  good: boolean | null;
  icon: ElementType;
}) {
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-muted">{label}</span>
        <Icon className={`h-4 w-4 ${good === null ? "text-muted" : good ? "text-emerald" : "text-critical"}`} />
      </div>
      <div className={`mono text-2xl font-semibold ${good === null ? "text-white" : good ? "text-emerald" : "text-critical"}`}>
        {value}
      </div>
    </Card>
  );
}

export function SavingsPanel() {
  const [data, setData] = useState<OptimizationComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [none, setNone] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    setNone(false);
    try {
      const res = await getLatestComparison();
      setData(res);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load comparison";
      if (msg.includes("404")) {
        setNone(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const handler = () => load();
    window.addEventListener("ecoloop:ai-cycle-complete", handler);
    return () => window.removeEventListener("ecoloop:ai-cycle-complete", handler);
  }, []);

  if (loading) return <LoadingState label="Loading quantitative savings…" />;
  if (error) return <ErrorState message={error} />;
  if (none || !data) {
    return (
      <EmptyState label="No AI cycle has been run yet. Click 'Run AI Cycle' above to generate a baseline vs optimized comparison." />
    );
  }

  const { baseline, optimized, comparison } = data;

  const energyChartData = [
    { name: "Total", baseline: baseline.total_energy_kwh, optimized: optimized.total_energy_kwh },
    { name: "HVAC", baseline: baseline.hvac_energy_kwh, optimized: optimized.hvac_energy_kwh },
    { name: "Lighting", baseline: baseline.lighting_energy_kwh, optimized: optimized.lighting_energy_kwh },
  ];

  const tempChartData = [
    { name: "Avg Indoor Temp (°C)", baseline: baseline.avg_indoor_temp_c ?? 0, optimized: optimized.avg_indoor_temp_c ?? 0 },
  ];

  const comfortChartData = [
    { name: "PMV", baseline: baseline.comfort_pmv ?? 0, optimized: optimized.comfort_pmv ?? 0 },
    { name: "PPD (%)", baseline: baseline.comfort_ppd ?? 0, optimized: optimized.comfort_ppd ?? 0 },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white">Quantitative Savings</h2>
        <div className="flex gap-2">
          <a
            href={getComparisonExportUrl("json")}
            className="flex items-center gap-1.5 rounded-lg bg-white/5 px-3 py-1.5 text-xs text-muted transition hover:bg-white/10 hover:text-white"
          >
            <Download className="h-3.5 w-3.5" /> JSON
          </a>
          <a
            href={getComparisonExportUrl("csv")}
            className="flex items-center gap-1.5 rounded-lg bg-white/5 px-3 py-1.5 text-xs text-muted transition hover:bg-white/10 hover:text-white"
          >
            <Download className="h-3.5 w-3.5" /> CSV
          </a>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <SavingsCard label="Baseline Energy" value={`${baseline.total_energy_kwh} kWh`} good={null} icon={Zap} />
        <SavingsCard label="Optimized Energy" value={`${optimized.total_energy_kwh} kWh`} good={comparison.energy_saved_kwh > 0} icon={Zap} />
        <SavingsCard label="Energy Saved" value={`${comparison.energy_saved_kwh} kWh`} good={comparison.energy_saved_kwh > 0} icon={Zap} />
        <SavingsCard label="Energy Saved %" value={pct(comparison.energy_saved_percent)} good={(comparison.energy_saved_percent ?? 0) > 0} icon={Zap} />
        <SavingsCard label="HVAC Savings" value={pct(comparison.hvac_saved_percent)} good={(comparison.hvac_saved_percent ?? 0) > 0} icon={Thermometer} />
        <SavingsCard label="Carbon Reduction" value={pct(comparison.carbon_reduction_percent)} good={(comparison.carbon_reduction_percent ?? 0) > 0} icon={Leaf} />
        <Card className="flex flex-col gap-2 md:col-span-2">
          <span className="text-xs uppercase tracking-wide text-muted">Comfort Status</span>
          <div className="flex items-center gap-2">
            <Badge status={comparison.comfort_maintained ? "ok" : "critical"} label={comparison.comfort_maintained ? "Maintained" : "Violated"} />
            <span className="mono text-xs text-muted">
              Δtemp {comparison.avg_temp_diff_c ?? "—"}°C · ΔPMV {comparison.pmv_diff ?? "—"} · ΔPPD {comparison.ppd_diff ?? "—"}
            </span>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <h3 className="mb-3 text-sm font-medium text-white">Baseline vs Optimized Energy (kWh)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={energyChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94A3B8" }} />
              <Bar dataKey="baseline" fill="#F59E0B" radius={[4, 4, 0, 0]} />
              <Bar dataKey="optimized" fill="#10B981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h3 className="mb-3 text-sm font-medium text-white">Baseline vs Optimized Temperature</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={tempChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} domain={[15, 30]} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94A3B8" }} />
              <Bar dataKey="baseline" fill="#F59E0B" radius={[4, 4, 0, 0]} />
              <Bar dataKey="optimized" fill="#10B981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h3 className="mb-3 text-sm font-medium text-white">Baseline vs Optimized Comfort</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={comfortChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94A3B8" }} />
              <Bar dataKey="baseline" fill="#F59E0B" radius={[4, 4, 0, 0]} />
              <Bar dataKey="optimized" fill="#10B981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
