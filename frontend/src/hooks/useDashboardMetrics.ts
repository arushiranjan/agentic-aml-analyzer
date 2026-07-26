"use client";
import { getDashboardMetrics } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";

export function useDashboardMetrics(intervalMs = 5000) {
  const { data, error } = usePolling(getDashboardMetrics, intervalMs);
  return { data, error };
}
