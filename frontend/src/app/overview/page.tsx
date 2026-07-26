"use client";
import { Cloud, Gauge, Leaf, Thermometer, Zap } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { MetricCard } from "@/components/dashboard/metric-card";
import { EnergyChart } from "@/components/dashboard/energy-chart";
import { TemperatureChart } from "@/components/dashboard/temperature-chart";
import { BuildingStatusPanel, AIStatusPanel, SimulationStatusPanel } from "@/components/dashboard/status-panels";
import { SavingsPanel } from "@/components/dashboard/savings-panel";
import { useDashboardMetrics } from "@/hooks/useDashboardMetrics";
import { LoadingState, ErrorState } from "@/components/ui/states";

export default function OverviewPage() {
  const { data, error } = useDashboardMetrics(5000);

  return (
    <>
      <Topbar title="Building Overview" />

      {error && <ErrorState message={error} />}

      {!data ? (
        <LoadingState label="Loading building state…" />
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
            <MetricCard label="Energy Usage" value={data.energy_usage_kw.toString()} unit="kW" icon={Zap} accent="cyan" />
            <MetricCard label="Indoor Temp" value={data.indoor_temp_c.toString()} unit="°C" icon={Thermometer} accent="emerald" />
            <MetricCard label="Outdoor Temp" value={data.outdoor_temp_c.toString()} unit="°C" icon={Cloud} accent="amber" />
            <MetricCard label="Comfort Score" value={data.comfort_score.toString()} unit="/100" icon={Gauge} accent="emerald" />
            <MetricCard label="Carbon Today" value={data.carbon_kg_today.toString()} unit="kg" icon={Leaf} accent="critical" />
          </div>

          <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <EnergyChart series={data.energy_series} />
            <TemperatureChart series={data.temperature_series} />
          </div>

          <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            <BuildingStatusPanel data={data} />
            <AIStatusPanel data={data} />
            <SimulationStatusPanel data={data} />
          </div>

          <SavingsPanel />
        </>
      )}
    </>
  );
}
