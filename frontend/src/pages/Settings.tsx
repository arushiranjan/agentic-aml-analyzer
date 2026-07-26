import { useState } from "react";
import { CircleCheck, CircleAlert, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { checkHealth } from "@/lib/api";
import { useDataset } from "@/context/DatasetContext";

export default function Settings() {
  const { datasetId } = useDataset();
  const [checking, setChecking] = useState(false);
  const [healthy, setHealthy] = useState<boolean | null>(null);

  async function handleCheck() {
    setChecking(true);
    try {
      await checkHealth();
      setHealthy(true);
    } catch {
      setHealthy(false);
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Backend connectivity and configuration reference.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Backend Connection</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">API base URL</span>
            <span className="font-mono">{import.meta.env.VITE_API_BASE_URL || "/api (dev proxy → localhost:8000)"}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Active dataset</span>
            <span className="font-mono">{datasetId ?? "none"}</span>
          </div>
          <div className="flex items-center gap-3 pt-2">
            <Button variant="secondary" size="sm" onClick={handleCheck} disabled={checking}>
              {checking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              Check backend health
            </Button>
            {healthy === true && <Badge variant="success" className="gap-1"><CircleCheck className="h-3 w-3" /> Online</Badge>}
            {healthy === false && <Badge variant="danger" className="gap-1"><CircleAlert className="h-3 w-3" /> Unreachable</Badge>}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Configuration Reference</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>LLM provider, model name, and API key are configured via the backend's <code className="font-mono text-foreground">.env</code> file (see backend <code className="font-mono text-foreground">.env.example</code>). Restart the backend after changing them.</p>
          <p>Risk-score weights (<code className="font-mono text-foreground">RISK_RULE_WEIGHT</code> / <code className="font-mono text-foreground">RISK_ML_WEIGHT</code>) and per-rule importance weights (<code className="font-mono text-foreground">config.py</code>) are environment-configurable on the backend — see the README's "How Risk Scoring Works" section.</p>
        </CardContent>
      </Card>
    </div>
  );
}
