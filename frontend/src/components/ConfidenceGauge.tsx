import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from "recharts";

/** Circular gauge (0-100) used for confidence and risk scores across the app. */
export function ConfidenceGauge({
  value, label, size = 140, color = "hsl(217 91% 60%)",
}: {
  value: number; // 0-100
  label?: string;
  size?: number;
  color?: string;
}) {
  const data = [{ name: "value", value, fill: color }];
  return (
    <div className="flex flex-col items-center" style={{ width: size }}>
      <ResponsiveContainer width={size} height={size}>
        <RadialBarChart
          innerRadius="72%"
          outerRadius="100%"
          data={data}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar background={{ fill: "hsl(222 15% 14%)" }} dataKey="value" cornerRadius={999} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="-mt-[88px] flex flex-col items-center">
        <span className="text-2xl font-semibold mono-tabular">{value.toFixed(0)}%</span>
        {label && <span className="text-xs text-muted-foreground">{label}</span>}
      </div>
      <div className="h-[16px]" />
    </div>
  );
}
