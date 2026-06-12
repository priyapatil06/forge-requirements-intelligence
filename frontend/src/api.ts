import type { ArtifactRun, ForgeSession, IntakeForm } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; mock_llm: boolean }>("/api/v1/health"),
  listSessions: () => request<ForgeSession[]>("/api/v1/sessions"),
  createSession: (payload: IntakeForm) =>
    request<ForgeSession>("/api/v1/sessions", { method: "POST", body: JSON.stringify(payload) }),
  updateSession: (id: string, payload: IntakeForm) =>
    request<ForgeSession>(`/api/v1/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  generate: (id: string) =>
    request<ArtifactRun>(`/api/v1/sessions/${id}/generate`, { method: "POST" }),
  updateArtifacts: (id: string, artifacts: unknown) =>
    request<ArtifactRun>(`/api/v1/runs/${id}`, {
      method: "PUT",
      body: JSON.stringify({ artifacts }),
    }),
  review: (id: string, decision: string, note: string) =>
    request<ArtifactRun>(`/api/v1/runs/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ decision, note }),
    }),
  jiraStatus: () =>
    request<{
      configured: boolean;
      connections: { id: string; site_name: string; site_url: string; cloud_id: string }[];
    }>("/api/v1/jira/status"),
  jiraStart: () => request<{ authorization_url: string }>("/api/v1/jira/oauth/start"),
  jiraSync: (runId: string, payload: unknown) =>
    request<{ created_issues: { key?: string; id?: string }[]; warnings: string[] }>(
      `/api/v1/runs/${runId}/jira-sync`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
};

export function exportUrl(runId: string, format: "json" | "openapi" | "mermaid" | "zip") {
  return `${BASE}/api/v1/runs/${runId}/export?format=${format}`;
}
