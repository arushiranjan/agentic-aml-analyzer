"use client";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { Card } from "@/components/ui/card";

export function TemperatureChart({
  series,
}: {
  series: { time: string; indoor: number; outdoor: number }[];
}) {
  return (
    <Card>
      <h3 className="mb-3 text-sm font-medium text-white">Indoor vs Outdoor Temperature (°C)</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={series}>
          <XAxis dataKey="time" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
          <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
            labelStyle={{ color: "#94A3B8" }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: "#94A3B8" }} />
          <Line type="monotone" dataKey="indoor" stroke="#10B981" strokeWidth={2} dot={false} name="Indoor" />
          <Line type="monotone" dataKey="outdoor" stroke="#F59E0B" strokeWidth={2} dot={false} name="Outdoor" />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
