import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { useDataset } from "@/context/DatasetContext";
import { fetchModelStatus, fetchSystemStatus, fetchRiskReport, apiErrorMessage } from "@/lib/api";
import { formatTimestamp, titleCase } from "@/lib/utils";
import type { ModelStatus, SystemStatus, RiskReportRow } from "@/types";
import { Cpu, Info } from "lucide-react";

const tooltipStyle = { background: "hsl(222 22% 9%)", border: "1px solid hsl(222 15% 18%)", fontSize: 12 };
const axisTick = { fontSize: 11, fill: "hsl(215 12% 58%)" };

export default function ModelInsights() {
  const { datasetId } = useDataset();
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [riskRows, setRiskRows] = useState<RiskReportRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetchModelStatus(datasetId ?? undefined),
      fetchSystemStatus(),
      datasetId ? fetchRiskReport(datasetId) : Promise.resolve(null),
    ])
      .then(([m, s, r]) => {
        setModelStatus(m);
        setSystemStatus(s);
        setRiskRows(r?.risk_score?.risk_report ?? []);
      })
      .catch((err) => setError(apiErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [datasetId]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-56 w-full" />)}
      </div>
    );
  }

  if (error) {
    return <div className="rounded-md border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div>;
  }

  // ML score histogram — real data from the actual fitted Isolation Forest,
  // bucketed client-side into 10 bins across [0, 1].
  const bins = Array.from({ length: 10 }, (_, i) => ({ label: `${(i / 10).toFixed(1)}–${((i + 1) / 10).toFixed(1)}`, count: 0 }));
  riskRows.forEach((r) => {
    const idx = Math.min(9, Math.floor(r.ml_score * 10));
    bins[idx].count += 1;
  });

  // Rule trigger frequency — how many scored customers each rule actually
  // fired for in this dataset. This is real, derived telemetry (a
  // legitimate proxy for "feature importance" for a rule-based system),
  // not a fabricated supervised-model metric.
  const ruleFrequency: Record<string, number> = {};
  riskRows.forEach((r) => r.rule_hits.forEach((h) => { ruleFrequency[h.rule] = (ruleFrequency[h.rule] ?? 0) + 1; }));
  const ruleFrequencyData = Object.entries(ruleFrequency)
    .map(([rule, count]) => ({ rule: titleCase(rule), count }))
    .sort((a, b) => b.count - a.count);

  const ruleImportanceData = systemStatus
    ? Object.entries(systemStatus.rule_importance).map(([rule, weight]) => ({ rule: titleCase(rule), weight }))
        .sort((a, b) => b.weight - a.weight)
    : [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Model Insights</h1>
        <p className="text-sm text-muted-foreground">Real telemetry from the Isolation Forest and the importance-weighted Rule Engine.</p>
      </div>

      <div className="flex items-start gap-2 rounded-md border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-foreground/90">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        <p>
          This pipeline uses an <strong>unsupervised Isolation Forest</strong> plus a{" "}
          <strong>rule engine</strong> — there is no labeled ground truth in this dataset, so a supervised
          classifier (Random Forest), ROC curve, or confusion matrix would not be meaningful here and isn't
          fabricated below. What's shown is real: the model's actual configuration, the live anomaly-score
          distribution, and how often each rule fired across the loaded dataset.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center gap-2 space-y-0">
            <Cpu className="h-4 w-4 text-primary" />
            <CardTitle>Isolation Forest</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="Algorithm" value={modelStatus?.algorithm} />
            <Row label="Trained" value={modelStatus?.trained ? "Yes" : "No"} />
            <Row label="Last trained at" value={formatTimestamp(modelStatus?.trained_at)} />
            <Row label="Default contamination" value={modelStatus?.contamination_default?.toString()} />
            <div>
              <p className="mb-1.5 text-xs uppercase text-muted-foreground">Feature columns</p>
              <div className="flex flex-wrap gap-1.5">
                {modelStatus?.feature_columns.map((f) => <Badge key={f} variant="outline">{f}</Badge>)}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Anomaly Score Distribution</CardTitle></CardHeader>
          <CardContent>
            {riskRows.length === 0 ? (
              <EmptyState icon={Cpu} title="No scored customers yet" description="Run an investigation or the risk report first." />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={bins}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 15% 18%)" />
                  <XAxis dataKey="label" tick={axisTick} interval={1} />
                  <YAxis tick={axisTick} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="count" fill="hsl(217 91% 60%)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Rule Importance Weights (config.py)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={ruleImportanceData} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 15% 18%)" />
                <XAxis type="number" domain={[0, 0.5]} tick={axisTick} />
                <YAxis type="category" dataKey="rule" tick={{ fontSize: 10, fill: "hsl(215 12% 58%)" }} width={130} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="weight" fill="hsl(270 60% 65%)" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Rule Trigger Frequency (this dataset)</CardTitle></CardHeader>
          <CardContent>
            {ruleFrequencyData.length === 0 ? (
              <p className="text-sm text-muted-foreground">No rule hits recorded yet — run the risk report on the Dashboard or Analytics page.</p>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={ruleFrequencyData} layout="vertical" margin={{ left: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 15% 18%)" />
                  <XAxis type="number" tick={axisTick} allowDecimals={false} />
                  <YAxis type="category" dataKey="rule" tick={{ fontSize: 10, fill: "hsl(215 12% 58%)" }} width={130} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="count" fill="hsl(152 55% 45%)" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex items-center justify-between border-b border-border/50 pb-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value ?? "—"}</span>
    </div>
  );
}
