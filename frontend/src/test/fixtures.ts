import type { Incident } from "../types";

export const confirmedIncident: Incident = {
  incident_id: "ignis-qnxpi-01-boot-1",
  device_id: "ignis-qnxpi-01",
  boot_id: "boot",
  hazard_state: "CONFIRMED",
  response_state: "AWAITING_RESPONSE",
  first_zone: "Stovetop",
  current_zone: "Stovetop",
  peak_fire_confidence: 0.91,
  peak_smoke_confidence: 0.76,
  max_growth_percent: 38,
  smoke_first: true,
  smoke_to_fire_delay_seconds: 4.1,
  seconds_persistent: 8.2,
  confirmed_at: "2026-07-18T12:00:00Z",
  updated_at: "2026-07-18T12:00:08Z",
  call_status: null,
};

