"use client";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/ui/card";

export function EnergyChart({ series, title = "Energy Usage (kW)" }: { series: { time: string; value: number }[]; title?: string }) {
  return (
    <Card>
      <h3 className="mb-3 text-sm font-medium text-white">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={series}>
          <defs>
            <linearGradient id="energyGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22D3EE" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#22D3EE" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="time" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
          <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
            labelStyle={{ color: "#94A3B8" }}
          />
          <Area type="monotone" dataKey="value" stroke="#22D3EE" fill="url(#energyGradient)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}
