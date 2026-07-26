import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Database, Users, Receipt, Cpu, Brain, ShieldCheck, Clock, Upload, Search, Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/StatCard";
import { EmptyState } from "@/components/EmptyState";
import { RiskBadge } from "@/components/RiskBadge";
import { useDataset } from "@/context/DatasetContext";
import { uploadDataset, fetchSystemStatus, fetchModelStatus, trainModel, apiErrorMessage } from "@/lib/api";
import { getInvestigationHistory } from "@/lib/investigationHistory";
import { formatTimestamp } from "@/lib/utils";
import type { SystemStatus, ModelStatus, InvestigationEntry } from "@/types";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const { datasetId, summary, setDatasetId, refreshSummary, loadingSummary } = useDataset();
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<InvestigationEntry[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchSystemStatus().then(setSystemStatus).catch(() => setSystemStatus(null));
    setRecent(getInvestigationHistory().slice(0, 5));
  }, []);

  useEffect(() => {
    if (datasetId) {
      fetchModelStatus(datasetId).then(setModelStatus).catch(() => setModelStatus(null));
    }
  }, [datasetId, summary]);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const res = await uploadDataset(file);
      setDatasetId(res.dataset_id);
      await refreshSummary();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setUploading(false);
    }
  }, [setDatasetId, refreshSummary]);

  const handleTrain = useCallback(async () => {
    if (!datasetId) return;
    setTraining(true);
    setError(null);
    try {
      await trainModel(datasetId);
      const status = await fetchModelStatus(datasetId);
      setModelStatus(status);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setTraining(false);
    }
  }, [datasetId]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Overview of the loaded dataset and AI pipeline status.</p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
          />
          <Button variant="secondary" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {uploading ? "Uploading..." : "Upload Dataset"}
          </Button>
          <Button onClick={handleTrain} disabled={!datasetId || training}>
            {training ? <Loader2 className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
            {training ? "Training..." : "Train / Retrain Model"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div>
      )}

      {!datasetId ? (
        <EmptyState
          icon={Database}
          title="No dataset loaded yet"
          description="Upload a transaction CSV to populate the dashboard, or drop sample_data/transactions.csv from the project."
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Transactions" value={summary?.num_transactions?.toLocaleString() ?? "—"} icon={Receipt} accent="primary" />
            <StatCard label="Customers" value={summary?.num_customers?.toLocaleString() ?? "—"} icon={Users} accent="primary" />
            <StatCard label="Beneficiaries" value={summary?.num_beneficiaries?.toLocaleString() ?? "—"} icon={Database} accent="primary" />
            <StatCard
              label="Model Loaded"
              value={modelStatus?.trained ? "Yes" : "Not trained"}
              icon={Cpu}
              accent={modelStatus?.trained ? "success" : "warning"}
              hint={modelStatus?.trained_at ? `Trained ${formatTimestamp(modelStatus.trained_at)}` : "Click Train / Retrain"}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Planner Status</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-success" />
                  <span className="text-sm font-medium">Active</span>
                </div>
                <Badge variant={systemStatus?.planner_mode === "llm" ? "primary" : "outline"}>
                  {systemStatus?.planner_mode === "llm" ? "LLM mode" : "Keyword fallback"}
                </Badge>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Rule Engine Status</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-success" />
                  <span className="text-sm font-medium">Active</span>
                </div>
                <Badge variant="outline">{systemStatus?.rule_count ?? "—"} rules loaded</Badge>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Last Training Time</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium mono-tabular">{formatTimestamp(modelStatus?.trained_at)}</span>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm font-medium text-foreground">Recent Investigations</CardTitle>
          <Link to="/investigation">
            <Button variant="ghost" size="sm"><Search className="h-3.5 w-3.5" /> New Investigation</Button>
          </Link>
        </CardHeader>
        <CardContent>
          {recent.length === 0 ? (
            <p className="text-sm text-muted-foreground">No investigations yet — try asking the agent something on the Investigation page.</p>
          ) : (
            <div className="space-y-2">
              {recent.map((entry, i) => {
                const topRow = entry.response.results.risk_score?.risk_report?.[0];
                return (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="flex items-center justify-between rounded-md border border-border bg-muted/30 px-3 py-2 text-sm"
                  >
                    <div className="flex flex-col">
                      <span className="font-medium">{entry.query}</span>
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(entry.timestamp)} · {entry.response.plan.goal}
                      </span>
                    </div>
                    {topRow && <RiskBadge level={topRow.risk_level} />}
                  </motion.div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {loadingSummary && <p className="text-xs text-muted-foreground">Refreshing dataset summary...</p>}
    </div>
  );
}
