"use client";
import { useState } from "react";
import { Play, Zap } from "lucide-react";
import { runAgentCycle, runSimulation } from "@/lib/api";

interface TopbarProps {
  title?: string;
  showActions?: boolean;
}

export function Topbar({ title = "Building Overview", showActions = true }: TopbarProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleRunSimulation = async () => {
    setBusy("simulation");
    try {
      const res = await runSimulation(false);
      setMessage(`Simulation ${res.simulation_id} completed in ${res.duration_seconds}s`);
    } catch {
      setMessage("Simulation failed to run.");
    } finally {
      setBusy(null);
    }
  };

  const handleRunCycle = async () => {
    setBusy("cycle");
    try {
      const res = await runAgentCycle();
      setMessage(`Agent cycle ${res.cycle_id}: ${res.status}`);
      window.dispatchEvent(new CustomEvent("ecoloop:ai-cycle-complete"));
    } catch {
      setMessage("Agent cycle failed to run.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <header className="glass mb-6 flex items-center justify-between rounded-2xl px-5 py-4">
      <div>
        <h1 className="text-lg font-semibold text-white">{title}</h1>
        {message && <p className="text-xs text-muted">{message}</p>}
      </div>
      {showActions && (
        <div className="flex gap-3">
          <button
            onClick={handleRunSimulation}
            disabled={busy !== null}
            className="flex items-center gap-2 rounded-xl bg-cyan/15 px-4 py-2 text-sm font-medium text-cyan transition hover:bg-cyan/25 disabled:opacity-50"
          >
            <Zap className="h-4 w-4" />
            {busy === "simulation" ? "Running…" : "Run Simulation"}
          </button>
          <button
            onClick={handleRunCycle}
            disabled={busy !== null}
            className="flex items-center gap-2 rounded-xl bg-emerald/15 px-4 py-2 text-sm font-medium text-emerald transition hover:bg-emerald/25 disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            {busy === "cycle" ? "Running…" : "Run AI Cycle"}
          </button>
        </div>
      )}
    </header>
  );
}
