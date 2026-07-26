"use client";
import { Zap, TrendingUp, Calendar, CalendarDays } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { Card } from "@/components/ui/card";
import { MetricCard } from "@/components/dashboard/metric-card";
import { EnergyChart } from "@/components/dashboard/energy-chart";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states";
import { usePolling } from "@/hooks/usePolling";
import { getEnergyHistory } from "@/lib/api";

export default function EnergyPage() {
  const { data, error, loading } = usePolling(() => getEnergyHistory(48), 8000);

  return (
    <>
      <Topbar title="Energy" showActions={false} />
      {error && <ErrorState message={error} />}
      {loading && !data ? (
        <LoadingState label="Loading energy history…" />
      ) : !data || data.series.length === 0 ? (
        <EmptyState label="No energy history yet — run the AI cycle or wait for a tick." />
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard label="Total (latest)" value={data.series[data.series.length - 1].total.toString()} unit="kW" icon={Zap} accent="cyan" />
            <MetricCard label="Peak Demand" value={data.peak_demand_kw.toString()} unit="kW" icon={TrendingUp} accent="amber" />
            <MetricCard label="Weekly Total" value={data.weekly_consumption_kwh.toString()} unit="kWh" icon={CalendarDays} accent="emerald" />
            <MetricCard
              label="Today"
              value={(data.daily_consumption_kwh[data.daily_consumption_kwh.length - 1]?.kwh ?? 0).toString()}
              unit="kWh"
              icon={Calendar}
              accent="cyan"
            />
          </div>

          <div className="mb-6">
            <EnergyChart series={data.series.map((s) => ({ time: s.time, value: s.total }))} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <h3 className="mb-3 text-sm font-medium text-white">Latest Breakdown</h3>
              {(() => {
                const last = data.series[data.series.length - 1];
                return (
                  <div className="space-y-2 text-sm">
                    <Row label="HVAC" value={`${last.hvac} kW`} />
                    <Row label="Lighting" value={`${last.lighting} kW`} />
                    <Row label="Plug Load" value={`${last.plug} kW`} />
                    <Row label="Total" value={`${last.total} kW`} />
                  </div>
                );
              })()}
            </Card>
            <Card>
              <h3 className="mb-3 text-sm font-medium text-white">Daily Consumption</h3>
              <div className="space-y-2 text-sm">
                {data.daily_consumption_kwh.map((d) => (
                  <Row key={d.date} label={d.date} value={`${d.kwh} kWh`} />
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted">{label}</span>
      <span className="mono text-white">{value}</span>
    </div>
  );
}
