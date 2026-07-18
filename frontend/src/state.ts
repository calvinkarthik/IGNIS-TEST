import type {
  DetectionPacket,
  Envelope,
  FramePacket,
  Health,
  IgnisState,
  Incident,
  Snapshot,
  TimelineEvent,
  ZoneConfiguration,
} from "./types";

export const initialState: IgnisState = {
  connection: "CONNECTING",
  demoCallsEnabled: false,
  frame: null,
  detections: null,
  incidents: [],
  events: [],
  health: {},
  zones: null,
  callUpdate: null,
};

export type Action =
  | { type: "CONNECTION"; value: IgnisState["connection"] }
  | { type: "MESSAGE"; envelope: Envelope }
  | { type: "EVENTS"; events: TimelineEvent[] };

function replaceIncident(incidents: Incident[], update: Incident): Incident[] {
  return [update, ...incidents.filter((incident) => incident.incident_id !== update.incident_id)].sort(
    (left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at),
  );
}

export function reducer(state: IgnisState, action: Action): IgnisState {
  if (action.type === "CONNECTION") return { ...state, connection: action.value };
  if (action.type === "EVENTS") return { ...state, events: action.events.slice(-100) };
  const { type, data } = action.envelope;
  switch (type) {
    case "system_snapshot": {
      const snapshot = data as Snapshot;
      return {
        ...state,
        connection: "LIVE",
        demoCallsEnabled: snapshot.demo_calls_enabled,
        frame: snapshot.latest_frame
          ? { ...snapshot.latest_frame, receivedAt: Date.now() }
          : state.frame,
        detections: snapshot.latest_detections ?? state.detections,
        incidents: snapshot.incidents,
        health: {
          ...(snapshot.health ?? {}),
          qnx_connected: snapshot.devices.some((device) => device.connected),
        },
        zones: snapshot.zones ?? state.zones,
      };
    }
    case "frame":
      return { ...state, frame: { ...(data as Omit<FramePacket, "receivedAt">), receivedAt: Date.now() } };
    case "detections":
      return { ...state, detections: data as DetectionPacket };
    case "incident_update":
      return { ...state, incidents: replaceIncident(state.incidents, data as Incident) };
    case "timeline_event":
      return { ...state, events: [...state.events, data as TimelineEvent].slice(-100) };
    case "health_update":
      return { ...state, health: { ...state.health, ...(data as Health) } };
    case "call_update":
      return { ...state, callUpdate: data as Record<string, unknown> };
    case "configuration_update": {
      const update = data as { configuration?: ZoneConfiguration };
      return { ...state, zones: update.configuration ?? state.zones };
    }
    default:
      return state;
  }
}

