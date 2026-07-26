import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Loader2, Sparkles, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { PlanSteps } from "@/components/PlanSteps";
import { RiskResultCard } from "@/components/RiskResultCard";
import { EmptyState } from "@/components/EmptyState";
import { useDataset } from "@/context/DatasetContext";
import { askAgent, apiErrorMessage } from "@/lib/api";
import { addInvestigationEntry, getInvestigationHistory, clearInvestigationHistory } from "@/lib/investigationHistory";
import { formatTimestamp } from "@/lib/utils";
import type { InvestigationEntry } from "@/types";

const EXAMPLE_QUERIES = [
  "Find suspicious customers",
  "Find structuring patterns",
  "Explain customer C901",
  "Show high-risk customers",
  "Find money mules and hub accounts",
  "Average transaction amount",
];

export default function Investigation() {
  const { datasetId } = useDataset();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Every completed investigation is appended here in full — this is the
  // fix for the old bug where re-rendering a past turn only showed a
  // placeholder. Each entry below always renders its OWN complete
  // response object, never a shared/overwritten "latest result" variable.
  const [entries, setEntries] = useState<InvestigationEntry[]>(() => getInvestigationHistory());

  async function runInvestigation(q: string) {
    const trimmed = q.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    try {
      const response = await askAgent(trimmed, datasetId ?? undefined);
      const entry = addInvestigationEntry(trimmed, response);
      setEntries((prev) => [entry, ...prev]);
      setQuery("");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    clearInvestigationHistory();
    setEntries([]);
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Investigation</h1>
        <p className="text-sm text-muted-foreground">
          Ask the planning agent a question — it decides which tools to run and shows its reasoning.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-3 p-5">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runInvestigation(query)}
                placeholder='e.g. "Find structuring patterns" or "Explain customer C901"'
                className="h-11 pl-9 text-sm"
              />
            </div>
            <Button size="lg" onClick={() => runInvestigation(query)} disabled={loading || !query.trim()}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Investigate
            </Button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_QUERIES.map((q) => (
              <button
                key={q}
                onClick={() => runInvestigation(q)}
                disabled={loading}
                className="rounded-full border border-border bg-muted/40 px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-md border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div>
      )}

      {loading && (
        <Card>
          <CardContent className="flex items-center gap-3 p-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Planning and executing tools...
          </CardContent>
        </Card>
      )}

      {entries.length === 0 && !loading ? (
        <EmptyState icon={Search} title="No investigations yet" description="Try one of the example queries above to get started." />
      ) : (
        <div className="flex flex-col gap-6">
          {entries.length > 0 && (
            <div className="flex justify-end">
              <Button variant="ghost" size="sm" onClick={handleClear}>
                <Trash2 className="h-3.5 w-3.5" /> Clear history
              </Button>
            </div>
          )}
          <AnimatePresence initial={false}>
            {entries.map((entry) => (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <InvestigationResult entry={entry} />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

function InvestigationResult({ entry }: { entry: InvestigationEntry }) {
  const { query, timestamp, response } = entry;
  const { plan, results } = response;
  const riskRows = results.risk_score?.risk_report ?? [];
  const explanations = results.explanation?.explanations ?? [];
  const explanationByCustomer = Object.fromEntries(explanations.map((e) => [e.customer_id, e]));

  return (
    <Card className="border-primary/20">
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="text-xs">Query</CardTitle>
          <p className="text-base font-medium">{query}</p>
          <p className="text-xs text-muted-foreground">{formatTimestamp(timestamp)}</p>
        </div>
        <Badge variant="outline">{results.tools_executed.join(" → ")}</Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div>
          <h4 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">Goal</h4>
          <p className="text-sm">{plan.goal}</p>
        </div>

        <PlanSteps steps={plan.steps} source={plan.source} />

        {results.warning && (
          <div className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
            {results.warning}
          </div>
        )}

        {results.eda && (
          <div>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Transaction Statistics</h4>
            {results.eda.transaction_stats.message ? (
              <p className="text-sm text-muted-foreground">{results.eda.transaction_stats.message}</p>
            ) : (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Object.entries(results.eda.transaction_stats)
                  .filter(([k]) => k !== "date_range")
                  .map(([k, v]) => (
                    <div key={k} className="rounded-md border border-border bg-muted/30 p-3">
                      <p className="text-[11px] uppercase text-muted-foreground">{k.replace(/_/g, " ")}</p>
                      <p className="mono-tabular text-sm font-semibold">{typeof v === "number" ? v.toLocaleString() : String(v)}</p>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {results.graph && results.graph.graph_hits.length > 0 && (
          <div>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Network Intelligence ({results.graph.graph_hits.length} flagged)
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {results.graph.graph_hits.slice(0, 12).map((hit, i) => (
                <Badge key={i} variant="outline" title={hit.reason}>
                  {hit.customer_id} · {hit.rule.replace(/_/g, " ")}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {riskRows.length > 0 && (
          <div className="flex flex-col gap-4">
            <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Risk Results ({riskRows.length})
            </h4>
            {riskRows.slice(0, 10).map((row) => (
              <RiskResultCard key={row.customer_id} row={row} explanation={explanationByCustomer[row.customer_id]} />
            ))}
          </div>
        )}

        {!results.eda && riskRows.length === 0 && !results.warning && (!results.graph || results.graph.graph_hits.length === 0) && (
          <p className="text-sm text-muted-foreground">No results to display for this query.</p>
        )}
      </CardContent>
    </Card>
  );
}
