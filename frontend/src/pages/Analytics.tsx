import { useEffect, useState } from "react";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, LineChart, Line,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RiskBadge } from "@/components/RiskBadge";
import { EmptyState } from "@/components/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { useDataset } from "@/context/DatasetContext";
import { fetchEda, fetchRiskReport, apiErrorMessage } from "@/lib/api";
import type { EdaResult, RiskReportRow } from "@/types";
import { BarChart3 } from "lucide-react";

const RISK_COLORS: Record<string, string> = {
  High: "hsl(0 72% 58%)",
  Medium: "hsl(38 92% 55%)",
  Low: "hsl(152 55% 45%)",
};
const PALETTE = ["hsl(217 91% 60%)", "hsl(152 55% 45%)", "hsl(38 92% 55%)", "hsl(0 72% 58%)", "hsl(270 60% 65%)", "hsl(190 70% 55%)"];

const tooltipStyle = { background: "hsl(222 22% 9%)", border: "1px solid hsl(222 15% 18%)", fontSize: 12 };
const axisTick = { fontSize: 11, fill: "hsl(215 12% 58%)" };

export default function Analytics() {
  const { datasetId } = useDataset();
  const [eda, setEda] = useState<EdaResult | null>(null);
  const [riskRows, setRiskRows] = useState<RiskReportRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!datasetId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    Promise.all([fetchEda(datasetId), fetchRiskReport(datasetId)])
      .then(([edaRes, riskRes]) => {
        setEda(edaRes);
        setRiskRows(riskRes.risk_score?.risk_report ?? []);
      })
      .catch((err) => setError(apiErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [datasetId]);

  if (!datasetId) {
    return <EmptyState icon={BarChart3} title="No dataset loaded" description="Upload a dataset on the Dashboard page first." />;
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-64 w-full" />)}
      </div>
    );
  }

  if (error) {
    return <div className="rounded-md border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div>;
  }

  const riskCounts = ["High", "Medium", "Low"].map((level) => ({
    name: level,
    value: riskRows.filter((r) => r.risk_level === level).length,
  }));

  const dailyData = eda?.distribution.daily_txn_counts.dates.map((d, i) => ({
    date: d, count: eda.distribution.daily_txn_counts.counts[i],
  })) ?? [];

  const hourlyData = eda?.distribution.hourly_txn_counts.hours.map((h, i) => ({
    hour: `${h}:00`, count: eda.distribution.hourly_txn_counts.counts[i],
  })) ?? [];

  const amountHistData = eda?.distribution.amount_histogram.counts.map((c, i) => ({
    range: `${Math.round(eda.distribution.amount_histogram.bin_edges[i])}`,
    count: c,
  })) ?? [];

  const channelData = eda?.distribution.channel_counts
    ? eda.distribution.channel_counts.labels.map((l, i) => ({ name: l, value: eda.distribution.channel_counts!.counts[i] }))
    : [];

  const countryData = eda?.distribution.country_counts
    ? eda.distribution.country_counts.labels.map((l, i) => ({ name: l, value: eda.distribution.country_counts!.counts[i] }))
    : [];

  const topSuspicious = [...riskRows].sort((a, b) => b.final_score - a.final_score).slice(0, 10);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground">Interactive charts across the full loaded dataset.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Risk Distribution</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={riskCounts} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
                  {riskCounts.map((entry) => <Cell key={entry.name} fill={RISK_COLORS[entry.name]} />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Transaction Amount Distribution</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={amountHistData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 15% 18%)" />
                <XAxis dataKey="range" tick={axisTick} interval={4} />
                <YAxis tick={axisTick} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" fill="hsl(217 91% 60%)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Daily Transaction Volume</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 15% 18%)" />
                <XAxis dataKey="date" tick={axisTick} interval={9} />
                <YAxis tick={axisTick} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="count" stroke="hsl(217 91% 60%)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Hourly Transaction Pattern</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 15% 18%)" />
                <XAxis dataKey="hour" tick={axisTick} interval={2} />
                <YAxis tick={axisTick} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" fill="hsl(270 60% 65%)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {channelData.length > 0 && (
          <Card>
            <CardHeader><CardTitle>Payment Channels</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={channelData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
                    {channelData.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {countryData.length > 0 && (
          <Card>
            <CardHeader><CardTitle>Countries</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={countryData} layout="vertical" margin={{ left: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 15% 18%)" />
                  <XAxis type="number" tick={axisTick} />
                  <YAxis type="category" dataKey="name" tick={axisTick} width={80} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="value" fill="hsl(190 70% 55%)" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>

      <Card>
        <CardHeader><CardTitle>Top Suspicious Customers</CardTitle></CardHeader>
        <CardContent>
          {topSuspicious.length === 0 ? (
            <p className="text-sm text-muted-foreground">No customers scored yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                    <th className="py-2 pr-4">Customer</th>
                    <th className="py-2 pr-4">Final Score</th>
                    <th className="py-2 pr-4">Rule Score</th>
                    <th className="py-2 pr-4">ML Score</th>
                    <th className="py-2 pr-4">Confidence</th>
                    <th className="py-2 pr-4">Risk Level</th>
                  </tr>
                </thead>
                <tbody>
                  {topSuspicious.map((row) => (
                    <tr key={row.customer_id} className="border-b border-border/50 last:border-0">
                      <td className="py-2 pr-4 font-mono">{row.customer_id}</td>
                      <td className="py-2 pr-4 mono-tabular">{row.final_score.toFixed(3)}</td>
                      <td className="py-2 pr-4 mono-tabular">{row.rule_score.toFixed(3)}</td>
                      <td className="py-2 pr-4 mono-tabular">{row.ml_score.toFixed(3)}</td>
                      <td className="py-2 pr-4 mono-tabular">{row.confidence}%</td>
                      <td className="py-2 pr-4"><RiskBadge level={row.risk_level} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
