import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { DatasetSummary } from "@/types";
import { fetchDatasetSummary } from "@/lib/api";

interface DatasetContextValue {
  datasetId: string | null;
  summary: DatasetSummary | null;
  loadingSummary: boolean;
  setDatasetId: (id: string) => void;
  refreshSummary: () => Promise<void>;
}

const DatasetContext = createContext<DatasetContextValue | undefined>(undefined);

const STORAGE_KEY = "aml_dataset_id";

export function DatasetProvider({ children }: { children: ReactNode }) {
  const [datasetId, setDatasetIdState] = useState<string | null>(() => sessionStorage.getItem(STORAGE_KEY));
  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  const setDatasetId = useCallback((id: string) => {
    sessionStorage.setItem(STORAGE_KEY, id);
    setDatasetIdState(id);
  }, []);

  const refreshSummary = useCallback(async () => {
    if (!datasetId) return;
    setLoadingSummary(true);
    try {
      const data = await fetchDatasetSummary(datasetId);
      setSummary(data);
    } catch {
      setSummary(null);
    } finally {
      setLoadingSummary(false);
    }
  }, [datasetId]);

  useEffect(() => {
    refreshSummary();
  }, [refreshSummary]);

  return (
    <DatasetContext.Provider value={{ datasetId, summary, loadingSummary, setDatasetId, refreshSummary }}>
      {children}
    </DatasetContext.Provider>
  );
}

export function useDataset(): DatasetContextValue {
  const ctx = useContext(DatasetContext);
  if (!ctx) throw new Error("useDataset() must be used within a <DatasetProvider>");
  return ctx;
}
