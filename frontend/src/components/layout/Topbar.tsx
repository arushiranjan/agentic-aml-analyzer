import { useEffect, useState } from "react";
import { Database, CircleCheck, CircleAlert } from "lucide-react";
import { useDataset } from "@/context/DatasetContext";
import { checkHealth } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

export function Topbar() {
  const { datasetId, summary } = useDataset();
  const [backendUp, setBackendUp] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    checkHealth()
      .then(() => mounted && setBackendUp(true))
      .catch(() => mounted && setBackendUp(false));
    return () => { mounted = false; };
  }, []);

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-surface/60 px-6 backdrop-blur">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Database className="h-4 w-4" />
        {datasetId ? (
          <span>
            Dataset <span className="font-mono text-foreground">{datasetId}</span>
            {summary && (
              <span className="text-muted-foreground"> · {summary.num_transactions.toLocaleString()} txns · {summary.num_customers.toLocaleString()} customers</span>
            )}
          </span>
        ) : (
          <span>No dataset loaded — go to Dashboard to upload one</span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {backendUp === null ? null : backendUp ? (
          <Badge variant="success" className="gap-1">
            <CircleCheck className="h-3 w-3" /> Backend online
          </Badge>
        ) : (
          <Badge variant="danger" className="gap-1">
            <CircleAlert className="h-3 w-3" /> Backend unreachable
          </Badge>
        )}
      </div>
    </header>
  );
}
