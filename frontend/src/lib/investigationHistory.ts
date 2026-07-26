import type { ChatResponse, InvestigationEntry } from "@/types";

// Persisted in sessionStorage so the Dashboard's "Recent Investigations"
// and the Investigation page's history list share the same data, and it
// survives navigation between pages (cleared when the browser tab closes).
//
// IMPORTANT: this stores the FULL ChatResponse per entry, not a summary
// placeholder — this is the direct fix for the old Streamlit bug where
// re-rendered chat turns only showed "See results above." instead of the
// actual results.

const STORAGE_KEY = "aml_investigation_history";
const MAX_ENTRIES = 50;

export function getInvestigationHistory(): InvestigationEntry[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as InvestigationEntry[]) : [];
  } catch {
    return [];
  }
}

export function addInvestigationEntry(query: string, response: ChatResponse): InvestigationEntry {
  const entry: InvestigationEntry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    query,
    timestamp: new Date().toISOString(),
    response,
  };
  const existing = getInvestigationHistory();
  const updated = [entry, ...existing].slice(0, MAX_ENTRIES);
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  return entry;
}

export function clearInvestigationHistory(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}
