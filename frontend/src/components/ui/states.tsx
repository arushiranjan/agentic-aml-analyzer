import { Card } from "@/components/ui/card";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <div className="text-sm text-muted">{label}</div>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="glass mb-4 rounded-xl border border-critical/30 px-4 py-3 text-sm text-critical">
      {message} — is the backend running on :8000?
    </div>
  );
}

export function EmptyState({ label = "No data yet." }: { label?: string }) {
  return (
    <Card>
      <p className="text-sm text-muted">{label}</p>
    </Card>
  );
}
