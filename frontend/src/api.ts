import type { Incident, TimelineEvent, ZoneConfiguration } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : `request_failed_${response.status}`;
    throw new Error(detail);
  }
  return body as T;
}

export const api = {
  health: () => request<Record<string, unknown>>("/api/health"),
  setArmed: (armed: boolean) =>
    request<{ armed: boolean }>("/api/arming", {
      method: "PUT",
      body: JSON.stringify({ armed }),
    }),
  incidents: () => request<Incident[]>("/api/incidents"),
  events: (incidentId: string) =>
    request<TimelineEvent[]>(`/api/incidents/${encodeURIComponent(incidentId)}/events`),
  zones: () => request<ZoneConfiguration>("/api/config/zones"),
  saveZones: (configuration: ZoneConfiguration) =>
    request<{ configuration: ZoneConfiguration; acknowledged: boolean }>("/api/config/zones", {
      method: "PUT",
      body: JSON.stringify(configuration),
    }),
  confirm: (incidentId: string, source: "manual" | "voice_agent" = "manual", note = "") =>
    request(`/api/incidents/${encodeURIComponent(incidentId)}/confirm`, {
      method: "POST",
      body: JSON.stringify({ source, note }),
    }),
  cancel: (
    incidentId: string,
    reason: "controlled_flame" | "false_alarm" | "testing" | "other",
    source: "manual" | "voice_agent" = "manual",
    note = "",
  ) =>
    request(`/api/incidents/${encodeURIComponent(incidentId)}/cancel`, {
      method: "POST",
      body: JSON.stringify({ source, reason, note }),
    }),
  reset: (incidentId: string) =>
    request(`/api/incidents/${encodeURIComponent(incidentId)}/reset`, {
      method: "POST",
      body: JSON.stringify({ source: "manual", note: "Operator reviewed incident" }),
    }),
  callDemo: (incidentId: string) =>
    request<Record<string, unknown>>(
      `/api/incidents/${encodeURIComponent(incidentId)}/call-demo-dispatch`,
      { method: "POST" },
    ),
  signedUrl: (incidentId: string) =>
    request<{ signed_url: string; context: Record<string, unknown> }>(
      `/api/voice/signed-url?incident_id=${encodeURIComponent(incidentId)}`,
    ),
  context: (incidentId: string) =>
    request<Record<string, unknown>>(`/api/incidents/${encodeURIComponent(incidentId)}/context`),
};

