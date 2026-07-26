"use client";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { DashboardMetrics } from "@/types";

export function BuildingStatusPanel({ data }: { data: DashboardMetrics }) {
  return (
    <Card>
      <h3 className="mb-3 text-sm font-medium text-white">Building Status</h3>
      <div className="space-y-2 text-sm">
        <Row label="HVAC" value={<Badge status={data.hvac_status} />} />
        <Row label="HVAC Mode" value={<span className="mono text-white">{data.hvac_mode}</span>} />
        <Row label="Comfort Score" value={<span className="mono text-white">{data.comfort_score}/100</span>} />
        <Row label="Carbon Today" value={<span className="mono text-white">{data.carbon_kg_today} kg</span>} />
        <Row label="Cost Today" value={<span className="mono text-white">${data.cost_usd_today}</span>} />
      </div>
    </Card>
  );
}

export function AIStatusPanel({ data }: { data: DashboardMetrics }) {
  return (
    <Card>
      <h3 className="mb-3 text-sm font-medium text-white">AI Status</h3>
      <div className="space-y-3 text-sm">
        <Row label="Optimization" value={<Badge status={data.optimization_status} />} />
        <Row label="Confidence" value={<span className="mono text-white">{Math.round(data.ai_confidence * 100)}%</span>} />
        <div>
          <span className="text-xs text-muted">Latest Decision</span>
          <p className="mt-1 text-cyan">{data.ai_decision}</p>
        </div>
      </div>
    </Card>
  );
}

export function SimulationStatusPanel({ data }: { data: DashboardMetrics }) {
  return (
    <Card>
      <h3 className="mb-3 text-sm font-medium text-white">Simulation Status</h3>
      <div className="space-y-2 text-sm">
        <Row label="Status" value={<Badge status={data.simulation_status} />} />
        <Row
          label="Last Run"
          value={<span className="mono text-white">{data.last_simulation_at ? new Date(data.last_simulation_at).toLocaleTimeString() : "—"}</span>}
        />
        <Row label="Indoor Temp" value={<span className="mono text-white">{data.indoor_temp_c}°C</span>} />
        <Row label="Outdoor Temp" value={<span className="mono text-white">{data.outdoor_temp_c}°C</span>} />
      </div>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted">{label}</span>
      {value}
    </div>
  );
}
