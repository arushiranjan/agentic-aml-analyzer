import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RiskBadge } from "./RiskBadge";
import { EvidenceList } from "./EvidenceList";
import { ConfidenceGauge } from "./ConfidenceGauge";
import type { RiskReportRow, ExplanationEntry } from "@/types";
import { titleCase } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export function RiskResultCard({
  row, explanation,
}: { row: RiskReportRow; explanation?: ExplanationEntry }) {
  const delta = row.history_delta;

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="text-xs">Customer</CardTitle>
          <p className="font-mono text-lg font-semibold">{row.customer_id}</p>
        </div>
        <RiskBadge level={row.risk_level} />
      </CardHeader>

      <CardContent className="flex flex-col gap-5 lg:flex-row">
        <div className="flex shrink-0 items-center gap-6">
          <ConfidenceGauge value={row.confidence} label="Confidence" />
          <div className="flex flex-col gap-3 text-sm">
            <div>
              <span className="text-muted-foreground">Final Score</span>
              <p className="mono-tabular text-lg font-semibold">{row.final_score.toFixed(3)}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Rule Score</span>
              <p className="mono-tabular">{row.rule_score.toFixed(3)} <span className="text-xs text-muted-foreground">({(row.weights_used.rule_weight * 100).toFixed(0)}% weight)</span></p>
            </div>
            <div>
              <span className="text-muted-foreground">ML (Isolation Forest) Score</span>
              <p className="mono-tabular">{row.ml_score.toFixed(3)} <span className="text-xs text-muted-foreground">({(row.weights_used.ml_weight * 100).toFixed(0)}% weight)</span></p>
            </div>
            {delta && (
              <div className="flex items-center gap-1 text-xs">
                {delta.change > 0 ? (
                  <TrendingUp className="h-3.5 w-3.5 text-danger" />
                ) : delta.change < 0 ? (
                  <TrendingDown className="h-3.5 w-3.5 text-success" />
                ) : (
                  <Minus className="h-3.5 w-3.5 text-muted-foreground" />
                )}
                <span className="text-muted-foreground">
                  {delta.change === 0 ? "No change" : `${delta.change > 0 ? "+" : ""}${delta.change}`} since last check
                </span>
              </div>
            )}
          </div>
        </div>

        <Separator orientation="vertical" className="hidden lg:block" />

        <div className="flex-1 space-y-4">
          {explanation && (
            <div>
              <h4 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Explanation & Recommendation
              </h4>
              <p className="text-sm leading-relaxed text-foreground/90">{explanation.explanation}</p>
            </div>
          )}

          <div>
            <h4 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Triggered Rules ({row.rule_hits.length})
            </h4>
            {row.rule_hits.length === 0 ? (
              <p className="text-sm text-muted-foreground">No rule-engine hits — flagged by ML anomaly detection only.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {row.rule_hits.map((hit) => (
                  <Badge key={hit.rule} variant="outline" title={hit.reason}>
                    {titleCase(hit.rule)} · {hit.score.toFixed(2)}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <div>
            <h4 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">Evidence</h4>
            <EvidenceList items={row.evidence} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
