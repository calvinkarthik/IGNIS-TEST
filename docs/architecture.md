# Architecture

IGNIS keeps authority close to the camera. Network or laptop loss must not prevent local visual verification.

```mermaid
flowchart LR
  subgraph QNX["QNX edge authority"]
    CAM["camera_service"] --> RING["bounded shared frame ring"]
    RING --> INF["inference_service"]
    INF --> ENG["incident_engine"]
    ENG --> EVID["local evidence + timeline"]
    ENG --> ALARM["alarm_service"]
    RING --> STREAM["stream_service"]
    ENG --> STREAM
    WATCH["watchdog_service"] -. heartbeats/restarts .-> CAM
    WATCH -. heartbeats/restarts .-> INF
    WATCH -. heartbeats/restarts .-> ENG
  end
  STREAM <--> |"authenticated framed TCP"| API["FastAPI coordination"]
  API --> DB["SQLite incidents/events/calls"]
  API <--> |"snapshot + WebSocket"| UI["React dashboard"]
  UI --> |"manual opt-in"| VOICE["ElevenLabs occupant agent"]
  API --> |"allowlisted demo only"| CALL["ElevenLabs + Twilio"]
```

## Authority boundaries

- QNX owns timestamps, inference, persistence, zones, incident creation, evidence, local alarm, and device health.
- FastAPI owns persistence on the laptop, browser broadcast, typed occupant actions, deterministic response timeout, call safety, and provider reconciliation.
- React renders authoritative state and submits requests. It never manufactures incident truth or call connection status.
- The voice agent communicates through typed backend tools only. It cannot change visual evidence or select a destination.

## Failure isolation

Each edge service is a separate executable. Frames use a bounded latest-frame ring; notifications and health use small messages. Streaming has lower priority than inference, and incident/event queues are distinct from replaceable video frames. The watchdog applies restart budgets and exposes degraded/recovered health.

## Modes

- `qnx`: guarded Sensor Framework and TFLite adapters, completed against the target's known-working vendor sample.
- `replay`: the same incident interfaces consume prerecorded/deterministic inputs.
- `simulator`: Python emits production packets to exercise the backend and frontend without edge hardware.

