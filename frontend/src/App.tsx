import { useEffect, useMemo, useState } from "react";
import { CameraStage } from "./components/CameraStage";
import { DemoBanner } from "./components/DemoBanner";
import { HealthStrip } from "./components/HealthStrip";
import { IncidentControls } from "./components/IncidentControls";
import { StatusPanel } from "./components/StatusPanel";
import { Timeline } from "./components/Timeline";
import { VoicePanel } from "./components/VoicePanel";
import { ZoneEditor } from "./components/ZoneEditor";
import { useIgnisSocket } from "./hooks/useIgnisSocket";
import type { ZoneConfiguration } from "./types";

function ResponseCountdown({ confirmedAt, active }: { confirmedAt?: string | null; active: boolean }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, []);
  if (!active || !confirmedAt) return <span>Standby</span>;
  const remaining = Math.max(0, 10 - (now - Date.parse(confirmedAt)) / 1_000);
  return <span>{remaining > 0 ? `${remaining.toFixed(1)} s` : "Backend validating eligibility"}</span>;
}

export default function App() {
  const { state, refreshEvents } = useIgnisSocket();
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [localZones, setLocalZones] = useState<ZoneConfiguration | null>(null);
  const incident = useMemo(
    () =>
      state.incidents.find((item) => item.incident_id === selectedIncidentId) ??
      state.incidents[0] ??
      null,
    [selectedIncidentId, state.incidents],
  );

  useEffect(() => {
    if (state.zones) setLocalZones(state.zones);
  }, [state.zones]);

  useEffect(() => {
    if (incident) void refreshEvents(incident.incident_id);
  }, [incident?.incident_id]);

  const awaitingResponse = incident?.response_state === "AWAITING_RESPONSE";
  return (
    <div className="app-shell">
      <DemoBanner callsEnabled={state.demoCallsEnabled} />
      <header className="main-header">
        <div className="brand-block">
          <div className="ignis-mark"><span>I</span></div>
          <div><h1>IGNIS</h1><p>Visual incident intelligence</p></div>
        </div>
        <div className="header-center">
          <span className="eyebrow">Edge authority</span>
          <strong>QNX sees and decides</strong>
        </div>
        <div className={`connection-pill ${state.connection.toLowerCase()}`}>
          <span />{state.connection}
        </div>
      </header>

      <HealthStrip health={state.health} connection={state.connection} />

      <main>
        <section className="primary-grid">
          <div className="camera-column">
            <div className="panel-heading camera-heading">
              <div><span className="section-kicker">Observed evidence</span><h2>Live camera</h2></div>
              <div className="camera-actions">
                <ZoneEditor configuration={localZones} onSaved={setLocalZones} />
                <span className="stream-meta">640 × 480 · bounded stream</span>
              </div>
            </div>
            <CameraStage frame={state.frame} detections={state.detections} zones={localZones} />
            <div className="camera-caption">
              <span>Bounding boxes and zones are normalized to the source image—not the outer panel.</span>
              <span>{state.detections?.inference_duration_ms?.toFixed(1) ?? "—"} ms inference</span>
            </div>
          </div>
          <StatusPanel incident={incident} />
        </section>

        <section className="response-ribbon">
          <div><span className="section-kicker">Deterministic response timer</span><strong><ResponseCountdown confirmedAt={incident?.confirmed_at} active={awaitingResponse} /></strong></div>
          <p>
            {awaitingResponse
              ? "Awaiting a clear occupant response. Timeout is enforced by FastAPI, not by the voice model."
              : "Escalation begins only after sustained visual confirmation and server-side eligibility checks."}
          </p>
          <div className="call-truth">
            <span>Call state</span>
            <strong>{String(state.callUpdate?.status ?? incident?.call_status ?? "NO REQUEST")}</strong>
            <small>{incident?.call_status === "INITIATED" ? "Connection unknown" : "Provider evidence required"}</small>
          </div>
        </section>

        <VoicePanel incident={incident} />

        <section className="lower-grid">
          <Timeline events={state.events} />
          <aside className="history-panel">
            <div className="panel-heading"><div><span className="section-kicker">SQLite record</span><h2>Incident history</h2></div><span>{state.incidents.length}</span></div>
            {state.incidents.length === 0 ? (
              <p className="empty-copy">No incidents have been received from the Pi.</p>
            ) : (
              <div className="history-list">
                {state.incidents.slice(0, 5).map((item) => (
                  <button
                    key={item.incident_id}
                    className={item.incident_id === incident?.incident_id ? "active" : ""}
                    onClick={() => setSelectedIncidentId(item.incident_id)}
                  >
                    <span>{item.hazard_state.replaceAll("_", " ")}</span>
                    <strong>{item.first_zone ?? "Unconfigured area"}</strong>
                    <small>{new Date(item.updated_at).toLocaleString()}</small>
                  </button>
                ))}
              </div>
            )}
          </aside>
        </section>

        <IncidentControls incident={incident} callsEnabled={state.demoCallsEnabled} />
      </main>

      <footer>
        <span>IGNIS PROTOTYPE · VISUAL OBSERVATIONS ARE NOT CERTAINTY</span>
        <span>Never replaces certified alarms or normal emergency procedures</span>
      </footer>
    </div>
  );
}

