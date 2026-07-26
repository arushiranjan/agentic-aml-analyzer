"use client";
import { Topbar } from "@/components/layout/topbar";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states";
import { usePolling } from "@/hooks/usePolling";
import { getAgentsHistory } from "@/lib/api";

const WORKFLOW = ["Observe", "Analyze", "Plan", "Execute", "Validate", "Report"];

export default function AgentReasoningPage() {
  const { data, error, loading } = usePolling(() => getAgentsHistory(20), 8000);

  return (
    <>
      <Topbar title="Agent Reasoning" />
      {error && <ErrorState message={error} />}

      <Card className="mb-6">
        <h3 className="mb-3 text-sm font-medium text-white">Workflow</h3>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
          {WORKFLOW.map((step, i) => (
            <span key={step} className="flex items-center gap-2">
              <span className="rounded-lg bg-white/5 px-3 py-1 text-white">{step}</span>
              {i < WORKFLOW.length - 1 && <span>→</span>}
            </span>
          ))}
        </div>
      </Card>

      {loading && !data ? (
        <LoadingState label="Loading agent cycle history…" />
      ) : !data || data.cycles.length === 0 ? (
        <EmptyState label='No agent cycles yet — click "Run AI Cycle" above.' />
      ) : (
        <div className="space-y-4">
          {data.cycles.map((c) => (
            <Card key={c.cycle_id}>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="mono text-sm text-white">{c.cycle_id}</span>
                  <span className="ml-3 text-xs text-muted">
                    {c.timestamp ? new Date(c.timestamp).toLocaleString() : "—"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge status={c.status} />
                  <span className="text-xs text-muted">confidence {Math.round(c.confidence * 100)}%</span>
                  <span className="text-xs text-muted">{c.duration_ms} ms</span>
                </div>
              </div>

              <p className="mb-3 text-sm text-cyan">{c.decision}</p>

              <div className="mb-3 flex flex-wrap gap-2 text-xs text-muted">
                <span>Tools used: {c.tools_used.join(", ") || "—"}</span>
              </div>

              <div className="mb-3 text-xs text-muted">
                Generated actions:{" "}
                {c.generated_actions.map((a, i) => (
                  <span key={i} className="mono text-white">
                    {JSON.stringify(a)}
                    {i < c.generated_actions.length - 1 ? ", " : ""}
                  </span>
                ))}
              </div>

              <div className="mb-4 text-xs text-muted">
                Validation: <span className="mono text-white">{JSON.stringify(c.validation_result)}</span>
              </div>

              <div className="space-y-2 border-t border-white/5 pt-3">
                {c.steps.map((s, i) => (
                  <div key={i} className="text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{s.agent}</span>
                      {s.confidence != null && <span className="text-xs text-muted">{Math.round(s.confidence * 100)}%</span>}
                      {s.latency_ms != null && <span className="text-xs text-muted">{s.latency_ms} ms</span>}
                    </div>
                    <p className="text-muted">{s.reasoning}</p>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
