import type { Audit, CreateAuditRequest, FindingsResponse, Readiness } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Request failed");
  }

  return (await response.json()) as T;
}

export const api = {
  createAudit: (payload: CreateAuditRequest) =>
    request<Audit>("/api/audits", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAudit: (auditId: string) => request<Audit>(`/api/audits/${auditId}`),
  getFindings: (auditId: string) => request<FindingsResponse>(`/api/audits/${auditId}/findings`),
  getReadiness: () => request<Readiness>("/api/readiness"),
  getReportUrl: (auditId: string) => `${API_BASE_URL}/api/audits/${auditId}/report`,
  getAudits: (params?: { status?: string; url_contains?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.append("status", params.status);
    if (params?.url_contains) searchParams.append("url_contains", params.url_contains);
    const query = searchParams.toString();
    return request<Audit[]>(`/api/audits${query ? `?${query}` : ""}`);
  },
};
