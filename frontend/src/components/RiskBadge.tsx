import { Badge } from "@/components/ui/badge";
import { AlertTriangle, AlertCircle, CheckCircle2 } from "lucide-react";

export function RiskBadge({ level }: { level: string }) {
  if (level === "High") {
    return (
      <Badge variant="danger" className="gap-1">
        <AlertTriangle className="h-3 w-3" /> High Risk
      </Badge>
    );
  }
  if (level === "Medium") {
    return (
      <Badge variant="warning" className="gap-1">
        <AlertCircle className="h-3 w-3" /> Medium Risk
      </Badge>
    );
  }
  return (
    <Badge variant="success" className="gap-1">
      <CheckCircle2 className="h-3 w-3" /> Low Risk
    </Badge>
  );
}
