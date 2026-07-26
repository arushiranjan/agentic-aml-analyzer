"use client";
import { Leaf, Gauge, TrendingDown, Wind } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { MetricCard } from "@/components/dashboard/metric-card";
import { EnergyChart } from "@/components/dashboard/energy-chart";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states";
import { usePolling } from "@/hooks/usePolling";
import { getCarbonHistory } from "@/lib/api";

export default function CarbonPage() {
  const { data, error, loading } = usePolling(() => getCarbonHistory(48), 8000);

  return (
    <>
      <Topbar title="Carbon" showActions={false} />
      {error && <ErrorState message={error} />}
      {loading && !data ? (
        <LoadingState label="Loading carbon history…" />
      ) : !data || data.series.length === 0 ? (
        <EmptyState label="No carbon history yet — run the AI cycle or wait for a tick." />
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard label="Today's Emissions" value={data.today_carbon_kg.toString()} unit="kg" icon={Leaf} accent="critical" />
            <MetricCard label="Carbon Intensity" value={data.carbon_intensity_kg_per_kwh.toString()} unit="kg/kWh" icon={Wind} accent="amber" />
            <MetricCard label="Est. Savings" value={data.estimated_savings_pct.toString()} unit="%" icon={TrendingDown} accent="emerald" />
            <MetricCard label="Sustainability Score" value={data.sustainability_score.toString()} unit="/100" icon={Gauge} accent="emerald" />
          </div>

          <EnergyChart series={data.series.map((s) => ({ time: s.time, value: s.carbon_kg }))} title="Carbon Emissions (kg)" />

          <p className="mt-4 text-xs text-muted">
            Rolling average: <span className="mono text-white">{data.rolling_average_kg} kg</span> per 15-minute tick.
          </p>
        </>
      )}
    </>
  );
}
