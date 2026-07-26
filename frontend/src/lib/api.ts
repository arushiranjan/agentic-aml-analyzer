import axios from "axios";
import type {
  UploadResponse, DatasetSummary, SystemStatus, ModelStatus,
  ChatResponse, EdaResult, ExecutorResults, CustomerDetails,
  TimelineResult, HistorySnapshot, GraphVizResult,
} from "@/types";

const baseURL = import.meta.env.VITE_API_BASE_URL || "/api";

export const api = axios.create({ baseURL, timeout: 120_000 });

// ---------------------------------------------------------------------------
// Every function here is a thin, typed wrapper over an existing FastAPI
// endpoint in backend/main.py. No business logic lives here — this file's
// only job is "call the right URL, get back the right TypeScript shape".
// ---------------------------------------------------------------------------

export async function uploadDataset(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<UploadResponse>("/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function fetchDatasetSummary(datasetId?: string): Promise<DatasetSummary> {
  const { data } = await api.get<DatasetSummary>("/dataset/summary", { params: { dataset_id: datasetId } });
  return data;
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const { data } = await api.get<SystemStatus>("/system/status");
  return data;
}

export async function fetchModelStatus(datasetId?: string): Promise<ModelStatus> {
  const { data } = await api.get<ModelStatus>("/model/status", { params: { dataset_id: datasetId } });
  return data;
}

export async function trainModel(datasetId?: string): Promise<{ model_status: string; customers_scored: number }> {
  const { data } = await api.post("/train", null, { params: { dataset_id: datasetId } });
  return data;
}

export async function askAgent(query: string, datasetId?: string): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/chat", { query, dataset_id: datasetId });
  return data;
}

export async function fetchEda(datasetId?: string, filters?: Record<string, unknown>): Promise<EdaResult> {
  const { data } = await api.post<EdaResult>("/eda", { dataset_id: datasetId, ...filters });
  return data;
}

export async function fetchRiskReport(datasetId?: string): Promise<ExecutorResults> {
  const { data } = await api.post<ExecutorResults>("/risk-report", null, { params: { dataset_id: datasetId } });
  return data;
}

export async function fetchCustomerDetails(customerId: string, datasetId?: string): Promise<CustomerDetails> {
  const { data } = await api.get<CustomerDetails>(`/customer/${encodeURIComponent(customerId)}`, {
    params: { dataset_id: datasetId },
  });
  return data;
}

export async function fetchTimeline(customerId: string, datasetId?: string): Promise<TimelineResult> {
  const { data } = await api.get<TimelineResult>(`/timeline/${encodeURIComponent(customerId)}`, {
    params: { dataset_id: datasetId },
  });
  return data;
}

export async function fetchHistory(customerId: string, datasetId?: string): Promise<{ customer_id: string; history: HistorySnapshot[] }> {
  const { data } = await api.get(`/history/${encodeURIComponent(customerId)}`, { params: { dataset_id: datasetId } });
  return data;
}

export async function fetchGraph(customerId: string, datasetId?: string, hops = 1): Promise<GraphVizResult> {
  const { data } = await api.get<GraphVizResult>(`/graph/${encodeURIComponent(customerId)}`, {
    params: { dataset_id: datasetId, hops },
  });
  return data;
}

export async function checkHealth(): Promise<{ status: string }> {
  const { data } = await api.get("/health");
  return data;
}

/** Extracts a readable message from an Axios error, falling back gracefully. */
export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (err.response?.status) return `Request failed with status ${err.response.status}`;
    if (err.code === "ECONNABORTED") return "Request timed out — the backend may be busy.";
    return err.message || "Network error — is the backend running?";
  }
  return err instanceof Error ? err.message : "An unexpected error occurred.";
}
