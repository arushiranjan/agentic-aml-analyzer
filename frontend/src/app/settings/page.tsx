"use client";
import { Topbar } from "@/components/layout/topbar";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingState, ErrorState } from "@/components/ui/states";
import { usePolling } from "@/hooks/usePolling";
import { getSettingsView } from "@/lib/api";

export default function SettingsPage() {
  const { data, error, loading } = usePolling(getSettingsView, 15000);

  return (
    <>
      <Topbar title="Settings" showActions={false} />
      {error && <ErrorState message={error} />}
      {loading && !data ? (
        <LoadingState label="Loading settings…" />
      ) : data ? (
        <>
          <p className="mb-4 text-xs text-muted">
            {data.read_only ? "Settings are read-only in this phase." : ""}
          </p>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <h3 className="mb-3 text-sm font-medium text-white">Simulation</h3>
              <div className="space-y-2 text-sm">
                <Row label="Polling Interval" value={`${data.simulation.polling_interval_seconds}s`} />
                <Row label="Simulation Tick" value={`${data.simulation.simulation_tick_minutes} min`} />
              </div>
            </Card>
            <Card>
              <h3 className="mb-3 text-sm font-medium text-white">Optimization</h3>
              <div className="space-y-2 text-sm">
                <Row label="Comfort Priority" value={data.optimization.comfort_priority.toString()} />
                <Row label="Max Retries" value={data.optimization.max_retries.toString()} />
                <Row label="Max Actions / Cycle" value={data.optimization.max_actions_per_cycle.toString()} />
                <Row label="Cycle Interval" value={`${data.optimization.cycle_interval_minutes} min`} />
                <Row label="Optimization Mode" value={data.optimization.optimization_mode} />
              </div>
            </Card>
            <Card>
              <h3 className="mb-3 text-sm font-medium text-white">LLM</h3>
              <div className="space-y-2 text-sm">
                <Row label="Model" value={data.llm.model} />
                <Row label="Mode" value={<Badge status={data.llm.mode} />} />
                <Row label="Temperature" value={data.llm.temperature.toString()} />
                <Row label="Context Window" value={data.llm.context_window.toString()} />
              </div>
            </Card>
            <Card>
              <h3 className="mb-3 text-sm font-medium text-white">EnergyPlus</h3>
              <div className="space-y-2 text-sm">
                <Row label="Mode" value={<Badge status={data.energyplus.mode} />} />
                <Row label="IDF Path" value={<span className="mono text-xs">{data.energyplus.idf_path}</span>} />
                <Row label="EPW Path" value={<span className="mono text-xs">{data.energyplus.epw_path}</span>} />
              </div>
            </Card>
          </div>
        </>
      ) : null}
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
