import { useCallback, useEffect, useState } from "react";
import { Search, Loader2, User, Clock, Users2, History as HistoryIcon } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ConfidenceGauge } from "@/components/ConfidenceGauge";
import { RiskBadge } from "@/components/RiskBadge";
import { EvidenceList } from "@/components/EvidenceList";
import { EmptyState } from "@/components/EmptyState";
import { useDataset } from "@/context/DatasetContext";
import { fetchCustomerDetails, fetchTimeline, fetchRiskReport, apiErrorMessage } from "@/lib/api";
import { formatTimestamp, titleCase } from "@/lib/utils";
import type { CustomerDetails as CustomerDetailsType, TimelineResult, RiskReportRow } from "@/types";

export default function CustomerDetailsPage() {
  const { datasetId } = useDataset();
  const [customerId, setCustomerId] = useState("");
  const [details, setDetails] = useState<CustomerDetailsType | null>(null);
  const [timeline, setTimeline] = useState<TimelineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [topCustomers, setTopCustomers] = useState<RiskReportRow[]>([]);

  useEffect(() => {
    if (!datasetId) return;
    fetchRiskReport(datasetId)
      .then((res) => setTopCustomers((res.risk_score?.risk_report ?? []).slice(0, 8)))
      .catch(() => setTopCustomers([]));
  }, [datasetId]);

  const lookup = useCallback(async (id: string) => {
    const trimmed = id.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    try {
      const [detailsRes, timelineRes] = await Promise.all([
        fetchCustomerDetails(trimmed, datasetId ?? undefined),
        fetchTimeline(trimmed, datasetId ?? undefined),
      ]);
      setDetails(detailsRes);
      setTimeline(timelineRes);
      setCustomerId(trimmed);
    } catch (err) {
      setError(apiErrorMessage(err));
      setDetails(null);
      setTimeline(null);
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  const riskRow = details?.risk_score?.risk_report?.[0];
  const explanation = details?.explanation?.explanations?.[0];
  const chartData = (timeline?.events ?? []).map((e) => ({
    time: formatTimestamp(e.timestamp),
    amount: e.amount,
  }));

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Customer Details</h1>
        <p className="text-sm text-muted-foreground">Look up a customer to see their full risk profile, evidence, and transaction timeline.</p>
      </div>

      <Card>
        <CardContent className="flex gap-2 p-5">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && lookup(customerId)}
              placeholder="Enter customer ID, e.g. C901"
              className="h-10 pl-9"
            />
          </div>
          <Button onClick={() => lookup(customerId)} disabled={loading || !customerId.trim()}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <User className="h-4 w-4" />}
            Look Up
          </Button>
        </CardContent>
      </Card>

      {error && <div className="rounded-md border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div>}

      {!details && !loading && (
        <>
          {topCustomers.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Top Suspicious Customers — click to view</CardTitle></CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {topCustomers.map((c) => (
                  <button
                    key={c.customer_id}
                    onClick={() => lookup(c.customer_id)}
                    className="flex items-center gap-2 rounded-md border border-border bg-muted/40 px-3 py-1.5 text-sm hover:border-primary/40"
                  >
                    <span className="font-mono">{c.customer_id}</span>
                    <RiskBadge level={c.risk_level} />
                  </button>
                ))}
              </CardContent>
            </Card>
          )}
          <EmptyState icon={User} title="No customer selected" description="Search a customer ID above, or pick one from the list." />
        </>
      )}

      {details && (
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader className="flex-row items-start justify-between space-y-0">
              <div>
                <CardTitle className="text-xs">Customer Profile</CardTitle>
                <p className="font-mono text-2xl font-semibold">{customerId}</p>
              </div>
              {riskRow && <RiskBadge level={riskRow.risk_level} />}
            </CardHeader>
            <CardContent className="flex flex-col gap-6 lg:flex-row">
              {riskRow && (
                <div className="flex shrink-0 flex-col items-center gap-2">
                  <ConfidenceGauge value={riskRow.final_score * 100} label="Risk Score" color="hsl(0 72% 58%)" />
                  <Badge variant="outline">Confidence {riskRow.confidence}%</Badge>
                </div>
              )}
              <div className="grid flex-1 grid-cols-2 gap-3 sm:grid-cols-3">
                {Object.entries(details.customer_stats ?? {}).flatMap(([k, v]) => {
                  if (k === "customers" && Array.isArray(v)) {
                    const c = v[0] as Record<string, unknown> | undefined;
                    if (!c) return [];
                    return Object.entries(c).map(([ck, cv]) => (
                      <StatBlock key={ck} label={ck} value={cv} />
                    ));
                  }
                  return [<StatBlock key={k} label={k} value={v} />];
                })}
              </div>
            </CardContent>
          </Card>

          {chartData.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Investigation Timeline</CardTitle></CardHeader>
              <CardContent>
                <p className="mb-3 text-sm text-foreground/90">🤖 {timeline?.caption}</p>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 15% 18%)" />
                    <XAxis dataKey="time" tick={{ fontSize: 10, fill: "hsl(215 12% 58%)" }} />
                    <YAxis tick={{ fontSize: 10, fill: "hsl(215 12% 58%)" }} />
                    <Tooltip contentStyle={{ background: "hsl(222 22% 9%)", border: "1px solid hsl(222 15% 18%)", fontSize: 12 }} />
                    <Line type="monotone" dataKey="amount" stroke="hsl(217 91% 60%)" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Triggered Rules</CardTitle></CardHeader>
              <CardContent>
                {riskRow && riskRow.rule_hits.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {riskRow.rule_hits.map((hit) => (
                      <Badge key={hit.rule} variant="outline" title={hit.reason}>
                        {titleCase(hit.rule)} · {hit.score.toFixed(2)}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No rule-engine hits for this customer.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Evidence</CardTitle></CardHeader>
              <CardContent><EvidenceList items={riskRow?.evidence ?? []} /></CardContent>
            </Card>
          </div>

          {explanation && (
            <Card>
              <CardHeader><CardTitle>Explanation & Recommendation</CardTitle></CardHeader>
              <CardContent><p className="text-sm leading-relaxed">{explanation.explanation}</p></CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="flex-row items-center gap-2 space-y-0">
              <HistoryIcon className="h-4 w-4 text-muted-foreground" />
              <CardTitle>Previous Alerts / Investigation History</CardTitle>
            </CardHeader>
            <CardContent>
              {details.history.length === 0 ? (
                <p className="text-sm text-muted-foreground">No prior snapshots — this is the first time this customer has been scored.</p>
              ) : (
                <div className="space-y-2">
                  {details.history.map((h, i) => (
                    <div key={i} className="flex items-center justify-between rounded-md border border-border bg-muted/30 px-3 py-2 text-sm">
                      <span className="flex items-center gap-2 text-muted-foreground">
                        <Clock className="h-3.5 w-3.5" /> {formatTimestamp(h.timestamp)}
                      </span>
                      <span className="mono-tabular">{h.final_score.toFixed(3)}</span>
                      <RiskBadge level={h.risk_level} />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {details.graph && details.graph.centrality.length > 0 && (
            <Card>
              <CardHeader className="flex-row items-center gap-2 space-y-0">
                <Users2 className="h-4 w-4 text-muted-foreground" />
                <CardTitle>Beneficiary / Network Position</CardTitle>
              </CardHeader>
              <CardContent>
                {(() => {
                  const row = details.graph!.centrality.find((c) => c.customer_id === customerId);
                  if (!row) return <p className="text-sm text-muted-foreground">No network data for this customer.</p>;
                  return (
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <StatBlock label="Degree (connections)" value={row.degree} />
                      <StatBlock label="PageRank" value={row.pagerank} />
                      <StatBlock label="Betweenness" value={row.betweenness} />
                      <StatBlock label="Pass-through ratio" value={row.passthrough_ratio} />
                    </div>
                  );
                })()}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function StatBlock({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-md border border-border bg-muted/30 p-3">
      <p className="text-[11px] uppercase text-muted-foreground">{label.replace(/_/g, " ")}</p>
      <p className="mono-tabular text-sm font-semibold">
        {typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: 3 }) : String(value)}
      </p>
    </div>
  );
}
