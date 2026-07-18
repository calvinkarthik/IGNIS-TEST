export type HazardState =
  | "CLEAR"
  | "SUSPECTED"
  | "VERIFYING"
  | "CONFIRMED"
  | "VISUAL_SIGNATURE_LOST"
  | "RESOLVED"
  | "DEGRADED";

export type ResponseState =
  | "IDLE"
  | "AWAITING_RESPONSE"
  | "CANCELLED"
  | "ESCALATING"
  | "CALL_REQUESTED"
  | "CALL_INITIATED"
  | "CALL_CONNECTED"
  | "CALL_COMPLETED"
  | "CALL_FAILED";

export interface Box {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface Detection {
  class_name: "fire" | "smoke" | "occupant";
  class_id: number;
  confidence: number;
  bbox: Box;
}

export interface DetectionPacket {
  frame_sequence: number;
  monotonic_ns: number;
  inference_duration_ms: number;
  detections: Detection[];
}

export interface FramePacket {
  device_id: string;
  frame_sequence: number;
  width: number;
  height: number;
  jpeg_quality: number;
  monotonic_ns: number;
  source_mode?: string;
  jpeg_base64: string;
  receivedAt: number;
}

export interface Incident {
  incident_id: string;
  device_id: string;
  boot_id: string;
  hazard_state: HazardState;
  response_state: ResponseState;
  first_zone?: string;
  current_zone?: string;
  peak_fire_confidence: number;
  peak_smoke_confidence: number;
  max_growth_percent?: number | null;
  smoke_first?: boolean | null;
  smoke_to_fire_delay_seconds?: number | null;
  seconds_persistent: number;
  occupant_visible?: boolean | null;
  occupant_response?: string | null;
  call_status?: string | null;
  call_sid?: string | null;
  confirmed_at?: string | null;
  updated_at: string;
}

export interface TimelineEvent {
  id?: number;
  incident_id?: string;
  event_type: string;
  source: string;
  received_at?: string;
  payload?: Record<string, unknown>;
}

export interface Health {
  status?: string;
  qnx_connected?: boolean;
  camera?: string;
  inference?: string;
  incident_engine?: string;
  stream?: string;
  last_frame_age_ms?: number;
  last_inference_age_ms?: number;
  inference_latency_ms?: number;
  watchdog_restart_count?: number;
  source_mode?: string;
}

export interface Zone {
  id: string;
  name: string;
  points: [number, number][];
}

export interface ZoneConfiguration {
  schema_version: 1;
  configuration_version: number;
  frame_aspect_ratio: number;
  zones: Zone[];
}

export interface Snapshot {
  demo_system: true;
  demo_calls_enabled: boolean;
  devices: Array<{ device_id: string; connected: boolean; health?: Health }>;
  incidents: Incident[];
  latest_frame?: Omit<FramePacket, "receivedAt"> | null;
  latest_detections?: DetectionPacket | null;
  health?: Health;
  zones?: ZoneConfiguration;
}

export interface Envelope<T = unknown> {
  schema_version: 1;
  type: string;
  sent_at: string;
  data: T;
}

export interface IgnisState {
  connection: "CONNECTING" | "LIVE" | "RECONNECTING" | "OFFLINE";
  demoCallsEnabled: boolean;
  frame: FramePacket | null;
  detections: DetectionPacket | null;
  incidents: Incident[];
  events: TimelineEvent[];
  health: Health;
  zones: ZoneConfiguration | null;
  callUpdate: Record<string, unknown> | null;
}

