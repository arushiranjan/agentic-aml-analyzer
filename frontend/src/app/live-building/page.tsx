"use client";
import { Topbar } from "@/components/layout/topbar";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingState, ErrorState } from "@/components/ui/states";
import { usePolling } from "@/hooks/usePolling";
import { getBuildingLive } from "@/lib/api";

export default function LiveBuildingPage() {
  const { data, error, loading } = usePolling(getBuildingLive, 5000);

  return (
    <>
      <Topbar title="Live Building" showActions={false} />
      {error && <ErrorState message={error} />}
      {loading && !data ? (
        <LoadingState label="Loading live building state…" />
      ) : data ? (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Stat label="Sim Clock" value={new Date(data.sim_time).toLocaleString()} />
            <Stat label="Indoor Temp" value={`${data.indoor_temp_c} °C`} />
            <Stat label="Outdoor Temp" value={`${data.outdoor_temp_c} °C`} />
            <Stat label="Humidity" value={`${data.humidity_pct} %`} />
            <Stat label="Occupancy" value={data.occupancy.toString()} />
            <Stat label="HVAC Status" value={<Badge status={data.hvac_status} />} />
            <Stat label="HVAC Mode" value={<Badge status={data.hvac_mode} />} />
            <Stat label="Weather" value={<Badge status={data.weather_condition} />} />
            <Stat label="Lighting Load" value={`${data.lighting_load_kw} kW`} />
            <Stat label="Equipment Load" value={`${data.equipment_load_kw} kW`} />
            <Stat label="Solar Radiation" value={`${data.solar_radiation_wm2} W/m²`} />
            <Stat label="Health Score" value={`${data.overall_health_score}/100`} />
          </div>

          <Card>
            <h3 className="mb-3 text-sm font-medium text-white">Building Floor Summary</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase text-muted">
                    <th className="pb-2 pr-4">Zone</th>
                    <th className="pb-2 pr-4">Temp (°C)</th>
                    <th className="pb-2 pr-4">Humidity (%)</th>
                    <th className="pb-2 pr-4">CO₂ (ppm)</th>
                    <th className="pb-2 pr-4">Illuminance (lux)</th>
                    <th className="pb-2 pr-4">Occupancy</th>
                    <th className="pb-2 pr-4">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.floor_summary.map((z) => (
                    <tr key={z.name} className="border-t border-white/5">
                      <td className="py-2 pr-4 text-white">{z.name}</td>
                      <td className="py-2 pr-4 mono text-muted">{z.temperature_c}</td>
                      <td className="py-2 pr-4 mono text-muted">{z.humidity_pct}</td>
                      <td className="py-2 pr-4 mono text-muted">{z.co2_ppm}</td>
                      <td className="py-2 pr-4 mono text-muted">{z.illuminance_lux}</td>
                      <td className="py-2 pr-4 mono text-muted">{z.occupancy}</td>
                      <td className="py-2 pr-4"><Badge status={z.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      ) : null}
    </>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted">{label}</span>
      <div className="mono text-lg font-semibold text-white">{value}</div>
    </Card>
  );
}
